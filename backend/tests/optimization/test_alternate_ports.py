import unittest

from src.rerouting.alternate_ports import rank_alternate_ports


class AlternatePortTests(unittest.TestCase):
    def setUp(self):
        self.vessel = {"vessel_id": "V-01", "teu_capacity": 5000}
        self.ports = [
            {
                "port_id": "ALT-NEAR",
                "port_name": "Near Port",
                "distance_km": 120,
                "estimated_available_teu": 6000,
            },
            {
                "port_id": "ALT-FAR",
                "port_name": "Far Port",
                "distance_km": 500,
                "estimated_available_teu": 15000,
            },
            {
                "port_id": "ALT-FULL",
                "port_name": "Full Port",
                "distance_km": 80,
                "estimated_available_teu": 3000,
            },
            {
                "port_id": "ALT-MID",
                "port_name": "Middle Port",
                "distance_km": 250,
                "estimated_available_teu": 7000,
            },
        ]

    def test_does_not_recommend_when_delay_is_below_threshold(self):
        self.assertEqual(
            rank_alternate_ports(self.vessel, 6, 6, self.ports),
            [],
        )

    def test_excludes_insufficient_capacity_and_returns_top_three(self):
        results = rank_alternate_ports(
            self.vessel, predicted_delay_hours=12, delay_threshold_hours=6,
            alternate_ports=self.ports, limit=3,
        )

        self.assertEqual([result["port_id"] for result in results], [
            "ALT-NEAR", "ALT-MID", "ALT-FAR"
        ])
        self.assertEqual(len(results), 3)
        self.assertTrue(all(result["estimated_available_teu"] >= 5000 for result in results))
        self.assertTrue(all(0 <= result["score"] <= 100 for result in results))
        self.assertTrue(all("reason" in result for result in results))

    def test_limit_can_return_two_alternates(self):
        results = rank_alternate_ports(
            self.vessel, 12, 6, self.ports, limit=2
        )
        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()
