import unittest

from fastapi.testclient import TestClient

from backend.app.main import app


class OperationsApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_timeline_contract_is_72_hours_and_frontend_ready(self):
        response = self.client.get(
            "/api/v1/timeline",
            params={"start": "2026-01-01T00:00:00+00:00", "seed": 42},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["api_version"], "v1")
        self.assertEqual(body["duration_hours"], 72)
        self.assertEqual(len(body["berths"]), 8)
        self.assertTrue(body["items"])
        self.assertTrue(
            {
                "vessel_id",
                "berth_id",
                "scheduled_start",
                "scheduled_end",
                "eta",
                "etd",
                "wait_hours",
                "priority",
                "teu_capacity",
                "status",
            }.issubset(body["items"][0])
        )

    def test_hotspot_contract_contains_berth_and_yard_heatmap_items(self):
        response = self.client.get(
            "/api/v1/hotspots",
            params={"as_of": "2026-01-01T00:00:00+00:00", "seed": 42},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["api_version"], "v1")
        self.assertEqual(body["horizon_hours"], 24)
        self.assertEqual(
            {item["resource_type"] for item in body["items"]},
            {"berth", "yard"},
        )
        self.assertTrue(all(0 <= item["score"] <= 100 for item in body["items"]))
        self.assertTrue(all(item["factors"] for item in body["items"]))

    def test_invalid_timezone_is_rejected(self):
        response = self.client.get("/api/v1/timeline?start=2026-01-01T00:00:00")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
