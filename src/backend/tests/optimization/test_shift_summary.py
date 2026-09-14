import json
import unittest
from datetime import datetime, timezone

from src.llm.shift_summary import build_shift_supervisor_prompt


class ShiftSummaryPromptTests(unittest.TestCase):
    def test_prompt_contains_normalized_optimizer_json_and_operational_guidance(self):
        optimizer_output = [
            {
                "vessel_id": "V-03",
                "berth_id": "B-01",
                "scheduled_start": "2026-01-01T06:00+00:00",
                "scheduled_end": "2026-01-01T09:00+00:00",
                "wait_hours": 4.0,
                "priority": "critical",
            }
        ]

        messages = build_shift_supervisor_prompt(
            optimizer_output,
            generated_at=datetime(2026, 1, 1, 5, tzinfo=timezone.utc),
        )

        self.assertEqual([message["role"] for message in messages], ["system", "user"])
        self.assertIn('"vessel_id": "V-03"', messages[1]["content"])
        self.assertIn("critical vessel is waiting", messages[0]["content"])
        self.assertIn('"berths_at_risk"', messages[0]["content"])
        self.assertIn("2026-01-01T05:00+00:00", messages[1]["content"])

    def test_accepts_json_string_and_rejects_non_array_payloads(self):
        messages = build_shift_supervisor_prompt(json.dumps([]))
        self.assertIn("Optimizer output JSON", messages[1]["content"])

        with self.assertRaisesRegex(ValueError, "JSON array"):
            build_shift_supervisor_prompt('{"berth_id": "B-01"}')

        with self.assertRaisesRegex(ValueError, "valid JSON"):
            build_shift_supervisor_prompt("{not-json}")


if __name__ == "__main__":
    unittest.main()
