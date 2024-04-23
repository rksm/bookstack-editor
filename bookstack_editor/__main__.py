import os
import sys
from pathlib import Path
from loguru import logger
from argparse import ArgumentParser
import dotenv

from bookstack_editor.api import Api, BOOKSTACK_FILE_NAME, BookstackRoot

logger.remove()
logger.add(sink=sys.stderr, level="INFO")


def main():
    parser = ArgumentParser()
    commands = parser.add_subparsers(dest="command")
    subparser = commands.add_parser("sync")
    subparser.add_argument("--force", action="store_true", help="force sync")
    args = parser.parse_args()

    wiki_dir = Path.cwd()
    bookstack_file = Path.cwd() / BOOKSTACK_FILE_NAME
    while not bookstack_file.exists():
        if wiki_dir == wiki_dir.parent:
            logger.error(f"No {BOOKSTACK_FILE_NAME} found")
            sys.exit(1)
        wiki_dir = wiki_dir.parent
        bookstack_file = wiki_dir / BOOKSTACK_FILE_NAME

    os.chdir(wiki_dir)

    if (wiki_dir / ".env").exists():
        dotenv.load_dotenv(wiki_dir / ".env")

    token_id = os.environ.get('BOOKSTACK_TOKEN_ID')
    if token_id is None:
        logger.error("BOOKSTACK_TOKEN_ID not found")
        sys.exit(1)
    token_secret = os.environ.get('BOOKSTACK_TOKEN_SECRET')
    if token_secret is None:
        logger.error("BOOKSTACK_TOKEN_SECRET not found")
        sys.exit(1)

    bookstack_wiki = BookstackRoot.model_validate_json(bookstack_file.read_text())
    api = Api(url=bookstack_wiki.url, token_id=token_id, token_secret=token_secret)
    bookstack_wiki.sync(wiki_dir, api, force=args.force)


if __name__ == '__main__':
    main()
