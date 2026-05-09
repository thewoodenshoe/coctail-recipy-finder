from __future__ import annotations

from app.ingestion.instagram_browser import _clean_page_text, _extract_best_caption, _post_id_from_url


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


def test_post_id_from_instagram_url():
    assert _post_id_from_url("https://www.instagram.com/p/DXnYlmJjk48/") == "DXnYlmJjk48"
    assert _post_id_from_url("https://www.instagram.com/reel/ABC123/") == "ABC123"
