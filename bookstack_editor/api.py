from typing import Generic, TypeVar
import bookstack
import pydantic
from pathlib import Path
from pprint import pp
from tqdm import tqdm
from loguru import logger

BOOKSTACK_FILE_NAME = ".bookstack.json"

DataT = TypeVar('DataT')


class Payload(pydantic.BaseModel, Generic[DataT]):
    data: DataT


class BooksData(pydantic.BaseModel):
    id: int
    slug: str
    name: str
    description: str
    created_at: str
    updated_at: str
    owned_by: int
    created_by: int
    updated_by: int


class UserData(pydantic.BaseModel):
    id: int
    name: str
    slug: str


class PageUpdateData(pydantic.BaseModel):
    id: int
    book_id: int
    chapter_id: int
    name: str
    slug: str
    html: str
    raw_html: str
    markdown: str
    priority: int
    created_at: str
    updated_at: str
    created_by: UserData
    updated_by: UserData
    owned_by: UserData
    revision_count: int
    draft: bool
    template: bool
    editor: str
    tags: list[str]


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

    def _update_from(self, data: PageUpdateData) -> None:
        self.updated_at = data.updated_at
        self.book_id = data.book_id
        self.chapter_id = data.chapter_id
        self.name = data.name

    @staticmethod
    def create(api: 'Api', book_id: int, book_slug: str, name: str, markdown: str) -> "PagesData":
        # book_id 	required_without:chapter_id integer
        # chapter_id 	required_without:book_id integer
        # name 	required string max:255
        # html 	required_without:markdown string
        # markdown 	required_without:html string
        # tags 	array
        # priority 	integer
        payload: dict = {
            "book_id": book_id,
            "markdown": markdown,
            "name": name,
        }
        raw_data: dict = api.post_pages_create(payload)
        data = PageUpdateData.model_validate(raw_data)
        return PagesData(
            name=data.name,
            id=data.id,
            slug=data.slug,
            book_slug=book_slug,
            book_id=data.book_id,
            chapter_id=data.chapter_id,
            draft=data.draft,
            template=data.template,
            created_at=data.created_at,
            updated_at=data.updated_at,
            priority=data.priority,
            owned_by=data.owned_by.id,
            created_by=data.created_by.id,
            updated_by=data.updated_by.id,
            revision_count=data.revision_count,
            editor=data.editor,
        )

    def update(self, api: 'Api', markdown: str) -> None:
        payload: dict = self.model_dump()
        payload["markdown"] = markdown
        payload["editor"] = "markdown"
        if self.chapter_id == 0:
            del payload["chapter_id"]
        elif self.book_id == 0:
            del payload["book_id"]
        new_data: dict = api.put_pages_update(payload)
        try:
            data = PageUpdateData.model_validate(new_data)
            self._update_from(data)
        except:
            pass


class DownloadedPage(pydantic.BaseModel):
    path_markdown: Path
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

    def __init__(self, url: str, token_id: str, token_secret: str):
        api = bookstack.BookStack(base_url=url, token_id=token_id, token_secret=token_secret)
        api.generate_api_methods()
        self.api = api

    def print_available_api_methods(self) -> None:
        pp(self.api.available_api_methods)

    def get_books_list(self) -> Payload[list[BooksData]]:
        raw = self.api.get_books_list()  # type: ignore
        return Payload[list[BooksData]].model_validate(raw)

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

    def post_pages_create(self, data: dict) -> dict:
        result = self.api.post_pages_create(data)  # type: ignore
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

        # step 1: remove pages that were removed upstream and have no local changes
        for key in removed_pages:
            page = self.pages[key]
            if page.is_modified():
                logger.warning(
                    f"[sync] {page.path_markdown} was removed upstream but has local changes, skipping removal")
                new_downloaded_pages.pages[key] = page
                continue
            logger.info(f"[sync] removing {page.path_markdown}")
            page.path_markdown.unlink()
            old_book_dirs.add(page.data.book_slug)

        # step 2: remove empty directories
        for old_book_dir in old_book_dirs:
            book_path = root_dir / old_book_dir
            if not list(book_path.iterdir()):
                logger.info(f"[sync] removing {book_path}")
                book_path.rmdir()

        # step 3: download new and updated pages
        # if a page is modified locally and remotely, skip it unless force is set
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
            source = api.get_pages_export_markdown(page.id).replace('\r\n', '\n').replace('\r', '\n')
            path_markdown.write_text(source)
            last_modified = path_markdown.stat().st_mtime
            new_downloaded_pages.pages[key] = DownloadedPage(path_markdown=path_markdown,
                                                             data=page,
                                                             last_modified=last_modified)
            tqdm.write(f"synced {page.book_slug}/{page.slug}")

        # step 4: update modified pages
        for key in modified_pages:
            page = modified_pages[key]
            page.data.update(api, page.path_markdown.read_text())
            page.last_modified = page.path_markdown.stat().st_mtime
            new_downloaded_pages.pages[key] = page
            tqdm.write(f"updated {page.path_markdown}")

        # step 5: Find new pages
        known_md_files = {page.path_markdown.resolve() for page in new_downloaded_pages.pages.values()}
        new_md_files = set()
        for md_file in root_dir.rglob("*.md"):
            md_file = md_file.resolve()
            if md_file.is_file() and md_file not in known_md_files:
                print(f"found new page {md_file}")
                new_md_files.add(md_file)
        if new_md_files:
            books_data = {book.slug: book for book in api.get_books_list().data}
            for f in new_md_files:
                book_slug = f.parent.name
                book = books_data.get(book_slug)
                if not book:
                    logger.error(f"cannot create wiki page for {f} because book {book_slug} does not exist")
                    continue
                name = f.stem
                markdown = f.read_text()
                page = PagesData.create(api, book_id=book.id, book_slug=book_slug, name=name, markdown=markdown)
                new_downloaded_pages.pages[page.key()] = DownloadedPage(path_markdown=f, data=page)

        (root_dir / BOOKSTACK_FILE_NAME).write_text(new_downloaded_pages.model_dump_json(indent=2))
        print(f"synced {len(pages.data)} pages")

        self.pages = new_downloaded_pages.pages
