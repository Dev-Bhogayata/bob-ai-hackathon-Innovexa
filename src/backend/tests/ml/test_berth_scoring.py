import unittest
from datetime import datetime, timezone

from src.data.generate_data import generate_dataset
from src.scoring.berth_scoring import score_berths


class BerthScoringTests(unittest.TestCase):
    def test_scores_are_bounded_and_include_every_berth(self):
        dataset = generate_dataset(seed=42)
        scores = score_berths(
            dataset["berths"],
            dataset["vessels"],
            dataset["yard_zones"],
            as_of=datetime(2026, 1, 10, tzinfo=timezone.utc),
        )

        self.assertEqual(len(scores), 8)
        self.assertEqual({score["berth_id"] for score in scores}, {"B-01", "B-02", "B-03", "B-04", "B-05", "B-06", "B-07", "B-08"})
        self.assertTrue(all(0 <= score["score"] <= 100 for score in scores))
        self.assertEqual(scores, sorted(scores, key=lambda result: (-result["score"], result["berth_id"])))

    def test_more_pressure_produces_a_lower_score(self):
        berths = [
            {"berth_id": "B-01", "assigned_crane_count": 4},
            {"berth_id": "B-02", "assigned_crane_count": 4},
        ]
        vessels = [
            {
                "vessel_id": "V-01",
                "assigned_berth_id": "B-01",
                "eta": "2026-01-01T02:00+00:00",
                "etd": "2026-01-01T18:00+00:00",
                "teu_capacity": 6000,
            }
        ]
        yard_zones = [{"capacity_teu": 1000, "current_fill_pct": 50}]

        scores = score_berths(
            berths,
            vessels,
            yard_zones,
            as_of=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        self.assertLess(scores[1]["score"], scores[0]["score"])
        self.assertEqual(scores[0]["berth_id"], "B-02")
        self.assertEqual(scores[1]["berth_id"], "B-01")


if __name__ == "__main__":
    unittest.main()
