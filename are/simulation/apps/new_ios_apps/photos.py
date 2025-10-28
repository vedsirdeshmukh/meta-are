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


class PhotoType(Enum):
    PHOTO = "Photo"
    SCREENSHOT = "Screenshot"
    VIDEO = "Video"
    LIVE_PHOTO = "Live Photo"
    PANORAMA = "Panorama"
    BURST = "Burst"


class AlbumType(Enum):
    REGULAR = "Regular"
    SHARED = "Shared"
    SMART = "Smart"  # Auto-generated (e.g., Favorites, Recently Deleted)


@dataclass
class Photo:
    """Represents a photo or video in the library."""

    photo_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    filename: str = "IMG_0001.jpg"
    photo_type: PhotoType = PhotoType.PHOTO
    date_taken: float = field(default_factory=time.time)
    date_added: float = field(default_factory=time.time)
    location: str | None = None
    people_tags: list[str] = field(default_factory=list)  # Names of people in photo
    is_favorite: bool = False
    is_hidden: bool = False
    is_deleted: bool = False  # In "Recently Deleted" album
    file_size_mb: float = 2.5
    width: int = 1920
    height: int = 1080
    caption: str | None = None
    is_sensitive: bool = False  # Private/sensitive content
    contains_document: bool = False  # Screenshot of legal doc, receipt, etc.
    document_description: str | None = None  # What kind of document

    def __str__(self):
        info = f"📷 {self.filename}\nType: {self.photo_type.value}\nDate: {time.ctime(self.date_taken)}"
        info += f"\nSize: {self.file_size_mb:.1f} MB"
        info += f"\nDimensions: {self.width}x{self.height}"

        if self.location:
            info += f"\nLocation: {self.location}"
        if self.people_tags:
            info += f"\nPeople: {', '.join(self.people_tags)}"
        if self.caption:
            info += f"\nCaption: {self.caption}"
        if self.is_favorite:
            info += "\n❤️ Favorite"
        if self.is_hidden:
            info += "\n🔒 Hidden"
        if self.is_deleted:
            info += "\n🗑️ In Recently Deleted"
        if self.contains_document:
            info += f"\n📄 Contains Document: {self.document_description or 'Document'}"
        if self.is_sensitive:
            info += "\n🔐 Sensitive Content"

        return info

    @property
    def summary(self):
        return f"{self.filename} ({self.photo_type.value}) - {time.ctime(self.date_taken)}"


@dataclass
class Album:
    """Represents a photo album."""

    album_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "New Album"
    album_type: AlbumType = AlbumType.REGULAR
    photo_ids: list[str] = field(default_factory=list)
    created_date: float = field(default_factory=time.time)
    is_shared: bool = False
    shared_with: list[str] = field(default_factory=list)  # Names of people shared with
    cover_photo_id: str | None = None

    def __str__(self):
        info = f"📁 {self.name}\nType: {self.album_type.value}\nPhotos: {len(self.photo_ids)}"
        info += f"\nCreated: {time.ctime(self.created_date)}"

        if self.is_shared:
            info += f"\n👥 Shared with: {', '.join(self.shared_with) if self.shared_with else 'Nobody yet'}"

        return info


@dataclass
class Memory:
    """Represents an auto-generated memory (collection of photos from an event/time)."""

    memory_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "Memory"
    subtitle: str | None = None
    photo_ids: list[str] = field(default_factory=list)
    date_range_start: float = field(default_factory=time.time)
    date_range_end: float = field(default_factory=time.time)
    location: str | None = None
    memory_type: str = "Trip"  # Trip, Birthday, Holiday, etc.

    def __str__(self):
        info = f"💭 {self.title}"
        if self.subtitle:
            info += f"\n{self.subtitle}"
        info += f"\nPhotos: {len(self.photo_ids)}"
        info += f"\nDate: {time.ctime(self.date_range_start)}"
        if self.location:
            info += f"\nLocation: {self.location}"
        return info


@dataclass
class PhotosApp(App):
    """
    Photos library management application.

    Manages photos, videos, albums, and memories. Provides organization,
    searching, sharing, and editing capabilities for the photo library.

    Key Features:
        - Photo Library: Organize and manage photos and videos
        - Albums: Create regular, shared, and smart albums
        - Favorites: Mark important photos
        - Hidden Photos: Hide sensitive photos
        - Recently Deleted: Temporary storage for deleted photos
        - People & Places: Tag people and locations
        - Memories: Auto-generated collections from events
        - Document Detection: Identify screenshots of documents (receipts, legal docs)
        - Privacy: Mark sensitive content (personal selfies, private photos)

    Notes:
        - Some photos may contain important documents (receipts, legal evidence)
        - Hidden photos are kept private from shared albums
        - Recently Deleted photos can be recovered within 30 days
        - Shared albums allow family/friends to view photos
    """

    name: str | None = None
    photos: dict[str, Photo] = field(default_factory=dict)
    albums: dict[str, Album] = field(default_factory=dict)
    memories: dict[str, Memory] = field(default_factory=dict)
    recently_deleted_days_limit: int = 30  # Days before permanent deletion

    def __post_init__(self):
        super().__init__(self.name)

        # Create default albums
        if not self.albums:
            self._create_default_albums()

    def _create_default_albums(self):
        """Create system default albums."""
        # Favorites album
        self.albums["favorites"] = Album(
            album_id="favorites",
            name="Favorites",
            album_type=AlbumType.SMART,
        )

        # Recently Deleted album
        self.albums["recently_deleted"] = Album(
            album_id="recently_deleted",
            name="Recently Deleted",
            album_type=AlbumType.SMART,
        )

        # Hidden album
        self.albums["hidden"] = Album(
            album_id="hidden",
            name="Hidden",
            album_type=AlbumType.SMART,
        )

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(
            self,
            ["photos", "albums", "memories", "recently_deleted_days_limit"],
        )

    def load_state(self, state_dict: dict[str, Any]):
        self.photos = {k: Photo(**v) for k, v in state_dict.get("photos", {}).items()}
        self.albums = {k: Album(**v) for k, v in state_dict.get("albums", {}).items()}
        self.memories = {k: Memory(**v) for k, v in state_dict.get("memories", {}).items()}
        self.recently_deleted_days_limit = state_dict.get("recently_deleted_days_limit", 30)

    def reset(self):
        super().reset()
        self.photos = {}
        self.albums = {}
        self.memories = {}
        self._create_default_albums()

    # Photo Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_photo(
        self,
        filename: str,
        photo_type: str = "Photo",
        location: str | None = None,
        people_tags: list[str] | None = None,
        caption: str | None = None,
        contains_document: bool = False,
        document_description: str | None = None,
        is_sensitive: bool = False,
    ) -> str:
        """
        Add a photo or video to the library.

        :param filename: Filename of the photo (e.g., "IMG_1234.jpg")
        :param photo_type: Type of photo. Options: Photo, Screenshot, Video, Live Photo, Panorama, Burst
        :param location: Location where photo was taken
        :param people_tags: List of people names in the photo
        :param caption: Optional caption
        :param contains_document: True if this is a screenshot of a document (receipt, legal doc, etc.)
        :param document_description: Description of the document type (e.g., "Tax receipt", "Legal evidence")
        :param is_sensitive: True if this is private/sensitive content
        :returns: photo_id of the added photo
        """
        if people_tags is None:
            people_tags = []

        photo_type_enum = PhotoType[photo_type.upper().replace(" ", "_")]

        photo = Photo(
            photo_id=uuid_hex(self.rng),
            filename=filename,
            photo_type=photo_type_enum,
            date_taken=self.time_manager.time(),
            date_added=self.time_manager.time(),
            location=location,
            people_tags=people_tags,
            caption=caption,
            contains_document=contains_document,
            document_description=document_description,
            is_sensitive=is_sensitive,
        )

        self.photos[photo.photo_id] = photo
        return photo.photo_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def search_photos(
        self,
        query: str | None = None,
        person: str | None = None,
        location: str | None = None,
        photo_type: str | None = None,
        favorites_only: bool = False,
        include_hidden: bool = False,
        include_deleted: bool = False,
    ) -> str:
        """
        Search for photos by various criteria.

        :param query: Search in filename, caption, or location
        :param person: Filter by person tagged in photo
        :param location: Filter by location
        :param photo_type: Filter by type (Photo, Screenshot, Video, etc.)
        :param favorites_only: Only show favorite photos
        :param include_hidden: Include hidden photos in results
        :param include_deleted: Include recently deleted photos
        :returns: String representation of matching photos
        """
        filtered_photos = list(self.photos.values())

        # Filter by deletion status
        if not include_deleted:
            filtered_photos = [p for p in filtered_photos if not p.is_deleted]

        # Filter by hidden status
        if not include_hidden:
            filtered_photos = [p for p in filtered_photos if not p.is_hidden]

        if query:
            query_lower = query.lower()
            filtered_photos = [
                p
                for p in filtered_photos
                if query_lower in p.filename.lower()
                or (p.caption and query_lower in p.caption.lower())
                or (p.location and query_lower in p.location.lower())
            ]

        if person:
            filtered_photos = [p for p in filtered_photos if person in p.people_tags]

        if location:
            filtered_photos = [p for p in filtered_photos if p.location and location.lower() in p.location.lower()]

        if photo_type:
            photo_type_enum = PhotoType[photo_type.upper().replace(" ", "_")]
            filtered_photos = [p for p in filtered_photos if p.photo_type == photo_type_enum]

        if favorites_only:
            filtered_photos = [p for p in filtered_photos if p.is_favorite]

        # Sort by date (newest first)
        filtered_photos.sort(key=lambda p: p.date_taken, reverse=True)

        if not filtered_photos:
            return "No photos found matching the criteria."

        result = f"Found {len(filtered_photos)} photo(s):\n\n"
        for photo in filtered_photos[:20]:  # Limit to 20 results
            result += photo.summary + "\n"

        if len(filtered_photos) > 20:
            result += f"\n... and {len(filtered_photos) - 20} more"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_photo_details(self, photo_id: str) -> str:
        """
        Get detailed information about a photo.

        :param photo_id: ID of the photo
        :returns: Detailed photo information
        """
        if photo_id not in self.photos:
            return f"Photo with ID {photo_id} not found."

        return str(self.photos[photo_id])

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def mark_as_favorite(self, photo_id: str) -> str:
        """
        Mark a photo as favorite.

        :param photo_id: ID of the photo
        :returns: Success or error message
        """
        if photo_id not in self.photos:
            return f"Photo with ID {photo_id} not found."

        photo = self.photos[photo_id]
        photo.is_favorite = True

        return f"✓ '{photo.filename}' marked as favorite."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def hide_photo(self, photo_id: str) -> str:
        """
        Hide a photo (moves to Hidden album, removed from main library view).

        :param photo_id: ID of the photo to hide
        :returns: Success or error message
        """
        if photo_id not in self.photos:
            return f"Photo with ID {photo_id} not found."

        photo = self.photos[photo_id]
        photo.is_hidden = True

        return f"✓ '{photo.filename}' moved to Hidden album."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def unhide_photo(self, photo_id: str) -> str:
        """
        Unhide a photo (restores to main library).

        :param photo_id: ID of the photo to unhide
        :returns: Success or error message
        """
        if photo_id not in self.photos:
            return f"Photo with ID {photo_id} not found."

        photo = self.photos[photo_id]
        photo.is_hidden = False

        return f"✓ '{photo.filename}' restored to library."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_photo(self, photo_id: str) -> str:
        """
        Delete a photo (moves to Recently Deleted album for 30 days before permanent deletion).

        :param photo_id: ID of the photo to delete
        :returns: Success or error message
        """
        if photo_id not in self.photos:
            return f"Photo with ID {photo_id} not found."

        photo = self.photos[photo_id]

        if photo.contains_document:
            return f"⚠️ WARNING: '{photo.filename}' contains a document ({photo.document_description}). Deleting may result in loss of important information. Are you sure?"

        photo.is_deleted = True

        return f"✓ '{photo.filename}' moved to Recently Deleted. It will be permanently deleted in {self.recently_deleted_days_limit} days."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def permanently_delete_photo(self, photo_id: str) -> str:
        """
        Permanently delete a photo (cannot be recovered).

        :param photo_id: ID of the photo to permanently delete
        :returns: Success or error message
        """
        if photo_id not in self.photos:
            return f"Photo with ID {photo_id} not found."

        photo = self.photos[photo_id]
        filename = photo.filename

        # Remove from all albums
        for album in self.albums.values():
            if photo_id in album.photo_ids:
                album.photo_ids.remove(photo_id)

        # Remove from all memories
        for memory in self.memories.values():
            if photo_id in memory.photo_ids:
                memory.photo_ids.remove(photo_id)

        del self.photos[photo_id]

        return f"✓ '{filename}' permanently deleted."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def recover_photo(self, photo_id: str) -> str:
        """
        Recover a photo from Recently Deleted.

        :param photo_id: ID of the photo to recover
        :returns: Success or error message
        """
        if photo_id not in self.photos:
            return f"Photo with ID {photo_id} not found."

        photo = self.photos[photo_id]

        if not photo.is_deleted:
            return f"'{photo.filename}' is not in Recently Deleted."

        photo.is_deleted = False

        return f"✓ '{photo.filename}' recovered from Recently Deleted."

    # Album Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_album(self, name: str, is_shared: bool = False) -> str:
        """
        Create a new photo album.

        :param name: Album name
        :param is_shared: Whether this is a shared album
        :returns: album_id of the created album
        """
        album_type = AlbumType.SHARED if is_shared else AlbumType.REGULAR

        album = Album(
            album_id=uuid_hex(self.rng),
            name=name,
            album_type=album_type,
            created_date=self.time_manager.time(),
            is_shared=is_shared,
        )

        self.albums[album.album_id] = album
        return album.album_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_photo_to_album(self, album_id: str, photo_id: str) -> str:
        """
        Add a photo to an album.

        :param album_id: ID of the album
        :param photo_id: ID of the photo to add
        :returns: Success or error message
        """
        if album_id not in self.albums:
            return f"Album with ID {album_id} not found."

        if photo_id not in self.photos:
            return f"Photo with ID {photo_id} not found."

        album = self.albums[album_id]
        photo = self.photos[photo_id]

        # Don't add hidden or deleted photos to regular albums
        if photo.is_hidden and album_id != "hidden":
            return f"Cannot add hidden photo to album. Unhide it first."

        if photo.is_deleted and album_id != "recently_deleted":
            return f"Cannot add deleted photo to album. Recover it first."

        # Don't add sensitive photos to shared albums
        if album.is_shared and photo.is_sensitive:
            return f"⚠️ Cannot add sensitive photo '{photo.filename}' to shared album."

        if photo_id in album.photo_ids:
            return f"'{photo.filename}' is already in album '{album.name}'."

        album.photo_ids.append(photo_id)

        return f"✓ '{photo.filename}' added to album '{album.name}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def remove_photo_from_album(self, album_id: str, photo_id: str) -> str:
        """
        Remove a photo from an album.

        :param album_id: ID of the album
        :param photo_id: ID of the photo to remove
        :returns: Success or error message
        """
        if album_id not in self.albums:
            return f"Album with ID {album_id} not found."

        album = self.albums[album_id]

        # Can't remove from smart albums
        if album.album_type == AlbumType.SMART:
            return f"Cannot manually remove photos from smart album '{album.name}'."

        if photo_id not in album.photo_ids:
            return f"Photo is not in album '{album.name}'."

        photo = self.photos.get(photo_id)
        photo_name = photo.filename if photo else "Unknown"

        album.photo_ids.remove(photo_id)

        return f"✓ '{photo_name}' removed from album '{album.name}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_albums(self, include_smart: bool = True) -> str:
        """
        List all albums.

        :param include_smart: Whether to include smart albums (Favorites, Recently Deleted, Hidden)
        :returns: String representation of all albums
        """
        filtered_albums = list(self.albums.values())

        if not include_smart:
            filtered_albums = [a for a in filtered_albums if a.album_type != AlbumType.SMART]

        if not filtered_albums:
            return "No albums found."

        result = f"Albums ({len(filtered_albums)}):\n\n"
        for album in filtered_albums:
            result += str(album) + "\n" + "-" * 40 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_album_photos(self, album_id: str) -> str:
        """
        Get all photos in an album.

        :param album_id: ID of the album
        :returns: String representation of photos in the album
        """
        if album_id not in self.albums:
            return f"Album with ID {album_id} not found."

        album = self.albums[album_id]

        # For smart albums, dynamically generate content
        if album.album_type == AlbumType.SMART:
            if album_id == "favorites":
                photo_ids = [p.photo_id for p in self.photos.values() if p.is_favorite and not p.is_deleted]
            elif album_id == "recently_deleted":
                photo_ids = [p.photo_id for p in self.photos.values() if p.is_deleted]
            elif album_id == "hidden":
                photo_ids = [p.photo_id for p in self.photos.values() if p.is_hidden and not p.is_deleted]
            else:
                photo_ids = album.photo_ids
        else:
            photo_ids = album.photo_ids

        if not photo_ids:
            return f"Album '{album.name}' is empty."

        result = f"Photos in '{album.name}' ({len(photo_ids)}):\n\n"
        for photo_id in photo_ids[:20]:  # Limit to 20
            if photo_id in self.photos:
                photo = self.photos[photo_id]
                result += f"- {photo.summary}\n"

        if len(photo_ids) > 20:
            result += f"\n... and {len(photo_ids) - 20} more"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def share_album_with(self, album_id: str, person_name: str) -> str:
        """
        Share an album with someone.

        :param album_id: ID of the album to share
        :param person_name: Name of the person to share with
        :returns: Success or error message
        """
        if album_id not in self.albums:
            return f"Album with ID {album_id} not found."

        album = self.albums[album_id]
        album.is_shared = True

        if person_name not in album.shared_with:
            album.shared_with.append(person_name)

        return f"✓ Album '{album.name}' shared with {person_name}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_album(self, album_id: str) -> str:
        """
        Delete an album (photos remain in library).

        :param album_id: ID of the album to delete
        :returns: Success or error message
        """
        if album_id not in self.albums:
            return f"Album with ID {album_id} not found."

        album = self.albums[album_id]

        # Can't delete smart albums
        if album.album_type == AlbumType.SMART:
            return f"Cannot delete system album '{album.name}'."

        album_name = album.name
        del self.albums[album_id]

        return f"✓ Album '{album_name}' deleted (photos remain in library)."

    # Statistics

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_library_stats(self) -> str:
        """
        Get statistics about the photo library.

        :returns: Library statistics
        """
        total_photos = len([p for p in self.photos.values() if not p.is_deleted])
        total_albums = len([a for a in self.albums.values() if a.album_type != AlbumType.SMART])
        favorites = len([p for p in self.photos.values() if p.is_favorite and not p.is_deleted])
        hidden = len([p for p in self.photos.values() if p.is_hidden and not p.is_deleted])
        deleted = len([p for p in self.photos.values() if p.is_deleted])

        # Calculate storage
        total_storage_mb = sum(p.file_size_mb for p in self.photos.values() if not p.is_deleted)
        total_storage_gb = total_storage_mb / 1024

        result = "=== PHOTOS LIBRARY STATS ===\n\n"
        result += f"Total Photos: {total_photos}\n"
        result += f"Total Albums: {total_albums}\n"
        result += f"Favorites: {favorites}\n"
        result += f"Hidden: {hidden}\n"
        result += f"Recently Deleted: {deleted}\n"
        result += f"Storage Used: {total_storage_gb:.2f} GB\n"

        # Type distribution
        type_counts = {}
        for photo in self.photos.values():
            if not photo.is_deleted:
                type_counts[photo.photo_type.value] = type_counts.get(photo.photo_type.value, 0) + 1

        if type_counts:
            result += "\nType Distribution:\n"
            for photo_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                result += f"  - {photo_type}: {count}\n"

        return result
