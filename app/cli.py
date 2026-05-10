from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from time import perf_counter

from app.config import get_settings
from app.db import init_database, session_scope
from app.gold import (
    clear_all_data,
    migrate_legacy_to_gold,
    rebuild_gold_search_index,
    transform_raw_posts,
    upsert_raw_post_from_ingested,
)
from app.creators import normalize_handle
from app.ingestion.instagram_browser import discover_creator_post_urls, fetch_instagram_post_text
from app.models import Creator
from app.services import import_post, provider_for_name, reparse_posts, sync_creators_from_config


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Initialize database schema and search index")
    sync_parser = subparsers.add_parser("sync-creators", help="Sync creators from config/creators.yml")
    sync_parser.add_argument("--provider", default="public", choices=["public", "instagram-public", "browser", "instagram-browser"])
    sync_parser.add_argument("--force-backfill", action="store_true", help="Run backfill for active creators even if they were previously marked backfilled")
    sync_parser.add_argument("--creator", help="Sync only one creator handle from config/creators.yml")

    auth_parser = subparsers.add_parser("instagram-auth", help="Create an authorized Instagram browser session outside the repo")
    auth_parser.add_argument("--headless", action="store_true")

    subparsers.add_parser("reparse-posts", help="Rebuild extracted recipes and search index from stored raw text")
    subparsers.add_parser("migrate-to-gold", help="Copy legacy posts/recipes into raw/extraction/gold tables")
    subparsers.add_parser("rebuild-gold-search", help="Rebuild the gold recipe FTS index")
    subparsers.add_parser("clear-data", help="Delete all captured post, extraction, recipe, and search data")

    transform_parser = subparsers.add_parser("transform-raw", help="Transform raw_posts into recipe_extractions and gold_recipes")
    transform_parser.add_argument("--creator", help="Transform only one creator handle")

    download_parser = subparsers.add_parser("download-raw", help="Download Instagram raw text into raw_posts")
    download_parser.add_argument("--creator", required=True)
    download_parser.add_argument("--limit", type=int, default=10)
    download_parser.add_argument("--parallel", type=int, default=3)

    import_parser = subparsers.add_parser("import-caption", help="Import one pasted caption")
    import_parser.add_argument("--creator", required=True)
    import_parser.add_argument("--url", required=True)
    import_parser.add_argument("--caption-file", required=True)

    args = parser.parse_args()
    settings = get_settings()

    if args.command == "init-db":
        init_database()
        print("Database initialized")
        return

    if args.command == "sync-creators":
        init_database()
        with session_scope() as session:
            provider = provider_for_name(args.provider)
            actions = sync_creators_from_config(
                session,
                settings.creator_config_path,
                provider=provider,
                force_backfill=args.force_backfill,
                only_handle=args.creator,
            )
            for action in actions:
                detail = f" - {action.message}" if action.message else ""
                print(f"{action.handle}: {action.action} -> {action.status}{detail}")
        return

    if args.command == "instagram-auth":
        from app.ingestion.instagram_browser import save_instagram_session

        save_instagram_session(settings.instagram_session_state_path, headless=args.headless)
        print(f"Instagram session saved to {settings.instagram_session_state_path}")
        return

    if args.command == "reparse-posts":
        init_database()
        with session_scope() as session:
            count = reparse_posts(session)
            print(f"Reparsed {count} posts")
        return

    if args.command == "migrate-to-gold":
        init_database()
        with session_scope() as session:
            counts = migrate_legacy_to_gold(session)
            print(
                "Migrated legacy data to gold: "
                f"{counts['raw_posts']} raw_posts, "
                f"{counts['recipe_extractions']} recipe_extractions, "
                f"{counts['gold_recipes']} gold_recipes created"
            )
        return

    if args.command == "rebuild-gold-search":
        init_database()
        with session_scope() as session:
            count = rebuild_gold_search_index(session)
            print(f"Rebuilt gold search index for {count} recipes")
        return

    if args.command == "clear-data":
        init_database()
        with session_scope() as session:
            clear_all_data(session)
            print("Deleted post, raw, extraction, gold, and search data")
        return

    if args.command == "transform-raw":
        init_database()
        with session_scope() as session:
            counts = transform_raw_posts(session, normalize_handle(args.creator) if args.creator else None)
            print(
                "Transformed raw posts: "
                f"{counts['processed']} processed, "
                f"{counts['active']} active, "
                f"{counts['not_recipe']} not_recipe, "
                f"{counts['low_confidence']} low_confidence, "
                f"{counts['failed']} failed"
            )
        return

    if args.command == "download-raw":
        init_database()
        handle = normalize_handle(args.creator)
        with session_scope() as session:
            creator = session.query(Creator).filter(Creator.handle == handle).one_or_none()
            if creator is None:
                raise SystemExit(f"Creator not found in database: {handle}. Run sync-creators or add config first.")
            profile_url = creator.profile_url

        started = perf_counter()
        urls = discover_creator_post_urls(settings.instagram_session_state_path, profile_url, args.limit)
        print(f"Discovered {len(urls)} URLs for @{handle}")
        downloaded = 0
        fetch_seconds_total = 0.0
        with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as executor:
            futures = {
                executor.submit(fetch_instagram_post_text, settings.instagram_session_state_path, url): url
                for url in urls
            }
            for future in as_completed(futures):
                url = futures[future]
                try:
                    ingested = future.result()
                    with session_scope() as session:
                        creator = session.query(Creator).filter(Creator.handle == handle).one()
                        upsert_raw_post_from_ingested(
                            session,
                            creator,
                            ingested,
                            provider_name="instagram_browser",
                        )
                    downloaded += 1
                    fetch_seconds_total += ingested.fetch_seconds or 0
                    print(
                        f"Downloaded {downloaded}/{len(urls)} {url} "
                        f"({ingested.fetch_seconds or 0:.2f}s, committed)"
                    )
                except Exception as exc:
                    print(f"Failed {url}: {exc}")
        elapsed = perf_counter() - started
        avg = elapsed / downloaded if downloaded else 0
        avg_fetch = fetch_seconds_total / downloaded if downloaded else 0
        print(
            f"Download complete: {downloaded} posts, "
            f"total_seconds={elapsed:.2f}, avg_seconds_per_post={avg:.2f}, "
            f"avg_fetch_seconds_per_post={avg_fetch:.2f}"
        )
        return

    if args.command == "import-caption":
        init_database()
        caption = Path(args.caption_file).read_text()
        with session_scope() as session:
            post = import_post(session, args.creator, args.url, caption)
            print(f"Imported post {post.id}: {post.source_url}")
        return


if __name__ == "__main__":
    main()
