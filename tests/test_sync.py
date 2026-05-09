from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.ingestion.base import IngestionResult
from app.models import Creator
from app.services import sync_creators_from_config, sync_decision


class FailingProvider:
    def backfill(self, creator):
        if creator.handle == "badcreator":
            raise RuntimeError("provider failed")
        return IngestionResult(posts=[], message="ok")

    def incremental(self, creator):
        return IngestionResult(posts=[], message="incremental ok")


def write_config(path: Path) -> None:
    path.write_text(
        """
creators:
  - handle: newcreator
    profile_url: "https://www.instagram.com/newcreator/"
    active: true
  - handle: oldcreator
    profile_url: "https://www.instagram.com/oldcreator/"
    active: true
  - handle: inactivecreator
    profile_url: "https://www.instagram.com/inactivecreator/"
    active: false
  - handle: badcreator
    profile_url: "https://www.instagram.com/badcreator/"
    active: true
"""
    )


def test_sync_decision_rules():
    assert sync_decision(Creator(handle="x", profile_url="x", active=False)) == "skip"
    assert sync_decision(Creator(handle="x", profile_url="x", active=True)) == "backfill"
    assert (
        sync_decision(
            Creator(
                handle="x",
                profile_url="x",
                active=True,
                backfill_completed_at=datetime.now(timezone.utc),
            )
        )
        == "incremental"
    )


def test_sync_records_failures_without_crashing(db_session, tmp_path: Path):
    old = Creator(
        handle="oldcreator",
        profile_url="https://www.instagram.com/oldcreator/",
        active=True,
        backfill_completed_at=datetime.now(timezone.utc),
        sync_status="backfilled",
    )
    db_session.add(old)
    db_session.commit()

    path = tmp_path / "creators.yml"
    write_config(path)
    actions = sync_creators_from_config(db_session, path, provider=FailingProvider())
    db_session.commit()

    by_handle = {action.handle: action for action in actions}
    assert by_handle["newcreator"].action == "backfill"
    assert by_handle["oldcreator"].action == "incremental"
    assert by_handle["inactivecreator"].action == "skip"
    assert by_handle["badcreator"].status == "failed"
