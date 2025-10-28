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


class Priority(Enum):
    NONE = "None"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ReminderRepeat(Enum):
    NEVER = "Never"
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    YEARLY = "Yearly"
    CUSTOM = "Custom"


@dataclass
class Reminder:
    """Represents a reminder task."""

    reminder_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "Reminder"
    notes: str | None = None
    list_name: str = "Reminders"  # Which list this reminder belongs to
    is_completed: bool = False
    priority: Priority = Priority.NONE

    # Time-based
    due_date: float | None = None  # Timestamp for when it's due
    reminder_date: float | None = None  # When to send notification
    repeat: ReminderRepeat = ReminderRepeat.NEVER

    # Location-based
    location: str | None = None
    location_trigger: str | None = None  # "arriving" or "leaving"

    # Metadata
    created_date: float = field(default_factory=time.time)
    completed_date: float | None = None
    url: str | None = None  # Associated URL
    subtasks: list[dict[str, Any]] = field(default_factory=list)  # Checklist items
    tags: list[str] = field(default_factory=list)
    flagged: bool = False  # Starred/important

    def __str__(self):
        status = "✓" if self.is_completed else "○"
        flag = "🚩" if self.flagged else ""

        info = f"{status} {flag} {self.title}\n"
        info += f"List: {self.list_name}\n"

        if self.priority != Priority.NONE:
            priority_symbols = {
                Priority.LOW: "!",
                Priority.MEDIUM: "!!",
                Priority.HIGH: "!!!"
            }
            info += f"Priority: {priority_symbols.get(self.priority, '')} {self.priority.value}\n"

        if self.due_date:
            info += f"Due: {time.ctime(self.due_date)}\n"

        if self.reminder_date:
            info += f"Remind: {time.ctime(self.reminder_date)}\n"

        if self.repeat != ReminderRepeat.NEVER:
            info += f"Repeat: {self.repeat.value}\n"

        if self.location:
            trigger_text = f" ({self.location_trigger})" if self.location_trigger else ""
            info += f"Location: {self.location}{trigger_text}\n"

        if self.notes:
            info += f"Notes: {self.notes}\n"

        if self.subtasks:
            completed_subtasks = sum(1 for s in self.subtasks if s.get("completed", False))
            info += f"Subtasks: {completed_subtasks}/{len(self.subtasks)} completed\n"

        if self.tags:
            info += f"Tags: {', '.join(self.tags)}\n"

        if self.url:
            info += f"URL: {self.url}\n"

        if self.is_completed and self.completed_date:
            info += f"Completed: {time.ctime(self.completed_date)}\n"

        return info


@dataclass
class ReminderList:
    """Represents a list/group of reminders."""

    list_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Reminders"
    color: str = "blue"  # blue, red, orange, yellow, green, purple, brown, gray
    icon: str = "list.bullet"  # SF Symbol name
    is_shared: bool = False
    shared_with: list[str] = field(default_factory=list)  # Contact names

    def __str__(self):
        info = f"📋 {self.name}\n"
        info += f"Color: {self.color}\n"

        if self.is_shared:
            info += f"Shared with: {', '.join(self.shared_with)}\n"

        return info


@dataclass
class RemindersApp(App):
    """
    iOS Reminders application for task and reminder management.

    Manages reminders with support for lists, priorities, due dates, location triggers,
    recurring reminders, subtasks, and sharing.

    Key Features:
        - Multiple Lists: Organize reminders into different lists
        - Time-based Reminders: Set due dates and reminder times
        - Location-based: Remind when arriving/leaving locations
        - Recurring Reminders: Daily, weekly, monthly, yearly repeats
        - Priorities: None, Low, Medium, High priority levels
        - Subtasks: Break down reminders into checklist items
        - Flagging: Mark important reminders
        - Tags: Categorize reminders with custom tags
        - Sharing: Share lists with other people
        - Smart Lists: Scheduled, Flagged, All reminders

    Notes:
        - Reminders can be organized into custom lists
        - Location-based reminders trigger on arrival/departure
        - Completed reminders are preserved for history
        - Subtasks allow creating checklists within reminders
    """

    name: str | None = None
    reminders: dict[str, Reminder] = field(default_factory=dict)
    lists: dict[str, ReminderList] = field(default_factory=dict)
    default_list: str = "Reminders"  # Default list name

    def __post_init__(self):
        super().__init__(self.name)

        # Create default list if none exist
        if not self.lists:
            default_list = ReminderList(
                list_id=uuid_hex(self.rng),
                name=self.default_list,
                color="blue"
            )
            self.lists[default_list.list_id] = default_list

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(self, ["reminders", "lists", "default_list"])

    def load_state(self, state_dict: dict[str, Any]):
        self.reminders = {k: Reminder(**v) for k, v in state_dict.get("reminders", {}).items()}
        self.lists = {k: ReminderList(**v) for k, v in state_dict.get("lists", {}).items()}
        self.default_list = state_dict.get("default_list", "Reminders")

    def reset(self):
        super().reset()
        self.reminders = {}
        self.lists = {}

    # Reminder Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_reminder(
        self,
        title: str,
        list_name: str | None = None,
        notes: str | None = None,
        due_date: str | None = None,
        reminder_date: str | None = None,
        priority: str = "None",
        repeat: str = "Never",
        location: str | None = None,
        location_trigger: str | None = None,
        flagged: bool = False,
        tags: list[str] | None = None,
    ) -> str:
        """
        Create a new reminder.

        :param title: Title/description of the reminder
        :param list_name: Name of list to add reminder to (default: "Reminders")
        :param notes: Additional notes
        :param due_date: Due date in format "YYYY-MM-DD HH:MM:SS"
        :param reminder_date: When to send reminder notification in format "YYYY-MM-DD HH:MM:SS"
        :param priority: Priority level. Options: None, Low, Medium, High
        :param repeat: Repeat frequency. Options: Never, Daily, Weekly, Monthly, Yearly, Custom
        :param location: Location for location-based reminder
        :param location_trigger: When to trigger. Options: arriving, leaving
        :param flagged: Whether to flag/star this reminder
        :param tags: List of tags to categorize the reminder
        :returns: reminder_id of the created reminder
        """
        if tags is None:
            tags = []

        if list_name is None:
            list_name = self.default_list

        # Verify list exists
        list_exists = any(l.name == list_name for l in self.lists.values())
        if not list_exists:
            # Create the list
            new_list = ReminderList(
                list_id=uuid_hex(self.rng),
                name=list_name
            )
            self.lists[new_list.list_id] = new_list

        # Parse dates
        due_timestamp = None
        if due_date:
            from datetime import datetime, timezone
            dt = datetime.strptime(due_date, "%Y-%m-%d %H:%M:%S")
            due_timestamp = dt.replace(tzinfo=timezone.utc).timestamp()

        reminder_timestamp = None
        if reminder_date:
            from datetime import datetime, timezone
            dt = datetime.strptime(reminder_date, "%Y-%m-%d %H:%M:%S")
            reminder_timestamp = dt.replace(tzinfo=timezone.utc).timestamp()

        priority_enum = Priority[priority.upper()]
        repeat_enum = ReminderRepeat[repeat.upper()]

        reminder = Reminder(
            reminder_id=uuid_hex(self.rng),
            title=title,
            notes=notes,
            list_name=list_name,
            due_date=due_timestamp,
            reminder_date=reminder_timestamp,
            priority=priority_enum,
            repeat=repeat_enum,
            location=location,
            location_trigger=location_trigger,
            flagged=flagged,
            tags=tags,
            created_date=self.time_manager.time(),
        )

        self.reminders[reminder.reminder_id] = reminder
        return reminder.reminder_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_reminders(
        self,
        list_name: str | None = None,
        show_completed: bool = False,
        flagged_only: bool = False,
        tag: str | None = None,
    ) -> str:
        """
        List reminders with optional filters.

        :param list_name: Filter by list name (optional)
        :param show_completed: Whether to show completed reminders
        :param flagged_only: Only show flagged reminders
        :param tag: Filter by tag
        :returns: String representation of matching reminders
        """
        filtered_reminders = list(self.reminders.values())

        # Apply filters
        if list_name:
            filtered_reminders = [r for r in filtered_reminders if r.list_name == list_name]

        if not show_completed:
            filtered_reminders = [r for r in filtered_reminders if not r.is_completed]

        if flagged_only:
            filtered_reminders = [r for r in filtered_reminders if r.flagged]

        if tag:
            filtered_reminders = [r for r in filtered_reminders if tag in r.tags]

        if not filtered_reminders:
            return "No reminders found."

        # Sort by due date, then by flagged status, then by priority
        def sort_key(r):
            priority_values = {Priority.HIGH: 3, Priority.MEDIUM: 2, Priority.LOW: 1, Priority.NONE: 0}
            return (
                r.due_date if r.due_date else float('inf'),
                not r.flagged,  # Flagged first
                -priority_values[r.priority],  # Higher priority first
            )

        filtered_reminders.sort(key=sort_key)

        result = f"Reminders ({len(filtered_reminders)}):\n\n"
        for reminder in filtered_reminders:
            result += str(reminder) + "-" * 60 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def complete_reminder(self, reminder_id: str) -> str:
        """
        Mark a reminder as completed.

        :param reminder_id: ID of the reminder to complete
        :returns: Success or error message
        """
        if reminder_id not in self.reminders:
            return f"Reminder with ID {reminder_id} not found."

        reminder = self.reminders[reminder_id]
        reminder.is_completed = True
        reminder.completed_date = self.time_manager.time()

        # Handle recurring reminders - create next occurrence
        if reminder.repeat != ReminderRepeat.NEVER and reminder.due_date:
            next_reminder = self._create_next_recurring_reminder(reminder)
            if next_reminder:
                return f"✓ Reminder '{reminder.title}' completed. Next occurrence created for {time.ctime(next_reminder.due_date)}."

        return f"✓ Reminder '{reminder.title}' marked as completed."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def uncomplete_reminder(self, reminder_id: str) -> str:
        """
        Mark a completed reminder as not completed.

        :param reminder_id: ID of the reminder to uncomplete
        :returns: Success or error message
        """
        if reminder_id not in self.reminders:
            return f"Reminder with ID {reminder_id} not found."

        reminder = self.reminders[reminder_id]
        reminder.is_completed = False
        reminder.completed_date = None

        return f"✓ Reminder '{reminder.title}' marked as not completed."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_reminder(self, reminder_id: str) -> str:
        """
        Delete a reminder.

        :param reminder_id: ID of the reminder to delete
        :returns: Success or error message
        """
        if reminder_id not in self.reminders:
            return f"Reminder with ID {reminder_id} not found."

        reminder = self.reminders[reminder_id]
        del self.reminders[reminder_id]

        return f"✓ Reminder '{reminder.title}' deleted."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def update_reminder(
        self,
        reminder_id: str,
        title: str | None = None,
        notes: str | None = None,
        due_date: str | None = None,
        priority: str | None = None,
        flagged: bool | None = None,
    ) -> str:
        """
        Update an existing reminder.

        :param reminder_id: ID of the reminder to update
        :param title: New title (optional)
        :param notes: New notes (optional)
        :param due_date: New due date in format "YYYY-MM-DD HH:MM:SS" (optional)
        :param priority: New priority (None, Low, Medium, High) (optional)
        :param flagged: New flagged status (optional)
        :returns: Success or error message
        """
        if reminder_id not in self.reminders:
            return f"Reminder with ID {reminder_id} not found."

        reminder = self.reminders[reminder_id]
        changes = []

        if title is not None:
            reminder.title = title
            changes.append(f"title to '{title}'")

        if notes is not None:
            reminder.notes = notes
            changes.append("notes")

        if due_date is not None:
            from datetime import datetime, timezone
            dt = datetime.strptime(due_date, "%Y-%m-%d %H:%M:%S")
            reminder.due_date = dt.replace(tzinfo=timezone.utc).timestamp()
            changes.append(f"due date to {due_date}")

        if priority is not None:
            reminder.priority = Priority[priority.upper()]
            changes.append(f"priority to {priority}")

        if flagged is not None:
            reminder.flagged = flagged
            changes.append(f"flagged to {flagged}")

        if not changes:
            return "No changes specified."

        return f"✓ Updated reminder '{reminder.title}': {', '.join(changes)}."

    # Subtasks

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_subtask(self, reminder_id: str, subtask_title: str) -> str:
        """
        Add a subtask/checklist item to a reminder.

        :param reminder_id: ID of the reminder
        :param subtask_title: Title of the subtask
        :returns: Success or error message
        """
        if reminder_id not in self.reminders:
            return f"Reminder with ID {reminder_id} not found."

        reminder = self.reminders[reminder_id]
        subtask = {
            "id": uuid_hex(self.rng),
            "title": subtask_title,
            "completed": False
        }
        reminder.subtasks.append(subtask)

        return f"✓ Subtask '{subtask_title}' added to reminder '{reminder.title}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def complete_subtask(self, reminder_id: str, subtask_id: str) -> str:
        """
        Mark a subtask as completed.

        :param reminder_id: ID of the reminder
        :param subtask_id: ID of the subtask
        :returns: Success or error message
        """
        if reminder_id not in self.reminders:
            return f"Reminder with ID {reminder_id} not found."

        reminder = self.reminders[reminder_id]

        for subtask in reminder.subtasks:
            if subtask["id"] == subtask_id:
                subtask["completed"] = True

                # Check if all subtasks are completed
                all_completed = all(s["completed"] for s in reminder.subtasks)
                if all_completed:
                    return f"✓ Subtask completed. All subtasks in '{reminder.title}' are now complete!"

                return f"✓ Subtask '{subtask['title']}' marked as completed."

        return f"Subtask with ID {subtask_id} not found."

    # List Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_list(
        self,
        name: str,
        color: str = "blue",
        icon: str = "list.bullet",
    ) -> str:
        """
        Create a new reminder list.

        :param name: Name of the list
        :param color: Color for the list. Options: blue, red, orange, yellow, green, purple, brown, gray
        :param icon: SF Symbol icon name (default: list.bullet)
        :returns: list_id of the created list
        """
        # Check if list already exists
        for reminder_list in self.lists.values():
            if reminder_list.name == name:
                return f"A list named '{name}' already exists."

        reminder_list = ReminderList(
            list_id=uuid_hex(self.rng),
            name=name,
            color=color,
            icon=icon,
        )

        self.lists[reminder_list.list_id] = reminder_list
        return reminder_list.list_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def show_lists(self) -> str:
        """
        Show all reminder lists with reminder counts.

        :returns: String representation of all lists
        """
        if not self.lists:
            return "No reminder lists found."

        result = "Reminder Lists:\n\n"

        for reminder_list in self.lists.values():
            count = sum(1 for r in self.reminders.values()
                       if r.list_name == reminder_list.name and not r.is_completed)
            result += f"{str(reminder_list)}Active Reminders: {count}\n"
            result += "-" * 50 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_list(self, list_name: str, delete_reminders: bool = False) -> str:
        """
        Delete a reminder list.

        :param list_name: Name of the list to delete
        :param delete_reminders: If True, delete all reminders in the list. If False, move them to default list.
        :returns: Success or error message
        """
        if list_name == self.default_list:
            return f"Cannot delete the default list '{self.default_list}'."

        # Find the list
        list_to_delete = None
        for reminder_list in self.lists.values():
            if reminder_list.name == list_name:
                list_to_delete = reminder_list
                break

        if not list_to_delete:
            return f"List '{list_name}' not found."

        # Handle reminders in the list
        reminders_in_list = [r for r in self.reminders.values() if r.list_name == list_name]

        if delete_reminders:
            for reminder in reminders_in_list:
                del self.reminders[reminder.reminder_id]
            message = f"✓ List '{list_name}' and {len(reminders_in_list)} reminder(s) deleted."
        else:
            for reminder in reminders_in_list:
                reminder.list_name = self.default_list
            message = f"✓ List '{list_name}' deleted. {len(reminders_in_list)} reminder(s) moved to '{self.default_list}'."

        del self.lists[list_to_delete.list_id]
        return message

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def move_reminder_to_list(self, reminder_id: str, list_name: str) -> str:
        """
        Move a reminder to a different list.

        :param reminder_id: ID of the reminder to move
        :param list_name: Name of the destination list
        :returns: Success or error message
        """
        if reminder_id not in self.reminders:
            return f"Reminder with ID {reminder_id} not found."

        # Verify destination list exists
        list_exists = any(l.name == list_name for l in self.lists.values())
        if not list_exists:
            return f"List '{list_name}' not found. Create it first with create_list."

        reminder = self.reminders[reminder_id]
        old_list = reminder.list_name
        reminder.list_name = list_name

        return f"✓ Reminder '{reminder.title}' moved from '{old_list}' to '{list_name}'."

    # Smart Lists / Queries

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_scheduled_reminders(self) -> str:
        """
        Get all reminders with due dates (scheduled reminders).

        :returns: String representation of scheduled reminders
        """
        scheduled = [r for r in self.reminders.values()
                    if r.due_date is not None and not r.is_completed]

        if not scheduled:
            return "No scheduled reminders found."

        # Sort by due date
        scheduled.sort(key=lambda r: r.due_date)

        result = f"Scheduled Reminders ({len(scheduled)}):\n\n"
        for reminder in scheduled:
            result += str(reminder) + "-" * 60 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_flagged_reminders(self) -> str:
        """
        Get all flagged/important reminders.

        :returns: String representation of flagged reminders
        """
        flagged = [r for r in self.reminders.values() if r.flagged and not r.is_completed]

        if not flagged:
            return "No flagged reminders found."

        result = f"Flagged Reminders ({len(flagged)}):\n\n"
        for reminder in flagged:
            result += str(reminder) + "-" * 60 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_overdue_reminders(self) -> str:
        """
        Get all overdue reminders (past due date and not completed).

        :returns: String representation of overdue reminders
        """
        current_time = self.time_manager.time()
        overdue = [r for r in self.reminders.values()
                  if r.due_date is not None
                  and r.due_date < current_time
                  and not r.is_completed]

        if not overdue:
            return "No overdue reminders."

        # Sort by how overdue (oldest first)
        overdue.sort(key=lambda r: r.due_date)

        result = f"⚠️ Overdue Reminders ({len(overdue)}):\n\n"
        for reminder in overdue:
            days_overdue = (current_time - reminder.due_date) / (24 * 60 * 60)
            result += str(reminder)
            result += f"⏰ Overdue by {days_overdue:.1f} days\n"
            result += "-" * 60 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def search_reminders(self, query: str) -> str:
        """
        Search reminders by title or notes.

        :param query: Search query
        :returns: String representation of matching reminders
        """
        query_lower = query.lower()
        matches = [r for r in self.reminders.values()
                  if query_lower in r.title.lower()
                  or (r.notes and query_lower in r.notes.lower())]

        if not matches:
            return f"No reminders found matching '{query}'."

        result = f"Search Results for '{query}' ({len(matches)}):\n\n"
        for reminder in matches:
            result += str(reminder) + "-" * 60 + "\n"

        return result

    # Helper methods

    def _create_next_recurring_reminder(self, reminder: Reminder) -> Reminder | None:
        """Create the next occurrence of a recurring reminder."""
        if not reminder.due_date:
            return None

        from datetime import datetime, timedelta, timezone

        current_due = datetime.fromtimestamp(reminder.due_date, tz=timezone.utc)

        # Calculate next due date based on repeat frequency
        if reminder.repeat == ReminderRepeat.DAILY:
            next_due = current_due + timedelta(days=1)
        elif reminder.repeat == ReminderRepeat.WEEKLY:
            next_due = current_due + timedelta(weeks=1)
        elif reminder.repeat == ReminderRepeat.MONTHLY:
            # Add one month (approximately)
            next_due = current_due + timedelta(days=30)
        elif reminder.repeat == ReminderRepeat.YEARLY:
            next_due = current_due + timedelta(days=365)
        else:
            return None

        # Create new reminder
        next_reminder = Reminder(
            reminder_id=uuid_hex(self.rng),
            title=reminder.title,
            notes=reminder.notes,
            list_name=reminder.list_name,
            due_date=next_due.timestamp(),
            reminder_date=next_due.timestamp() if reminder.reminder_date else None,
            priority=reminder.priority,
            repeat=reminder.repeat,
            location=reminder.location,
            location_trigger=reminder.location_trigger,
            flagged=reminder.flagged,
            tags=reminder.tags.copy(),
            created_date=self.time_manager.time(),
        )

        self.reminders[next_reminder.reminder_id] = next_reminder
        return next_reminder
