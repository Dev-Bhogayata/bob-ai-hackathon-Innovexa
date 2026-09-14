import unittest

from src.optimization.berth_assignment import optimize_berth_assignments


class BerthAssignmentTests(unittest.TestCase):
    def setUp(self):
        self.berths = [
            {"berth_id": "B-01", "max_vessel_length_m": 200, "min_depth_m": 14, "assigned_crane_count": 2},
            {"berth_id": "B-02", "max_vessel_length_m": 350, "min_depth_m": 8, "assigned_crane_count": 3},
        ]
        self.vessels = [
            {"vessel_id": "V-01", "eta": "2026-01-01T00:00+00:00", "etd": "2026-01-01T04:00+00:00", "vessel_length_m": 180, "draft_m": 9, "required_cranes": 1, "priority": "critical"},
            {"vessel_id": "V-02", "eta": "2026-01-01T01:00+00:00", "etd": "2026-01-01T05:00+00:00", "vessel_length_m": 300, "draft_m": 7, "required_cranes": 2, "priority": "standard"},
            {"vessel_id": "V-03", "eta": "2026-01-01T02:00+00:00", "etd": "2026-01-01T05:00+00:00", "vessel_length_m": 170, "draft_m": 7, "required_cranes": 1, "priority": "standard"},
        ]

    def test_toy_case_assigns_all_and_respects_compatibility_and_overlap(self):
        results = optimize_berth_assignments(self.vessels, self.berths)
        self.assertEqual({row["vessel_id"] for row in results}, {"V-01", "V-02", "V-03"})
        by_vessel = {row["vessel_id"]: row for row in results}
        self.assertEqual(by_vessel["V-02"]["berth_id"], "B-02")
        self.assertEqual(by_vessel["V-01"]["berth_id"], "B-01")
        self.assertEqual(by_vessel["V-03"]["berth_id"], "B-01")
        self.assertEqual(by_vessel["V-01"]["wait_hours"], 0)
        self.assertEqual(by_vessel["V-03"]["wait_hours"], 2)

    def test_infeasible_vessel_is_reported(self):
        vessels = [dict(self.vessels[0], vessel_length_m=500)]
        with self.assertRaisesRegex(ValueError, "no compatible berth"):
            optimize_berth_assignments(vessels, self.berths)


if __name__ == "__main__":
    unittest.main()
