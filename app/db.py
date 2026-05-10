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
    add_raw_post_media_columns(db_engine)
    drop_obsolete_sqlite_tables(db_engine)
    create_gold_search_index(db_engine)


def add_raw_post_media_columns(db_engine: Engine) -> None:
    if db_engine.dialect.name != "sqlite":
        return
    columns = {
        "raw_thumbnail_url": "TEXT",
        "local_image_path": "TEXT",
        "image_capture_status": "VARCHAR(64)",
        "image_capture_error": "TEXT",
    }
    with db_engine.begin() as connection:
        existing = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(raw_posts)")).all()
        }
        for column_name, column_type in columns.items():
            if column_name not in existing:
                connection.execute(text(f"ALTER TABLE raw_posts ADD COLUMN {column_name} {column_type}"))


def drop_obsolete_sqlite_tables(db_engine: Engine) -> None:
    if db_engine.dialect.name != "sqlite":
        return
    with db_engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS search_index"))
        connection.execute(text("DROP TABLE IF EXISTS recipes"))
        connection.execute(text("DROP TABLE IF EXISTS posts"))


def create_gold_search_index(db_engine: Engine) -> None:
    with db_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS gold_recipe_search_index USING fts5(
                    gold_recipe_id UNINDEXED,
                    source_url UNINDEXED,
                    creator_handle,
                    drink_title,
                    drink_title_normalized,
                    base_spirits,
                    ingredient_names,
                    tags,
                    intro_text,
                    raw_fallback_text
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
