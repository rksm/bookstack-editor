import os
import sys
from typing import Generic, TypeVar
import bookstack
import pydantic
from pathlib import Path
from pprint import pp
from tqdm import tqdm
from loguru import logger
from argparse import ArgumentParser
import dotenv

logger.remove()
logger.add(sink=sys.stderr, level="INFO")

DataT = TypeVar('DataT')


class Payload(pydantic.BaseModel, Generic[DataT]):
    data: DataT


class PagesData(pydantic.BaseModel):
    name: str
    id: int
    slug: str
    book_slug: str
    book_id: int
    chapter_id: int
    draft: bool
    template: bool
    created_at: str
    updated_at: str
    priority: int
    owned_by: int
    created_by: int
    updated_by: int
    revision_count: int
    editor: str

    def key(self) -> str:
        return f"{self.book_slug}/{self.slug}"

    def url(self, base_url: str) -> str:
        return f"{base_url}/books/{self.book_slug}/page/{self.slug}"

    def update(self, api: 'Api', markdown: str) -> None:
        payload: dict = self.model_dump()
        payload["markdown"] = markdown
        payload["editor"] = "markdown"
        if self.chapter_id == 0:
            del payload["chapter_id"]
        elif self.book_id == 0:
            del payload["book_id"]
        new_data = api.put_pages_update(payload)
        if updated_at := new_data.get("updated_at"):
            self.updated_at = updated_at
        if book_id := new_data.get("book_id"):
            self.book_id = book_id
        if book_slug := new_data.get("book_slug"):
            self.book_slug = book_slug
        if chapter_id := new_data.get("chapter_id"):
            self.chapter_id = chapter_id
        if name := new_data.get("name"):
            self.name = name


class DownloadedPage(pydantic.BaseModel):
    path_markdown: Path
    # path_html: Path
    data: PagesData
    last_modified: float = 0

    def key(self) -> str:
        return self.data.key()

    def url(self, base_url: str) -> str:
        return self.data.url(base_url)

    def is_modified(self) -> bool:
        return self.path_markdown.stat().st_mtime != self.last_modified


class Api():
    api: bookstack.BookStack

    def __init__(self, api: bookstack.BookStack):
        api.generate_api_methods()
        self.api = api

    def print_available_api_methods(self) -> None:
        pp(self.api.available_api_methods)

    def get_pages_list(self) -> Payload[list[PagesData]]:
        raw = self.api.get_pages_list()  # type: ignore
        return Payload[list[PagesData]].model_validate(raw)

    def get_pages_export_html(self, page_id: int) -> str:
        return self.api.get_pages_export_html({"id": page_id})  # type: ignore

    def get_pages_export_markdown(self, page_id: int) -> str:
        markdown: str = self.api.get_pages_export_markdown({"id": page_id})  # type: ignore
        if markdown.startswith("# "):
            lines = markdown.splitlines()[1:]
            markdown = "\n".join(lines).strip()
        return markdown

    def get_pages_export_pdf(self, page_id: int) -> str:
        return self.api.get_pages_export_pdf({"id": page_id})  # type: ignore

    def get_pages_export_plain_text(self, page_id: int) -> str:
        return self.api.get_pages_export_plain_text({"id": page_id})  # type: ignore

    def put_pages_update(self, data: dict) -> dict:
        result = self.api.put_pages_update(data)  # type: ignore
        if result.get("error"):
            message = result.get("message") or str(result)
            code = result.get("code")
            id = data.get("id") or data.get("page_id") or "unknown page"
            logger.error(f"Error updating {id}: {message} ({code})")
        return result


class BookstackRoot(pydantic.BaseModel):
    url: str
    pages: dict[str, DownloadedPage]

    def sync(self, root_dir: Path, api: Api, force: bool) -> None:
        pages = api.get_pages_list()

        new_downloaded_pages = BookstackRoot(url=self.url, pages={})

        new_pages = {page.key(): page for page in pages.data}
        modified_pages = {page.key(): page for page in self.pages.values() if page.is_modified()}
        removed_pages = self.pages.keys() - new_pages.keys()
        old_book_dirs: set[str] = set()

        for key in removed_pages:
            page = self.pages[key]
            if page.is_modified():
                logger.warning(
                    f"[sync] {page.path_markdown} was removed upstream but has local changes, skipping removal")
                new_downloaded_pages.pages[key] = page
                continue
            logger.info(f"[sync] removing {page.path_markdown}")
            page.path_markdown.unlink()
            # if page.path_html.exists():
            #     page.path_html.unlink()
            old_book_dirs.add(page.data.book_slug)

        for old_book_dir in old_book_dirs:
            book_path = root_dir / old_book_dir
            if not list(book_path.iterdir()):
                logger.info(f"[sync] removing {book_path}")
                book_path.rmdir()

        for key in tqdm(new_pages.keys()):
            old_page = self.pages.get(key)
            page = new_pages[key]

            if old_page and old_page.data.updated_at == page.updated_at:
                new_downloaded_pages.pages[key] = old_page
                continue

            if old_page and key in modified_pages and not force:
                del modified_pages[key]
                tqdm.write(f"[sync] {old_page.key()} is modified locally and remotely, skipping")
                new_downloaded_pages.pages[key] = old_page
                continue

            book_path = root_dir / page.book_slug
            book_path.mkdir(parents=True, exist_ok=True)
            path_markdown = root_dir / page.book_slug / (page.slug + ".md")
            # path_html = root_dir / page.book_slug / (page.slug + ".html")
            source = api.get_pages_export_markdown(page.id).replace('\r\n', '\n').replace('\r', '\n')
            path_markdown.write_text(source)
            # path_html.write_text(api.get_pages_export_html(page.id))
            last_modified = path_markdown.stat().st_mtime
            new_downloaded_pages.pages[key] = DownloadedPage(
                path_markdown=path_markdown,
                # path_html=path_html,
                data=page,
                last_modified=last_modified)
            tqdm.write(f"synced {page.book_slug}/{page.slug}")

        for key in modified_pages:
            page = modified_pages[key]
            page.data.update(api, page.path_markdown.read_text())
            # page.path_html.write_text(api.get_pages_export_html(page.data.id))
            page.last_modified = page.path_markdown.stat().st_mtime
            new_downloaded_pages.pages[key] = page
            tqdm.write(f"updated {page.key()}")

        (root_dir / BOOKSTACK_FILE_NAME).write_text(new_downloaded_pages.model_dump_json(indent=2))
        print(f"synced {len(pages.data)} pages")

        self.pages = new_downloaded_pages.pages

BOOKSTACK_FILE_NAME = ".bookstack.json"

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
    api = Api(api=bookstack.BookStack(base_url=bookstack_wiki.url, token_id=token_id, token_secret=token_secret))
    bookstack_wiki.sync(wiki_dir, api, force=args.force)


if __name__ == '__main__':
    main()
