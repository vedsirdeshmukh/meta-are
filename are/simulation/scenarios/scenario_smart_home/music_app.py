# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

"""
Music App for Playlist and Playback Management

This app manages music playback, playlists, and can be integrated with smart home automations.
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from are.simulation.apps.app import App
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import get_state_dict, type_check


class PlaybackState(Enum):
    """Music playback states"""

    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class Song:
    """Represents a music track"""

    title: str
    artist: str
    album: str
    duration_seconds: int
    song_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    genre: str = ""

    def __str__(self):
        return f"{self.title} by {self.artist}"


@dataclass
class Playlist:
    """Represents a music playlist"""

    name: str
    songs: list[str] = field(default_factory=list)  # List of song_ids
    playlist_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str = ""

    def __post_init__(self):
        if not self.name or len(self.name.strip()) == 0:
            raise ValueError("Playlist name cannot be empty")

    def __str__(self):
        return f"Playlist: {self.name} ({len(self.songs)} songs)"


@dataclass
class MusicApp(App):
    """
    Music playback and playlist management app.

    Features:
    - Manage music library (songs)
    - Create and manage playlists
    - Control playback (play, pause, stop)
    - Integration with smart home (play specific playlist on automation)
    """

    name: str | None = "MusicApp"
    songs: dict[str, Song] = field(default_factory=dict)
    playlists: dict[str, Playlist] = field(default_factory=dict)
    playback_state: PlaybackState = PlaybackState.STOPPED
    current_playlist_id: str | None = None
    current_song_index: int = 0
    volume: int = 50  # 0-100

    def __post_init__(self):
        super().__init__(self.name)

    # ========================================================================
    # State Management
    # ========================================================================

    def get_state(self) -> dict[str, Any]:
        """Return serializable state"""
        return get_state_dict(
            self,
            [
                "songs",
                "playlists",
                "playback_state",
                "current_playlist_id",
                "current_song_index",
                "volume",
            ],
        )

    def load_state(self, state_dict: dict[str, Any]):
        """Restore state from saved data"""
        self.songs = {}
        self.playlists = {}

        # Restore songs
        for song_id, song_data in state_dict.get("songs", {}).items():
            song = Song(
                title=song_data["title"],
                artist=song_data["artist"],
                album=song_data["album"],
                duration_seconds=song_data["duration_seconds"],
                song_id=song_data.get("song_id", song_id),
                genre=song_data.get("genre", ""),
            )
            self.songs[song_id] = song

        # Restore playlists
        for playlist_id, playlist_data in state_dict.get("playlists", {}).items():
            playlist = Playlist(
                name=playlist_data["name"],
                songs=playlist_data["songs"],
                playlist_id=playlist_data.get("playlist_id", playlist_id),
                description=playlist_data.get("description", ""),
            )
            self.playlists[playlist_id] = playlist

        self.playback_state = PlaybackState(
            state_dict.get("playback_state", "stopped")
        )
        self.current_playlist_id = state_dict.get("current_playlist_id")
        self.current_song_index = state_dict.get("current_song_index", 0)
        self.volume = state_dict.get("volume", 50)

    def reset(self):
        """Reset app to initial state"""
        super().reset()
        self.songs = {}
        self.playlists = {}
        self.playback_state = PlaybackState.STOPPED
        self.current_playlist_id = None
        self.current_song_index = 0
        self.volume = 50

    # ========================================================================
    # Song Management Tools
    # ========================================================================

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_song(
        self,
        title: str,
        artist: str,
        album: str,
        duration_seconds: int,
        genre: str = "",
    ) -> str:
        """
        Add a song to the music library.

        :param title: Song title
        :param artist: Artist name
        :param album: Album name
        :param duration_seconds: Song duration in seconds
        :param genre: Music genre (optional)
        :returns: The song_id of the added song
        """
        song = Song(
            title=title,
            artist=artist,
            album=album,
            duration_seconds=duration_seconds,
            genre=genre,
        )
        self.songs[song.song_id] = song
        return song.song_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_songs(self, genre: str | None = None) -> list[dict[str, Any]]:
        """
        List all songs in the library.

        :param genre: Optional genre filter
        :returns: List of song information dictionaries
        """
        songs = list(self.songs.values())

        if genre:
            songs = [s for s in songs if s.genre.lower() == genre.lower()]

        return [
            {
                "song_id": s.song_id,
                "title": s.title,
                "artist": s.artist,
                "album": s.album,
                "duration_seconds": s.duration_seconds,
                "genre": s.genre,
            }
            for s in songs
        ]

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def search_songs(self, query: str) -> list[dict[str, Any]]:
        """
        Search for songs by title, artist, or album.

        :param query: Search query
        :returns: List of matching songs
        """
        query_lower = query.lower()
        matching_songs = [
            s
            for s in self.songs.values()
            if query_lower in s.title.lower()
            or query_lower in s.artist.lower()
            or query_lower in s.album.lower()
        ]

        return [
            {
                "song_id": s.song_id,
                "title": s.title,
                "artist": s.artist,
                "album": s.album,
                "duration_seconds": s.duration_seconds,
                "genre": s.genre,
            }
            for s in matching_songs
        ]

    # ========================================================================
    # Playlist Management Tools
    # ========================================================================

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_playlist(
        self, name: str, description: str = "", song_ids: list[str] | None = None
    ) -> str:
        """
        Create a new playlist.

        :param name: Playlist name
        :param description: Optional playlist description
        :param song_ids: Optional list of song IDs to add to the playlist
        :returns: The playlist_id of the created playlist
        """
        if song_ids is None:
            song_ids = []

        # Validate that all songs exist
        for song_id in song_ids:
            if song_id not in self.songs:
                raise KeyError(f"Song {song_id} not found")

        playlist = Playlist(name=name, songs=song_ids, description=description)
        self.playlists[playlist.playlist_id] = playlist
        return playlist.playlist_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_playlists(self) -> list[dict[str, Any]]:
        """
        List all playlists.

        :returns: List of playlist information dictionaries
        """
        return [
            {
                "playlist_id": p.playlist_id,
                "name": p.name,
                "description": p.description,
                "num_songs": len(p.songs),
            }
            for p in self.playlists.values()
        ]

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_playlist(self, playlist_id: str) -> dict[str, Any]:
        """
        Get detailed information about a playlist.

        :param playlist_id: The playlist to retrieve
        :returns: Playlist details including all songs
        """
        if playlist_id not in self.playlists:
            raise KeyError(f"Playlist {playlist_id} not found")

        playlist = self.playlists[playlist_id]
        songs_info = [
            {
                "song_id": song_id,
                "title": self.songs[song_id].title,
                "artist": self.songs[song_id].artist,
            }
            for song_id in playlist.songs
            if song_id in self.songs
        ]

        return {
            "playlist_id": playlist.playlist_id,
            "name": playlist.name,
            "description": playlist.description,
            "songs": songs_info,
        }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_song_to_playlist(self, playlist_id: str, song_id: str) -> str:
        """
        Add a song to a playlist.

        :param playlist_id: The playlist to add to
        :param song_id: The song to add
        :returns: Success message
        """
        if playlist_id not in self.playlists:
            raise KeyError(f"Playlist {playlist_id} not found")
        if song_id not in self.songs:
            raise KeyError(f"Song {song_id} not found")

        playlist = self.playlists[playlist_id]
        if song_id not in playlist.songs:
            playlist.songs.append(song_id)

        return f"Added '{self.songs[song_id].title}' to playlist '{playlist.name}'"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def remove_song_from_playlist(self, playlist_id: str, song_id: str) -> str:
        """
        Remove a song from a playlist.

        :param playlist_id: The playlist to remove from
        :param song_id: The song to remove
        :returns: Success message
        """
        if playlist_id not in self.playlists:
            raise KeyError(f"Playlist {playlist_id} not found")

        playlist = self.playlists[playlist_id]
        if song_id in playlist.songs:
            playlist.songs.remove(song_id)
            return f"Removed song from playlist '{playlist.name}'"
        else:
            return f"Song not found in playlist '{playlist.name}'"

    # ========================================================================
    # Playback Control Tools
    # ========================================================================

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def play_playlist(self, playlist_id: str) -> str:
        """
        Start playing a playlist.

        :param playlist_id: The playlist to play
        :returns: Success message with current song info
        """
        if playlist_id not in self.playlists:
            raise KeyError(f"Playlist {playlist_id} not found")

        playlist = self.playlists[playlist_id]
        if not playlist.songs:
            raise ValueError(f"Playlist '{playlist.name}' is empty")

        self.current_playlist_id = playlist_id
        self.current_song_index = 0
        self.playback_state = PlaybackState.PLAYING

        current_song_id = playlist.songs[0]
        current_song = self.songs[current_song_id]

        return f"Now playing playlist '{playlist.name}': {current_song.title} by {current_song.artist}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def pause_playback(self) -> str:
        """
        Pause music playback.

        :returns: Success message
        """
        if self.playback_state == PlaybackState.STOPPED:
            return "No music is currently playing"

        self.playback_state = PlaybackState.PAUSED
        return "Playback paused"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def resume_playback(self) -> str:
        """
        Resume music playback.

        :returns: Success message
        """
        if self.playback_state == PlaybackState.STOPPED:
            return "No playlist selected. Use play_playlist to start playback"

        self.playback_state = PlaybackState.PLAYING
        return "Playback resumed"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def stop_playback(self) -> str:
        """
        Stop music playback.

        :returns: Success message
        """
        self.playback_state = PlaybackState.STOPPED
        self.current_playlist_id = None
        self.current_song_index = 0
        return "Playback stopped"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_volume(self, volume: int) -> str:
        """
        Set the playback volume.

        :param volume: Volume level (0-100)
        :returns: Success message
        """
        if not 0 <= volume <= 100:
            raise ValueError("Volume must be between 0 and 100")

        self.volume = volume
        return f"Volume set to {volume}%"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_playback_status(self) -> dict[str, Any]:
        """
        Get current playback status.

        :returns: Playback information including state, current song, volume
        """
        status = {
            "state": self.playback_state.value,
            "volume": self.volume,
            "current_playlist_id": self.current_playlist_id,
            "current_song": None,
        }

        if (
            self.current_playlist_id
            and self.current_playlist_id in self.playlists
        ):
            playlist = self.playlists[self.current_playlist_id]
            if (
                0 <= self.current_song_index < len(playlist.songs)
                and playlist.songs[self.current_song_index] in self.songs
            ):
                song = self.songs[playlist.songs[self.current_song_index]]
                status["current_song"] = {
                    "title": song.title,
                    "artist": song.artist,
                    "album": song.album,
                }
                status["current_playlist_name"] = playlist.name

        return status

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def find_playlist_by_name(self, name: str) -> Playlist | None:
        """Find a playlist by name (case-insensitive)"""
        for playlist in self.playlists.values():
            if playlist.name.lower() == name.lower():
                return playlist
        return None
