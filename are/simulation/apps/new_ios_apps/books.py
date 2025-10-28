# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from are.simulation.apps.app import App
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import get_state_dict, type_check, uuid_hex


class BookType(Enum):
    EBOOK = "eBook"
    AUDIOBOOK = "Audiobook"
    PDF = "PDF"


class Genre(Enum):
    FICTION = "Fiction"
    NON_FICTION = "Non-Fiction"
    MYSTERY = "Mystery"
    ROMANCE = "Romance"
    SCIENCE_FICTION = "Science Fiction"
    FANTASY = "Fantasy"
    BIOGRAPHY = "Biography"
    HISTORY = "History"
    SELF_HELP = "Self Help"
    BUSINESS = "Business"
    EDUCATION = "Education"
    OTHER = "Other"


class ReadingStatus(Enum):
    NOT_STARTED = "Not Started"
    READING = "Reading"
    FINISHED = "Finished"


@dataclass
class Book:
    """Represents a book in the library."""

    book_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "Untitled"
    author: str = "Unknown Author"
    book_type: BookType = BookType.EBOOK
    genre: Genre = Genre.OTHER
    pages: int | None = None
    duration_minutes: int | None = None  # For audiobooks
    description: str = ""
    publish_year: int | None = None
    reading_status: ReadingStatus = ReadingStatus.NOT_STARTED
    current_page: int = 0
    current_time_minutes: int = 0  # For audiobooks
    is_favorite: bool = False
    purchase_date: float = field(default_factory=time.time)
    last_opened: float | None = None
    notes: list[str] = field(default_factory=list)

    def __str__(self):
        info = f"📚 {self.title}\nAuthor: {self.author}\nType: {self.book_type.value}"
        info += f"\nGenre: {self.genre.value}"

        if self.publish_year:
            info += f"\nPublished: {self.publish_year}"

        info += f"\nStatus: {self.reading_status.value}"

        if self.book_type == BookType.AUDIOBOOK and self.duration_minutes:
            progress_pct = (self.current_time_minutes / self.duration_minutes) * 100 if self.duration_minutes > 0 else 0
            info += f"\nProgress: {progress_pct:.0f}% ({self.current_time_minutes}/{self.duration_minutes} minutes)"
        elif self.pages:
            progress_pct = (self.current_page / self.pages) * 100 if self.pages > 0 else 0
            info += f"\nProgress: {progress_pct:.0f}% (Page {self.current_page}/{self.pages})"

        if self.is_favorite:
            info += "\n❤️ Favorite"

        return info

    @property
    def summary(self):
        return f"{self.title} by {self.author}"


@dataclass
class Collection:
    """Represents a collection of books."""

    collection_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "New Collection"
    book_ids: list[str] = field(default_factory=list)
    created_date: float = field(default_factory=time.time)

    def __str__(self):
        return f"📚 {self.name}\nBooks: {len(self.book_ids)}\nCreated: {time.ctime(self.created_date)}"


@dataclass
class BooksApp(App):
    """
    Books and audiobooks library application.

    Manages digital books, audiobooks, reading progress, and collections.
    Provides reading, listening, and organization features.

    Key Features:
        - Library: Organize books and audiobooks
        - Reading Progress: Track page/time progress
        - Collections: Create custom book collections
        - Notes: Add notes and highlights
        - Favorites: Mark favorite books
        - Reading Goals: Set and track reading goals
        - Statistics: Track reading habits

    Notes:
        - Audiobooks track time progress
        - eBooks and PDFs track page progress
        - Reading progress is saved automatically
    """

    name: str | None = None
    books: dict[str, Book] = field(default_factory=dict)
    collections: dict[str, Collection] = field(default_factory=dict)
    currently_reading_id: str | None = None
    reading_goal_books_per_year: int | None = None

    def __post_init__(self):
        super().__init__(self.name)

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(
            self,
            ["books", "collections", "currently_reading_id", "reading_goal_books_per_year"],
        )

    def load_state(self, state_dict: dict[str, Any]):
        self.books = {k: Book(**v) for k, v in state_dict.get("books", {}).items()}
        self.collections = {k: Collection(**v) for k, v in state_dict.get("collections", {}).items()}
        self.currently_reading_id = state_dict.get("currently_reading_id")
        self.reading_goal_books_per_year = state_dict.get("reading_goal_books_per_year")

    def reset(self):
        super().reset()
        self.books = {}
        self.collections = {}
        self.currently_reading_id = None

    # Book Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_book(
        self,
        title: str,
        author: str,
        book_type: str = "eBook",
        genre: str = "Other",
        pages: int | None = None,
        duration_minutes: int | None = None,
        publish_year: int | None = None,
    ) -> str:
        """
        Add a book to the library.

        :param title: Book title
        :param author: Book author
        :param book_type: Type of book. Options: eBook, Audiobook, PDF
        :param genre: Genre. Options: Fiction, Non-Fiction, Mystery, Romance, Science Fiction, Fantasy, Biography, History, Self Help, Business, Education, Other
        :param pages: Number of pages (for eBooks/PDFs)
        :param duration_minutes: Duration in minutes (for audiobooks)
        :param publish_year: Year of publication
        :returns: book_id of the added book
        """
        book_type_enum = BookType[book_type.upper().replace(" ", "")]
        genre_enum = Genre[genre.upper().replace(" ", "_").replace("-", "_")]

        book = Book(
            book_id=uuid_hex(self.rng),
            title=title,
            author=author,
            book_type=book_type_enum,
            genre=genre_enum,
            pages=pages,
            duration_minutes=duration_minutes,
            publish_year=publish_year,
            purchase_date=self.time_manager.time(),
        )

        self.books[book.book_id] = book
        return book.book_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def search_books(
        self,
        query: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        book_type: str | None = None,
        reading_status: str | None = None,
    ) -> str:
        """
        Search for books in the library.

        :param query: Search in title or description
        :param author: Filter by author name
        :param genre: Filter by genre
        :param book_type: Filter by type (eBook, Audiobook, PDF)
        :param reading_status: Filter by status (Not Started, Reading, Finished)
        :returns: String representation of matching books
        """
        filtered_books = list(self.books.values())

        if query:
            query_lower = query.lower()
            filtered_books = [
                b for b in filtered_books if query_lower in b.title.lower() or query_lower in b.description.lower()
            ]

        if author:
            filtered_books = [b for b in filtered_books if author.lower() in b.author.lower()]

        if genre:
            genre_enum = Genre[genre.upper().replace(" ", "_").replace("-", "_")]
            filtered_books = [b for b in filtered_books if b.genre == genre_enum]

        if book_type:
            book_type_enum = BookType[book_type.upper().replace(" ", "")]
            filtered_books = [b for b in filtered_books if b.book_type == book_type_enum]

        if reading_status:
            status_enum = ReadingStatus[reading_status.upper().replace(" ", "_")]
            filtered_books = [b for b in filtered_books if b.reading_status == status_enum]

        if not filtered_books:
            return "No books found matching the criteria."

        result = f"Found {len(filtered_books)} book(s):\n\n"
        for book in filtered_books[:20]:
            result += book.summary + f" ({book.reading_status.value})\n"

        if len(filtered_books) > 20:
            result += f"\n... and {len(filtered_books) - 20} more"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def start_reading(self, book_id: str) -> str:
        """
        Start reading a book.

        :param book_id: ID of the book to start reading
        :returns: Success or error message
        """
        if book_id not in self.books:
            return f"Book with ID {book_id} not found."

        book = self.books[book_id]
        book.reading_status = ReadingStatus.READING
        book.last_opened = self.time_manager.time()
        self.currently_reading_id = book_id

        return f"📖 Started reading: {book.title}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def update_progress(self, book_id: str, page: int | None = None, time_minutes: int | None = None) -> str:
        """
        Update reading progress for a book.

        :param book_id: ID of the book
        :param page: Current page number (for eBooks/PDFs)
        :param time_minutes: Current time in minutes (for audiobooks)
        :returns: Success or error message
        """
        if book_id not in self.books:
            return f"Book with ID {book_id} not found."

        book = self.books[book_id]
        book.last_opened = self.time_manager.time()

        if page is not None:
            book.current_page = page
            progress_pct = (page / book.pages) * 100 if book.pages else 0
            result = f"✓ Progress updated to page {page}"

            if progress_pct >= 100:
                book.reading_status = ReadingStatus.FINISHED
                result += f"\n🎉 Finished reading '{book.title}'!"

            return result

        if time_minutes is not None:
            book.current_time_minutes = time_minutes
            progress_pct = (time_minutes / book.duration_minutes) * 100 if book.duration_minutes else 0
            result = f"✓ Progress updated to {time_minutes} minutes"

            if progress_pct >= 100:
                book.reading_status = ReadingStatus.FINISHED
                result += f"\n🎉 Finished '{book.title}'!"

            return result

        return "Please provide either page or time_minutes to update progress."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def mark_as_finished(self, book_id: str) -> str:
        """
        Mark a book as finished.

        :param book_id: ID of the book
        :returns: Success or error message
        """
        if book_id not in self.books:
            return f"Book with ID {book_id} not found."

        book = self.books[book_id]
        book.reading_status = ReadingStatus.FINISHED

        if book.pages:
            book.current_page = book.pages
        if book.duration_minutes:
            book.current_time_minutes = book.duration_minutes

        return f"✓ '{book.title}' marked as finished."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_note(self, book_id: str, note: str) -> str:
        """
        Add a note or highlight to a book.

        :param book_id: ID of the book
        :param note: Note text
        :returns: Success or error message
        """
        if book_id not in self.books:
            return f"Book with ID {book_id} not found."

        book = self.books[book_id]
        book.notes.append(note)

        return f"✓ Note added to '{book.title}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def mark_as_favorite(self, book_id: str) -> str:
        """
        Mark a book as favorite.

        :param book_id: ID of the book
        :returns: Success or error message
        """
        if book_id not in self.books:
            return f"Book with ID {book_id} not found."

        book = self.books[book_id]
        book.is_favorite = True

        return f"✓ '{book.title}' marked as favorite."

    # Collections

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_collection(self, name: str) -> str:
        """
        Create a new book collection.

        :param name: Collection name
        :returns: collection_id of the created collection
        """
        collection = Collection(
            collection_id=uuid_hex(self.rng),
            name=name,
            created_date=self.time_manager.time(),
        )

        self.collections[collection.collection_id] = collection
        return collection.collection_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_book_to_collection(self, collection_id: str, book_id: str) -> str:
        """
        Add a book to a collection.

        :param collection_id: ID of the collection
        :param book_id: ID of the book to add
        :returns: Success or error message
        """
        if collection_id not in self.collections:
            return f"Collection with ID {collection_id} not found."

        if book_id not in self.books:
            return f"Book with ID {book_id} not found."

        collection = self.collections[collection_id]
        book = self.books[book_id]

        if book_id in collection.book_ids:
            return f"'{book.title}' is already in collection."

        collection.book_ids.append(book_id)
        return f"✓ '{book.title}' added to collection '{collection.name}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_collections(self) -> str:
        """
        List all book collections.

        :returns: String representation of collections
        """
        if not self.collections:
            return "No collections found."

        result = f"Collections ({len(self.collections)}):\n\n"
        for collection in self.collections.values():
            result += str(collection) + "\n" + "-" * 40 + "\n"

        return result

    # Statistics

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_reading_goal(self, books_per_year: int) -> str:
        """
        Set annual reading goal.

        :param books_per_year: Number of books to read per year
        :returns: Success message
        """
        self.reading_goal_books_per_year = books_per_year
        return f"✓ Reading goal set to {books_per_year} books per year."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_reading_stats(self) -> str:
        """
        Get reading statistics.

        :returns: Reading statistics
        """
        total_books = len(self.books)
        ebooks = sum(1 for b in self.books.values() if b.book_type == BookType.EBOOK)
        audiobooks = sum(1 for b in self.books.values() if b.book_type == BookType.AUDIOBOOK)
        pdfs = sum(1 for b in self.books.values() if b.book_type == BookType.PDF)

        finished = sum(1 for b in self.books.values() if b.reading_status == ReadingStatus.FINISHED)
        reading = sum(1 for b in self.books.values() if b.reading_status == ReadingStatus.READING)
        not_started = sum(1 for b in self.books.values() if b.reading_status == ReadingStatus.NOT_STARTED)

        result = "=== READING STATS ===\n\n"
        result += f"Total Books: {total_books}\n"
        result += f"  - eBooks: {ebooks}\n"
        result += f"  - Audiobooks: {audiobooks}\n"
        result += f"  - PDFs: {pdfs}\n\n"
        result += f"Finished: {finished}\n"
        result += f"Currently Reading: {reading}\n"
        result += f"Not Started: {not_started}\n"

        if self.reading_goal_books_per_year:
            result += f"\nReading Goal: {finished}/{self.reading_goal_books_per_year} books this year\n"

        return result
