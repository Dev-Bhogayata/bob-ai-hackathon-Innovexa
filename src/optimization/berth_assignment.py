"""CP-SAT berth assignment optimizer.

The model assigns every vessel to one compatible berth and chooses a start
time at or after its ETA. Vessels sharing a berth cannot overlap. The
objective minimizes weighted waiting time, with higher-priority vessels
receiving a larger penalty for delay.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence

from ortools.sat.python import cp_model

PRIORITY_WEIGHT = {"standard": 1, "priority": 2, "critical": 4}
TIME_SCALE = 60  # CP-SAT time units are minutes.


def _time(value: Any) -> datetime:
    return datetime.fromisoformat(str(value))


def _minutes(value: datetime, origin: datetime) -> int:
    return round((value - origin).total_seconds() / TIME_SCALE)


def _number(vessel: Mapping[str, Any], key: str, default: float) -> float:
    try:
        return float(vessel.get(key, default))
    except (TypeError, ValueError) as error:
        raise ValueError(f"{key} must be numeric") from error


def optimize_berth_assignments(
    vessels: Sequence[Mapping[str, Any]],
    berths: Sequence[Mapping[str, Any]],
    *,
    solver_time_limit_seconds: float = 10.0,
) -> list[dict[str, Any]]:
    """Return one feasible berth assignment and schedule per vessel."""
    if not vessels:
        return []
    if not berths:
        raise ValueError("berths must not be empty")
    if solver_time_limit_seconds <= 0:
        raise ValueError("solver_time_limit_seconds must be positive")

    origin = min(_time(vessel["eta"]) for vessel in vessels)
    model = cp_model.CpModel()
    assignments: dict[tuple[int, int], cp_model.IntVar] = {}
    starts: dict[tuple[int, int], cp_model.IntVar] = {}
    ends: dict[tuple[int, int], cp_model.IntVar] = {}
    intervals: dict[tuple[int, int], cp_model.IntervalVar] = {}
    waits: dict[int, cp_model.IntVar] = {}
    compatible_options: dict[int, list[int]] = {}

    max_end = max(_minutes(_time(vessel["etd"]), origin) for vessel in vessels)
    for vessel_index, vessel in enumerate(vessels):
        eta = _minutes(_time(vessel["eta"]), origin)
        duration = _minutes(_time(vessel["etd"]), _time(vessel["eta"]))
        if duration <= 0:
            raise ValueError(f"vessel {vessel.get('vessel_id', vessel_index)} has non-positive service duration")
        options: list[int] = []
        for berth_index, berth in enumerate(berths):
            compatible = (
                _number(vessel, "vessel_length_m", 0) <= _number(berth, "max_vessel_length_m", float("inf"))
                and _number(vessel, "draft_m", 0) <= _number(berth, "min_depth_m", float("inf"))
                and _number(vessel, "required_cranes", 1) <= _number(berth, "assigned_crane_count", 0)
            )
            if not compatible:
                continue
            options.append(berth_index)
            key = (vessel_index, berth_index)
            assigned = model.NewBoolVar(f"assigned_{vessel_index}_{berth_index}")
            start = model.NewIntVar(eta, max_end + duration, f"start_{vessel_index}_{berth_index}")
            end = model.NewIntVar(eta + duration, max_end + 2 * duration, f"end_{vessel_index}_{berth_index}")
            interval = model.NewOptionalIntervalVar(start, duration, end, assigned, f"interval_{vessel_index}_{berth_index}")
            assignments[key], starts[key], ends[key], intervals[key] = assigned, start, end, interval
        if not options:
            raise ValueError(f"vessel {vessel.get('vessel_id', vessel_index)} has no compatible berth")
        compatible_options[vessel_index] = options
        model.Add(sum(assignments[(vessel_index, berth_index)] for berth_index in options) == 1)
        wait = model.NewIntVar(0, max_end + duration, f"wait_{vessel_index}")
        waits[vessel_index] = wait
        for berth_index in options:
            model.Add(wait == starts[(vessel_index, berth_index)] - eta).OnlyEnforceIf(assignments[(vessel_index, berth_index)])

    for berth_index in range(len(berths)):
        berth_intervals = [
            intervals[(vessel_index, berth_index)]
            for vessel_index in range(len(vessels))
            if berth_index in compatible_options[vessel_index]
        ]
        model.AddNoOverlap(berth_intervals)

    model.Minimize(
        sum(
            PRIORITY_WEIGHT.get(str(vessel.get("priority", "standard")), 1) * waits[index]
            for index, vessel in enumerate(vessels)
        )
    )
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = solver_time_limit_seconds
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"berth assignment solver failed with status {solver.StatusName(status)}")

    results: list[dict[str, Any]] = []
    for vessel_index, vessel in enumerate(vessels):
        berth_index = next(
            option
            for option in compatible_options[vessel_index]
            if solver.Value(assignments[(vessel_index, option)])
        )
        start = solver.Value(starts[(vessel_index, berth_index)])
        end = solver.Value(ends[(vessel_index, berth_index)])
        berth = berths[berth_index]
        results.append(
            {
                "vessel_id": vessel.get("vessel_id", f"V-{vessel_index + 1:03d}"),
                "berth_id": berth.get("berth_id", f"B-{berth_index + 1:02d}"),
                "scheduled_start": (origin + timedelta(minutes=start)).isoformat(timespec="minutes"),
                "scheduled_end": (origin + timedelta(minutes=end)).isoformat(timespec="minutes"),
                "wait_hours": round(solver.Value(waits[vessel_index]) / 60, 2),
                "priority": vessel.get("priority", "standard"),
            }
        )
    return results
