"""GET /api/me carries the viewer's first name from their workspace profile, so the greeting can say it."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fairshare import dbx  # noqa: E402
from server import api  # noqa: E402


@pytest.fixture
def client():
    from server.main import create_app
    return TestClient(create_app())


def _profile(user):
    return SimpleNamespace(current_user=SimpleNamespace(me=lambda: user))


def test_me_first_name_from_profile(client, monkeypatch):
    monkeypatch.setattr(api, "_has_profile", lambda v: True)
    monkeypatch.setattr(dbx, "workspace_client", lambda: _profile(SimpleNamespace(display_name="Matthew Bell", name=SimpleNamespace(given_name="Matthew"))))
    assert client.get("/api/me").json()["name"] == "Matthew"


def test_me_first_name_falls_back_to_display_name(client, monkeypatch):
    monkeypatch.setattr(api, "_has_profile", lambda v: True)
    monkeypatch.setattr(dbx, "workspace_client", lambda: _profile(SimpleNamespace(display_name="Matthew Bell", name=None)))
    assert client.get("/api/me").json()["name"] == "Matthew"


def test_me_name_is_null_when_the_profile_lookup_fails(client, monkeypatch):
    monkeypatch.setattr(api, "_has_profile", lambda v: True)

    def boom():
        raise RuntimeError("SCIM down")
    monkeypatch.setattr(dbx, "workspace_client", boom)
    assert client.get("/api/me").json()["name"] is None


def test_me_name_is_null_without_a_profile(client, monkeypatch):
    monkeypatch.setattr(api, "_has_profile", lambda v: False)
    assert client.get("/api/me").json()["name"] is None
