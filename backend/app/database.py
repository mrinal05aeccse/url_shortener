import os
from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")

# For SQLite only: allow multiple threads in dev
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    """
    Create database tables. Call at application startup.
    """
    SQLModel.metadata.create_all(engine)


def get_session():
    """
    Generator that yields a SQLModel Session so callers can call next(get_session()).
    Example (used in this project): session = next(get_session())
    """
    with Session(engine) as session:
        yield session