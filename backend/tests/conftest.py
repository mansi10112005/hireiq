import pytest


@pytest.fixture(autouse=True)
def isolate_external_services(monkeypatch):
    """Every test runs without the real AI and without a database,
    unless it installs its own fake or a real test repository."""
    monkeypatch.setattr("app.workflows.nodes.get_llm_client", lambda: None)
    monkeypatch.setattr("app.workflows.nodes.get_repository", lambda: None)