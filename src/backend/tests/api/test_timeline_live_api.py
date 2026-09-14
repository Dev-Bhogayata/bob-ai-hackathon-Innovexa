import unittest

from fastapi.testclient import TestClient

from src.backend.app.main import app


class LiveTimelineApiTests(unittest.TestCase):
    client = TestClient(app)

    def scenario(self):
        return {
            "vessels": [{
                "vessel_id": "V-1", "eta": "2026-01-01T00:00:00+00:00",
                "etd": "2026-01-01T12:00:00+00:00", "teu_capacity": 1000,
                "vessel_length_m": 200, "draft_m": 10, "required_cranes": 1,
                "cargo_type": "containers", "priority": "priority",
            }],
            "berths": [{
                "berth_id": "B-1", "max_vessel_length_m": 300,
                "min_depth_m": 12, "assigned_crane_count": 2,
            }],
            "yard_zones": [{
                "zone_id": "Y-1", "capacity_teu": 5000,
                "current_fill_pct": 10, "cargo_type": "containers",
            }],
        }

    def test_post_timeline_schedules_live_scenario(self):
        response = self.client.post("/api/v1/timeline", json={
            "scenario": self.scenario(),
            "window_start": "2026-01-01T00:00:00+00:00",
            "window_end": "2026-01-02T00:00:00+00:00",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["vessel_id"], "V-1")
        self.assertEqual(response.json()["duration_hours"], 24)

    def test_post_timeline_rejects_invalid_scenario(self):
        scenario = self.scenario()
        scenario["vessels"][0]["etd"] = "2025-12-31T23:00:00+00:00"
        response = self.client.post("/api/v1/timeline", json={
            "scenario": scenario,
            "window_start": "2026-01-01T00:00:00+00:00",
            "window_end": "2026-01-02T00:00:00+00:00",
        })
        self.assertEqual(response.status_code, 422)
        self.assertIn("etd must be after eta", response.text)

    def test_post_timeline_rejects_timezone_free_window(self):
        response = self.client.post("/api/v1/timeline", json={
            "scenario": self.scenario(),
            "window_start": "2026-01-01T00:00:00",
            "window_end": "2026-01-02T00:00:00+00:00",
        })
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
