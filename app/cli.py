from __future__ import annotations

import argparse
from pathlib import Path

from app.config import get_settings
from app.db import init_database, session_scope
from app.gold import migrate_legacy_to_gold, rebuild_gold_search_index
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

    if args.command == "import-caption":
        init_database()
        caption = Path(args.caption_file).read_text()
        with session_scope() as session:
            post = import_post(session, args.creator, args.url, caption)
            print(f"Imported post {post.id}: {post.source_url}")
        return


if __name__ == "__main__":
    main()
