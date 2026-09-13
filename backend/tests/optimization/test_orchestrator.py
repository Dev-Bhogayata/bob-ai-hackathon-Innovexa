import logging
import unittest
from unittest.mock import Mock

from src.agent.orchestrator import orchestrate


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.vessels = [{"vessel_id": "V-01", "teu_capacity": 5000}]
        self.berths = [{"berth_id": "B-01"}]
        self.ports = [{"port_id": "ALT-01"}]

    def test_skips_optimization_and_routing_when_thresholds_are_not_met(self):
        predict = Mock(return_value={"predictions": [{"vessel_id": "V-01", "predicted_delay_hours": 4}], "hotspots": [{"score": 70}]})
        optimize = Mock()
        route = Mock()
        plan = Mock(return_value=[{"role": "user", "content": "plan"}])

        result = orchestrate(
            window_start="2026-01-01T00:00:00+00:00",
            window_end="2026-01-04T00:00:00+00:00",
            vessels=self.vessels,
            berths=self.berths,
            alternate_ports=self.ports,
            predict_congestion_fn=predict,
            optimize_berths_fn=optimize,
            recommend_routing_fn=route,
            generate_plan_fn=plan,
        )

        optimize.assert_not_called()
        route.assert_not_called()
        plan.assert_called_once()
        self.assertFalse(result["decisions"]["optimization_called"])
        self.assertFalse(result["decisions"]["routing_called"])

    def test_calls_all_conditional_steps_and_returns_one_json_object(self):
        predict = Mock(return_value={"predictions": [{"vessel_id": "V-01", "predicted_delay_hours": 13}], "hotspots": [{"berth_id": "B-01", "score": 71}]})
        optimize = Mock(return_value=[{"vessel_id": "V-01", "berth_id": "B-01"}])
        route = Mock(return_value={"V-01": [{"port_id": "ALT-01"}]})
        plan = Mock(return_value=[{"role": "system", "content": "briefing"}])

        result = orchestrate(
            window_start="2026-01-01T00:00:00+00:00",
            window_end="2026-01-04T00:00:00+00:00",
            vessels=self.vessels,
            berths=self.berths,
            alternate_ports=self.ports,
            predict_congestion_fn=predict,
            optimize_berths_fn=optimize,
            recommend_routing_fn=route,
            generate_plan_fn=plan,
        )

        optimize.assert_called_once_with(self.vessels, self.berths)
        route.assert_called_once()
        plan.assert_called_once()
        self.assertEqual(result["optimization"], [{"vessel_id": "V-01", "berth_id": "B-01"}])
        self.assertEqual(result["routing"]["V-01"][0]["port_id"], "ALT-01")
        self.assertEqual(result["plan"][0]["role"], "system")
        self.assertEqual(result["decisions"]["optimization_called"], True)
        self.assertEqual(result["decisions"]["routing_called"], True)

    def test_logs_duration_and_output_size_for_each_step(self):
        records = []

        class Capture(logging.Handler):
            def emit(self, record):
                records.append(record)

        logger = logging.getLogger("portflow.orchestrator")
        handler = Capture()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        try:
            orchestrate(
                window_start="2026-01-01T00:00:00+00:00",
                window_end="2026-01-04T00:00:00+00:00",
                vessels=self.vessels,
                berths=self.berths,
                alternate_ports=self.ports,
                predict_congestion_fn=Mock(return_value={"predictions": [], "hotspots": []}),
                generate_plan_fn=Mock(return_value=[]),
            )
        finally:
            logger.removeHandler(handler)
        self.assertEqual([record.step for record in records], [
            "predict_congestion", "optimize_berths", "recommend_routing", "generate_plan"
        ])
        self.assertTrue(all(record.duration_ms >= 0 for record in records))
        self.assertTrue(all(record.output_size_bytes >= 0 for record in records))


if __name__ == "__main__":
    unittest.main()
