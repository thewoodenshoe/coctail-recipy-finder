from __future__ import annotations

import argparse
from pathlib import Path

from app.config import get_settings
from app.db import init_database, session_scope
from app.services import import_post, sync_creators_from_config


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Initialize database schema and search index")
    subparsers.add_parser("sync-creators", help="Sync creators from config/creators.yml")

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
            actions = sync_creators_from_config(session, settings.creator_config_path)
            for action in actions:
                detail = f" - {action.message}" if action.message else ""
                print(f"{action.handle}: {action.action} -> {action.status}{detail}")
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
