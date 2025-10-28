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


class PodcastCategory(Enum):
    NEWS = "News"
    COMEDY = "Comedy"
    TRUE_CRIME = "True Crime"
    BUSINESS = "Business"
    TECHNOLOGY = "Technology"
    EDUCATION = "Education"
    HEALTH = "Health & Fitness"
    SPORTS = "Sports"
    ARTS = "Arts"
    HISTORY = "History"
    SCIENCE = "Science"
    SOCIETY = "Society & Culture"
    OTHER = "Other"


class EpisodeStatus(Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


@dataclass
class Episode:
    """Represents a podcast episode."""

    episode_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "Untitled Episode"
    podcast_title: str = "Unknown Podcast"
    duration_seconds: int = 1800  # 30 minutes default
    description: str = ""
    publish_date: float = field(default_factory=time.time)
    is_downloaded: bool = False
    is_played: bool = False
    playback_position_seconds: int = 0
    status: EpisodeStatus = EpisodeStatus.NOT_STARTED
    explicit: bool = False

    def __str__(self):
        info = f"🎙️ {self.title}\nPodcast: {self.podcast_title}"
        info += f"\nDuration: {self.duration_seconds // 60} minutes"
        info += f"\nPublished: {time.ctime(self.publish_date)}"
        info += f"\nStatus: {self.status.value}"

        if self.playback_position_seconds > 0:
            progress_pct = (self.playback_position_seconds / self.duration_seconds) * 100
            info += f"\nProgress: {progress_pct:.0f}%"

        if self.is_downloaded:
            info += "\n📥 Downloaded"
        if self.explicit:
            info += "\n🔞 Explicit"

        return info

    @property
    def summary(self):
        return f"{self.podcast_title} - {self.title}"


@dataclass
class Podcast:
    """Represents a podcast show."""

    podcast_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "Untitled Podcast"
    author: str = "Unknown"
    description: str = ""
    category: PodcastCategory = PodcastCategory.OTHER
    is_subscribed: bool = False
    notification_enabled: bool = False
    auto_download: bool = False
    episode_ids: list[str] = field(default_factory=list)

    def __str__(self):
        info = f"🎙️ {self.title}\nBy: {self.author}\nCategory: {self.category.value}"
        info += f"\nEpisodes: {len(self.episode_ids)}"

        if self.is_subscribed:
            info += "\n✓ Subscribed"
            if self.notification_enabled:
                info += " (Notifications ON)"
            if self.auto_download:
                info += " (Auto-download)"

        return info


@dataclass
class Playlist:
    """Represents a podcast playlist."""

    playlist_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "New Playlist"
    episode_ids: list[str] = field(default_factory=list)
    created_date: float = field(default_factory=time.time)

    def __str__(self):
        return f"📋 {self.name}\nEpisodes: {len(self.episode_ids)}\nCreated: {time.ctime(self.created_date)}"


@dataclass
class PodcastsApp(App):
    """
    Podcasts streaming and management application.

    Manages podcast subscriptions, episodes, playback, and downloads.
    Provides discovery, organization, and listening features.

    Key Features:
        - Podcast Subscriptions: Subscribe to favorite podcasts
        - Episode Management: Download, play, and track episodes
        - Playlists: Create custom episode playlists
        - Playback Control: Play, pause, skip, adjust speed
        - Auto-download: Automatically download new episodes
        - Notifications: Get notified of new episodes
        - Progress Tracking: Resume where you left off
        - Listening History: Track completed episodes

    Notes:
        - Episodes can be downloaded for offline listening
        - Subscriptions can have auto-download enabled
        - Playback position is saved automatically
    """

    name: str | None = None
    podcasts: dict[str, Podcast] = field(default_factory=dict)
    episodes: dict[str, Episode] = field(default_factory=dict)
    playlists: dict[str, Playlist] = field(default_factory=dict)
    currently_playing_episode_id: str | None = None
    is_playing: bool = False
    playback_speed: float = 1.0  # 0.5x to 2.0x

    def __post_init__(self):
        super().__init__(self.name)

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(
            self,
            [
                "podcasts",
                "episodes",
                "playlists",
                "currently_playing_episode_id",
                "is_playing",
                "playback_speed",
            ],
        )

    def load_state(self, state_dict: dict[str, Any]):
        self.podcasts = {k: Podcast(**v) for k, v in state_dict.get("podcasts", {}).items()}
        self.episodes = {k: Episode(**v) for k, v in state_dict.get("episodes", {}).items()}
        self.playlists = {k: Playlist(**v) for k, v in state_dict.get("playlists", {}).items()}
        self.currently_playing_episode_id = state_dict.get("currently_playing_episode_id")
        self.is_playing = state_dict.get("is_playing", False)
        self.playback_speed = state_dict.get("playback_speed", 1.0)

    def reset(self):
        super().reset()
        self.podcasts = {}
        self.episodes = {}
        self.playlists = {}
        self.currently_playing_episode_id = None
        self.is_playing = False

    # Podcast Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_podcast(
        self,
        title: str,
        author: str,
        category: str = "Other",
        description: str = "",
    ) -> str:
        """
        Add a podcast show to the library.

        :param title: Podcast title
        :param author: Podcast author/creator
        :param category: Category. Options: News, Comedy, True Crime, Business, Technology, Education, Health & Fitness, Sports, Arts, History, Science, Society & Culture, Other
        :param description: Podcast description
        :returns: podcast_id of the added podcast
        """
        category_enum = PodcastCategory[category.upper().replace(" ", "_").replace("&", "AND")]

        podcast = Podcast(
            podcast_id=uuid_hex(self.rng),
            title=title,
            author=author,
            category=category_enum,
            description=description,
        )

        self.podcasts[podcast.podcast_id] = podcast
        return podcast.podcast_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def subscribe_to_podcast(self, podcast_id: str, enable_notifications: bool = False, auto_download: bool = False) -> str:
        """
        Subscribe to a podcast.

        :param podcast_id: ID of the podcast to subscribe to
        :param enable_notifications: Enable notifications for new episodes
        :param auto_download: Automatically download new episodes
        :returns: Success or error message
        """
        if podcast_id not in self.podcasts:
            return f"Podcast with ID {podcast_id} not found."

        podcast = self.podcasts[podcast_id]
        podcast.is_subscribed = True
        podcast.notification_enabled = enable_notifications
        podcast.auto_download = auto_download

        return f"✓ Subscribed to '{podcast.title}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def unsubscribe_from_podcast(self, podcast_id: str) -> str:
        """
        Unsubscribe from a podcast.

        :param podcast_id: ID of the podcast to unsubscribe from
        :returns: Success or error message
        """
        if podcast_id not in self.podcasts:
            return f"Podcast with ID {podcast_id} not found."

        podcast = self.podcasts[podcast_id]
        podcast.is_subscribed = False
        podcast.notification_enabled = False
        podcast.auto_download = False

        return f"✓ Unsubscribed from '{podcast.title}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_podcasts(self, subscribed_only: bool = False) -> str:
        """
        List all podcasts.

        :param subscribed_only: Only show subscribed podcasts
        :returns: String representation of podcasts
        """
        filtered_podcasts = list(self.podcasts.values())

        if subscribed_only:
            filtered_podcasts = [p for p in filtered_podcasts if p.is_subscribed]

        if not filtered_podcasts:
            return "No podcasts found."

        result = f"Podcasts ({len(filtered_podcasts)}):\n\n"
        for podcast in filtered_podcasts:
            result += str(podcast) + "\n" + "-" * 40 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def search_podcasts(self, query: str | None = None, category: str | None = None) -> str:
        """
        Search for podcasts.

        :param query: Search in title, author, or description
        :param category: Filter by category
        :returns: String representation of matching podcasts
        """
        filtered_podcasts = list(self.podcasts.values())

        if query:
            query_lower = query.lower()
            filtered_podcasts = [
                p
                for p in filtered_podcasts
                if query_lower in p.title.lower()
                or query_lower in p.author.lower()
                or query_lower in p.description.lower()
            ]

        if category:
            category_enum = PodcastCategory[category.upper().replace(" ", "_").replace("&", "AND")]
            filtered_podcasts = [p for p in filtered_podcasts if p.category == category_enum]

        if not filtered_podcasts:
            return "No podcasts found matching the criteria."

        result = f"Found {len(filtered_podcasts)} podcast(s):\n\n"
        for podcast in filtered_podcasts[:10]:
            result += f"- {podcast.title} by {podcast.author} ({podcast.category.value})\n"

        if len(filtered_podcasts) > 10:
            result += f"\n... and {len(filtered_podcasts) - 10} more"

        return result

    # Episode Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_episode(
        self,
        podcast_id: str,
        title: str,
        duration_seconds: int,
        description: str = "",
        explicit: bool = False,
    ) -> str:
        """
        Add an episode to a podcast.

        :param podcast_id: ID of the podcast this episode belongs to
        :param title: Episode title
        :param duration_seconds: Episode duration in seconds
        :param description: Episode description
        :param explicit: Whether episode contains explicit content
        :returns: episode_id of the added episode
        """
        if podcast_id not in self.podcasts:
            return f"Podcast with ID {podcast_id} not found."

        podcast = self.podcasts[podcast_id]

        episode = Episode(
            episode_id=uuid_hex(self.rng),
            title=title,
            podcast_title=podcast.title,
            duration_seconds=duration_seconds,
            description=description,
            publish_date=self.time_manager.time(),
            explicit=explicit,
        )

        self.episodes[episode.episode_id] = episode
        podcast.episode_ids.append(episode.episode_id)

        # Auto-download if enabled
        if podcast.auto_download:
            episode.is_downloaded = True

        return episode.episode_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_podcast_episodes(self, podcast_id: str) -> str:
        """
        Get all episodes for a podcast.

        :param podcast_id: ID of the podcast
        :returns: String representation of episodes
        """
        if podcast_id not in self.podcasts:
            return f"Podcast with ID {podcast_id} not found."

        podcast = self.podcasts[podcast_id]

        if not podcast.episode_ids:
            return f"No episodes found for '{podcast.title}'."

        # Sort by publish date (newest first)
        episodes = [self.episodes[eid] for eid in podcast.episode_ids if eid in self.episodes]
        episodes.sort(key=lambda e: e.publish_date, reverse=True)

        result = f"Episodes of '{podcast.title}' ({len(episodes)}):\n\n"
        for episode in episodes[:20]:
            result += f"- {episode.title} ({episode.status.value})\n"

        if len(episodes) > 20:
            result += f"\n... and {len(episodes) - 20} more"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def download_episode(self, episode_id: str) -> str:
        """
        Download an episode for offline listening.

        :param episode_id: ID of the episode to download
        :returns: Success or error message
        """
        if episode_id not in self.episodes:
            return f"Episode with ID {episode_id} not found."

        episode = self.episodes[episode_id]

        if episode.is_downloaded:
            return f"'{episode.title}' is already downloaded."

        episode.is_downloaded = True
        return f"✓ '{episode.title}' downloaded."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_downloaded_episode(self, episode_id: str) -> str:
        """
        Delete a downloaded episode to free up storage.

        :param episode_id: ID of the episode to delete
        :returns: Success or error message
        """
        if episode_id not in self.episodes:
            return f"Episode with ID {episode_id} not found."

        episode = self.episodes[episode_id]

        if not episode.is_downloaded:
            return f"'{episode.title}' is not downloaded."

        episode.is_downloaded = False
        return f"✓ Downloaded file for '{episode.title}' deleted."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_unplayed_episodes(self) -> str:
        """
        Get all unplayed episodes from subscribed podcasts.

        :returns: String representation of unplayed episodes
        """
        subscribed_podcast_ids = {pid for pid, p in self.podcasts.items() if p.is_subscribed}

        unplayed_episodes = [
            e
            for e in self.episodes.values()
            if not e.is_played
            and e.status == EpisodeStatus.NOT_STARTED
            and any(pid for pid in subscribed_podcast_ids if e.episode_id in self.podcasts[pid].episode_ids)
        ]

        if not unplayed_episodes:
            return "No unplayed episodes from subscribed podcasts."

        # Sort by publish date (newest first)
        unplayed_episodes.sort(key=lambda e: e.publish_date, reverse=True)

        result = f"Unplayed Episodes ({len(unplayed_episodes)}):\n\n"
        for episode in unplayed_episodes[:20]:
            result += f"- {episode.summary}\n"

        if len(unplayed_episodes) > 20:
            result += f"\n... and {len(unplayed_episodes) - 20} more"

        return result

    # Playback Control

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def play_episode(self, episode_id: str) -> str:
        """
        Play an episode.

        :param episode_id: ID of the episode to play
        :returns: Success or error message
        """
        if episode_id not in self.episodes:
            return f"Episode with ID {episode_id} not found."

        episode = self.episodes[episode_id]

        self.currently_playing_episode_id = episode_id
        self.is_playing = True

        if episode.status == EpisodeStatus.NOT_STARTED:
            episode.status = EpisodeStatus.IN_PROGRESS

        return f"▶️ Now playing: {episode.summary}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def pause_playback(self) -> str:
        """
        Pause current playback.

        :returns: Success or error message
        """
        if not self.is_playing:
            return "Playback is already paused."

        self.is_playing = False
        return "⏸️ Playback paused."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def mark_episode_as_played(self, episode_id: str) -> str:
        """
        Mark an episode as played/completed.

        :param episode_id: ID of the episode
        :returns: Success or error message
        """
        if episode_id not in self.episodes:
            return f"Episode with ID {episode_id} not found."

        episode = self.episodes[episode_id]
        episode.is_played = True
        episode.status = EpisodeStatus.COMPLETED
        episode.playback_position_seconds = episode.duration_seconds

        return f"✓ '{episode.title}' marked as played."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_playback_speed(self, speed: float) -> str:
        """
        Set playback speed.

        :param speed: Playback speed (0.5 to 2.0)
        :returns: Success or error message
        """
        if not 0.5 <= speed <= 2.0:
            return "Playback speed must be between 0.5x and 2.0x."

        self.playback_speed = speed
        return f"✓ Playback speed set to {speed}x."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_now_playing(self) -> str:
        """
        Get information about the currently playing episode.

        :returns: Current episode information or status
        """
        if not self.currently_playing_episode_id:
            return "Nothing is currently playing."

        if self.currently_playing_episode_id not in self.episodes:
            return "Currently playing episode not found."

        episode = self.episodes[self.currently_playing_episode_id]
        status = "▶️ Playing" if self.is_playing else "⏸️ Paused"

        result = f"{status} at {self.playback_speed}x speed\n\n{str(episode)}"

        return result

    # Playlists

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_playlist(self, name: str) -> str:
        """
        Create a new episode playlist.

        :param name: Playlist name
        :returns: playlist_id of the created playlist
        """
        playlist = Playlist(
            playlist_id=uuid_hex(self.rng),
            name=name,
            created_date=self.time_manager.time(),
        )

        self.playlists[playlist.playlist_id] = playlist
        return playlist.playlist_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_episode_to_playlist(self, playlist_id: str, episode_id: str) -> str:
        """
        Add an episode to a playlist.

        :param playlist_id: ID of the playlist
        :param episode_id: ID of the episode to add
        :returns: Success or error message
        """
        if playlist_id not in self.playlists:
            return f"Playlist with ID {playlist_id} not found."

        if episode_id not in self.episodes:
            return f"Episode with ID {episode_id} not found."

        playlist = self.playlists[playlist_id]
        episode = self.episodes[episode_id]

        if episode_id in playlist.episode_ids:
            return f"'{episode.title}' is already in playlist."

        playlist.episode_ids.append(episode_id)
        return f"✓ '{episode.title}' added to playlist '{playlist.name}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_playlists(self) -> str:
        """
        List all playlists.

        :returns: String representation of playlists
        """
        if not self.playlists:
            return "No playlists found."

        result = f"Playlists ({len(self.playlists)}):\n\n"
        for playlist in self.playlists.values():
            result += str(playlist) + "\n" + "-" * 40 + "\n"

        return result

    # Statistics

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_listening_stats(self) -> str:
        """
        Get podcast listening statistics.

        :returns: Listening statistics
        """
        total_subscriptions = sum(1 for p in self.podcasts.values() if p.is_subscribed)
        total_episodes = len(self.episodes)
        played_episodes = sum(1 for e in self.episodes.values() if e.is_played)
        downloaded_episodes = sum(1 for e in self.episodes.values() if e.is_downloaded)

        # Calculate listening time
        total_listening_seconds = sum(
            e.playback_position_seconds for e in self.episodes.values() if e.playback_position_seconds > 0
        )
        total_listening_hours = total_listening_seconds // 3600
        total_listening_minutes = (total_listening_seconds % 3600) // 60

        result = "=== PODCASTS STATS ===\n\n"
        result += f"Subscriptions: {total_subscriptions}\n"
        result += f"Total Episodes: {total_episodes}\n"
        result += f"Played Episodes: {played_episodes}\n"
        result += f"Downloaded Episodes: {downloaded_episodes}\n"
        result += f"Total Listening Time: {total_listening_hours}h {total_listening_minutes}m\n"

        return result
