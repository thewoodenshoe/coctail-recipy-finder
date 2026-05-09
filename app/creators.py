from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class CreatorConfig:
    handle: str
    profile_url: str
    active: bool = True
    display_name: str | None = None


def normalize_handle(handle: str) -> str:
    cleaned = handle.strip()
    cleaned = cleaned.removeprefix("@")
    cleaned = cleaned.rstrip("/")
    if "instagram.com/" in cleaned:
        cleaned = cleaned.split("instagram.com/", 1)[1].split("/", 1)[0]
    return cleaned.lower()


def load_creator_config(path: Path) -> list[CreatorConfig]:
    if not path.exists():
        raise FileNotFoundError(f"Creator config not found: {path}")

    raw = yaml.safe_load(path.read_text()) or {}
    rows = raw.get("creators") or []
    creators: list[CreatorConfig] = []
    seen: set[str] = set()

    for row in rows:
        handle = normalize_handle(str(row["handle"]))
        if not handle:
            raise ValueError("Creator handle cannot be blank")
        if handle in seen:
            raise ValueError(f"Duplicate creator handle in config: {handle}")
        seen.add(handle)
        creators.append(
            CreatorConfig(
                handle=handle,
                profile_url=str(row["profile_url"]).strip(),
                active=bool(row.get("active", True)),
                display_name=row.get("display_name"),
            )
        )
    return creators
