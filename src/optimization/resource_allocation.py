"""Explicit crane and yard allocation checks for live operations."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence


def allocate_cranes(
    vessel: Mapping[str, Any],
    berth: Mapping[str, Any],
) -> list[str]:
    required = int(vessel.get("required_cranes", 1))
    available = int(berth.get("assigned_crane_count", 0))
    if required < 1 or required > available:
        raise ValueError(f"{vessel.get('vessel_id')} requires unavailable cranes at {berth.get('berth_id')}")
    return [f"{berth['berth_id']}-CRANE-{index}" for index in range(1, required + 1)]


def allocate_yard_zones(
    vessels: Sequence[Mapping[str, Any]],
    yard_zones: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Fit vessel TEU into compatible remaining yard capacity, largest first."""
    remaining = {
        str(zone["zone_id"]): float(zone["capacity_teu"])
        * (1 - float(zone["current_fill_pct"]) / 100)
        for zone in yard_zones
    }
    by_type = {str(zone["zone_id"]): str(zone.get("cargo_type", "")) for zone in yard_zones}
    allocations: dict[str, dict[str, Any]] = {}
    for vessel in sorted(vessels, key=lambda row: float(row["teu_capacity"]), reverse=True):
        teu = float(vessel["teu_capacity"])
        cargo = str(vessel.get("cargo_type", ""))
        candidates = [
            zone_id for zone_id in remaining
            if not by_type[zone_id] or by_type[zone_id] == cargo
        ]
        if sum(remaining[zone_id] for zone_id in candidates) < teu:
            candidates = list(remaining)
        if sum(remaining[zone_id] for zone_id in candidates) < teu:
            allocations[str(vessel["vessel_id"])] = {
                "yard_zone_id": "UNALLOCATED",
                "allocated_teu": 0,
                "remaining_teu": round(sum(remaining.values()), 1),
                "capacity_shortfall_teu": teu - sum(remaining.values()),
            }
            continue
        zone_allocations: list[dict[str, Any]] = []
        for zone_id in sorted(candidates, key=lambda candidate: remaining[candidate], reverse=True):
            amount = min(teu, remaining[zone_id])
            if amount <= 0:
                continue
            remaining[zone_id] -= amount
            teu -= amount
            zone_allocations.append({"yard_zone_id": zone_id, "allocated_teu": amount})
            if teu <= 0:
                break
        allocations[str(vessel["vessel_id"])] = {
            "yard_zone_id": ",".join(item["yard_zone_id"] for item in zone_allocations),
            "allocated_teu": sum(item["allocated_teu"] for item in zone_allocations),
            "remaining_teu": round(sum(remaining.values()), 1),
            "capacity_shortfall_teu": 0,
        }
    return allocations
