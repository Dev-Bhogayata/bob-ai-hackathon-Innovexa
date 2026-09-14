"""Operations visualization endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.data.generate_data import generate_dataset
from src.scoring.berth_scoring import score_berths
from src.optimization.berth_assignment import optimize_berth_assignments
from src.optimization.resource_allocation import allocate_cranes, allocate_yard_zones
from src.llm.shift_summary import build_shift_supervisor_prompt
from src.llm.watsonx import generate_watsonx_summary

from src.backend.app.schemas.operations import (
    HotspotFactor,
    HotspotItem,
    HotspotResponse,
    TimelineItem,
    TimelineResponse,
    SupervisorSummaryRequest,
    SupervisorSummaryResponse,
    TimelineRequest,
    HotspotRequest,
)

router = APIRouter(prefix="/api/v1", tags=["operations"])


def _parse_datetime(value: str | None, default: datetime) -> datetime:
    if value is None:
        return default
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="start must be ISO-8601") from error
    if parsed.tzinfo is None:
        raise HTTPException(status_code=400, detail="start must include a timezone")
    return parsed


def _dataset(seed: int) -> dict[str, list[dict[str, Any]]]:
    return generate_dataset(seed)


def _build_timeline(
    window_start: datetime,
    window_end: datetime,
    dataset: dict[str, list[dict[str, Any]]],
    *,
    apply_shocks: bool = False,
) -> TimelineResponse:
    """Run the shared optimizer pipeline for generated or live scenario data."""
    vessels = [
        vessel
        for vessel in dataset["vessels"]
        if datetime.fromisoformat(str(vessel["etd"])) > window_start
        and datetime.fromisoformat(str(vessel["eta"])) < window_end
    ]
    berths = [dict(berth) for berth in dataset["berths"]]
    # A shock is deliberately applied conservatively to the planning window.
    # The optimizer is not time-dependent, so reducing berth capacity for any
    # overlapping shock avoids promising unavailable crane capacity.
    for berth in berths:
        reductions = [
            float(shock.get("capacity_reduction_pct", 0))
            for shock in dataset.get("shocks", [])
            if apply_shocks
            and datetime.fromisoformat(str(shock["start_time"])) < window_end
            and datetime.fromisoformat(str(shock["end_time"])) > window_start
        ]
        if reductions:
            berth["assigned_crane_count"] = max(
                1,
                int(berth["assigned_crane_count"] * max(0.0, 1 - max(reductions) / 100)),
            )
    if not vessels:
        return TimelineResponse(
            window_start=window_start,
            window_end=window_end,
            duration_hours=max(1, round((window_end - window_start).total_seconds() / 3600)),
            berths=[berth["berth_id"] for berth in berths],
            items=[],
        )
    try:
        assignments = optimize_berth_assignments(vessels, berths)
        yard_allocations = allocate_yard_zones(vessels, dataset["yard_zones"])
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=f"scenario cannot be scheduled: {error}") from error
    vessels_by_id = {str(vessel["vessel_id"]): vessel for vessel in vessels}
    berths_by_id = {str(berth["berth_id"]): berth for berth in berths}
    items = []
    for assignment in assignments:
        vessel = vessels_by_id[str(assignment["vessel_id"])]
        items.append(
            TimelineItem(
                **assignment,
                eta=datetime.fromisoformat(str(vessel["eta"])),
                etd=datetime.fromisoformat(str(vessel["etd"])),
                teu_capacity=int(vessel["teu_capacity"]),
                status="delayed" if assignment["wait_hours"] > 0 else "scheduled",
                crane_ids=allocate_cranes(vessel, berths_by_id[str(assignment["berth_id"])]),
                yard_zone_id=yard_allocations[str(assignment["vessel_id"])]["yard_zone_id"],
                yard_allocated_teu=yard_allocations[str(vessel["vessel_id"])]["allocated_teu"],
                yard_capacity_shortfall_teu=yard_allocations[str(vessel["vessel_id"])].get(
                    "capacity_shortfall_teu", 0
                ),
            )
        )
    return TimelineResponse(
        window_start=window_start,
        window_end=window_end,
        duration_hours=max(1, round((window_end - window_start).total_seconds() / 3600)),
        berths=[berth["berth_id"] for berth in berths],
        items=[
            item for item in items
            if item.scheduled_start < window_end and item.scheduled_end > window_start
        ],
    )


@router.get("/timeline", response_model=TimelineResponse)
def get_timeline(
    start: str | None = Query(default=None, description="ISO-8601 window start"),
    seed: int = Query(default=42, ge=0),
) -> TimelineResponse:
    """Return berth intervals for the next 72 hours."""
    dataset = _dataset(seed)
    first_eta = min(datetime.fromisoformat(row["eta"]) for row in dataset["vessels"])
    window_start = _parse_datetime(start, first_eta)
    window_end = window_start + timedelta(hours=72)
    return _build_timeline(window_start, window_end, dataset)


@router.post("/timeline", response_model=TimelineResponse)
def post_timeline(request: TimelineRequest) -> TimelineResponse:
    """Schedule a caller-provided live scenario for an explicit time window."""
    dataset = {
        "vessels": [vessel.model_dump(mode="json") for vessel in request.scenario.vessels],
        "berths": [berth.model_dump(mode="json") for berth in request.scenario.berths],
        "yard_zones": [zone.model_dump(mode="json") for zone in request.scenario.yard_zones],
        "shocks": [shock.model_dump(mode="json") for shock in request.scenario.shocks],
    }
    return _build_timeline(request.window_start, request.window_end, dataset, apply_shocks=True)


@router.get("/hotspots", response_model=HotspotResponse)
def get_hotspots(
    as_of: str | None = Query(default=None, description="ISO-8601 observation time"),
    horizon_hours: int = Query(default=24, ge=1, le=72),
    seed: int = Query(default=42, ge=0),
) -> HotspotResponse:
    """Return berth and yard pressure scores for the heatmap."""
    dataset = _dataset(seed)
    first_eta = min(datetime.fromisoformat(row["eta"]) for row in dataset["vessels"])
    observation_time = _parse_datetime(as_of, first_eta)
    return _build_hotspots(dataset, observation_time, horizon_hours)


def _build_hotspots(
    dataset: dict[str, list[dict[str, Any]]],
    observation_time: datetime,
    horizon_hours: int,
) -> HotspotResponse:
    berth_scores = score_berths(
        dataset["berths"],
        dataset["vessels"],
        dataset["yard_zones"],
        as_of=observation_time,
        horizon_hours=horizon_hours,
    )
    items: list[HotspotItem] = []
    for berth in berth_scores:
        pressure_score = round(100 - berth["score"], 1)
        risk_level = "high" if pressure_score >= 70 else "medium" if pressure_score >= 40 else "low"
        items.append(
            HotspotItem(
                resource_id=berth["berth_id"],
                resource_type="berth",
                label=berth["berth_name"],
                score=pressure_score,
                risk_level=risk_level,
                factors=[
                    HotspotFactor(name="incoming_teu", value=berth["incoming_teu"], unit="TEU"),
                    HotspotFactor(name="occupied_vessels", value=berth["occupied_vessel_count"], unit="vessels"),
                    HotspotFactor(name="yard_fill", value=berth["yard_fill_pressure"] * 100, unit="percent"),
                ],
                recommended_action=(
                    "Review berth sequence and prioritize high-risk arrivals"
                    if risk_level != "low"
                    else "No immediate berth intervention required"
                ),
            )
        )
    for zone in dataset["yard_zones"]:
        fill = float(zone["current_fill_pct"])
        risk_level = "high" if fill >= 80 else "medium" if fill >= 60 else "low"
        items.append(
            HotspotItem(
                resource_id=zone["zone_id"],
                resource_type="yard",
                label=zone["zone_name"],
                score=fill,
                risk_level=risk_level,
                factors=[
                    HotspotFactor(name="fill", value=fill, unit="percent"),
                    HotspotFactor(name="capacity", value=float(zone["capacity_teu"]), unit="TEU"),
                ],
                recommended_action=(
                    "Prioritize yard moves and protect remaining capacity"
                    if risk_level != "low"
                    else "Continue normal yard monitoring"
                ),
            )
        )
    return HotspotResponse(
        as_of=observation_time,
        horizon_hours=horizon_hours,
        items=sorted(items, key=lambda item: item.score, reverse=True),
    )


@router.post("/hotspots", response_model=HotspotResponse)
def post_hotspots(request: HotspotRequest) -> HotspotResponse:
    """Score hotspots for a caller-provided live scenario."""
    dataset = {
        "vessels": [vessel.model_dump(mode="json") for vessel in request.scenario.vessels],
        "berths": [berth.model_dump(mode="json") for berth in request.scenario.berths],
        "yard_zones": [zone.model_dump(mode="json") for zone in request.scenario.yard_zones],
    }
    return _build_hotspots(dataset, request.as_of, request.horizon_hours)


@router.post("/supervisor-summary", response_model=SupervisorSummaryResponse)
def supervisor_summary(request: SupervisorSummaryRequest) -> SupervisorSummaryResponse:
    """Create a supervisor briefing locally or through IBM watsonx.ai."""
    payload = [
        {"kind": "assignment", **item} for item in request.assignments
    ] + [
        {"kind": "prediction", **item} for item in request.predictions
    ] + [
        {"kind": "route_recommendation", "vessel_id": vessel_id, "options": options}
        for vessel_id, options in request.route_recommendations.items()
    ]
    messages = build_shift_supervisor_prompt(payload)
    if not request.live:
        return SupervisorSummaryResponse(mode="prompt", messages=messages)
    try:
        summary = generate_watsonx_summary(messages)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return SupervisorSummaryResponse(
        mode="watsonx",
        messages=messages,
        summary=summary,
    )
