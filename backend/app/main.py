from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Request, Depends
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, AnyUrl, field_validator
from sqlmodel import select
import os
import re
from contextlib import asynccontextmanager

from .database import init_db, get_session
from .models import URL, ClickEvent
from .utils import generate_alias
from .geo import get_country_from_ip
from .export import (
    generate_url_summary_csv,
    generate_daily_analytics_csv,
    generate_events_csv
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB (reads DATABASE_URL from env if not provided)
    init_db()
    yield

# Initialize FastAPI with documentation
app = FastAPI(
    title="URL Shortener MVP",
    description="A minimal URL shortener service with analytics and geographic tracking",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to specific domains in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "changeme")


class ShortenRequest(BaseModel):
    """Request model for creating a shortened URL.
    
    Attributes:
        target: The long URL to shorten (must be valid HTTP/HTTPS URL)
        custom_alias: Optional custom short alias (3-20 alphanumeric characters)
        ttl_days: Optional time-to-live in days (>0 or None for no expiration)
    """
    target: AnyUrl
    custom_alias: Optional[str] = None
    ttl_days: Optional[int] = None
    
    @field_validator('custom_alias')
    def validate_custom_alias(cls, v):
        if v in (None, ""):
            return None
        if not re.match(r'^[a-zA-Z0-9_-]{3,20}$', v):
            raise ValueError('Alias must be 3-20 characters: letters, numbers, -, _')
        return v
    
    @field_validator('ttl_days')
    def validate_ttl_days(cls, v):
        if v is not None and abs(v) > 36500:  # 100 years
            raise ValueError('ttl_days must be <= 36500 (100 years)')
        return v


class ShortenResponse(BaseModel):
    """Response model for shortened URL creation.
    
    Attributes:
        alias: The generated or custom short alias
        target: The target URL (echoed from request)
    """
    alias: str
    target: str

@app.post("/api/v1/shorten", response_model=ShortenResponse, tags=["URL Shortening"])
def create_short_url(body: ShortenRequest):
    """Create a new shortened URL.
    
    **Rate Limiting:** 100 requests per hour per IP (future implementation)
    
    Args:
        body: ShortenRequest with target URL and optional custom alias/TTL
    
    Returns:
        ShortenResponse with the generated alias and target URL
    
    Raises:
        HTTPException 409: If custom_alias already exists
        HTTPException 422: If request validation fails (invalid URL, alias format, TTL)
        HTTPException 500: If unable to generate unique alias
    """
    session = next(get_session())

    # handle custom alias
    if body.custom_alias:
        statement = select(URL).where(URL.alias == body.custom_alias)
        existing = session.exec(statement).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="alias already exists"
            )
        alias = body.custom_alias
    else:
        # generate until unique
        for _ in range(10):
            alias = generate_alias()
            statement = select(URL).where(URL.alias == alias)
            if not session.exec(statement).first():
                break
        else:
            raise HTTPException(status_code=500, detail="could not generate unique alias")

    expires_at = None
    if body.ttl_days is not None and body.ttl_days != 0:
        expires_at = datetime.utcnow() + timedelta(days=body.ttl_days)

    url = URL(alias=alias, target=str(body.target), expires_at=expires_at)
    session.add(url)
    session.commit()
    session.refresh(url)

    return ShortenResponse(alias=url.alias, target=url.target)


@app.get("/{alias}", tags=["Redirect"])
def redirect_alias(alias: str, request: Request):
    """Redirect to the target URL and record analytics.
    
    Increments click counter and records click event with IP, user-agent, and country.
    
    Args:
        alias: The shortened URL alias
        request: HTTP request (for IP and user-agent extraction)
    
    Returns:
        RedirectResponse to the target URL
    
    Raises:
        HTTPException 404: If alias not found or URL expired
    """
    session = next(get_session())
    statement = select(URL).where(URL.alias == alias)
    url = session.exec(statement).first()
    if not url:
        raise HTTPException(status_code=404, detail="not found")
    if url.expires_at and datetime.utcnow() > url.expires_at:
        raise HTTPException(status_code=404, detail="expired")

    # record click event with geographic data
    ip = request.client.host if request.client else None
    ua = request.headers.get('user-agent')
    country = get_country_from_ip(ip)
    event = ClickEvent(url_id=url.id, ip=ip, ua=ua, country=country)
    session.add(event)
    # also increment aggregate counter (fast read)
    url.clicks += 1
    session.add(url)
    session.commit()

    return RedirectResponse(url.target)


@app.get("/api/v1/info/{alias}", tags=["Admin Analytics"])
def info(alias: str, api_key: Optional[str] = None):
    """Get metadata for a shortened URL.
    
    **Authentication:** Requires admin API key via query parameter
    
    Args:
        alias: The shortened URL alias
        api_key: Admin API key for authentication
    
    Returns:
        JSON with URL metadata: alias, target, clicks, created_at, expires_at
    
    Raises:
        HTTPException 401: If API key is missing or incorrect
        HTTPException 404: If alias not found
    """
    if api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")
    session = next(get_session())
    statement = select(URL).where(URL.alias == alias)
    url = session.exec(statement).first()
    if not url:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "alias": url.alias,
        "target": url.target,
        "clicks": url.clicks,
        "created_at": url.created_at.isoformat(),
        "expires_at": url.expires_at.isoformat() if url.expires_at else None
    }


@app.get("/api/v1/analytics/{alias}", tags=["Admin Analytics"])
def analytics(alias: str, days: int = 7, api_key: Optional[str] = None):
    """Get temporal (daily) click analytics for a URL.
    
    **Authentication:** Requires admin API key
    
    Args:
        alias: The shortened URL alias
        days: Number of days to look back (default: 7)
        api_key: Admin API key for authentication
    
    Returns:
        JSON with daily click breakdown: alias, total_clicks, daily_counts (by date)
    
    Raises:
        HTTPException 401: If API key is missing or incorrect
        HTTPException 404: If alias not found
    """
    if api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")
    session = next(get_session())
    statement = select(URL).where(URL.alias == alias)
    url = session.exec(statement).first()
    if not url:
        raise HTTPException(status_code=404, detail="not found")

    # aggregate click events by day for the last `days` days
    cutoff = datetime.utcnow() - timedelta(days=days)
    stmt = select(ClickEvent).where(ClickEvent.url_id == url.id, ClickEvent.timestamp >= cutoff)
    events = session.exec(stmt).all()

    # bucket by date
    counts = {}
    for e in events:
        day = e.timestamp.date().isoformat()
        counts[day] = counts.get(day, 0) + 1

    return {
        "alias": alias,
        "total_clicks": url.clicks,
        "recent_days": days,
        "daily_counts": counts,
    }


@app.get("/api/v1/analytics/{alias}/geo", tags=["Admin Analytics"])
def analytics_by_country(alias: str, api_key: Optional[str] = None):
    """Get geographic (country-based) click analytics for a URL.
    
    **Authentication:** Requires admin API key
    
    Args:
        alias: The shortened URL alias
        api_key: Admin API key for authentication
    
    Returns:
        JSON with country breakdown: alias, by_country (dict), total_clicks
    
    Raises:
        HTTPException 401: If API key is missing or incorrect
        HTTPException 404: If alias not found
    """
    if api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")
    
    session = next(get_session())
    statement = select(URL).where(URL.alias == alias)
    url = session.exec(statement).first()
    if not url:
        raise HTTPException(status_code=404, detail="not found")
    
    # Aggregate clicks by country
    from sqlalchemy import func
    stmt = select(ClickEvent.country, func.count()).where(
        ClickEvent.url_id == url.id
    ).group_by(ClickEvent.country)
    
    results = session.exec(stmt).all()
    
    # Format as dict
    geo_data = {country: count for country, count in results}
    
    return {
        "alias": url.alias,
        "by_country": geo_data,
        "total_clicks": sum(geo_data.values())
    }


@app.get("/api/v1/export/url/{alias}", tags=["Export"])
def export_url_summary(alias: str, api_key: Optional[str] = None):
    """Export URL summary as CSV.
    
    **Authentication:** Requires admin API key
    
    Args:
        alias: The shortened URL alias
        api_key: Admin API key for authentication
    
    Returns:
        CSV file with URL metadata and statistics
    
    Raises:
        HTTPException 401: If API key is missing or incorrect
        HTTPException 404: If alias not found
    """
    if api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")
    
    session = next(get_session())
    statement = select(URL).where(URL.alias == alias)
    url = session.exec(statement).first()
    if not url:
        raise HTTPException(status_code=404, detail="not found")
    
    # Fetch all click events for this URL
    events = session.exec(
        select(ClickEvent).where(ClickEvent.url_id == url.id)
    ).all()
    
    csv_content = generate_url_summary_csv(url, events)
    
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=url_{alias}_summary.csv"}
    )


@app.get("/api/v1/export/analytics/{alias}", tags=["Export"])
def export_analytics_csv(alias: str, api_key: Optional[str] = None):
    """Export daily analytics as CSV.
    
    **Authentication:** Requires admin API key
    
    Args:
        alias: The shortened URL alias
        api_key: Admin API key for authentication
    
    Returns:
        CSV file with daily click breakdown
    
    Raises:
        HTTPException 401: If API key is missing or incorrect
        HTTPException 404: If alias not found
    """
    if api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")
    
    session = next(get_session())
    statement = select(URL).where(URL.alias == alias)
    url = session.exec(statement).first()
    if not url:
        raise HTTPException(status_code=404, detail="not found")
    
    events = session.exec(
        select(ClickEvent).where(ClickEvent.url_id == url.id)
    ).all()
    
    csv_content = generate_daily_analytics_csv(url, events)
    
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=analytics_{alias}.csv"}
    )


@app.get("/api/v1/export/events/{alias}", tags=["Export"])
def export_events_csv(alias: str, api_key: Optional[str] = None):
    """Export raw click events as CSV.
    
    **Authentication:** Requires admin API key
    
    **WARNING:** May contain sensitive data (IP addresses, user-agents).
    Ensure compliance with privacy policies before using.
    
    Args:
        alias: The shortened URL alias
        api_key: Admin API key for authentication
    
    Returns:
        CSV file with individual click events
    
    Raises:
        HTTPException 401: If API key is missing or incorrect
        HTTPException 404: If alias not found
    """
    if api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")
    
    session = next(get_session())
    statement = select(URL).where(URL.alias == alias)
    url = session.exec(statement).first()
    if not url:
        raise HTTPException(status_code=404, detail="not found")
    
    events = session.exec(
        select(ClickEvent).where(ClickEvent.url_id == url.id)
    ).all()
    
    csv_content = generate_events_csv(events)
    
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=events_{alias}.csv"}
    )