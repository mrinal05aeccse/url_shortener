import os
from sqlmodel import SQLModel, create_engine, Session

def get_engine():
    database_url = os.getenv("DATABASE_URL", "sqlite:///./data.db")
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, echo=False, connect_args=connect_args)

def init_db() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)

def get_session():
    engine = get_engine()
    with Session(engine) as session:
        yield session