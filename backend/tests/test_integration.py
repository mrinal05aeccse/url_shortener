import os
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

# ensure the app uses sqlite in-memory for tests
from app import main
from app.database import init_db, engine


def setup_module(module):
    # initialize in-memory sqlite for tests
    init_db("sqlite:///:memory:")


def test_shorten_and_redirect():
    client = TestClient(main.app)
    resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert "alias" in data

    alias = data["alias"]
    r = client.get(f"/{alias}", allow_redirects=False)
    assert r.status_code in (301, 302)
    assert r.headers.get("location") == "https://example.com"
