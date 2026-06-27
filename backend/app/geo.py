"""
Geographic utility for IP geolocation.
Uses MaxMind GeoIP2 free database if available.
Gracefully degrades if database is unavailable.

Environment: GEOIP_DB_PATH (path to GeoLite2-City.mmdb, optional)
"""

import os
from typing import Optional

try:
    import geoip2.database
    GEOIP_AVAILABLE = True
except ImportError:
    GEOIP_AVAILABLE = False


GEOIP_DB_PATH = os.getenv("GEOIP_DB_PATH", "./data/GeoLite2-City.mmdb")


def get_country_from_ip(ip: Optional[str]) -> str:
    """
    Resolve IP address to 2-letter ISO country code.
    
    Args:
        ip: IP address to geolocate
        
    Returns:
        2-letter ISO country code, or "XX" if resolution fails
        
    Gracefully handles:
    - Missing or invalid IP
    - GeoIP2 library not installed
    - GeoIP database file not found
    - Geolocation lookup errors
    """
    if not ip:
        return "XX"
    
    if not GEOIP_AVAILABLE:
        # Library not installed; silently degrade
        return "XX"
    
    if not os.path.exists(GEOIP_DB_PATH):
        # Database file not found; silently degrade
        return "XX"
    
    try:
        with geoip2.database.Reader(GEOIP_DB_PATH) as reader:
            response = reader.city(ip)
            country = response.country.iso_code
            return country if country else "XX"
    except Exception as e:
        # Any error: geolocation fails silently
        # (In production, log this with structured logging)
        return "XX"
