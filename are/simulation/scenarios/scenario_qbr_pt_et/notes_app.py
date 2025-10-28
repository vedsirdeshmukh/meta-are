# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.


"""
iOS Notes App implementation for ARE scenarios.

This app simulates iOS Notes functionality including:
- Creating, reading, updating, and deleting notes
- Organizing notes in folders
- Pinning notes for quick access
- Adding checklists to notes
- Linking between notes
- Searching notes by content
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from are.simulation.apps.app import App
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import get_state_dict, type_check, uuid_hex

logger = logging.getLogger(__name__)


@dataclass
class Note:
    """Represents a single note in the iOS Notes app."""

    note_id: str
    title: str
    content: str
    folder: str = "Notes"  # Folder path like "Work" or "Personal/Family"
    updated_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    is_pinned: bool = False
    has_checklist: bool = False

    def __str__(self):
        pinned_str = " [PINNED]" if self.is_pinned else ""
        checklist_str = " [CHECKLIST]" if self.has_checklist else ""
        updated = datetime.fromtimestamp(self.updated_at, tz=timezone.utc).strftime("%b %d, %I:%M %p")
        return f"[{self.note_id}] {self.title}{pinned_str}{checklist_str}\nFolder: {self.folder}\nUpdated: {updated}\n\n{self.content[:200]}{'...' if len(self.content) > 200 else ''}"


@dataclass
class NotesApp(App):
    """
    iOS Notes application that manages text notes with folders, pinning, and checklists.

    Features:
        - CRUD operations for notes
        - Folder organization
        - Pinning important notes
        - Checklist support
        - Full-text search
        - Note linking
    """

    name: str | None = "Notes"
    notes: dict[str, Note] = field(default_factory=dict)
    folders: set[str] = field(default_factory=lambda: {"Notes"})  # Default folder

    def __post_init__(self):
        super().__init__(self.name)

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(self, ["notes", "folders"])

    def load_state(self, state_dict: dict[str, Any]):
        self.notes = {
            note_id: Note(**note_data)
            for note_id, note_data in state_dict.get("notes", {}).items()
        }
        self.folders = set(state_dict.get("folders", ["Notes"]))

    def reset(self):
        super().reset()
        self.notes = {}
        self.folders = {"Notes"}

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_note(
        self,
        title: str,
        content: str,
        folder: str = "Notes",
    ) -> str:
        """
        Create a new note in the specified folder.

        :param title: Title of the note
        :param content: Content/body of the note
        :param folder: Folder to place the note in (default: "Notes")
        :returns: The note_id of the created note
        """
        note_id = uuid_hex(self.rng)
        self.folders.add(folder)

        note = Note(
            note_id=note_id,
            title=title,
            content=content,
            folder=folder,
            updated_at=self.time_manager.time(),
        )
        self.notes[note_id] = note
        return note_id

    @type_check
    @app_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_note(self, note_id: str) -> Note:
        """
        Get a specific note by its ID.

        :param note_id: ID of the note to retrieve
        :returns: The Note object
        :raises ValueError: If note_id doesn't exist
        """
        if note_id not in self.notes:
            raise ValueError(f"Note with id {note_id} does not exist.")
        return self.notes[note_id]

    @type_check
    @app_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_notes(
        self,
        folder: str | None = None,
        pinned_only: bool = False,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Note]:
        """
        List notes, optionally filtered by folder and/or pinned status.

        :param folder: If specified, only show notes in this folder
        :param pinned_only: If True, only show pinned notes
        :param offset: Offset for pagination (default: 0)
        :param limit: Maximum number of notes to return (default: 20)
        :returns: List of Note objects matching the criteria
        """
        filtered_notes = list(self.notes.values())

        if folder:
            filtered_notes = [n for n in filtered_notes if n.folder == folder]

        if pinned_only:
            filtered_notes = [n for n in filtered_notes if n.is_pinned]

        # Sort by updated_at descending (most recent first)
        filtered_notes.sort(key=lambda n: n.updated_at, reverse=True)

        return filtered_notes[offset : offset + limit]

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def update_note(
        self,
        note_id: str,
        title: str | None = None,
        content: str | None = None,
        folder: str | None = None,
    ) -> str:
        """
        Update an existing note's title, content, or folder.

        :param note_id: ID of the note to update
        :param title: New title (if provided)
        :param content: New content (if provided)
        :param folder: New folder (if provided)
        :returns: Success message
        :raises ValueError: If note_id doesn't exist
        """
        if note_id not in self.notes:
            raise ValueError(f"Note with id {note_id} does not exist.")

        note = self.notes[note_id]

        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if folder is not None:
            self.folders.add(folder)
            note.folder = folder

        note.updated_at = self.time_manager.time()

        return f"Note {note_id} updated successfully."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_note(self, note_id: str) -> str:
        """
        Delete a note permanently.

        :param note_id: ID of the note to delete
        :returns: Success message
        :raises ValueError: If note_id doesn't exist
        """
        if note_id not in self.notes:
            raise ValueError(f"Note with id {note_id} does not exist.")

        del self.notes[note_id]
        return f"Note {note_id} deleted successfully."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def pin_note(self, note_id: str, pinned: bool = True) -> str:
        """
        Pin or unpin a note for quick access.

        :param note_id: ID of the note to pin/unpin
        :param pinned: True to pin, False to unpin
        :returns: Success message
        :raises ValueError: If note_id doesn't exist
        """
        if note_id not in self.notes:
            raise ValueError(f"Note with id {note_id} does not exist.")

        note = self.notes[note_id]
        note.is_pinned = pinned
        note.updated_at = self.time_manager.time()

        action = "pinned" if pinned else "unpinned"
        return f"Note {note_id} {action} successfully."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_checklist_to_note(self, note_id: str, checklist_items: list[str]) -> str:
        """
        Convert a note to include a checklist or add checklist items.
        This appends checklist items to the note content in markdown format.

        :param note_id: ID of the note
        :param checklist_items: List of checklist items to add
        :returns: Success message
        :raises ValueError: If note_id doesn't exist
        """
        if note_id not in self.notes:
            raise ValueError(f"Note with id {note_id} does not exist.")

        note = self.notes[note_id]

        # Add checklist items in markdown format
        checklist_text = "\n".join([f"- [ ] {item}" for item in checklist_items])

        if note.content:
            note.content += "\n\n" + checklist_text
        else:
            note.content = checklist_text

        note.has_checklist = True
        note.updated_at = self.time_manager.time()

        return f"Added {len(checklist_items)} checklist items to note {note_id}."

    @type_check
    @app_tool()
    @event_registered(operation_type=OperationType.READ)
    def search_notes(self, query: str, search_in_content: bool = True) -> list[Note]:
        """
        Search notes by title and optionally content.

        :param query: Search query string
        :param search_in_content: If True, search in note content as well as title
        :returns: List of notes matching the query
        """
        query_lower = query.lower()
        results = []

        for note in self.notes.values():
            if query_lower in note.title.lower():
                results.append(note)
            elif search_in_content and query_lower in note.content.lower():
                results.append(note)

        # Sort by updated_at descending
        results.sort(key=lambda n: n.updated_at, reverse=True)
        return results

    @type_check
    @app_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_folders(self) -> list[str]:
        """
        List all folders in the Notes app.

        :returns: List of folder names
        """
        return sorted(list(self.folders))

    @type_check
    @app_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_notes_in_folder(self, folder: str) -> list[Note]:
        """
        Get all notes in a specific folder.

        :param folder: Folder name
        :returns: List of notes in the folder
        """
        notes_in_folder = [n for n in self.notes.values() if n.folder == folder]
        notes_in_folder.sort(key=lambda n: n.updated_at, reverse=True)
        return notes_in_folder
