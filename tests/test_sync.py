from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.ingestion.base import IngestionResult
from app.models import Creator, GoldRecipe, RawPost
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


def test_force_backfill_overrides_existing_backfill_status(db_session, tmp_path: Path):
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
    path.write_text(
        """
creators:
  - handle: oldcreator
    profile_url: "https://www.instagram.com/oldcreator/"
    active: true
"""
    )

    actions = sync_creators_from_config(
        db_session,
        path,
        provider=FailingProvider(),
        force_backfill=True,
    )

    assert actions[0].action == "backfill"


def test_sync_can_limit_to_one_creator(db_session, tmp_path: Path):
    path = tmp_path / "creators.yml"
    write_config(path)

    actions = sync_creators_from_config(
        db_session,
        path,
        provider=FailingProvider(),
        only_handle="oldcreator",
    )

    assert [action.handle for action in actions] == ["oldcreator"]


def test_sync_writes_raw_and_gold_records(db_session, tmp_path: Path):
    class RecipeProvider:
        def backfill(self, creator):
            from app.ingestion.base import IngestedPost

            return IngestionResult(
                posts=[
                    IngestedPost(
                        source_url="https://www.instagram.com/p/DXnYlmJjk48/",
                        caption_text="PINK PONY CLUB\n1.5oz | 45ml gin\nShake hard.",
                        raw_text="raw page text\nPINK PONY CLUB\n1.5oz | 45ml gin\nShake hard.",
                    )
                ],
                message="ok",
            )

        def incremental(self, creator):
            return self.backfill(creator)

    path = tmp_path / "creators.yml"
    path.write_text(
        """
creators:
  - handle: notjustabartender
    profile_url: "https://www.instagram.com/notjustabartender/"
    active: true
"""
    )

    actions = sync_creators_from_config(db_session, path, provider=RecipeProvider())
    db_session.commit()

    assert actions[0].status == "backfilled"
    assert db_session.query(RawPost).count() == 1
    assert db_session.query(GoldRecipe).count() == 1


def test_backfill_without_posts_does_not_mark_backfill_complete(db_session, tmp_path: Path):
    class EmptyProvider:
        def backfill(self, creator):
            return IngestionResult(posts=[], message="no posts")

        def incremental(self, creator):
            return IngestionResult(posts=[], message="no posts")

    path = tmp_path / "creators.yml"
    path.write_text(
        """
creators:
  - handle: thirstywhale_
    profile_url: "https://www.instagram.com/thirstywhale_/"
    active: true
"""
    )

    actions = sync_creators_from_config(db_session, path, provider=EmptyProvider())
    db_session.commit()

    creator = db_session.query(Creator).filter(Creator.handle == "thirstywhale_").one()
    assert actions[0].status == "backfill_no_posts"
    assert creator.sync_status == "backfill_no_posts"
    assert creator.backfill_completed_at is None
