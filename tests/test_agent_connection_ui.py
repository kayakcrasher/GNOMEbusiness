from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HTML = (
    ROOT / "frontend/agents.html"
).read_text()

JS = (
    ROOT / "frontend/js/agent-connections.js"
).read_text()


def test_connection_panel_exists():
    assert 'id="agent-connections"' in HTML
    assert 'id="create-agent"' in HTML
    assert 'id="agent-list"' in HTML


def test_agent_permissions_are_scoped():
    for scope in (
        "leads:read",
        "appointments:read",
        "jobs:work",
    ):
        assert scope in HTML

    assert "proposals:create" not in HTML


def test_connector_api_wired():
    assert "/api/connectors/manage" in JS
    assert 'credentials: "same-origin"' in JS


def test_secret_is_one_time_display():
    assert 'id="agent-secret" hidden' in HTML
    assert "hideToken()" in JS
    assert "currentToken = \"\"" in JS


def test_revocation_requires_confirmation():
    assert "confirm(" in JS
    assert '"/revoke"' in JS


def test_existing_approval_center_preserved():
    assert 'id="proposals"' in HTML
    assert 'id="approved"' in HTML
    assert 'id="rejected"' in HTML
