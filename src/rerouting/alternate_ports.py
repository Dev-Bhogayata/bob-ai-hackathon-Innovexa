"""Explainable alternate-port ranking for delayed vessels."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

DISTANCE_WEIGHT = 0.60
CAPACITY_WEIGHT = 0.40


def _positive_number(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be numeric") from error
    if number < 0:
        raise ValueError(f"{field} must be non-negative")
    return number


def rank_alternate_ports(
    vessel: Mapping[str, Any],
    predicted_delay_hours: float,
    delay_threshold_hours: float,
    alternate_ports: Sequence[Mapping[str, Any]],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Rank feasible alternate ports for a vessel with excessive delay.

    Each port must provide ``port_id``, ``distance_km``, and
    ``estimated_available_teu``. Ports unable to accommodate the vessel's
    ``teu_capacity`` are excluded. Scores are transparent: 60% inverse
    distance and 40% capacity adequacy. The result includes the components so
    operators can explain every recommendation.
    """
    predicted_delay_hours = _positive_number(
        predicted_delay_hours, "predicted_delay_hours"
    )
    delay_threshold_hours = _positive_number(
        delay_threshold_hours, "delay_threshold_hours"
    )
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if predicted_delay_hours <= delay_threshold_hours:
        return []

    vessel_teu = _positive_number(vessel.get("teu_capacity"), "teu_capacity")
    candidates: list[dict[str, Any]] = []
    for port in alternate_ports:
        port_id = str(port.get("port_id", "")).strip()
        if not port_id:
            raise ValueError("each alternate port must have a port_id")
        distance_km = _positive_number(port.get("distance_km"), "distance_km")
        available_teu = _positive_number(
            port.get("estimated_available_teu"), "estimated_available_teu"
        )
        if available_teu < vessel_teu:
            continue
        candidates.append(
            {
                "port_id": port_id,
                "port_name": port.get("port_name", port_id),
                "distance_km": distance_km,
                "estimated_available_teu": available_teu,
            }
        )

    if not candidates:
        return []
    max_distance = max(candidate["distance_km"] for candidate in candidates)
    for candidate in candidates:
        distance_score = (
            1.0
            if max_distance == 0
            else 1 - candidate["distance_km"] / max_distance
        )
        capacity_score = min(
            1.0, candidate["estimated_available_teu"] / vessel_teu
        )
        candidate["distance_score"] = round(distance_score, 3)
        candidate["capacity_score"] = round(capacity_score, 3)
        candidate["score"] = round(
            100
            * (
                DISTANCE_WEIGHT * distance_score
                + CAPACITY_WEIGHT * capacity_score
            ),
            1,
        )
        candidate["reason"] = (
            f"{candidate['distance_km']:.0f} km away with "
            f"{candidate['estimated_available_teu']:.0f} TEU available"
        )

    return sorted(
        candidates,
        key=lambda candidate: (
            -candidate["score"],
            candidate["distance_km"],
            candidate["port_id"],
        ),
    )[:limit]
