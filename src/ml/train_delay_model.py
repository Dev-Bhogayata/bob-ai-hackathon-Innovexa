"""Train an XGBoost model that predicts vessel delay hours.

The script uses the existing synthetic vessels, berths, yard zones, and hourly
arrival stream. Since this project has no real historical delay log yet, it
creates reproducible historical outcomes from those operational features. The
generated target is explicitly marked as synthetic and should be replaced with
observed port outcomes before production use.

Example:

    python src/ml/train_delay_model.py
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.data.generate_data import generate_dataset

FEATURE_COLUMNS = [
    "teu_capacity",
    "priority_score",
    "cargo_is_reefer",
    "cargo_is_bulk",
    "cargo_is_vehicles",
    "cargo_is_project",
    "berth_crane_count",
    "berth_length_limit_m",
    "berth_depth_limit_m",
    "incoming_arrivals",
    "incoming_expected_arrivals",
    "congestion_index",
    "active_shock_count",
    "yard_fill_pct",
    "hour_of_day",
    "day_of_simulation",
]
PRIORITY_SCORES = {"standard": 0.0, "priority": 0.5, "critical": 1.0}


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _arrival_context(
    eta: datetime, arrival_stream: list[dict[str, Any]]
) -> dict[str, Any]:
    hourly = min(
        arrival_stream,
        key=lambda row: abs(_parse_time(row["timestamp"]) - eta),
    )
    return hourly


def _build_features(
    vessels: list[dict[str, Any]],
    berths: list[dict[str, Any]],
    yard_zones: list[dict[str, Any]],
    arrival_stream: list[dict[str, Any]],
) -> pd.DataFrame:
    berth_by_id = {str(berth["berth_id"]): berth for berth in berths}
    weighted_yard_fill = sum(
        float(zone["capacity_teu"]) * float(zone["current_fill_pct"])
        for zone in yard_zones
    ) / sum(float(zone["capacity_teu"]) for zone in yard_zones)
    rows: list[dict[str, Any]] = []
    for vessel in vessels:
        eta = _parse_time(str(vessel["eta"]))
        berth = berth_by_id[str(vessel["assigned_berth_id"])]
        context = _arrival_context(eta, arrival_stream)
        cargo_type = str(vessel["cargo_type"])
        rows.append(
            {
                "teu_capacity": float(vessel["teu_capacity"]),
                "priority_score": PRIORITY_SCORES[str(vessel["priority"])],
                "cargo_is_reefer": float(cargo_type == "reefer"),
                "cargo_is_bulk": float(cargo_type == "bulk"),
                "cargo_is_vehicles": float(cargo_type == "vehicles"),
                "cargo_is_project": float(cargo_type == "project_cargo"),
                "berth_crane_count": float(berth["assigned_crane_count"]),
                "berth_length_limit_m": float(berth["max_vessel_length_m"]),
                "berth_depth_limit_m": float(berth["min_depth_m"]),
                "incoming_arrivals": float(context["arrivals"]),
                "incoming_expected_arrivals": float(context["expected_arrivals"]),
                "congestion_index": float(context["congestion_index"]),
                "active_shock_count": float(context["active_shock_count"]),
                "yard_fill_pct": weighted_yard_fill,
                "hour_of_day": eta.hour,
                "day_of_simulation": (
                    eta - _parse_time(arrival_stream[0]["_start_time"])
                ).days
                if "_start_time" in arrival_stream[0]
                else (eta - _parse_time(arrival_stream[0]["timestamp"])).days,
            }
        )
    return pd.DataFrame(rows, columns=FEATURE_COLUMNS)


def _add_simulation_metadata(
    arrival_stream: list[dict[str, Any]], start_time: datetime
) -> list[dict[str, Any]]:
    return [dict(row, _start_time=start_time.isoformat()) for row in arrival_stream]


def create_historical_records(
    dataset: dict[str, list[dict[str, Any]]],
    *,
    seed: int,
    history_size: int = 20,
) -> tuple[pd.DataFrame, pd.Series]:
    """Create historical feature/outcome rows from the synthetic operations log."""
    if history_size < 2:
        raise ValueError("history_size must be at least 2")
    rng = random.Random(seed)
    arrival_stream = _add_simulation_metadata(
        dataset["arrival_stream"],
        _parse_time(dataset["arrival_stream"][0]["timestamp"]),
    )
    base_features = _build_features(
        dataset["vessels"],
        dataset["berths"],
        dataset["yard_zones"],
        arrival_stream,
    )
    historical_features = pd.concat(
        [
            base_features.assign(
                incoming_arrivals=lambda frame: frame["incoming_arrivals"]
                .add(rng.gauss(0, 0.8), fill_value=0)
                .clip(lower=0),
                congestion_index=lambda frame: frame["congestion_index"]
                .add(rng.gauss(0, 0.04), fill_value=0)
                .clip(0, 1),
                yard_fill_pct=lambda frame: frame["yard_fill_pct"]
                .add(rng.gauss(0, 2.0), fill_value=0)
                .clip(0, 100),
            )
            for _ in range(history_size)
        ],
        ignore_index=True,
    )
    noise = pd.Series(
        [max(0, rng.gauss(0, 2.5)) for _ in range(len(historical_features))]
    )
    target = (
        0.0035 * historical_features["teu_capacity"]
        + 3.5 * historical_features["congestion_index"]
        + 1.8 * historical_features["active_shock_count"]
        + 0.08 * historical_features["yard_fill_pct"]
        + 2.5 * historical_features["priority_score"]
        - 1.8 * historical_features["berth_crane_count"]
        + noise
    ).clip(lower=0).round(2)
    return historical_features, target.rename("delay_hours")


def train_delay_model(
    features: pd.DataFrame, target: pd.Series, *, seed: int
) -> tuple[XGBRegressor, dict[str, float]]:
    train_x, test_x, train_y, test_y = train_test_split(
        features[FEATURE_COLUMNS],
        target,
        test_size=0.2,
        random_state=seed,
    )
    model = XGBRegressor(
        n_estimators=250,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.9,
        objective="reg:squarederror",
        random_state=seed,
        n_jobs=2,
    )
    model.fit(train_x, train_y, verbose=False)
    predictions = model.predict(test_x)
    metrics = {
        "mae_hours": round(float(mean_absolute_error(test_y, predictions)), 3),
        "rmse_hours": round(float(mean_squared_error(test_y, predictions) ** 0.5), 3),
        "r2": round(float(r2_score(test_y, predictions)), 3),
        "train_rows": float(len(train_x)),
        "test_rows": float(len(test_x)),
    }
    return model, metrics


def save_feature_importance(model: XGBRegressor, output_path: Path) -> None:
    importance = pd.Series(
        model.feature_importances_, index=FEATURE_COLUMNS
    ).sort_values()
    plt.figure(figsize=(10, 7))
    importance.plot(kind="barh", color="#1464a5")
    plt.title("PortFlow vessel delay model — feature importance")
    plt.xlabel("Relative importance")
    plt.ylabel("Feature")
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=180)
    plt.close()


def save_historical_outcomes(
    output_path: Path, features: pd.DataFrame, target: pd.Series
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    features.assign(delay_hours=target).to_csv(output_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--history-size", type=int, default=20)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/models"),
        help="Directory for model, chart, metrics, and historical outcomes",
    )
    args = parser.parse_args()

    dataset = generate_dataset(args.seed)
    features, target = create_historical_records(
        dataset, seed=args.seed, history_size=args.history_size
    )
    model, metrics = train_delay_model(features, target, seed=args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_model(args.output_dir / "vessel_delay_xgboost.json")
    save_feature_importance(model, args.output_dir / "feature_importance.png")
    save_historical_outcomes(
        args.output_dir / "historical_delay_outcomes.csv", features, target
    )
    (args.output_dir / "metrics.json").write_text(
        json.dumps(
            {
                **metrics,
                "target": "delay_hours",
                "synthetic_outcomes": True,
                "feature_columns": FEATURE_COLUMNS,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Trained on {len(features)} historical rows")
    print(f"MAE: {metrics['mae_hours']:.3f} hours")
    print(f"RMSE: {metrics['rmse_hours']:.3f} hours")
    print(f"R²: {metrics['r2']:.3f}")
    print(f"Saved model and feature importance chart to {args.output_dir}")


if __name__ == "__main__":
    main()
