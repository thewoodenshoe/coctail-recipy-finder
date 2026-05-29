from __future__ import annotations

import argparse
from pathlib import Path

from app.config import get_settings
from app.db import init_database, session_scope
from app.gold import (
    clear_all_data,
    rebuild_gold_search_index,
    transform_raw_posts,
)
from app.creators import normalize_handle
from app.services import (
    import_instagram_jsonl_to_gold,
    provider_for_name,
    sync_creators_from_config,
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Initialize database schema and search index")
    sync_parser = subparsers.add_parser("sync-creators", help="Sync creators from config/creators.yml")
    sync_parser.add_argument("--provider", default="public", choices=["public", "instagram-public"])
    sync_parser.add_argument("--force-backfill", action="store_true", help="Run backfill for active creators even if they were previously marked backfilled")
    sync_parser.add_argument("--creator", help="Sync only one creator handle from config/creators.yml")

    subparsers.add_parser("rebuild-gold-search", help="Rebuild the gold recipe FTS index")
    subparsers.add_parser("clear-data", help="Delete all captured post, extraction, recipe, and search data")

    transform_parser = subparsers.add_parser("transform-raw", help="Transform raw_posts into recipe_extractions and gold_recipes")
    transform_parser.add_argument("--creator", help="Transform only one creator handle")

    import_jsonl_parser = subparsers.add_parser("import-jsonl", help="Import captured Instagram JSONL rows")
    import_jsonl_parser.add_argument("--creator", required=True)
    import_jsonl_parser.add_argument("--jsonl-file", required=True)
    import_jsonl_parser.add_argument("--profile-url")
    import_jsonl_parser.add_argument("--skip-transform", action="store_true")
    import_jsonl_parser.add_argument(
        "--replace-creator-data",
        action="store_true",
        help="Delete existing raw/extracted/gold rows for this creator before importing",
    )

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

    if args.command == "import-jsonl":
        init_database()
        with session_scope() as session:
            result = import_instagram_jsonl_to_gold(
                session,
                args.creator,
                Path(args.jsonl_file),
                profile_url=args.profile_url,
                transform=not args.skip_transform,
                replace_creator_data=args.replace_creator_data,
            )
            print(
                f"Imported @{result.creator_handle}: "
                f"{result.rows_seen} rows seen, "
                f"{result.imported} imported, "
                f"{result.skipped} skipped, "
                f"{result.active} active, "
                f"{result.not_recipe} not_recipe, "
                f"{result.low_confidence} low_confidence, "
                f"{result.failed} failed"
            )
        return


if __name__ == "__main__":
    main()
