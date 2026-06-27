"""
Unit tests for backend utility functions and models.
"""

import pytest
from app.utils import generate_alias
from app.geo import get_country_from_ip
from app.models import URL, ClickEvent
from datetime import datetime, timedelta


class TestAliasGeneration:
    """Tests for URL alias generation utility."""
    
    def test_generate_alias_length(self):
        """Test that generated alias has correct length."""
        alias = generate_alias()
        assert len(alias) == 6  # Default length
        
    def test_generate_alias_custom_length(self):
        """Test alias generation with custom length."""
        for length in [3, 5, 10, 20]:
            alias = generate_alias(length=length)
            assert len(alias) == length
    
    def test_generate_alias_characters(self):
        """Test that alias contains only valid characters."""
        import string
        valid_chars = set(string.ascii_letters + string.digits)
        
        for _ in range(10):
            alias = generate_alias()
            for char in alias:
                assert char in valid_chars
    
    def test_generate_alias_randomness(self):
        """Test that generated aliases are reasonably random."""
        aliases = [generate_alias() for _ in range(100)]
        
        # Should have high uniqueness
        unique_aliases = set(aliases)
        assert len(unique_aliases) > 95  # At least 95% unique
        
    def test_generate_alias_not_empty(self):
        """Test that alias is never empty."""
        for _ in range(20):
            alias = generate_alias()
            assert len(alias) > 0
            assert alias.strip() == alias


class TestGeolocation:
    """Tests for IP geolocation utility."""
    
    def test_get_country_from_ip_invalid_ip(self):
        """Test geolocation with invalid IP."""
        # Invalid IPs should default to "XX"
        assert get_country_from_ip("invalid") == "XX"
        assert get_country_from_ip("999.999.999.999") == "XX"
    
    def test_get_country_from_ip_none(self):
        """Test geolocation with None input."""
        assert get_country_from_ip(None) == "XX"
    
    def test_get_country_from_ip_empty_string(self):
        """Test geolocation with empty string."""
        assert get_country_from_ip("") == "XX"
    
    def test_get_country_from_ip_private_ip(self):
        """Test geolocation with private IPs (should default to XX if DB unavailable)."""
        # These will return "XX" if GeoIP DB is not available
        result = get_country_from_ip("192.168.1.1")
        assert result == "XX"  # Default for private IPs or missing DB
        
        result = get_country_from_ip("10.0.0.1")
        assert result == "XX"
    
    def test_get_country_from_ip_format(self):
        """Test that result is always 2-letter uppercase code."""
        result = get_country_from_ip("192.0.2.1")
        assert isinstance(result, str)
        assert len(result) == 2
        assert result.isupper()


class TestURLModel:
    """Tests for URL model validation and behavior."""
    
    def test_url_model_creation(self):
        """Test basic URL model creation."""
        url = URL(
            alias="test123",
            target="https://example.com"
        )
        assert url.alias == "test123"
        assert url.target == "https://example.com"
        assert url.clicks == 0
    
    def test_url_with_expiration(self):
        """Test URL model with expiration."""
        expires = datetime.utcnow() + timedelta(days=7)
        url = URL(
            alias="test123",
            target="https://example.com",
            expires_at=expires
        )
        assert url.expires_at == expires
    
    def test_url_created_at_default(self):
        """Test that created_at is set to current time."""
        url = URL(alias="test", target="https://example.com")
        assert url.created_at is not None
        # Should be very recent
        assert (datetime.utcnow() - url.created_at).total_seconds() < 1
    
    def test_url_clicks_default(self):
        """Test that clicks defaults to 0."""
        url = URL(alias="test", target="https://example.com")
        assert url.clicks == 0


class TestClickEventModel:
    """Tests for ClickEvent model."""
    
    def test_click_event_creation(self):
        """Test basic ClickEvent creation."""
        event = ClickEvent(url_id=1)
        assert event.url_id == 1
        assert event.country == "XX"  # Default
    
    def test_click_event_with_country(self):
        """Test ClickEvent with country code."""
        event = ClickEvent(url_id=1, country="US")
        assert event.country == "US"
    
    def test_click_event_with_metadata(self):
        """Test ClickEvent with IP and user-agent."""
        event = ClickEvent(
            url_id=1,
            ip="192.0.2.1",
            ua="Mozilla/5.0...",
            country="GB"
        )
        assert event.ip == "192.0.2.1"
        assert event.ua == "Mozilla/5.0..."
        assert event.country == "GB"
    
    def test_click_event_timestamp_default(self):
        """Test that timestamp is set to current time."""
        event = ClickEvent(url_id=1)
        assert event.timestamp is not None
        assert (datetime.utcnow() - event.timestamp).total_seconds() < 1


class TestExportUtilities:
    """Tests for CSV export utilities."""
    
    def test_export_imports(self):
        """Test that export module can be imported."""
        try:
            from app.export import (
                generate_url_summary_csv,
                generate_daily_analytics_csv,
                generate_events_csv
            )
            assert callable(generate_url_summary_csv)
            assert callable(generate_daily_analytics_csv)
            assert callable(generate_events_csv)
        except ImportError:
            pytest.fail("Export module import failed")
    
    def test_csv_output_format(self):
        """Test that CSV output is valid."""
        from app.export import generate_url_summary_csv
        
        url = URL(alias="test", target="https://example.com")
        events = []
        
        csv_content = generate_url_summary_csv(url, events)
        
        # Should be a string
        assert isinstance(csv_content, str)
        # Should contain header
        assert "alias" in csv_content
        # Should contain data
        assert "test" in csv_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
