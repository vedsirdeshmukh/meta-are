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


class ContentType(Enum):
    MOVIE = "Movie"
    TV_SHOW = "TV Show"
    DOCUMENTARY = "Documentary"
    SPORTS = "Sports"


class Genre(Enum):
    ACTION = "Action"
    COMEDY = "Comedy"
    DRAMA = "Drama"
    HORROR = "Horror"
    THRILLER = "Thriller"
    ROMANCE = "Romance"
    SCIENCE_FICTION = "Science Fiction"
    DOCUMENTARY = "Documentary"
    ANIMATION = "Animation"
    FAMILY = "Family"
    OTHER = "Other"


class WatchStatus(Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


@dataclass
class Content:
    """Represents a movie or TV show."""

    content_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "Untitled"
    content_type: ContentType = ContentType.MOVIE
    genre: Genre = Genre.OTHER
    release_year: int | None = None
    duration_minutes: int = 120  # For movies
    num_seasons: int | None = None  # For TV shows
    num_episodes: int | None = None  # For TV shows
    description: str = ""
    rating: str | None = None  # G, PG, PG-13, R, etc.
    is_in_watchlist: bool = False
    watch_status: WatchStatus = WatchStatus.NOT_STARTED
    progress_percent: int = 0
    last_watched: float | None = None
    is_favorite: bool = False

    def __str__(self):
        info = f"📺 {self.title} ({self.release_year or 'Unknown'})\nType: {self.content_type.value}"
        info += f"\nGenre: {self.genre.value}"

        if self.rating:
            info += f"\nRating: {self.rating}"

        if self.content_type == ContentType.MOVIE:
            info += f"\nDuration: {self.duration_minutes} minutes"
        elif self.num_seasons:
            info += f"\nSeasons: {self.num_seasons}"
            if self.num_episodes:
                info += f" | Episodes: {self.num_episodes}"

        info += f"\nWatch Status: {self.watch_status.value}"

        if self.progress_percent > 0:
            info += f" ({self.progress_percent}%)"

        if self.is_in_watchlist:
            info += "\n➕ In Watchlist"
        if self.is_favorite:
            info += "\n❤️ Favorite"

        return info

    @property
    def summary(self):
        return f"{self.title} ({self.release_year or 'Unknown'}) - {self.content_type.value}"


@dataclass
class Subscription:
    """Represents a streaming service subscription."""

    subscription_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    service_name: str = "Streaming Service"
    monthly_cost: float = 9.99
    is_active: bool = True
    renewal_date: float | None = None

    def __str__(self):
        info = f"📺 {self.service_name}\nCost: ${self.monthly_cost:.2f}/month"

        if self.is_active:
            info += "\n✓ Active"
            if self.renewal_date:
                info += f"\nRenews: {time.ctime(self.renewal_date)}"
        else:
            info += "\n⏸️ Inactive"

        return info


@dataclass
class TVApp(App):
    """
    TV and movie streaming application.

    Manages movies, TV shows, watchlist, subscriptions, and viewing history.
    Provides content discovery, playback control, and recommendation features.

    Key Features:
        - Content Library: Browse movies and TV shows
        - Watchlist: Add content to watch later
        - Watch History: Track viewing progress
        - Subscriptions: Manage streaming service subscriptions
        - Parental Controls: Filter content by rating
        - Favorites: Mark favorite content
        - Progress Tracking: Resume where you left off
        - Recommendations: Discover new content

    Notes:
        - Content can be filtered by rating for parental controls
        - Watchlist helps organize content to watch
        - Progress is saved automatically
    """

    name: str | None = None
    content: dict[str, Content] = field(default_factory=dict)
    subscriptions: dict[str, Subscription] = field(default_factory=dict)
    currently_watching_id: str | None = None
    is_playing: bool = False
    parental_control_max_rating: str | None = None  # G, PG, PG-13, R

    def __post_init__(self):
        super().__init__(self.name)

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(
            self,
            [
                "content",
                "subscriptions",
                "currently_watching_id",
                "is_playing",
                "parental_control_max_rating",
            ],
        )

    def load_state(self, state_dict: dict[str, Any]):
        self.content = {k: Content(**v) for k, v in state_dict.get("content", {}).items()}
        self.subscriptions = {k: Subscription(**v) for k, v in state_dict.get("subscriptions", {}).items()}
        self.currently_watching_id = state_dict.get("currently_watching_id")
        self.is_playing = state_dict.get("is_playing", False)
        self.parental_control_max_rating = state_dict.get("parental_control_max_rating")

    def reset(self):
        super().reset()
        self.content = {}
        self.subscriptions = {}
        self.currently_watching_id = None
        self.is_playing = False

    # Content Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_content(
        self,
        title: str,
        content_type: str,
        genre: str = "Other",
        release_year: int | None = None,
        duration_minutes: int | None = None,
        num_seasons: int | None = None,
        rating: str | None = None,
    ) -> str:
        """
        Add a movie or TV show to the library.

        :param title: Content title
        :param content_type: Type of content. Options: Movie, TV Show, Documentary, Sports
        :param genre: Genre. Options: Action, Comedy, Drama, Horror, Thriller, Romance, Science Fiction, Documentary, Animation, Family, Other
        :param release_year: Year of release
        :param duration_minutes: Duration in minutes (for movies)
        :param num_seasons: Number of seasons (for TV shows)
        :param rating: Content rating (G, PG, PG-13, R, etc.)
        :returns: content_id of the added content
        """
        content_type_enum = ContentType[content_type.upper().replace(" ", "_")]
        genre_enum = Genre[genre.upper().replace(" ", "_")]

        content_obj = Content(
            content_id=uuid_hex(self.rng),
            title=title,
            content_type=content_type_enum,
            genre=genre_enum,
            release_year=release_year,
            duration_minutes=duration_minutes or 120,
            num_seasons=num_seasons,
            rating=rating,
        )

        self.content[content_obj.content_id] = content_obj
        return content_obj.content_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def search_content(
        self,
        query: str | None = None,
        content_type: str | None = None,
        genre: str | None = None,
        watchlist_only: bool = False,
    ) -> str:
        """
        Search for movies and TV shows.

        :param query: Search in title or description
        :param content_type: Filter by type (Movie, TV Show, etc.)
        :param genre: Filter by genre
        :param watchlist_only: Only show content in watchlist
        :returns: String representation of matching content
        """
        filtered_content = list(self.content.values())

        if query:
            query_lower = query.lower()
            filtered_content = [
                c
                for c in filtered_content
                if query_lower in c.title.lower() or query_lower in c.description.lower()
            ]

        if content_type:
            content_type_enum = ContentType[content_type.upper().replace(" ", "_")]
            filtered_content = [c for c in filtered_content if c.content_type == content_type_enum]

        if genre:
            genre_enum = Genre[genre.upper().replace(" ", "_")]
            filtered_content = [c for c in filtered_content if c.genre == genre_enum]

        if watchlist_only:
            filtered_content = [c for c in filtered_content if c.is_in_watchlist]

        # Apply parental controls
        if self.parental_control_max_rating:
            rating_order = ["G", "PG", "PG-13", "R", "NC-17"]
            max_index = rating_order.index(self.parental_control_max_rating) if self.parental_control_max_rating in rating_order else len(rating_order)
            filtered_content = [
                c for c in filtered_content if c.rating and c.rating in rating_order and rating_order.index(c.rating) <= max_index
            ]

        if not filtered_content:
            return "No content found matching the criteria."

        result = f"Found {len(filtered_content)} item(s):\n\n"
        for content_item in filtered_content[:20]:
            result += content_item.summary + "\n"

        if len(filtered_content) > 20:
            result += f"\n... and {len(filtered_content) - 20} more"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_to_watchlist(self, content_id: str) -> str:
        """
        Add content to watchlist.

        :param content_id: ID of the content
        :returns: Success or error message
        """
        if content_id not in self.content:
            return f"Content with ID {content_id} not found."

        content_item = self.content[content_id]
        content_item.is_in_watchlist = True

        return f"✓ '{content_item.title}' added to watchlist."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def remove_from_watchlist(self, content_id: str) -> str:
        """
        Remove content from watchlist.

        :param content_id: ID of the content
        :returns: Success or error message
        """
        if content_id not in self.content:
            return f"Content with ID {content_id} not found."

        content_item = self.content[content_id]
        content_item.is_in_watchlist = False

        return f"✓ '{content_item.title}' removed from watchlist."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def mark_as_favorite(self, content_id: str) -> str:
        """
        Mark content as favorite.

        :param content_id: ID of the content
        :returns: Success or error message
        """
        if content_id not in self.content:
            return f"Content with ID {content_id} not found."

        content_item = self.content[content_id]
        content_item.is_favorite = True

        return f"✓ '{content_item.title}' marked as favorite."

    # Playback

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def play_content(self, content_id: str) -> str:
        """
        Play a movie or TV show.

        :param content_id: ID of the content to play
        :returns: Success or error message
        """
        if content_id not in self.content:
            return f"Content with ID {content_id} not found."

        content_item = self.content[content_id]

        # Check parental controls
        if self.parental_control_max_rating and content_item.rating:
            rating_order = ["G", "PG", "PG-13", "R", "NC-17"]
            if content_item.rating in rating_order and self.parental_control_max_rating in rating_order:
                if rating_order.index(content_item.rating) > rating_order.index(self.parental_control_max_rating):
                    return f"⚠️ Cannot play '{content_item.title}': Content rating ({content_item.rating}) exceeds parental control limit ({self.parental_control_max_rating})."

        self.currently_watching_id = content_id
        self.is_playing = True

        if content_item.watch_status == WatchStatus.NOT_STARTED:
            content_item.watch_status = WatchStatus.IN_PROGRESS

        content_item.last_watched = self.time_manager.time()

        return f"▶️ Now playing: {content_item.title}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def mark_as_watched(self, content_id: str) -> str:
        """
        Mark content as watched/completed.

        :param content_id: ID of the content
        :returns: Success or error message
        """
        if content_id not in self.content:
            return f"Content with ID {content_id} not found."

        content_item = self.content[content_id]
        content_item.watch_status = WatchStatus.COMPLETED
        content_item.progress_percent = 100

        return f"✓ '{content_item.title}' marked as watched."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_continue_watching(self) -> str:
        """
        Get list of content in progress to continue watching.

        :returns: String representation of in-progress content
        """
        in_progress = [
            c for c in self.content.values() if c.watch_status == WatchStatus.IN_PROGRESS and c.progress_percent > 0
        ]

        if not in_progress:
            return "No content in progress."

        # Sort by last watched (most recent first)
        in_progress.sort(key=lambda c: c.last_watched or 0, reverse=True)

        result = f"Continue Watching ({len(in_progress)}):\n\n"
        for content_item in in_progress[:10]:
            result += f"- {content_item.title} ({content_item.progress_percent}%)\n"

        return result

    # Subscriptions

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_subscription(self, service_name: str, monthly_cost: float) -> str:
        """
        Add a streaming service subscription.

        :param service_name: Name of the streaming service
        :param monthly_cost: Monthly subscription cost
        :returns: subscription_id of the added subscription
        """
        subscription = Subscription(
            subscription_id=uuid_hex(self.rng),
            service_name=service_name,
            monthly_cost=monthly_cost,
            is_active=True,
            renewal_date=self.time_manager.time() + (30 * 24 * 3600),  # 30 days from now
        )

        self.subscriptions[subscription.subscription_id] = subscription
        return subscription.subscription_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def cancel_subscription(self, subscription_id: str) -> str:
        """
        Cancel a streaming subscription.

        :param subscription_id: ID of the subscription to cancel
        :returns: Success or error message
        """
        if subscription_id not in self.subscriptions:
            return f"Subscription with ID {subscription_id} not found."

        subscription = self.subscriptions[subscription_id]
        subscription.is_active = False

        return f"✓ Subscription to '{subscription.service_name}' cancelled."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_subscriptions(self) -> str:
        """
        List all streaming subscriptions.

        :returns: String representation of subscriptions
        """
        if not self.subscriptions:
            return "No subscriptions found."

        active = [s for s in self.subscriptions.values() if s.is_active]
        inactive = [s for s in self.subscriptions.values() if not s.is_active]

        result = ""

        if active:
            total_cost = sum(s.monthly_cost for s in active)
            result += f"Active Subscriptions ({len(active)}) - Total: ${total_cost:.2f}/month\n\n"
            for sub in active:
                result += str(sub) + "\n" + "-" * 40 + "\n"

        if inactive:
            result += f"\nInactive Subscriptions ({len(inactive)})\n\n"
            for sub in inactive:
                result += str(sub) + "\n" + "-" * 40 + "\n"

        return result

    # Parental Controls

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_parental_control(self, max_rating: str) -> str:
        """
        Set parental control rating limit.

        :param max_rating: Maximum allowed rating. Options: G, PG, PG-13, R, NC-17, or 'None' to disable
        :returns: Success message
        """
        if max_rating.upper() == "NONE":
            self.parental_control_max_rating = None
            return "✓ Parental controls disabled."

        if max_rating not in ["G", "PG", "PG-13", "R", "NC-17"]:
            return "Invalid rating. Options: G, PG, PG-13, R, NC-17, or 'None' to disable"

        self.parental_control_max_rating = max_rating
        return f"✓ Parental control set to {max_rating}. Content above this rating will be blocked."

    # Statistics

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_watch_stats(self) -> str:
        """
        Get watching statistics.

        :returns: Watch statistics
        """
        total_content = len(self.content)
        movies = sum(1 for c in self.content.values() if c.content_type == ContentType.MOVIE)
        tv_shows = sum(1 for c in self.content.values() if c.content_type == ContentType.TV_SHOW)
        watchlist_count = sum(1 for c in self.content.values() if c.is_in_watchlist)
        watched_count = sum(1 for c in self.content.values() if c.watch_status == WatchStatus.COMPLETED)
        in_progress_count = sum(1 for c in self.content.values() if c.watch_status == WatchStatus.IN_PROGRESS)

        result = "=== TV STATS ===\n\n"
        result += f"Total Content: {total_content}\n"
        result += f"Movies: {movies}\n"
        result += f"TV Shows: {tv_shows}\n"
        result += f"Watchlist: {watchlist_count}\n"
        result += f"Watched: {watched_count}\n"
        result += f"In Progress: {in_progress_count}\n"

        active_subs = sum(1 for s in self.subscriptions.values() if s.is_active)
        if active_subs > 0:
            total_cost = sum(s.monthly_cost for s in self.subscriptions.values() if s.is_active)
            result += f"\nActive Subscriptions: {active_subs} (${total_cost:.2f}/month)\n"

        return result
