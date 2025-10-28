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


class NoteType(Enum):
    TEXT = "Text"
    CHECKLIST = "Checklist"
    SKETCH = "Sketch"


@dataclass
class Note:
    """Represents a note document."""

    note_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "New Note"
    content: str = ""
    note_type: NoteType = NoteType.TEXT
    folder: str = "Notes"  # Folder name

    # Metadata
    created_date: float = field(default_factory=time.time)
    modified_date: float = field(default_factory=time.time)
    is_pinned: bool = False
    is_locked: bool = False  # Password protected
    is_shared: bool = False
    shared_with: list[str] = field(default_factory=list)  # Contact names

    # Content organization
    tags: list[str] = field(default_factory=list)
    attachments: list[dict[str, Any]] = field(default_factory=list)  # File attachments
    checklist_items: list[dict[str, Any]] = field(default_factory=list)  # For checklist notes
    links: list[str] = field(default_factory=list)  # URLs mentioned in note

    # Formatting
    is_bold: bool = False
    is_italic: bool = False
    has_heading: bool = False

    def __post_init__(self):
        # Extract URLs from content
        if self.content and not self.links:
            import re
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            self.links = re.findall(url_pattern, self.content)

    def __str__(self):
        pin_indicator = "📌 " if self.is_pinned else ""
        lock_indicator = "🔒 " if self.is_locked else ""
        share_indicator = "👥 " if self.is_shared else ""

        info = f"{pin_indicator}{lock_indicator}{share_indicator}{self.title}\n"
        info += f"Folder: {self.folder}\n"
        info += f"Type: {self.note_type.value}\n"
        info += f"Created: {time.ctime(self.created_date)}\n"
        info += f"Modified: {time.ctime(self.modified_date)}\n"

        if self.tags:
            info += f"Tags: {', '.join(['#' + tag for tag in self.tags])}\n"

        if self.note_type == NoteType.CHECKLIST and self.checklist_items:
            completed = sum(1 for item in self.checklist_items if item.get("completed", False))
            info += f"Checklist: {completed}/{len(self.checklist_items)} completed\n"

        if self.attachments:
            info += f"Attachments: {len(self.attachments)}\n"

        if self.links:
            info += f"Links: {len(self.links)}\n"

        if self.is_shared:
            info += f"Shared with: {', '.join(self.shared_with)}\n"

        # Show content preview
        content_preview = self.content[:200] + "..." if len(self.content) > 200 else self.content
        info += f"\nContent:\n{content_preview}\n"

        return info

    @property
    def word_count(self) -> int:
        """Calculate word count of the note."""
        return len(self.content.split()) if self.content else 0


@dataclass
class Folder:
    """Represents a folder for organizing notes."""

    folder_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Notes"
    parent_folder: str | None = None  # For nested folders
    icon: str = "folder"
    color: str | None = None

    def __str__(self):
        return f"📁 {self.name}"


@dataclass
class NotesApp(App):
    """
    iOS Notes application for creating and organizing text notes.

    Manages notes with support for folders, tags, checklists, attachments,
    sharing, and various formatting options.

    Key Features:
        - Multiple Note Types: Text, Checklist, Sketch notes
        - Folders: Organize notes into folders and subfolders
        - Pinning: Pin important notes to top
        - Locking: Password-protect sensitive notes
        - Tags: Categorize notes with hashtags
        - Attachments: Add files, images, and other media
        - Checklists: Create todo lists within notes
        - Sharing: Share notes with other people
        - Search: Find notes by title, content, or tags
        - Smart Folders: Recently Deleted, Pinned, Shared

    Notes:
        - Pinned notes appear at the top of the list
        - Locked notes require password to view/edit
        - Notes can contain multiple attachments
        - Tags are extracted from content or added manually
        - Deleted notes can be recovered from Recently Deleted folder
    """

    name: str | None = None
    notes: dict[str, Note] = field(default_factory=dict)
    folders: dict[str, Folder] = field(default_factory=dict)
    recently_deleted: dict[str, Note] = field(default_factory=dict)  # Deleted notes
    default_folder: str = "Notes"

    def __post_init__(self):
        super().__init__(self.name)

        # Create default folder if none exist
        if not self.folders:
            default_folder = Folder(
                folder_id=uuid_hex(self.rng),
                name=self.default_folder
            )
            self.folders[default_folder.folder_id] = default_folder

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(self, ["notes", "folders", "recently_deleted", "default_folder"])

    def load_state(self, state_dict: dict[str, Any]):
        self.notes = {k: Note(**v) for k, v in state_dict.get("notes", {}).items()}
        self.folders = {k: Folder(**v) for k, v in state_dict.get("folders", {}).items()}
        self.recently_deleted = {k: Note(**v) for k, v in state_dict.get("recently_deleted", {}).items()}
        self.default_folder = state_dict.get("default_folder", "Notes")

    def reset(self):
        super().reset()
        self.notes = {}
        self.folders = {}
        self.recently_deleted = {}

    # Note Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_note(
        self,
        title: str,
        content: str = "",
        folder: str | None = None,
        note_type: str = "Text",
        tags: list[str] | None = None,
        is_pinned: bool = False,
    ) -> str:
        """
        Create a new note.

        :param title: Title of the note
        :param content: Content/body of the note
        :param folder: Folder to save note in (default: "Notes")
        :param note_type: Type of note. Options: Text, Checklist, Sketch
        :param tags: List of tags to categorize the note
        :param is_pinned: Whether to pin the note
        :returns: note_id of the created note
        """
        if tags is None:
            tags = []

        if folder is None:
            folder = self.default_folder

        # Verify folder exists
        folder_exists = any(f.name == folder for f in self.folders.values())
        if not folder_exists:
            # Create the folder
            new_folder = Folder(
                folder_id=uuid_hex(self.rng),
                name=folder
            )
            self.folders[new_folder.folder_id] = new_folder

        note_type_enum = NoteType[note_type.upper()]

        note = Note(
            note_id=uuid_hex(self.rng),
            title=title,
            content=content,
            note_type=note_type_enum,
            folder=folder,
            tags=tags,
            is_pinned=is_pinned,
            created_date=self.time_manager.time(),
            modified_date=self.time_manager.time(),
        )

        self.notes[note.note_id] = note
        return note.note_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_notes(
        self,
        folder: str | None = None,
        pinned_only: bool = False,
        tag: str | None = None,
        sort_by: str = "modified",
    ) -> str:
        """
        List notes with optional filters.

        :param folder: Filter by folder name (optional)
        :param pinned_only: Only show pinned notes
        :param tag: Filter by tag
        :param sort_by: Sort by 'modified', 'created', 'title', or 'word_count' (default: modified)
        :returns: String representation of matching notes
        """
        filtered_notes = list(self.notes.values())

        # Apply filters
        if folder:
            filtered_notes = [n for n in filtered_notes if n.folder == folder]

        if pinned_only:
            filtered_notes = [n for n in filtered_notes if n.is_pinned]

        if tag:
            filtered_notes = [n for n in filtered_notes if tag in n.tags]

        if not filtered_notes:
            return "No notes found."

        # Sort notes
        if sort_by == "modified":
            filtered_notes.sort(key=lambda n: n.modified_date, reverse=True)
        elif sort_by == "created":
            filtered_notes.sort(key=lambda n: n.created_date, reverse=True)
        elif sort_by == "title":
            filtered_notes.sort(key=lambda n: n.title.lower())
        elif sort_by == "word_count":
            filtered_notes.sort(key=lambda n: n.word_count, reverse=True)

        # Pinned notes always appear first
        pinned = [n for n in filtered_notes if n.is_pinned]
        unpinned = [n for n in filtered_notes if not n.is_pinned]
        filtered_notes = pinned + unpinned

        result = f"Notes ({len(filtered_notes)}):\n\n"
        for note in filtered_notes:
            result += str(note) + "-" * 70 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_note(self, note_id: str) -> str:
        """
        Get full details of a specific note.

        :param note_id: ID of the note
        :returns: Complete note information including full content
        """
        if note_id not in self.notes:
            return f"Note with ID {note_id} not found."

        note = self.notes[note_id]

        if note.is_locked:
            return f"🔒 Note '{note.title}' is locked. Unlock it first to view contents."

        info = str(note)

        # For checklist notes, show all items
        if note.note_type == NoteType.CHECKLIST and note.checklist_items:
            info += "\nChecklist Items:\n"
            for item in note.checklist_items:
                status = "✓" if item.get("completed", False) else "○"
                info += f"  {status} {item['text']}\n"

        return info

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def update_note(
        self,
        note_id: str,
        title: str | None = None,
        content: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """
        Update an existing note.

        :param note_id: ID of the note to update
        :param title: New title (optional)
        :param content: New content (optional)
        :param tags: New tags list (optional)
        :returns: Success or error message
        """
        if note_id not in self.notes:
            return f"Note with ID {note_id} not found."

        note = self.notes[note_id]

        if note.is_locked:
            return f"🔒 Note '{note.title}' is locked. Unlock it first to edit."

        changes = []

        if title is not None:
            note.title = title
            changes.append("title")

        if content is not None:
            note.content = content
            # Re-extract links
            import re
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            note.links = re.findall(url_pattern, content)
            changes.append("content")

        if tags is not None:
            note.tags = tags
            changes.append("tags")

        if changes:
            note.modified_date = self.time_manager.time()

        return f"✓ Note '{note.title}' updated: {', '.join(changes)}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def append_to_note(self, note_id: str, text: str) -> str:
        """
        Append text to the end of a note.

        :param note_id: ID of the note
        :param text: Text to append
        :returns: Success or error message
        """
        if note_id not in self.notes:
            return f"Note with ID {note_id} not found."

        note = self.notes[note_id]

        if note.is_locked:
            return f"🔒 Note '{note.title}' is locked. Unlock it first to edit."

        note.content += "\n" + text
        note.modified_date = self.time_manager.time()

        return f"✓ Text appended to note '{note.title}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_note(self, note_id: str) -> str:
        """
        Delete a note (moves to Recently Deleted).

        :param note_id: ID of the note to delete
        :returns: Success or error message
        """
        if note_id not in self.notes:
            return f"Note with ID {note_id} not found."

        note = self.notes[note_id]

        # Move to recently deleted
        self.recently_deleted[note_id] = note
        del self.notes[note_id]

        return f"✓ Note '{note.title}' moved to Recently Deleted."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def recover_note(self, note_id: str) -> str:
        """
        Recover a note from Recently Deleted.

        :param note_id: ID of the note to recover
        :returns: Success or error message
        """
        if note_id not in self.recently_deleted:
            return f"Note with ID {note_id} not found in Recently Deleted."

        note = self.recently_deleted[note_id]
        self.notes[note_id] = note
        del self.recently_deleted[note_id]

        return f"✓ Note '{note.title}' recovered from Recently Deleted."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def permanently_delete_note(self, note_id: str) -> str:
        """
        Permanently delete a note from Recently Deleted.

        :param note_id: ID of the note to permanently delete
        :returns: Success or error message
        """
        if note_id not in self.recently_deleted:
            return f"Note with ID {note_id} not found in Recently Deleted."

        note = self.recently_deleted[note_id]
        del self.recently_deleted[note_id]

        return f"✓ Note '{note.title}' permanently deleted."

    # Note Actions

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def pin_note(self, note_id: str) -> str:
        """
        Pin a note to the top of the list.

        :param note_id: ID of the note to pin
        :returns: Success or error message
        """
        if note_id not in self.notes:
            return f"Note with ID {note_id} not found."

        note = self.notes[note_id]
        note.is_pinned = True

        return f"📌 Note '{note.title}' pinned."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def unpin_note(self, note_id: str) -> str:
        """
        Unpin a note.

        :param note_id: ID of the note to unpin
        :returns: Success or error message
        """
        if note_id not in self.notes:
            return f"Note with ID {note_id} not found."

        note = self.notes[note_id]
        note.is_pinned = False

        return f"✓ Note '{note.title}' unpinned."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def lock_note(self, note_id: str) -> str:
        """
        Lock a note with password protection.

        :param note_id: ID of the note to lock
        :returns: Success or error message
        """
        if note_id not in self.notes:
            return f"Note with ID {note_id} not found."

        note = self.notes[note_id]
        note.is_locked = True

        return f"🔒 Note '{note.title}' locked."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def unlock_note(self, note_id: str) -> str:
        """
        Unlock a locked note.

        :param note_id: ID of the note to unlock
        :returns: Success or error message
        """
        if note_id not in self.notes:
            return f"Note with ID {note_id} not found."

        note = self.notes[note_id]
        note.is_locked = False

        return f"🔓 Note '{note.title}' unlocked."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def move_note_to_folder(self, note_id: str, folder_name: str) -> str:
        """
        Move a note to a different folder.

        :param note_id: ID of the note to move
        :param folder_name: Name of the destination folder
        :returns: Success or error message
        """
        if note_id not in self.notes:
            return f"Note with ID {note_id} not found."

        # Verify destination folder exists
        folder_exists = any(f.name == folder_name for f in self.folders.values())
        if not folder_exists:
            return f"Folder '{folder_name}' not found. Create it first with create_folder."

        note = self.notes[note_id]
        old_folder = note.folder
        note.folder = folder_name

        return f"✓ Note '{note.title}' moved from '{old_folder}' to '{folder_name}'."

    # Checklist Operations

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_checklist_item(self, note_id: str, item_text: str) -> str:
        """
        Add a checklist item to a note.

        :param note_id: ID of the note
        :param item_text: Text of the checklist item
        :returns: Success or error message
        """
        if note_id not in self.notes:
            return f"Note with ID {note_id} not found."

        note = self.notes[note_id]

        item = {
            "id": uuid_hex(self.rng),
            "text": item_text,
            "completed": False
        }
        note.checklist_items.append(item)
        note.modified_date = self.time_manager.time()

        return f"✓ Checklist item added to note '{note.title}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def check_checklist_item(self, note_id: str, item_id: str) -> str:
        """
        Mark a checklist item as completed.

        :param note_id: ID of the note
        :param item_id: ID of the checklist item
        :returns: Success or error message
        """
        if note_id not in self.notes:
            return f"Note with ID {note_id} not found."

        note = self.notes[note_id]

        for item in note.checklist_items:
            if item["id"] == item_id:
                item["completed"] = True
                note.modified_date = self.time_manager.time()

                completed = sum(1 for i in note.checklist_items if i["completed"])
                total = len(note.checklist_items)

                return f"✓ Checklist item completed. Progress: {completed}/{total}"

        return f"Checklist item with ID {item_id} not found."

    # Folder Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_folder(self, name: str, parent_folder: str | None = None) -> str:
        """
        Create a new folder for organizing notes.

        :param name: Name of the folder
        :param parent_folder: Name of parent folder for nesting (optional)
        :returns: folder_id of the created folder
        """
        # Check if folder already exists
        for folder in self.folders.values():
            if folder.name == name:
                return f"A folder named '{name}' already exists."

        folder = Folder(
            folder_id=uuid_hex(self.rng),
            name=name,
            parent_folder=parent_folder,
        )

        self.folders[folder.folder_id] = folder
        return folder.folder_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_folders(self) -> str:
        """
        List all folders with note counts.

        :returns: String representation of all folders
        """
        if not self.folders:
            return "No folders found."

        result = "Folders:\n\n"

        for folder in self.folders.values():
            count = sum(1 for n in self.notes.values() if n.folder == folder.name)
            result += f"{str(folder)} ({count} note{'s' if count != 1 else ''})\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_folder(self, folder_name: str, delete_notes: bool = False) -> str:
        """
        Delete a folder.

        :param folder_name: Name of the folder to delete
        :param delete_notes: If True, delete all notes in folder. If False, move them to default folder.
        :returns: Success or error message
        """
        if folder_name == self.default_folder:
            return f"Cannot delete the default folder '{self.default_folder}'."

        # Find the folder
        folder_to_delete = None
        for folder in self.folders.values():
            if folder.name == folder_name:
                folder_to_delete = folder
                break

        if not folder_to_delete:
            return f"Folder '{folder_name}' not found."

        # Handle notes in the folder
        notes_in_folder = [n for n in self.notes.values() if n.folder == folder_name]

        if delete_notes:
            for note in notes_in_folder:
                self.recently_deleted[note.note_id] = note
                del self.notes[note.note_id]
            message = f"✓ Folder '{folder_name}' deleted. {len(notes_in_folder)} note(s) moved to Recently Deleted."
        else:
            for note in notes_in_folder:
                note.folder = self.default_folder
            message = f"✓ Folder '{folder_name}' deleted. {len(notes_in_folder)} note(s) moved to '{self.default_folder}'."

        del self.folders[folder_to_delete.folder_id]
        return message

    # Search and Discovery

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def search_notes(self, query: str) -> str:
        """
        Search notes by title, content, or tags.

        :param query: Search query
        :returns: String representation of matching notes
        """
        query_lower = query.lower()
        matches = []

        for note in self.notes.values():
            # Search in title
            if query_lower in note.title.lower():
                matches.append(note)
                continue

            # Search in content
            if note.content and query_lower in note.content.lower():
                matches.append(note)
                continue

            # Search in tags
            if any(query_lower in tag.lower() for tag in note.tags):
                matches.append(note)
                continue

        if not matches:
            return f"No notes found matching '{query}'."

        result = f"Search Results for '{query}' ({len(matches)}):\n\n"
        for note in matches:
            result += str(note) + "-" * 70 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_pinned_notes(self) -> str:
        """
        Get all pinned notes.

        :returns: String representation of pinned notes
        """
        pinned = [n for n in self.notes.values() if n.is_pinned]

        if not pinned:
            return "No pinned notes found."

        # Sort by modified date
        pinned.sort(key=lambda n: n.modified_date, reverse=True)

        result = f"📌 Pinned Notes ({len(pinned)}):\n\n"
        for note in pinned:
            result += str(note) + "-" * 70 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_recently_deleted(self) -> str:
        """
        Get all notes in Recently Deleted.

        :returns: String representation of deleted notes
        """
        if not self.recently_deleted:
            return "Recently Deleted is empty."

        result = f"🗑️ Recently Deleted ({len(self.recently_deleted)}):\n\n"
        for note in self.recently_deleted.values():
            result += str(note) + "-" * 70 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_notes_summary(self) -> str:
        """
        Get summary of all notes and folders.

        :returns: Summary statistics
        """
        total_notes = len(self.notes)
        total_folders = len(self.folders)
        pinned_count = sum(1 for n in self.notes.values() if n.is_pinned)
        locked_count = sum(1 for n in self.notes.values() if n.is_locked)
        shared_count = sum(1 for n in self.notes.values() if n.is_shared)
        deleted_count = len(self.recently_deleted)

        summary = "=== NOTES SUMMARY ===\n\n"
        summary += f"Total Notes: {total_notes}\n"
        summary += f"Total Folders: {total_folders}\n"
        summary += f"Pinned: {pinned_count}\n"
        summary += f"Locked: {locked_count}\n"
        summary += f"Shared: {shared_count}\n"
        summary += f"Recently Deleted: {deleted_count}\n\n"

        # Folder breakdown
        summary += "Notes by Folder:\n"
        for folder in self.folders.values():
            count = sum(1 for n in self.notes.values() if n.folder == folder.name)
            if count > 0:
                summary += f"  {folder.name}: {count}\n"

        # Note types
        text_count = sum(1 for n in self.notes.values() if n.note_type == NoteType.TEXT)
        checklist_count = sum(1 for n in self.notes.values() if n.note_type == NoteType.CHECKLIST)

        summary += f"\nNote Types:\n"
        summary += f"  Text: {text_count}\n"
        summary += f"  Checklist: {checklist_count}\n"

        return summary
