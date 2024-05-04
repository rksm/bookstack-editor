import os
import sys
from pathlib import Path
from loguru import logger
from argparse import ArgumentParser
import dotenv

from bookstack_editor.api import Api, BOOKSTACK_FILE_NAME, BookstackRoot

logger.remove()
logger.add(sink=sys.stderr, level="INFO")


def _read_secret(wiki_dir: Path) -> tuple[str, str]:
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
    return token_id, token_secret


def main():
    parser = ArgumentParser()
    parser.add_argument("--dir", '-d', help="wiki directory", required=False)
    commands = parser.add_subparsers(dest="command")
    subparser = commands.add_parser("sync", help="sync wiki with online bookstack instance")
    subparser.add_argument("--force", action="store_true", help="force sync")
    subparser = commands.add_parser("page-link", help="get a link to a page / inside a page")
    subparser.add_argument(
        "file",
        help=
        "the markdown file representing the page in the format 'book-slug/page-slug.md' or 'book-slug/page-slug.md:line-number'"
    )
    args = parser.parse_args()

    if args.dir:
        os.chdir(args.dir)

    # find bookstack database file
    wiki_dir = Path.cwd()
    bookstack_file = Path.cwd() / BOOKSTACK_FILE_NAME
    while not bookstack_file.exists():
        if wiki_dir == wiki_dir.parent:
            logger.error(f"No {BOOKSTACK_FILE_NAME} found")
            sys.exit(1)
        wiki_dir = wiki_dir.parent
        bookstack_file = wiki_dir / BOOKSTACK_FILE_NAME

    os.chdir(wiki_dir)

    match args.command:
        case "sync":
            token_id, token_secret = _read_secret(wiki_dir)
            bookstack_wiki = BookstackRoot.model_validate_json(bookstack_file.read_text())
            api = Api(url=bookstack_wiki.url, token_id=token_id, token_secret=token_secret)
            bookstack_wiki.sync(wiki_dir, api, force=args.force)

        case "page-link":
            bookstack_wiki = BookstackRoot.model_validate_json(bookstack_file.read_text())
            link = bookstack_wiki.get_link(Path(args.file).expanduser())
            print(link)


if __name__ == '__main__':
    main()

Path("~/foo").is_absolute()
Path("~/foo").expanduser().is_absolute()
