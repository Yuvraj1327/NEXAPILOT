"""Anthropic client — a thin, testable seam.

`get_anthropic_client()` is the one place the real SDK is constructed, so
tests can monkeypatch this single function to inject a mock client instead
of touching every call site (see tests/test_ai.py).
"""

from functools import lru_cache

import anthropic

from app.core.config import settings
from app.core.exceptions import AppError


class AIConfigurationError(AppError):
    status_code = 503
    code = "AI_NOT_CONFIGURED"


@lru_cache
def get_anthropic_client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise AIConfigurationError(
            "ANTHROPIC_API_KEY is not set. Add it to backend/.env to enable the AI layer."
        )
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)
