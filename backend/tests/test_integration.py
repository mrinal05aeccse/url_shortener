from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.database import init_db
from app.models import URL, ClickEvent
from sqlmodel import select
import os

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
    # expect redirect or 200 (depending on client)
    assert r.status_code in (302, 307, 200)
    if r.status_code in (302, 307):
        assert r.headers["location"] == "https://example.com"


def test_analytics_by_country():
    """Test that analytics aggregates clicks by country."""
    from backend.app.database import get_session
    
    # Create a short URL
    resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
    assert resp.status_code == 200
    alias = resp.json()["alias"]
    
    # Get the URL record
    session = next(get_session())
    url = session.exec(select(URL).where(URL.alias == alias)).first()
    assert url is not None
    
    # Simulate clicks from different countries
    for country in ["US", "GB", "US", "DE", "XX"]:
        event = ClickEvent(url_id=url.id, country=country)
        session.add(event)
    session.commit()
    
    # Fetch geographic analytics
    resp = client.get(f"/api/v1/analytics/{alias}/geo?api_key=changeme")
    assert resp.status_code == 200
    data = resp.json()
    
    # Verify aggregation
    assert data["by_country"]["US"] == 2
    assert data["by_country"]["GB"] == 1
    assert data["by_country"]["DE"] == 1
    assert data["by_country"]["XX"] == 1
    assert data["total_clicks"] == 5


def test_analytics_by_country_unauthorized():
    """Test that analytics endpoint requires API key."""
    resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
    alias = resp.json()["alias"]
    
    # Request without API key should fail
    resp = client.get(f"/api/v1/analytics/{alias}/geo")
    assert resp.status_code == 401
    assert "unauthorized" in resp.json()["detail"]
    
    # Request with wrong API key should fail
    resp = client.get(f"/api/v1/analytics/{alias}/geo?api_key=wrongkey")
    assert resp.status_code == 401


def test_analytics_by_country_not_found():
    """Test that analytics returns 404 for non-existent alias."""
    resp = client.get(f"/api/v1/analytics/nonexistent/geo?api_key=changeme")
    assert resp.status_code == 404


def test_export_url_summary():
    """Test CSV export of URL summary."""
    # Create and click a URL
    resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
    assert resp.status_code == 200
    alias = resp.json()["alias"]
    
    # Record some clicks
    from backend.app.database import get_session
    session = next(get_session())
    url = session.exec(select(URL).where(URL.alias == alias)).first()
    
    for i in range(3):
        event = ClickEvent(url_id=url.id, country="US" if i % 2 else "GB")
        session.add(event)
    session.commit()
    
    # Export summary
    resp = client.get(f"/api/v1/export/url/{alias}?api_key=changeme")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "alias" in resp.text
    assert alias in resp.text


def test_export_analytics_csv():
    """Test CSV export of daily analytics."""
    # Create and click a URL
    resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
    assert resp.status_code == 200
    alias = resp.json()["alias"]
    
    # Record events
    from backend.app.database import get_session
    session = next(get_session())
    url = session.exec(select(URL).where(URL.alias == alias)).first()
    
    for country in ["US", "GB", "US", "DE"]:
        event = ClickEvent(url_id=url.id, country=country)
        session.add(event)
    session.commit()
    
    # Export analytics
    resp = client.get(f"/api/v1/export/analytics/{alias}?api_key=changeme")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "date" in resp.text


def test_export_events_csv():
    """Test CSV export of raw events."""
    # Create and click a URL
    resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
    assert resp.status_code == 200
    alias = resp.json()["alias"]
    
    # Record events
    from backend.app.database import get_session
    session = next(get_session())
    url = session.exec(select(URL).where(URL.alias == alias)).first()
    
    for country in ["US", "GB"]:
        event = ClickEvent(url_id=url.id, country=country, ip="192.0.2.1")
        session.add(event)
    session.commit()
    
    # Export events
    resp = client.get(f"/api/v1/export/events/{alias}?api_key=changeme")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "timestamp" in resp.text


def test_export_requires_auth():
    """Test that export endpoints require API key."""
    resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
    alias = resp.json()["alias"]
    
    # Request without API key
    resp = client.get(f"/api/v1/export/url/{alias}")
    assert resp.status_code == 401
    
    resp = client.get(f"/api/v1/export/analytics/{alias}")
    assert resp.status_code == 401
    
    resp = client.get(f"/api/v1/export/events/{alias}")
    assert resp.status_code == 401