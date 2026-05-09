from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base


def _ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    raw_path = database_url.replace("sqlite:///", "", 1)
    if raw_path == ":memory:":
        return
    Path(raw_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def make_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().database_url
    _ensure_sqlite_parent(url)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_database(db_engine: Engine = engine) -> None:
    Base.metadata.create_all(bind=db_engine)
    migrate_sqlite_schema(db_engine)
    create_search_index(db_engine)


def migrate_sqlite_schema(db_engine: Engine) -> None:
    if db_engine.dialect.name != "sqlite":
        return
    with db_engine.begin() as connection:
        columns = {
            row["name"]
            for row in connection.execute(text("PRAGMA table_info(posts)")).mappings().all()
        }
        additions = {
            "raw_text": "ALTER TABLE posts ADD COLUMN raw_text TEXT",
            "raw_fetched_at": "ALTER TABLE posts ADD COLUMN raw_fetched_at DATETIME",
            "last_seen_at": "ALTER TABLE posts ADD COLUMN last_seen_at DATETIME",
        }
        for column, statement in additions.items():
            if column not in columns:
                connection.execute(text(statement))


def create_search_index(db_engine: Engine) -> None:
    with db_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
                    post_id UNINDEXED,
                    creator_handle,
                    source_url,
                    caption_text,
                    drink_name,
                    base_spirit,
                    ingredients,
                    method,
                    tags
                )
                """
            )
        )


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@contextmanager
def session_scope() -> Iterator[Session]:
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
