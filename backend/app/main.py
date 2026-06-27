from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, status, Request, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, AnyUrl
from sqlmodel import select
import os

from .database import init_db, get_session
from .models import URL, ClickEvent
from .utils import generate_alias

app = FastAPI(title="URL Shortener MVP")

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "changeme")


class ShortenRequest(BaseModel):
    target: AnyUrl
    custom_alias: str | None = None
    ttl_days: int | None = None


class ShortenResponse(BaseModel):
    alias: str
    target: str


@app.on_event("startup")
def on_startup():
    # Initialize DB (reads DATABASE_URL from env if not provided)
    init_db()


@app.post("/api/v1/shorten", response_model=ShortenResponse)
def create_short_url(body: ShortenRequest):
    session = next(get_session())

    # handle custom alias
    if body.custom_alias:
        statement = select(URL).where(URL.alias == body.custom_alias)
        existing = session.exec(statement).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="alias already exists")
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
    if body.ttl_days and body.ttl_days > 0:
        expires_at = datetime.utcnow() + timedelta(days=body.ttl_days)

    url = URL(alias=alias, target=str(body.target), expires_at=expires_at)
    session.add(url)
    session.commit()
    session.refresh(url)

    return ShortenResponse(alias=url.alias, target=url.target)


@app.get("/{alias}")
def redirect_alias(alias: str, request: Request):
    session = next(get_session())
    statement = select(URL).where(URL.alias == alias)
    url = session.exec(statement).first()
    if not url:
        raise HTTPException(status_code=404, detail="not found")
    if url.expires_at and datetime.utcnow() > url.expires_at:
        raise HTTPException(status_code=404, detail="expired")

    # record click event
    ip = request.client.host if request.client else None
    ua = request.headers.get('user-agent')
    event = ClickEvent(url_id=url.id, ip=ip, ua=ua)
    session.add(event)
    # also increment aggregate counter (fast read)
    url.clicks += 1
    session.add(url)
    session.commit()

    return RedirectResponse(url.target)


@app.get("/api/v1/info/{alias}")
def info(alias: str, api_key: str | None = None):
    if api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")
    session = next(get_session())
    statement = select(URL).where(URL.alias == alias)
    url = session.exec(statement).first()
    if not url:
        raise HTTPException(status_code=404, detail="not found")
    return {"alias": url.alias, "target": url.target, "clicks": url.clicks, "created_at": url.created_at.isoformat(), "expires_at": url.expires_at.isoformat() if url.expires_at else None}


@app.get("/api/v1/analytics/{alias}")
def analytics(alias: str, days: int = 7, api_key: str | None = None):
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