from __future__ import annotations

import re
from pathlib import Path

from app.config import get_settings
from app.ingestion.base import IngestedPost, IngestionResult
from app.models import Creator


POST_URL_RE = re.compile(r"https://www\.instagram\.com/(p|reel)/[A-Za-z0-9_-]+/?")
BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}


def save_instagram_session(session_state_path: Path, headless: bool = False) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed. Run: pip install -r requirements.txt") from exc

    session_state_path.expanduser().parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
        print("Log in to Instagram in the opened browser window.")
        print("When the Instagram home/profile page is fully loaded, return here and press Enter.")
        input()
        context.storage_state(path=str(session_state_path.expanduser()))
        browser.close()


class InstagramBrowserProvider:
    def __init__(self) -> None:
        settings = get_settings()
        self.session_state_path = settings.instagram_session_state_path.expanduser()
        self.backfill_max_posts = settings.instagram_backfill_max_posts
        self.incremental_max_posts = settings.instagram_incremental_max_posts
        self.unchanged_stop_count = settings.instagram_unchanged_stop_count

    def backfill(self, creator: Creator) -> IngestionResult:
        return self._sync_creator(creator, max_posts=self.backfill_max_posts, stop_on_known=False)

    def incremental(self, creator: Creator) -> IngestionResult:
        return self._sync_creator(creator, max_posts=self.incremental_max_posts, stop_on_known=True)

    def _sync_creator(self, creator: Creator, max_posts: int, stop_on_known: bool) -> IngestionResult:
        if not self.session_state_path.exists():
            raise RuntimeError(
                f"Instagram session state not found at {self.session_state_path}. "
                "Run: python -m app.cli instagram-auth"
            )

        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is not installed. Run: pip install -r requirements.txt") from exc

        posts: list[IngestedPost] = []
        known_unchanged = 0
        known_hashes = {post.source_url: post.content_hash for post in creator.posts}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(self.session_state_path))
            context.route("**/*", _abort_heavy_resources)
            page = context.new_page()
            profile_url = creator.profile_url.rstrip("/") + "/"
            page.goto(profile_url, wait_until="domcontentloaded", timeout=45000)
            urls = self._discover_post_urls(page, max_posts=max_posts)
            if not urls:
                browser.close()
                raise RuntimeError(
                    f"No Instagram post URLs discovered for @{creator.handle}. "
                    "The session may be logged out, challenged, or the profile markup changed."
                )

            for url in urls:
                try:
                    post_page = context.new_page()
                    post_page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    post_page.wait_for_timeout(1200)
                    raw_text = _clean_page_text(post_page.locator("body").inner_text(timeout=15000))
                    post_page.close()
                except PlaywrightTimeoutError:
                    continue

                caption_text = _extract_best_caption(raw_text)
                if not caption_text:
                    continue

                ingested = IngestedPost(
                    source_url=url,
                    caption_text=caption_text,
                    raw_text=raw_text,
                    external_post_id=_post_id_from_url(url),
                )
                posts.append(ingested)

                if stop_on_known and url in known_hashes:
                    known_unchanged += 1
                    if known_unchanged >= self.unchanged_stop_count:
                        break
                else:
                    known_unchanged = 0

            browser.close()

        return IngestionResult(posts=posts, message=f"Fetched text for {len(posts)} posts from @{creator.handle}")

    def _discover_post_urls(self, page, max_posts: int) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        stable_scrolls = 0

        while len(urls) < max_posts and stable_scrolls < 5:
            before = len(urls)
            for href in page.locator("a").evaluate_all("(links) => links.map((a) => a.href)"):
                match = POST_URL_RE.match(str(href))
                if match:
                    normalized = str(href).split("?")[0].rstrip("/") + "/"
                    if normalized not in seen:
                        seen.add(normalized)
                        urls.append(normalized)
                        if len(urls) >= max_posts:
                            break

            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(1500)
            stable_scrolls = stable_scrolls + 1 if len(urls) == before else 0

        return urls[:max_posts]


def _abort_heavy_resources(route) -> None:
    if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
        route.abort()
        return
    route.continue_()


def _clean_page_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    compacted = []
    previous = None
    for line in lines:
        if not line or line == previous:
            continue
        compacted.append(line)
        previous = line
    return "\n".join(compacted).strip()


def _extract_best_caption(raw_text: str) -> str:
    if not raw_text:
        return ""
    lines = raw_text.splitlines()
    content_lines = []
    skip_exact = {
        "Instagram",
        "Log in",
        "Sign up",
        "See more from",
        "Meta",
        "About",
        "Blog",
        "Jobs",
        "Help",
        "API",
        "Privacy",
        "Terms",
        "Locations",
    }
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped in skip_exact:
            continue
        if stripped.lower().startswith(("log in", "sign up", "view replies", "add a comment")):
            continue
        content_lines.append(stripped)
    return "\n".join(content_lines).strip()


def _post_id_from_url(url: str) -> str | None:
    parts = [part for part in url.split("/") if part]
    if len(parts) >= 2 and parts[-2] in {"p", "reel"}:
        return parts[-1]
    return None
