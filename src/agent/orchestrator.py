"""Time-window orchestration for the PortFlow decision pipeline.

The orchestration contract is intentionally small and JSON-friendly:

    predict_congestion -> optimize_berths (when a hotspot is present)
    -> recommend_routing (when delay exceeds 12 hours) -> generate_plan

The four functions are kept as separate callables so an API layer can replace
them with model-backed implementations without changing the pipeline.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any, Callable, Mapping, Sequence

from src.agent.portflow_loop import optimize as optimize_berths
from src.agent.portflow_loop import route as recommend_routing
from src.agent.portflow_loop import summarize as generate_plan
from src.agent.portflow_loop import predict as predict_congestion

LOGGER = logging.getLogger("portflow.orchestrator")
DELAY_THRESHOLD_HOURS = 12.0
HOTSPOT_THRESHOLD = 70.0


def _json_size(value: Any) -> int:
    """Return the UTF-8 JSON size of a step result."""
    return len(json.dumps(value, ensure_ascii=True, default=str).encode("utf-8"))


def _parse_window(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("time window values must be ISO-8601 timestamps") from error


def _log_step(
    step: str,
    started_at: float,
    output: Any,
    *,
    skipped: bool = False,
) -> None:
    LOGGER.info(
        "orchestrator_step",
        extra={
            "step": step,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            "output_size_bytes": _json_size(output),
            "skipped": skipped,
        },
    )


def orchestrate(
    *,
    window_start: datetime | str,
    window_end: datetime | str,
    vessels: Sequence[Mapping[str, Any]],
    berths: Sequence[Mapping[str, Any]],
    alternate_ports: Sequence[Mapping[str, Any]],
    predictor: Callable[[Mapping[str, Any]], float] | None = None,
    predict_congestion_fn: Callable[..., Any] = predict_congestion,
    optimize_berths_fn: Callable[..., Any] = optimize_berths,
    recommend_routing_fn: Callable[..., Any] = recommend_routing,
    generate_plan_fn: Callable[..., Any] = generate_plan,
) -> dict[str, Any]:
    """Run the conditional PortFlow pipeline for an inclusive time window.

    The congestion predictor is expected to return either vessel predictions
    (the existing default) or a mapping with ``predictions`` and ``hotspots``.
    Hotspots may be supplied as ``{"score": 75}`` or as a numeric score.
    """
    start = _parse_window(window_start)
    end = _parse_window(window_end)
    if end <= start:
        raise ValueError("window_end must be after window_start")

    step_started = time.perf_counter()
    congestion_result = predict_congestion_fn(vessels, predictor=predictor)
    _log_step("predict_congestion", step_started, congestion_result)

    if isinstance(congestion_result, Mapping):
        predictions = list(congestion_result.get("predictions", []))
        hotspots = list(congestion_result.get("hotspots", []))
    else:
        predictions = list(congestion_result)
        hotspots = []
    hotspot_scores = [
        float(hotspot.get("score", 0) if isinstance(hotspot, Mapping) else hotspot)
        for hotspot in hotspots
    ]
    optimization_required = any(score > HOTSPOT_THRESHOLD for score in hotspot_scores)

    step_started = time.perf_counter()
    optimization_result: Any = []
    if optimization_required:
        optimization_result = optimize_berths_fn(vessels, berths)
    _log_step(
        "optimize_berths",
        step_started,
        optimization_result,
        skipped=not optimization_required,
    )

    delayed_predictions = [
        prediction
        for prediction in predictions
        if float(prediction.get("predicted_delay_hours", 0)) > DELAY_THRESHOLD_HOURS
    ]
    step_started = time.perf_counter()
    routing_result: Any = {}
    if delayed_predictions:
        routing_result = recommend_routing_fn(
            vessels,
            delayed_predictions,
            alternate_ports,
            delay_threshold_hours=DELAY_THRESHOLD_HOURS,
        )
    _log_step(
        "recommend_routing",
        step_started,
        routing_result,
        skipped=not delayed_predictions,
    )

    step_started = time.perf_counter()
    plan_messages = generate_plan_fn(
        optimization_result,
        predictions=predictions,
        route_recommendations=routing_result,
    )
    _log_step("generate_plan", step_started, plan_messages)

    return {
        "window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "congestion": congestion_result,
        "optimization": optimization_result,
        "routing": routing_result,
        "plan": plan_messages,
        "decisions": {
            "hotspot_threshold": HOTSPOT_THRESHOLD,
            "delay_threshold_hours": DELAY_THRESHOLD_HOURS,
            "optimization_called": optimization_required,
            "routing_called": bool(delayed_predictions),
        },
    }


run_pipeline = orchestrate
