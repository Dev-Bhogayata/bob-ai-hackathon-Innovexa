import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.backend.app.main import app
from src.llm.watsonx import WatsonxConfigurationError, generate_watsonx_summary
from src.optimization.resource_allocation import allocate_cranes


class LiveResourceTests(unittest.TestCase):
    client = TestClient(app)

    def test_supervisor_summary_defaults_to_safe_local_prompt_mode(self):
        response = self.client.post(
            "/api/v1/supervisor-summary",
            json={"assignments": [{"vessel_id": "V-01", "berth_id": "B-01"}]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "prompt")
        self.assertIsNone(response.json()["summary"])

    def test_crane_allocation_is_explicit_and_validated(self):
        cranes = allocate_cranes(
            {"vessel_id": "V-01", "required_cranes": 2},
            {"berth_id": "B-01", "assigned_crane_count": 3},
        )
        self.assertEqual(cranes, ["B-01-CRANE-1", "B-01-CRANE-2"])
        with self.assertRaises(ValueError):
            allocate_cranes(
                {"vessel_id": "V-01", "required_cranes": 4},
                {"berth_id": "B-01", "assigned_crane_count": 3},
            )

    def test_live_watsonx_mode_fails_clearly_without_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(WatsonxConfigurationError):
                generate_watsonx_summary([])


if __name__ == "__main__":
    unittest.main()
