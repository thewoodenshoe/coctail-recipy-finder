from __future__ import annotations

import httpx

from app.ingestion.instagram_public import (
    _extract_post_urls,
    _fetch_public_post,
    _is_rejected_shell,
    _post_id_from_url,
    extract_public_metadata,
)


def test_extract_public_metadata_from_og_and_json_ld():
    page_html = """
<html>
  <head>
    <meta property="og:title" content="PINK PONY CLUB on Instagram">
    <meta property="og:description" content="1.5 oz gin | .25 oz Campari | Shake hard">
    <meta property="og:image" content="https://cdn.example/image.jpg">
    <link rel="canonical" href="https://www.instagram.com/p/DXnYlmJjk48/">
    <script type="application/ld+json">
      {"description": "Garnish with lemon peel", "name": "Pink Pony Club"}
    </script>
  </head>
</html>
"""

    metadata = extract_public_metadata(page_html)

    assert metadata["title"] == "PINK PONY CLUB on Instagram"
    assert metadata["description"] == "1.5 oz gin | .25 oz Campari | Shake hard"
    assert metadata["image_url"] == "https://cdn.example/image.jpg"
    assert metadata["canonical_url"] == "https://www.instagram.com/p/DXnYlmJjk48/"
    assert "Garnish with lemon peel" in metadata["json_ld_text"]


def test_extract_post_urls_from_profile_html():
    urls = _extract_post_urls(
        """
        <a href="/p/ABC123/">one</a>
        <a href="https://www.instagram.com/reel/DEF456/?x=1">two</a>
        <a href="/not-a-post/NOPE/">no</a>
        """,
        "https://www.instagram.com/thirstywhale_/",
        max_posts=10,
    )

    assert urls == [
        "https://www.instagram.com/p/ABC123/",
        "https://www.instagram.com/reel/DEF456/",
    ]


def test_fetch_public_post_rejects_login_shell():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<html><body>Log in to continue</body></html>",
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    try:
        _fetch_public_post(client, "https://www.instagram.com/p/ABC123/")
    except RuntimeError as exc:
        assert "login/error shell" in str(exc)
    else:
        raise AssertionError("expected login shell rejection")


def test_post_id_from_url():
    assert _post_id_from_url("https://www.instagram.com/p/ABC123/") == "ABC123"
    assert _post_id_from_url("https://www.instagram.com/reel/DEF456/") == "DEF456"
    assert _post_id_from_url("https://www.instagram.com/thirstywhale_/") is None


def test_is_rejected_shell():
    assert _is_rejected_shell("Sorry, this page isn't available.")
    assert not _is_rejected_shell("Gin Sour\n2 oz gin\nShake hard")
