"""Shared test setup.

The suite must not depend on whatever AI_ENGINE happens to be exported in the
shell or the CI job. Endpoint tests exercise the real pipeline through its
deterministic stubs, which need no weights and no GPU; tests that want the mock
engine instantiate `MockAIProvider` directly.
"""

import pytest

from app.core.config import settings
from app.services.ai_provider import get_ai_provider


@pytest.fixture(autouse=True)
def force_local_engine(monkeypatch):
    monkeypatch.setattr(settings, "AI_ENGINE", "local")
    get_ai_provider.cache_clear()
    yield
    get_ai_provider.cache_clear()
