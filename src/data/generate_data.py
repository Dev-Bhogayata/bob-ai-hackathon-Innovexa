"""Generate synthetic PortFlow data for local development and experiments.

The generator writes CSV files and a SQLite database containing the same
datasets. It intentionally uses only the Python standard library so it can be
run before the backend dependencies are installed:

    python src/data/generate_data.py

Use ``--seed`` to reproduce a dataset and ``--output-dir`` to choose where CSV
files and the SQLite database are written.
"""

from __future__ import annotations

import argparse
import csv
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

VESSEL_COUNT = 50
BERTH_COUNT = 8
YARD_ZONE_COUNT = 6
SIMULATION_DAYS = 30
DEFAULT_SEED = 42
START_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)

VESSEL_NAMES = (
    "Atlantic Trader",
    "Baltic Horizon",
    "Caspian Star",
    "Delta Meridian",
    "Eastern Pioneer",
    "Gulf Navigator",
    "Harbor Sentinel",
    "Indian Crest",
    "Jade Express",
    "Kite Runner",
)
CARGO_TYPES = ("containers", "reefer", "bulk", "vehicles", "project_cargo")
PRIORITIES = ("standard", "priority", "critical")
SHOCK_TYPES = ("storm", "equipment_breakdown")
SHOCK_DESCRIPTIONS = {
    "storm": "Severe weather reduces berth and yard handling capacity",
    "equipment_breakdown": "Critical handling equipment is unavailable",
}


def poisson(lam: float, rng: random.Random) -> int:
    """Draw a Poisson variate using Knuth's algorithm."""
    if lam < 0:
        raise ValueError("Poisson rate must be non-negative")
    if lam == 0:
        return 0

    threshold = 2.718281828459045 ** (-lam)
    product = 1.0
    count = 0
    while product > threshold:
        count += 1
        product *= rng.random()
    return count - 1


def isoformat(value: datetime) -> str:
    return value.isoformat(timespec="minutes")


def generate_shocks(
    rng: random.Random, start_time: datetime
) -> list[dict[str, Any]]:
    """Create non-overlapping shock events across the simulation horizon."""
    shocks: list[dict[str, Any]] = []
    current = start_time + timedelta(hours=rng.randint(24, 72))
    shock_id = 1
    while current < start_time + timedelta(days=SIMULATION_DAYS - 1):
        shock_type = rng.choice(SHOCK_TYPES)
        duration_hours = rng.randint(6, 18) if shock_type == "storm" else rng.randint(4, 12)
        severity = rng.choice(("moderate", "severe"))
        multiplier = 1.7 if severity == "moderate" else 2.4
        if shock_type == "equipment_breakdown":
            multiplier += 0.2
        shocks.append(
            {
                "shock_id": f"SHK-{shock_id:03d}",
                "shock_type": shock_type,
                "severity": severity,
                "start_time": isoformat(current),
                "end_time": isoformat(current + timedelta(hours=duration_hours)),
                "arrival_rate_multiplier": multiplier,
                "capacity_reduction_pct": 20 if severity == "moderate" else 40,
                "description": SHOCK_DESCRIPTIONS[shock_type],
            }
        )
        shock_id += 1
        current += timedelta(hours=rng.randint(72, 144))
    return shocks


def generate_vessels(
    rng: random.Random,
    start_time: datetime,
    berths: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    berth_limits = berths or [
        {
            "max_vessel_length_m": 400,
            "min_depth_m": 16,
            "assigned_crane_count": 6,
        }
    ]
    vessels: list[dict[str, Any]] = []
    for index in range(1, VESSEL_COUNT + 1):
        compatible_berth = rng.choice(berth_limits)
        eta = start_time + timedelta(
            hours=rng.uniform(0, SIMULATION_DAYS * 24 - 36)
        )
        port_hours = rng.uniform(12, 60)
        teu_capacity = rng.randrange(800, 12001, 200)
        vessels.append(
            {
                "vessel_id": f"V-{index:03d}",
                "vessel_name": f"{rng.choice(VESSEL_NAMES)} {index:02d}",
                "eta": isoformat(eta),
                "etd": isoformat(eta + timedelta(hours=port_hours)),
                "teu_capacity": teu_capacity,
                "vessel_length_m": rng.randrange(
                    140,
                    int(max(140, compatible_berth["max_vessel_length_m"])) + 1,
                    10,
                ),
                "draft_m": round(
                    rng.uniform(
                        7.0,
                        min(15.0, float(compatible_berth["min_depth_m"])),
                    ),
                    1,
                ),
                "required_cranes": rng.randint(
                    1, int(max(1, compatible_berth["assigned_crane_count"]))
                ),
                "cargo_type": rng.choice(CARGO_TYPES),
                "priority": rng.choices(PRIORITIES, weights=(65, 25, 10), k=1)[0],
                "assigned_berth_id": f"B-{rng.randint(1, BERTH_COUNT):02d}",
            }
        )
    return sorted(vessels, key=lambda vessel: vessel["eta"])


def generate_berths(rng: random.Random) -> list[dict[str, Any]]:
    berths: list[dict[str, Any]] = []
    for index in range(1, BERTH_COUNT + 1):
        berths.append(
            {
                "berth_id": f"B-{index:02d}",
                "berth_name": f"Berth {index}",
                "max_vessel_length_m": rng.randrange(180, 401, 10),
                "min_depth_m": round(rng.uniform(8.5, 16.0), 1),
                "assigned_crane_count": rng.randint(2, 6),
            }
        )
    return berths


def generate_yard_zones(rng: random.Random) -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    for index in range(1, YARD_ZONE_COUNT + 1):
        capacity_teu = rng.randrange(2500, 15001, 500)
        zones.append(
            {
                "zone_id": f"Y-{index:02d}",
                "zone_name": f"Yard Zone {index}",
                "cargo_type": CARGO_TYPES[(index - 1) % len(CARGO_TYPES)],
                "capacity_teu": capacity_teu,
                "current_fill_pct": round(rng.uniform(35, 88), 1),
                "reefer_plug_count": rng.randint(0, 180),
            }
        )
    return zones


def generate_arrival_stream(
    rng: random.Random,
    start_time: datetime,
    shocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate hourly Poisson arrivals and a congestion signal."""
    arrivals: list[dict[str, Any]] = []
    for hour in range(SIMULATION_DAYS * 24):
        timestamp = start_time + timedelta(hours=hour)
        active_shocks = [
            shock
            for shock in shocks
            if shock["start_time"] <= isoformat(timestamp) < shock["end_time"]
        ]
        multiplier = max(
            (float(shock["arrival_rate_multiplier"]) for shock in active_shocks),
            default=1.0,
        )
        expected_arrivals = 2.0 * multiplier
        arrival_count = poisson(expected_arrivals, rng)
        capacity_factor = max(
            0.35,
            1.0
            - sum(float(shock["capacity_reduction_pct"]) for shock in active_shocks) / 100,
        )
        congestion_index = round(
            min(1.0, max(0.0, arrival_count / (8.0 * capacity_factor))), 3
        )
        arrivals.append(
            {
                "timestamp": isoformat(timestamp),
                "arrivals": arrival_count,
                "expected_arrivals": round(expected_arrivals, 2),
                "active_shock_count": len(active_shocks),
                "shock_ids": ",".join(shock["shock_id"] for shock in active_shocks),
                "effective_capacity_factor": round(capacity_factor, 3),
                "congestion_index": congestion_index,
            }
        )
    return arrivals


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_sqlite(
    database_path: Path, datasets: dict[str, list[dict[str, Any]]]
) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for table_name, rows in datasets.items():
            columns = list(rows[0])
            column_sql = ", ".join(f'"{column}" TEXT' for column in columns)
            connection.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            connection.execute(
                f'CREATE TABLE "{table_name}" ({column_sql})'
            )
            placeholders = ", ".join("?" for _ in columns)
            connection.executemany(
                f'INSERT INTO "{table_name}" VALUES ({placeholders})',
                [[str(row[column]) for column in columns] for row in rows],
            )
        connection.commit()


def generate_dataset(seed: int = DEFAULT_SEED) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(seed)
    shocks = generate_shocks(rng, START_TIME)
    berths = generate_berths(rng)
    return {
        "vessels": generate_vessels(rng, START_TIME, berths),
        "berths": berths,
        "yard_zones": generate_yard_zones(rng),
        "shocks": shocks,
        "arrival_stream": generate_arrival_stream(rng, START_TIME, shocks),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "data" / "generated",
        help="Directory for CSV files and portflow.db",
    )
    args = parser.parse_args()

    datasets = generate_dataset(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for table_name, rows in datasets.items():
        write_csv(args.output_dir / f"{table_name}.csv", rows)
    write_sqlite(args.output_dir / "portflow.db", datasets)

    print(f"Generated {len(datasets['vessels'])} vessels")
    print(f"Generated {len(datasets['berths'])} berths")
    print(f"Generated {len(datasets['yard_zones'])} yard zones")
    print(f"Generated {len(datasets['arrival_stream'])} hourly arrival records")
    print(f"Generated {len(datasets['shocks'])} shock events")
    print(f"Saved CSV and SQLite data to {args.output_dir}")


if __name__ == "__main__":
    main()
