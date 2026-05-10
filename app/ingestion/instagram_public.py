from __future__ import annotations

import html
import json
import re
import time
from time import perf_counter
from typing import Any
from urllib.parse import urljoin

import httpx

from app.config import get_settings
from app.ingestion.base import IngestedPost, IngestionResult
from app.models import Creator


POST_URL_RE = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:[A-Za-z0-9_.]+/)?(?:p|reel)/[A-Za-z0-9_-]+/?"
    r"|/(?:[A-Za-z0-9_.]+/)?(?:p|reel)/[A-Za-z0-9_-]+/?"
)
META_RE = re.compile(
    r"<meta\s+[^>]*(?:property|name)=[\"'](?P<name>og:title|og:description|og:image|twitter:title|twitter:description|twitter:image)[\"'][^>]*>",
    re.IGNORECASE,
)
CONTENT_RE = re.compile(r"content=[\"'](?P<content>.*?)[\"']", re.IGNORECASE | re.DOTALL)
CANONICAL_RE = re.compile(
    r"<link\s+[^>]*rel=[\"']canonical[\"'][^>]*href=[\"'](?P<href>.*?)[\"'][^>]*>",
    re.IGNORECASE | re.DOTALL,
)
JSON_LD_RE = re.compile(
    r"<script\s+[^>]*type=[\"']application/ld\+json[\"'][^>]*>(?P<json>.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


class InstagramPublicProvider:
    """Conservative public HTTP provider.

    This provider uses normal unauthenticated HTTP GET requests only. It does not
    use account sessions, browser automation, CAPTCHA handling, proxies, or retry
    behavior intended to work around platform controls.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.backfill_max_posts = settings.instagram_public_backfill_max_posts
        self.incremental_max_posts = settings.instagram_public_incremental_max_posts
        self.request_delay_seconds = settings.instagram_public_request_delay_seconds

    def backfill(self, creator: Creator) -> IngestionResult:
        return self._fetch_creator(creator, max_posts=self.backfill_max_posts)

    def incremental(self, creator: Creator) -> IngestionResult:
        return self._fetch_creator(creator, max_posts=self.incremental_max_posts)

    def _fetch_creator(self, creator: Creator, max_posts: int) -> IngestionResult:
        posts: list[IngestedPost] = []
        failures: list[str] = []
        with httpx.Client(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "CocktailRecipeFinder/1.0 (+public source index)"},
        ) as client:
            profile_html = _get_public_html(client, creator.profile_url)
            urls = _extract_post_urls(profile_html, creator.profile_url, max_posts)
            for url in urls:
                time.sleep(max(0, self.request_delay_seconds))
                try:
                    posts.append(_fetch_public_post(client, url))
                except Exception as exc:
                    failures.append(f"{url}: {exc}")
        message = f"Fetched {len(posts)} public posts for @{creator.handle}"
        if failures:
            message += f"; {len(failures)} failed"
        if not posts and failures:
            message += f" - first failure: {failures[0]}"
        if not posts and not failures:
            message += "; no public post URLs found"
        return IngestionResult(posts=posts, message=message)


def _fetch_public_post(client: httpx.Client, source_url: str) -> IngestedPost:
    started = perf_counter()
    page_html = _get_public_html(client, source_url)
    metadata = extract_public_metadata(page_html)
    canonical_url = metadata.get("canonical_url") or source_url
    source_text = _source_text_from_metadata(metadata)
    if not source_text:
        raise RuntimeError("No public metadata or text extracted")
    if _is_rejected_shell(source_text):
        raise RuntimeError("Public response was an Instagram login/error shell")
    return IngestedPost(
        source_url=canonical_url,
        caption_text=source_text,
        raw_text=source_text,
        external_post_id=_post_id_from_url(canonical_url),
        raw_thumbnail_url=metadata.get("image_url"),
        image_capture_status="metadata_only" if metadata.get("image_url") else "missing_public_image_metadata",
        fetch_seconds=perf_counter() - started,
    )


def _get_public_html(client: httpx.Client, url: str) -> str:
    response = client.get(url)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type:
        raise RuntimeError(f"Expected HTML response, got {content_type or 'unknown content type'}")
    return response.text


def extract_public_metadata(page_html: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for match in META_RE.finditer(page_html):
        tag = match.group(0)
        content_match = CONTENT_RE.search(tag)
        if not content_match:
            continue
        name = match.group("name").lower()
        content = html.unescape(content_match.group("content")).strip()
        if name in {"og:title", "twitter:title"}:
            metadata.setdefault("title", content)
        elif name in {"og:description", "twitter:description"}:
            metadata.setdefault("description", content)
        elif name in {"og:image", "twitter:image"}:
            metadata.setdefault("image_url", content)
    canonical_match = CANONICAL_RE.search(page_html)
    if canonical_match:
        metadata["canonical_url"] = html.unescape(canonical_match.group("href")).strip()
    json_ld_text = _json_ld_text(page_html)
    if json_ld_text:
        metadata["json_ld_text"] = json_ld_text
    body_text = _visible_text(page_html)
    if body_text:
        metadata["body_text"] = body_text
    return metadata


def _extract_post_urls(profile_html: str, profile_url: str, max_posts: int) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in POST_URL_RE.finditer(profile_html):
        raw_url = match.group(0)
        absolute_url = urljoin(profile_url, raw_url).split("?")[0].rstrip("/") + "/"
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        urls.append(absolute_url)
        if len(urls) >= max_posts:
            break
    return urls


def _source_text_from_metadata(metadata: dict[str, str]) -> str:
    parts = [
        metadata.get("title", ""),
        metadata.get("description", ""),
        metadata.get("json_ld_text", ""),
        metadata.get("body_text", ""),
    ]
    return _clean_text("\n".join(part for part in parts if part))


def _json_ld_text(page_html: str) -> str:
    values: list[str] = []
    for match in JSON_LD_RE.finditer(page_html):
        raw = html.unescape(match.group("json")).strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        values.extend(_text_values(parsed))
    return _clean_text("\n".join(values))


def _text_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(_text_values(item))
        return values
    if isinstance(value, dict):
        values = []
        for key, item in value.items():
            if key in {"caption", "description", "headline", "name", "text", "articleBody"}:
                values.extend(_text_values(item))
        return values
    return []


def _visible_text(page_html: str) -> str:
    no_scripts = SCRIPT_STYLE_RE.sub(" ", page_html)
    text = TAG_RE.sub(" ", no_scripts)
    return _clean_text(html.unescape(text))


def _clean_text(value: str) -> str:
    lines = [line.strip() for line in re.split(r"[\r\n]+", value)]
    compacted = []
    previous = None
    for line in lines:
        line = re.sub(r"\s+", " ", line).strip()
        if not line or line == previous:
            continue
        compacted.append(line)
        previous = line
    return "\n".join(compacted).strip()


def _is_rejected_shell(text: str) -> bool:
    lower = text.lower()
    return any(
        marker in lower
        for marker in (
            "log in to continue",
            "sorry, this page isn't available",
            "the link you followed may be broken",
            "page may have been removed",
            "age-restricted content",
        )
    )


def _post_id_from_url(url: str) -> str | None:
    parts = [part for part in url.split("/") if part]
    if len(parts) >= 2 and parts[-2] in {"p", "reel"}:
        return parts[-1]
    return None
