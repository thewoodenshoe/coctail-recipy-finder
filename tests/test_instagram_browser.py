from __future__ import annotations

from app.ingestion.instagram_browser import (
    _clean_page_text,
    _extract_best_caption,
    _normalize_post_url_candidates,
    _post_id_from_url,
)


def test_browser_text_helpers_extract_clean_caption():
    raw = """
Instagram
PINK PONY CLUB
PINK PONY CLUB
.25oz | 7.5ml Campari
.66oz | 20ml strawberry syrup
1.5oz | 45ml gin
Log in to like or comment.
"""

    cleaned = _clean_page_text(raw)
    caption = _extract_best_caption(cleaned)

    assert caption.startswith("PINK PONY CLUB")
    assert ".66oz | 20ml strawberry syrup" in caption
    assert "Log in to like" not in caption


def test_browser_text_helpers_reject_instagram_error_page():
    raw = """
2
Sorry, this page isn't available.
The link you followed may be broken, or the page may have been removed. Go back to Instagram.
Consumer Health Privacy
Popular
Instagram Lite
"""

    assert _extract_best_caption(raw) == ""


def test_post_id_from_instagram_url():
    assert _post_id_from_url("https://www.instagram.com/p/DXnYlmJjk48/") == "DXnYlmJjk48"
    assert _post_id_from_url("https://www.instagram.com/reel/ABC123/") == "ABC123"


def test_normalize_relative_and_absolute_post_urls():
    urls = _normalize_post_url_candidates(
        [
            "https://www.instagram.com/reel/DXnYlmJjk48/?x=1",
            "/p/ABC123/",
            "/not-a-post/ABC123/",
        ]
    )

    assert urls == [
        "https://www.instagram.com/reel/DXnYlmJjk48/",
        "https://www.instagram.com/p/ABC123/",
    ]
