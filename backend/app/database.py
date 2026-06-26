import os
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/url_shortener")

engine = create_engine(DATABASE_URL, echo=False)


def init_db(database_url: str | None = None):
    global engine
    if database_url:
        engine = create_engine(database_url, echo=False)
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
