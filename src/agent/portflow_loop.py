"""Single-agent PortFlow decision loop.

The loop exposes four ordinary Python callables as tools:

    predict -> optimize -> route -> summarize

Each tool emits a structured trace event. The summarize step creates the
provider-neutral LLM messages from the optimizer JSON; an application can send
those messages to its selected LLM provider without changing the loop.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from src.llm.shift_summary import build_shift_supervisor_prompt
from src.optimization.berth_assignment import optimize_berth_assignments
from src.rerouting.alternate_ports import rank_alternate_ports

LOGGER = logging.getLogger("portflow.agent")


@dataclass
class TraceEvent:
    step: str
    status: str
    input_summary: dict[str, Any]
    output_summary: dict[str, Any]
    rationale: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "step": self.step,
            "status": self.status,
            "input": self.input_summary,
            "output": self.output_summary,
            "rationale": self.rationale,
        }


class JsonlTraceHandler(logging.Handler):
    """Write one machine-readable reasoning event per line."""

    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:
        event = getattr(record, "trace_event", None)
        if event is None:
            return
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")


def configure_trace_logging(path: Path) -> JsonlTraceHandler:
    """Attach a JSONL trace handler to the PortFlow agent logger."""
    handler = JsonlTraceHandler(path)
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    return handler


def _emit(event: TraceEvent, trace: list[dict[str, Any]]) -> None:
    serialized = event.as_dict()
    trace.append(serialized)
    LOGGER.info(event.step, extra={"trace_event": serialized})


def predict(
    vessels: Sequence[Mapping[str, Any]],
    *,
    predictor: Callable[[Mapping[str, Any]], float] | None = None,
    default_delay_hours: float = 0.0,
) -> list[dict[str, Any]]:
    """Predict delay per vessel using an injected model or explicit fallback.

    Inject a trained-model callable in production. The fallback is intentionally
    simple and visible for demos that have not loaded an artifact yet.
    """
    if default_delay_hours < 0:
        raise ValueError("default_delay_hours must be non-negative")
    predictions = []
    for vessel in vessels:
        delay = (
            predictor(vessel)
            if predictor is not None
            else default_delay_hours
        )
        if delay < 0:
            raise ValueError("predictor returned a negative delay")
        predictions.append(
            {
                "vessel_id": vessel.get("vessel_id"),
                "predicted_delay_hours": round(float(delay), 2),
            }
        )
    return predictions


def optimize(
    vessels: Sequence[Mapping[str, Any]],
    berths: Sequence[Mapping[str, Any]],
    *,
    solver_time_limit_seconds: float = 10.0,
) -> list[dict[str, Any]]:
    """Call the berth optimizer tool."""
    return optimize_berth_assignments(
        vessels, berths, solver_time_limit_seconds=solver_time_limit_seconds
    )


def route(
    vessels: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
    alternate_ports: Sequence[Mapping[str, Any]],
    *,
    delay_threshold_hours: float,
    limit: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    """Call the alternate-port tool only for vessels above the threshold."""
    vessels_by_id = {str(vessel["vessel_id"]): vessel for vessel in vessels}
    recommendations: dict[str, list[dict[str, Any]]] = {}
    for prediction in predictions:
        vessel_id = str(prediction["vessel_id"])
        vessel = vessels_by_id[vessel_id]
        options = rank_alternate_ports(
            vessel,
            prediction["predicted_delay_hours"],
            delay_threshold_hours,
            alternate_ports,
            limit=limit,
        )
        if options:
            recommendations[vessel_id] = options
    return recommendations


def summarize(
    optimizer_output: Sequence[Mapping[str, Any]],
    *,
    predictions: Sequence[Mapping[str, Any]] = (),
    route_recommendations: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> list[dict[str, str]]:
    """Create LLM messages containing optimizer and decision context."""
    context = [dict(row) for row in optimizer_output]
    prediction_by_id = {str(row["vessel_id"]): row for row in predictions}
    routes = route_recommendations or {}
    for row in context:
        vessel_id = str(row["vessel_id"])
        row["predicted_delay_hours"] = prediction_by_id.get(
            vessel_id, {}
        ).get("predicted_delay_hours")
        row["alternate_port_options"] = list(routes.get(vessel_id, []))
    return build_shift_supervisor_prompt(context)


TOOLS: dict[str, Callable[..., Any]] = {
    "predict": predict,
    "optimize": optimize,
    "route": route,
    "summarize": summarize,
}


def run_portflow_loop(
    vessels: Sequence[Mapping[str, Any]],
    berths: Sequence[Mapping[str, Any]],
    alternate_ports: Sequence[Mapping[str, Any]],
    *,
    predictor: Callable[[Mapping[str, Any]], float] | None = None,
    default_delay_hours: float = 0.0,
    delay_threshold_hours: float = 6.0,
    solver_time_limit_seconds: float = 10.0,
    trace_path: Path | None = None,
) -> dict[str, Any]:
    """Run predict -> optimize -> route -> summarize and return all artifacts."""
    trace: list[dict[str, Any]] = []
    handler = configure_trace_logging(trace_path) if trace_path else None
    try:
        predictions = predict(
            vessels, predictor=predictor, default_delay_hours=default_delay_hours
        )
        _emit(
            TraceEvent(
                "predict",
                "completed",
                {"vessel_count": len(vessels)},
                {"prediction_count": len(predictions), "above_threshold": sum(
                    row["predicted_delay_hours"] > delay_threshold_hours
                    for row in predictions
                )},
                "Predicted delay for every vessel before operational decisions.",
            ),
            trace,
        )
        assignments = optimize(
            vessels, berths, solver_time_limit_seconds=solver_time_limit_seconds
        )
        _emit(
            TraceEvent(
                "optimize",
                "completed",
                {"vessel_count": len(vessels), "berth_count": len(berths)},
                {"assignment_count": len(assignments), "total_wait_hours": round(
                    sum(row["wait_hours"] for row in assignments), 2
                )},
                "Assigned compatible berths and removed schedule overlaps while minimizing weighted wait.",
            ),
            trace,
        )
        recommendations = route(
            vessels,
            predictions,
            alternate_ports,
            delay_threshold_hours=delay_threshold_hours,
        )
        _emit(
            TraceEvent(
                "route",
                "completed",
                {"delay_threshold_hours": delay_threshold_hours},
                {"vessels_rerouted": len(recommendations), "recommendation_count": sum(
                    len(options) for options in recommendations.values()
                )},
                "Ranked alternate ports only for vessels above the delay threshold and with sufficient capacity.",
            ),
            trace,
        )
        messages = summarize(
            assignments,
            predictions=predictions,
            route_recommendations=recommendations,
        )
        _emit(
            TraceEvent(
                "summarize",
                "completed",
                {"assignment_count": len(assignments), "rerouted_vessel_count": len(recommendations)},
                {"message_count": len(messages), "format": "provider-neutral chat messages"},
                "Converted structured decisions into a supervisor-readable LLM briefing request.",
            ),
            trace,
        )
        return {
            "predictions": predictions,
            "assignments": assignments,
            "route_recommendations": recommendations,
            "summary_messages": messages,
            "trace": trace,
        }
    finally:
        if handler is not None:
            LOGGER.removeHandler(handler)
            handler.close()
