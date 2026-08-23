from __future__ import annotations

from pathlib import Path

from app.creators import load_creator_config, normalize_handle
from app.ingestion.base import IngestionResult
from app.services import sync_creators_from_config


class EmptyProvider:
    def backfill(self, _creator):
        return IngestionResult(posts=[], message="no posts")

    def incremental(self, _creator):
        return IngestionResult(posts=[], message="no posts")


def test_normalize_handle_accepts_url_and_at_prefix():
    assert normalize_handle("@NotJustABartender/") == "notjustabartender"
    assert normalize_handle("https://www.instagram.com/join_jules/") == "join_jules"


def test_load_creator_config(tmp_path: Path):
    path = tmp_path / "creators.yml"
    path.write_text(
        """
creators:
  - handle: "@TestCreator"
    profile_url: "https://www.instagram.com/testcreator/"
    active: true
"""
    )
    creators = load_creator_config(path)
    assert creators[0].handle == "testcreator"
    assert creators[0].active is True


def test_sync_creators_detects_new_creator(db_session, tmp_path: Path):
    path = tmp_path / "creators.yml"
    path.write_text(
        """
creators:
  - handle: notjustabartender
    profile_url: "https://www.instagram.com/notjustabartender/"
    active: true
"""
    )
    actions = sync_creators_from_config(db_session, path, provider=EmptyProvider())
    db_session.commit()
    assert actions[0].action == "backfill"
    assert actions[0].status == "backfill_no_posts"
