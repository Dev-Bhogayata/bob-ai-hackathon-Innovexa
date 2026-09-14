"""IBM watsonx.ai supervisor-summary adapter."""

from __future__ import annotations

import os
from typing import Any, Mapping

import httpx


class WatsonxConfigurationError(RuntimeError):
    """Raised when live watsonx configuration is incomplete."""


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise WatsonxConfigurationError(f"Missing required environment variable: {name}")
    return value


def generate_watsonx_summary(
    messages: list[Mapping[str, str]],
    *,
    timeout_seconds: float = 30.0,
) -> str:
    """Call watsonx.ai chat generation and return the generated text.

    The IBM project ID, region URL, and bearer token are supplied through
    environment variables. Tokens are never logged or included in errors.
    """
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    url = _required("WATSONX_URL").rstrip("/") + "/ml/v1/text/chat?version=2024-05-31"
    token = _required("WATSONX_API_KEY")
    project_id = _required("WATSONX_PROJECT_ID")
    model_id = os.getenv("WATSONX_MODEL_ID", "meta-llama/llama-3-1-70b-instruct")
    payload: dict[str, Any] = {
        "model_id": model_id,
        "project_id": project_id,
        "messages": list(messages),
        "max_tokens": 700,
        "temperature": 0.2,
    }
    try:
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
        return str(body["choices"][0]["message"]["content"])
    except httpx.HTTPError as error:
        raise RuntimeError("watsonx.ai request failed; check WATSONX_URL and credentials") from error
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise RuntimeError("watsonx.ai returned an unexpected response shape") from error
