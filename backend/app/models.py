from typing import Optional
from datetime import datetime, timedelta
from sqlmodel import SQLModel, Field, Column, String, Relationship
from typing import List


class URL(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    alias: str = Field(sa_column=Column(String, unique=True, index=True))
    target: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    clicks: int = 0
    events: List['ClickEvent'] = Relationship(back_populates='url')


class ClickEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url_id: int = Field(foreign_key='url.id', index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip: Optional[str] = None
    ua: Optional[str] = None
    country: Optional[str] = Field(default="XX")  # ISO 2-letter country code

    url: Optional[URL] = Relationship(back_populates='events')