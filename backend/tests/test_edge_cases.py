"""
Edge case and error scenario tests.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db
from app.models import URL, ClickEvent
from sqlmodel import select
from datetime import datetime, timedelta

client = TestClient(app)


@pytest.fixture(autouse=True)
def prepare_db(tmp_path, monkeypatch):
    """Setup temporary database for each test."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    init_db()
    yield


class TestExpiredURLs:
    """Test handling of expired URLs."""
    
    def test_expired_url_returns_404(self):
        """Test that accessing an expired URL returns 404."""
        # Create an already-expired URL
        from backend.app.database import get_session
        
        resp = client.post("/api/v1/shorten", json={
            "target": "https://example.com",
            "ttl_days": -1  # Expired immediately
        })
        
        alias = resp.json()["alias"]
        
        # Try to access expired URL
        resp = client.get(f"/{alias}")
        assert resp.status_code == 404
        assert "expired" in resp.json()["detail"]
    
    def test_url_expiration_exact_boundary(self):
        """Test URL expiration at exact expiration time."""
        from backend.app.database import get_session
        from unittest import mock
        
        # Create URL that expires in 0.1 seconds
        resp = client.post("/api/v1/shorten", json={
            "target": "https://example.com",
            "ttl_days": 0
        })
        alias = resp.json()["alias"]
        
        # Access before expiration should work (immediately)
        resp = client.get(f"/{alias}", allow_redirects=False)
        assert resp.status_code in (302, 307, 200)


class TestDuplicateAliases:
    """Test handling of duplicate alias attempts."""
    
    def test_custom_alias_already_exists(self):
        """Test that creating URL with existing custom alias fails."""
        # Create first URL with custom alias
        resp1 = client.post("/api/v1/shorten", json={
            "target": "https://example1.com",
            "custom_alias": "myalias"
        })
        assert resp1.status_code == 200
        
        # Try to create second URL with same custom alias
        resp2 = client.post("/api/v1/shorten", json={
            "target": "https://example2.com",
            "custom_alias": "myalias"
        })
        assert resp2.status_code == 409
        assert "already exists" in resp2.json()["detail"]
    
    def test_custom_alias_empty_string(self):
        """Test custom alias with empty string."""
        resp = client.post("/api/v1/shorten", json={
            "target": "https://example.com",
            "custom_alias": ""
        })
        # Should either fail validation or be treated as None
        assert resp.status_code in (400, 200)


class TestInvalidURLs:
    """Test handling of invalid target URLs."""
    
    def test_invalid_url_format(self):
        """Test that invalid URLs are rejected."""
        resp = client.post("/api/v1/shorten", json={
            "target": "not-a-valid-url"
        })
        # Should fail validation
        assert resp.status_code == 422
    
    def test_missing_target(self):
        """Test that missing target URL fails."""
        resp = client.post("/api/v1/shorten", json={})
        assert resp.status_code == 422
    
    def test_relative_url(self):
        """Test relative URL handling."""
        resp = client.post("/api/v1/shorten", json={
            "target": "/relative/path"
        })
        # Relative URLs should fail validation
        assert resp.status_code == 422


class TestAuthorizationErrors:
    """Test API key authentication."""
    
    def test_info_endpoint_without_key(self):
        """Test info endpoint without API key."""
        # First create a URL
        resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
        alias = resp.json()["alias"]
        
        # Try to get info without key
        resp = client.get(f"/api/v1/info/{alias}")
        assert resp.status_code == 401
    
    def test_info_endpoint_wrong_key(self):
        """Test info endpoint with wrong API key."""
        resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
        alias = resp.json()["alias"]
        
        resp = client.get(f"/api/v1/info/{alias}?api_key=wrongkey")
        assert resp.status_code == 401
    
    def test_analytics_without_key(self):
        """Test analytics endpoint without key."""
        resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
        alias = resp.json()["alias"]
        
        resp = client.get(f"/api/v1/analytics/{alias}")
        assert resp.status_code == 401
    
    def test_analytics_geo_without_key(self):
        """Test geographic analytics without key."""
        resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
        alias = resp.json()["alias"]
        
        resp = client.get(f"/api/v1/analytics/{alias}/geo")
        assert resp.status_code == 401


class TestNotFoundErrors:
    """Test 404 error handling."""
    
    def test_nonexistent_alias_redirect(self):
        """Test redirecting to nonexistent alias."""
        resp = client.get("/nonexistent123")
        assert resp.status_code == 404
    
    def test_nonexistent_info_endpoint(self):
        """Test info endpoint with nonexistent alias."""
        resp = client.get("/api/v1/info/nonexistent?api_key=changeme")
        assert resp.status_code == 404
    
    def test_nonexistent_analytics_endpoint(self):
        """Test analytics endpoint with nonexistent alias."""
        resp = client.get("/api/v1/analytics/nonexistent?api_key=changeme")
        assert resp.status_code == 404
    
    def test_nonexistent_geo_analytics(self):
        """Test geographic analytics with nonexistent alias."""
        resp = client.get("/api/v1/analytics/nonexistent/geo?api_key=changeme")
        assert resp.status_code == 404


class TestTTLValidation:
    """Test TTL (time-to-live) handling."""
    
    def test_zero_ttl_days(self):
        """Test URL with 0 TTL days."""
        resp = client.post("/api/v1/shorten", json={
            "target": "https://example.com",
            "ttl_days": 0
        })
        # Zero should be valid (expires immediately or treated as no TTL)
        assert resp.status_code in (200, 422)
    
    def test_negative_ttl_days(self):
        """Test URL with negative TTL days."""
        resp = client.post("/api/v1/shorten", json={
            "target": "https://example.com",
            "ttl_days": -5
        })
        # Negative TTL creates immediately expired URL
        alias = resp.json().get("alias")
        if alias:
            resp2 = client.get(f"/{alias}")
            assert resp2.status_code == 404
    
    def test_large_ttl_days(self):
        """Test URL with very large TTL."""
        resp = client.post("/api/v1/shorten", json={
            "target": "https://example.com",
            "ttl_days": 36500  # 100 years
        })
        assert resp.status_code == 200


class TestConcurrentClicks:
    """Test behavior under multiple clicks."""
    
    def test_multiple_clicks_increment_counter(self):
        """Test that multiple clicks increment the counter."""
        resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
        alias = resp.json()["alias"]
        
        # Make multiple requests
        for _ in range(5):
            client.get(f"/{alias}", allow_redirects=False)
        
        # Check counter
        resp = client.get(f"/api/v1/info/{alias}?api_key=changeme")
        assert resp.status_code == 200
        assert resp.json()["clicks"] >= 5
    
    def test_clicks_from_different_countries(self):
        """Test clicks from different countries."""
        from backend.app.database import get_session
        
        resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
        alias = resp.json()["alias"]
        
        # Manually add events from different countries
        session = next(get_session())
        url = session.exec(select(URL).where(URL.alias == alias)).first()
        
        for country in ["US", "GB", "JP", "DE", "FR"]:
            event = ClickEvent(url_id=url.id, country=country)
            session.add(event)
        session.commit()
        
        # Check geo analytics
        resp = client.get(f"/api/v1/analytics/{alias}/geo?api_key=changeme")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["by_country"]) == 5


class TestAnalyticsDateRange:
    """Test analytics with date range filtering."""
    
    def test_analytics_future_days_filter(self):
        """Test analytics with future days parameter."""
        resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
        alias = resp.json()["alias"]
        
        # Request analytics for future period
        resp = client.get(f"/api/v1/analytics/{alias}?days=365&api_key=changeme")
        assert resp.status_code == 200
        assert resp.json()["recent_days"] == 365
    
    def test_analytics_zero_days(self):
        """Test analytics with 0 days."""
        resp = client.post("/api/v1/shorten", json={"target": "https://example.com"})
        alias = resp.json()["alias"]
        
        resp = client.get(f"/api/v1/analytics/{alias}?days=0&api_key=changeme")
        assert resp.status_code == 200


class TestDataIntegrity:
    """Test data integrity across operations."""
    
    def test_url_info_consistency(self):
        """Test that info endpoint returns consistent data."""
        resp = client.post("/api/v1/shorten", json={
            "target": "https://example.com",
            "custom_alias": "mytest"
        })
        alias = resp.json()["alias"]
        
        resp1 = client.get(f"/api/v1/info/{alias}?api_key=changeme")
        data1 = resp1.json()
        
        # Verify all expected fields are present
        assert "alias" in data1
        assert "target" in data1
        assert "clicks" in data1
        assert "created_at" in data1
        assert "expires_at" in data1
        
        # Check values
        assert data1["alias"] == alias
        assert data1["target"] == "https://example.com/"  # May normalize URL
        assert data1["clicks"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
