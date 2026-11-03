import pytest


@pytest.fixture(autouse=True)
def no_real_llm(monkeypatch):
    """Every test runs without the real AI unless it installs its own fake."""
    monkeypatch.setattr("app.workflows.nodes.get_llm_client", lambda: None)