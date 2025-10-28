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


class Genre(Enum):
    POP = "Pop"
    ROCK = "Rock"
    HIP_HOP = "Hip Hop"
    JAZZ = "Jazz"
    CLASSICAL = "Classical"
    ELECTRONIC = "Electronic"
    COUNTRY = "Country"
    R_AND_B = "R&B"
    INDIE = "Indie"
    METAL = "Metal"
    FOLK = "Folk"
    OTHER = "Other"


@dataclass
class Song:
    """Represents a song in the music library."""

    song_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "Untitled"
    artist: str = "Unknown Artist"
    album: str = "Unknown Album"
    duration_seconds: int = 180  # 3 minutes default
    genre: Genre = Genre.OTHER
    year: int | None = None
    play_count: int = 0
    is_favorite: bool = False
    last_played: float | None = None
    explicit: bool = False

    def __str__(self):
        info = f"♪ {self.title}\nArtist: {self.artist}\nAlbum: {self.album}"
        info += f"\nDuration: {self.duration_seconds // 60}:{self.duration_seconds % 60:02d}"
        info += f"\nGenre: {self.genre.value}"

        if self.year:
            info += f"\nYear: {self.year}"
        if self.play_count > 0:
            info += f"\nPlays: {self.play_count}"
        if self.is_favorite:
            info += "\n❤️ Favorite"
        if self.explicit:
            info += "\n🔞 Explicit"

        return info

    @property
    def summary(self):
        return f"{self.title} - {self.artist}"


@dataclass
class Playlist:
    """Represents a music playlist."""

    playlist_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "New Playlist"
    description: str = ""
    song_ids: list[str] = field(default_factory=list)
    created_date: float = field(default_factory=time.time)
    last_modified: float = field(default_factory=time.time)
    is_smart_playlist: bool = False  # Auto-generated based on criteria
    is_collaborative: bool = False
    cover_art_url: str | None = None

    def __str__(self):
        info = f"📀 {self.name}\n"
        if self.description:
            info += f"Description: {self.description}\n"
        info += f"Songs: {len(self.song_ids)}"
        info += f"\nCreated: {time.ctime(self.created_date)}"

        if self.is_smart_playlist:
            info += "\n🤖 Smart Playlist"
        if self.is_collaborative:
            info += "\n👥 Collaborative"

        return info


@dataclass
class Artist:
    """Represents a music artist."""

    artist_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Unknown Artist"
    genre: Genre = Genre.OTHER
    bio: str | None = None
    is_following: bool = False

    def __str__(self):
        info = f"🎤 {self.name}\nGenre: {self.genre.value}"
        if self.is_following:
            info += "\n✓ Following"
        if self.bio:
            info += f"\nBio: {self.bio[:100]}..."
        return info


@dataclass
class Album:
    """Represents a music album."""

    album_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "Unknown Album"
    artist: str = "Unknown Artist"
    year: int | None = None
    genre: Genre = Genre.OTHER
    song_ids: list[str] = field(default_factory=list)
    cover_art_url: str | None = None

    def __str__(self):
        info = f"💿 {self.title}\nArtist: {self.artist}"
        if self.year:
            info += f"\nYear: {self.year}"
        info += f"\nGenre: {self.genre.value}"
        info += f"\nTracks: {len(self.song_ids)}"
        return info


@dataclass
class MusicApp(App):
    """
    Music streaming and library management application.

    Manages songs, playlists, artists, and albums in a personal music library.
    Provides features for organizing music, creating playlists, and tracking listening history.

    Key Features:
        - Music Library: Organize songs, albums, and artists
        - Playlists: Create and manage custom playlists
        - Playback Control: Play, pause, skip songs
        - Favorites: Mark favorite songs and artists
        - Smart Playlists: Auto-generated playlists based on criteria
        - Listening History: Track play counts and recent activity
        - Parental Controls: Filter explicit content

    Notes:
        - Songs can be organized into playlists and albums
        - Smart playlists auto-update based on listening habits
        - Parental controls can hide explicit content
    """

    name: str | None = None
    songs: dict[str, Song] = field(default_factory=dict)
    playlists: dict[str, Playlist] = field(default_factory=dict)
    artists: dict[str, Artist] = field(default_factory=dict)
    albums: dict[str, Album] = field(default_factory=dict)
    currently_playing_song_id: str | None = None
    is_playing: bool = False
    shuffle_enabled: bool = False
    repeat_mode: str = "off"  # off, one, all
    explicit_content_filter: bool = False  # Parental control

    def __post_init__(self):
        super().__init__(self.name)

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(
            self,
            [
                "songs",
                "playlists",
                "artists",
                "albums",
                "currently_playing_song_id",
                "is_playing",
                "shuffle_enabled",
                "repeat_mode",
                "explicit_content_filter",
            ],
        )

    def load_state(self, state_dict: dict[str, Any]):
        self.songs = {k: Song(**v) for k, v in state_dict.get("songs", {}).items()}
        self.playlists = {k: Playlist(**v) for k, v in state_dict.get("playlists", {}).items()}
        self.artists = {k: Artist(**v) for k, v in state_dict.get("artists", {}).items()}
        self.albums = {k: Album(**v) for k, v in state_dict.get("albums", {}).items()}
        self.currently_playing_song_id = state_dict.get("currently_playing_song_id")
        self.is_playing = state_dict.get("is_playing", False)
        self.shuffle_enabled = state_dict.get("shuffle_enabled", False)
        self.repeat_mode = state_dict.get("repeat_mode", "off")
        self.explicit_content_filter = state_dict.get("explicit_content_filter", False)

    def reset(self):
        super().reset()
        self.songs = {}
        self.playlists = {}
        self.artists = {}
        self.albums = {}
        self.currently_playing_song_id = None
        self.is_playing = False

    # Song Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_song(
        self,
        title: str,
        artist: str,
        album: str = "Unknown Album",
        duration_seconds: int = 180,
        genre: str = "Other",
        year: int | None = None,
        explicit: bool = False,
    ) -> str:
        """
        Add a song to the music library.

        :param title: Song title
        :param artist: Artist name
        :param album: Album name
        :param duration_seconds: Song duration in seconds
        :param genre: Music genre. Options: Pop, Rock, Hip Hop, Jazz, Classical, Electronic, Country, R&B, Indie, Metal, Folk, Other
        :param year: Release year
        :param explicit: Whether song contains explicit content
        :returns: song_id of the added song
        """
        genre_enum = Genre[genre.upper().replace(" ", "_").replace("&", "AND")]

        song = Song(
            song_id=uuid_hex(self.rng),
            title=title,
            artist=artist,
            album=album,
            duration_seconds=duration_seconds,
            genre=genre_enum,
            year=year,
            explicit=explicit,
        )

        self.songs[song.song_id] = song
        return song.song_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def search_songs(
        self,
        query: str | None = None,
        artist: str | None = None,
        album: str | None = None,
        genre: str | None = None,
        favorites_only: bool = False,
    ) -> str:
        """
        Search for songs by various criteria.

        :param query: Search in title, artist, or album
        :param artist: Filter by artist name
        :param album: Filter by album name
        :param genre: Filter by genre
        :param favorites_only: Only show favorite songs
        :returns: String representation of matching songs
        """
        filtered_songs = list(self.songs.values())

        if query:
            query_lower = query.lower()
            filtered_songs = [
                s
                for s in filtered_songs
                if query_lower in s.title.lower()
                or query_lower in s.artist.lower()
                or query_lower in s.album.lower()
            ]

        if artist:
            filtered_songs = [s for s in filtered_songs if artist.lower() in s.artist.lower()]

        if album:
            filtered_songs = [s for s in filtered_songs if album.lower() in s.album.lower()]

        if genre:
            genre_enum = Genre[genre.upper().replace(" ", "_").replace("&", "AND")]
            filtered_songs = [s for s in filtered_songs if s.genre == genre_enum]

        if favorites_only:
            filtered_songs = [s for s in filtered_songs if s.is_favorite]

        # Apply explicit content filter
        if self.explicit_content_filter:
            filtered_songs = [s for s in filtered_songs if not s.explicit]

        if not filtered_songs:
            return "No songs found matching the criteria."

        result = f"Found {len(filtered_songs)} song(s):\n\n"
        for song in filtered_songs[:20]:  # Limit to 20 results
            result += song.summary + "\n"

        if len(filtered_songs) > 20:
            result += f"\n... and {len(filtered_songs) - 20} more"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def mark_song_as_favorite(self, song_id: str) -> str:
        """
        Mark a song as favorite.

        :param song_id: ID of the song
        :returns: Success or error message
        """
        if song_id not in self.songs:
            return f"Song with ID {song_id} not found."

        song = self.songs[song_id]
        song.is_favorite = True
        return f"✓ '{song.title}' marked as favorite."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def remove_song_from_favorites(self, song_id: str) -> str:
        """
        Remove a song from favorites.

        :param song_id: ID of the song
        :returns: Success or error message
        """
        if song_id not in self.songs:
            return f"Song with ID {song_id} not found."

        song = self.songs[song_id]
        song.is_favorite = False
        return f"✓ '{song.title}' removed from favorites."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_song(self, song_id: str) -> str:
        """
        Delete a song from the library.

        :param song_id: ID of the song to delete
        :returns: Success or error message
        """
        if song_id not in self.songs:
            return f"Song with ID {song_id} not found."

        song = self.songs[song_id]
        song_title = song.title

        # Remove from all playlists
        for playlist in self.playlists.values():
            if song_id in playlist.song_ids:
                playlist.song_ids.remove(song_id)
                playlist.last_modified = self.time_manager.time()

        del self.songs[song_id]
        return f"✓ Song '{song_title}' deleted from library."

    # Playlist Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_playlist(self, name: str, description: str = "") -> str:
        """
        Create a new playlist.

        :param name: Playlist name
        :param description: Optional description
        :returns: playlist_id of the created playlist
        """
        playlist = Playlist(
            playlist_id=uuid_hex(self.rng),
            name=name,
            description=description,
            created_date=self.time_manager.time(),
            last_modified=self.time_manager.time(),
        )

        self.playlists[playlist.playlist_id] = playlist
        return playlist.playlist_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_song_to_playlist(self, playlist_id: str, song_id: str) -> str:
        """
        Add a song to a playlist.

        :param playlist_id: ID of the playlist
        :param song_id: ID of the song to add
        :returns: Success or error message
        """
        if playlist_id not in self.playlists:
            return f"Playlist with ID {playlist_id} not found."

        if song_id not in self.songs:
            return f"Song with ID {song_id} not found."

        playlist = self.playlists[playlist_id]
        song = self.songs[song_id]

        if song_id in playlist.song_ids:
            return f"'{song.title}' is already in playlist '{playlist.name}'."

        playlist.song_ids.append(song_id)
        playlist.last_modified = self.time_manager.time()

        return f"✓ '{song.title}' added to playlist '{playlist.name}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def remove_song_from_playlist(self, playlist_id: str, song_id: str) -> str:
        """
        Remove a song from a playlist.

        :param playlist_id: ID of the playlist
        :param song_id: ID of the song to remove
        :returns: Success or error message
        """
        if playlist_id not in self.playlists:
            return f"Playlist with ID {playlist_id} not found."

        playlist = self.playlists[playlist_id]

        if song_id not in playlist.song_ids:
            return f"Song is not in playlist '{playlist.name}'."

        song = self.songs.get(song_id)
        song_title = song.title if song else "Unknown"

        playlist.song_ids.remove(song_id)
        playlist.last_modified = self.time_manager.time()

        return f"✓ '{song_title}' removed from playlist '{playlist.name}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_playlists(self) -> str:
        """
        List all playlists.

        :returns: String representation of all playlists
        """
        if not self.playlists:
            return "No playlists found."

        result = f"Playlists ({len(self.playlists)}):\n\n"
        for playlist in self.playlists.values():
            result += str(playlist) + "\n" + "-" * 40 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_playlist_songs(self, playlist_id: str) -> str:
        """
        Get all songs in a playlist.

        :param playlist_id: ID of the playlist
        :returns: String representation of songs in the playlist
        """
        if playlist_id not in self.playlists:
            return f"Playlist with ID {playlist_id} not found."

        playlist = self.playlists[playlist_id]

        if not playlist.song_ids:
            return f"Playlist '{playlist.name}' is empty."

        result = f"Songs in '{playlist.name}' ({len(playlist.song_ids)}):\n\n"
        for i, song_id in enumerate(playlist.song_ids, 1):
            if song_id in self.songs:
                song = self.songs[song_id]
                result += f"{i}. {song.summary}\n"
            else:
                result += f"{i}. [Song not found]\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_playlist(self, playlist_id: str) -> str:
        """
        Delete a playlist.

        :param playlist_id: ID of the playlist to delete
        :returns: Success or error message
        """
        if playlist_id not in self.playlists:
            return f"Playlist with ID {playlist_id} not found."

        playlist_name = self.playlists[playlist_id].name
        del self.playlists[playlist_id]

        return f"✓ Playlist '{playlist_name}' deleted."

    # Playback Control

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def play_song(self, song_id: str) -> str:
        """
        Play a song.

        :param song_id: ID of the song to play
        :returns: Success or error message
        """
        if song_id not in self.songs:
            return f"Song with ID {song_id} not found."

        song = self.songs[song_id]

        if self.explicit_content_filter and song.explicit:
            return f"⚠️ Cannot play '{song.title}': Explicit content filter is enabled."

        song.play_count += 1
        song.last_played = self.time_manager.time()

        self.currently_playing_song_id = song_id
        self.is_playing = True

        return f"▶️ Now playing: {song.summary}"

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
    def resume_playback(self) -> str:
        """
        Resume paused playback.

        :returns: Success or error message
        """
        if self.is_playing:
            return "Playback is already active."

        if not self.currently_playing_song_id:
            return "No song is queued for playback."

        self.is_playing = True
        return "▶️ Playback resumed."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_now_playing(self) -> str:
        """
        Get information about the currently playing song.

        :returns: Current song information or status
        """
        if not self.currently_playing_song_id:
            return "Nothing is currently playing."

        if self.currently_playing_song_id not in self.songs:
            return "Currently playing song not found in library."

        song = self.songs[self.currently_playing_song_id]
        status = "▶️ Playing" if self.is_playing else "⏸️ Paused"

        result = f"{status}\n\n{str(song)}\n"

        if self.shuffle_enabled:
            result += "\n🔀 Shuffle: ON"
        if self.repeat_mode != "off":
            result += f"\n🔁 Repeat: {self.repeat_mode.upper()}"

        return result

    # Settings

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_explicit_content_filter(self, enabled: bool) -> str:
        """
        Enable or disable explicit content filter (parental control).

        :param enabled: True to filter explicit content, False to allow all content
        :returns: Success message
        """
        self.explicit_content_filter = enabled
        status = "enabled" if enabled else "disabled"
        return f"✓ Explicit content filter {status}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_shuffle(self, enabled: bool) -> str:
        """
        Enable or disable shuffle mode.

        :param enabled: True to enable shuffle, False to disable
        :returns: Success message
        """
        self.shuffle_enabled = enabled
        status = "enabled" if enabled else "disabled"
        return f"✓ Shuffle {status}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_repeat_mode(self, mode: str) -> str:
        """
        Set repeat mode for playback.

        :param mode: Repeat mode. Options: off, one (repeat current song), all (repeat playlist/queue)
        :returns: Success message
        """
        if mode not in ["off", "one", "all"]:
            return "Invalid repeat mode. Options: off, one, all"

        self.repeat_mode = mode
        return f"✓ Repeat mode set to '{mode}'."

    # Statistics

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_library_stats(self) -> str:
        """
        Get statistics about the music library.

        :returns: Library statistics
        """
        total_songs = len(self.songs)
        total_playlists = len(self.playlists)
        favorite_songs = sum(1 for s in self.songs.values() if s.is_favorite)
        total_plays = sum(s.play_count for s in self.songs.values())

        # Calculate total duration
        total_duration_seconds = sum(s.duration_seconds for s in self.songs.values())
        total_hours = total_duration_seconds // 3600
        total_minutes = (total_duration_seconds % 3600) // 60

        result = "=== MUSIC LIBRARY STATS ===\n\n"
        result += f"Total Songs: {total_songs}\n"
        result += f"Total Playlists: {total_playlists}\n"
        result += f"Favorite Songs: {favorite_songs}\n"
        result += f"Total Plays: {total_plays}\n"
        result += f"Total Duration: {total_hours}h {total_minutes}m\n"

        # Genre distribution
        if self.songs:
            genre_counts = {}
            for song in self.songs.values():
                genre_counts[song.genre.value] = genre_counts.get(song.genre.value, 0) + 1

            result += "\nGenre Distribution:\n"
            for genre, count in sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                result += f"  - {genre}: {count}\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_recently_played(self, limit: int = 10) -> str:
        """
        Get recently played songs.

        :param limit: Maximum number of songs to return
        :returns: String representation of recently played songs
        """
        played_songs = [s for s in self.songs.values() if s.last_played is not None]

        if not played_songs:
            return "No recently played songs."

        played_songs.sort(key=lambda s: s.last_played, reverse=True)
        played_songs = played_songs[:limit]

        result = f"Recently Played ({len(played_songs)}):\n\n"
        for song in played_songs:
            result += f"{song.summary} (Played {time.ctime(song.last_played)})\n"

        return result
