from typing import Optional
from datetime import datetime, timedelta
from sqlmodel import SQLModel, Field, Column, String
from sqlalchemy import func


class URL(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    alias: str = Field(sa_column=Column(String, unique=True, index=True))
    target: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    clicks: int = 0

