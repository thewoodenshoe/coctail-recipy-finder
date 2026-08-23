from __future__ import annotations

from sqlalchemy import text

from app.db import init_database, make_engine


def test_file_sqlite_uses_wal_and_waits_for_short_locks(tmp_path):
    database_path = tmp_path / "concurrent.db"
    engine = make_engine(f"sqlite:///{database_path}")
    init_database(engine)

    with engine.connect() as connection:
        journal_mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar_one()
        busy_timeout = connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one()

    assert journal_mode.lower() == "wal"
    assert busy_timeout == 30_000


def test_web_reads_continue_while_sync_holds_a_write_transaction(tmp_path):
    database_path = tmp_path / "concurrent.db"
    engine = make_engine(f"sqlite:///{database_path}")
    init_database(engine)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO creators (handle, profile_url, first_seen_at, sync_status, active)
                VALUES (
                    'test-creator',
                    'https://example.com/test-creator',
                    CURRENT_TIMESTAMP,
                    'never_synced',
                    1
                )
                """
            )
        )

    writer = engine.connect()
    try:
        writer.exec_driver_sql("BEGIN IMMEDIATE")
        writer.execute(
            text("UPDATE creators SET sync_status = 'syncing' WHERE handle = 'test-creator'")
        )

        with engine.connect() as reader:
            visible_status = reader.execute(
                text("SELECT sync_status FROM creators WHERE handle = 'test-creator'")
            ).scalar_one()

        assert visible_status == "never_synced"
    finally:
        writer.rollback()
        writer.close()
