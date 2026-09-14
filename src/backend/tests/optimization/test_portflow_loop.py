import json
import tempfile
import unittest
from pathlib import Path

from src.agent.portflow_loop import run_portflow_loop


class PortFlowLoopTests(unittest.TestCase):
    def test_loop_runs_in_order_and_writes_trace(self):
        berths = [
            {"berth_id": "B-01", "max_vessel_length_m": 200, "min_depth_m": 14, "assigned_crane_count": 2},
            {"berth_id": "B-02", "max_vessel_length_m": 350, "min_depth_m": 8, "assigned_crane_count": 3},
        ]
        vessels = [
            {"vessel_id": "V-01", "eta": "2026-01-01T00:00+00:00", "etd": "2026-01-01T04:00+00:00", "vessel_length_m": 180, "draft_m": 9, "required_cranes": 1, "priority": "critical", "teu_capacity": 4000},
            {"vessel_id": "V-02", "eta": "2026-01-01T01:00+00:00", "etd": "2026-01-01T05:00+00:00", "vessel_length_m": 300, "draft_m": 7, "required_cranes": 2, "priority": "standard", "teu_capacity": 4000},
            {"vessel_id": "V-03", "eta": "2026-01-01T02:00+00:00", "etd": "2026-01-01T05:00+00:00", "vessel_length_m": 170, "draft_m": 7, "required_cranes": 1, "priority": "standard", "teu_capacity": 4000},
        ]
        alternate_ports = [
            {"port_id": "ALT-01", "distance_km": 100, "estimated_available_teu": 10000}
        ]

        with tempfile.TemporaryDirectory() as directory:
            trace_path = Path(directory) / "trace.jsonl"
            result = run_portflow_loop(
                vessels,
                berths,
                alternate_ports,
                predictor=lambda vessel: 10 if vessel["vessel_id"] == "V-03" else 2,
                delay_threshold_hours=6,
                trace_path=trace_path,
            )

            self.assertEqual(
                [event["step"] for event in result["trace"]],
                ["predict", "optimize", "route", "summarize"],
            )
            self.assertEqual(list(result["route_recommendations"]), ["V-03"])
            self.assertEqual(len(result["summary_messages"]), 2)
            trace_rows = [
                json.loads(line) for line in trace_path.read_text().splitlines()
            ]
            self.assertEqual(len(trace_rows), 4)
            self.assertEqual(trace_rows[2]["output"]["vessels_rerouted"], 1)


if __name__ == "__main__":
    unittest.main()
