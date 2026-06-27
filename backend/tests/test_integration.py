from fastapi.testclient import TestClient
import pytest
from backend.app.main import app
from backend.app.database import init_db
from backend.app.models import URL

client = TestClient(app)


@pytest.fixture(autouse=True)
def prepare_db(tmp_path, monkeypatch):
    # Use a temporary SQLite DB for tests
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    init_db()
    yield


def test_shorten_and_redirect():
    # create short url
    resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert "alias" in data and "target" in data
    alias = data["alias"]

    # redirect
    r = client.get(f"/{alias}", allow_redirects=False)
    assert r.status_code in (302, 307) or r.status_code == 200
    # if redirect returned, location header should point to target
    if r.status_code in (302, 307):
        assert r.headers["location"] == "https://example.com"