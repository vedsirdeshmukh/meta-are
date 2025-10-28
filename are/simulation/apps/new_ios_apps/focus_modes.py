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


class FocusModeType(Enum):
    DO_NOT_DISTURB = "Do Not Disturb"
    PERSONAL = "Personal"
    WORK = "Work"
    SLEEP = "Sleep"
    DRIVING = "Driving"
    READING = "Reading"
    FITNESS = "Fitness"
    GAMING = "Gaming"
    CUSTOM = "Custom"


class NotificationSetting(Enum):
    ALL = "Allow All"
    NONE = "Silence All"
    PEOPLE = "People Only"
    APPS = "Apps Only"


@dataclass
class FocusMode:
    """Represents a Focus Mode configuration."""

    mode_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Focus"
    mode_type: FocusModeType = FocusModeType.DO_NOT_DISTURB
    is_active: bool = False
    is_enabled: bool = True

    # Notification settings
    notification_setting: NotificationSetting = NotificationSetting.NONE
    allowed_people: list[str] = field(default_factory=list)  # Contact names
    allowed_apps: list[str] = field(default_factory=list)  # App names
    allow_repeated_calls: bool = True  # Allow calls from same person within 3 min
    allow_critical_alerts: bool = True

    # Screen settings
    dim_lock_screen: bool = True
    hide_notification_badges: bool = True

    # Schedule
    is_scheduled: bool = False
    schedule_days: list[str] = field(default_factory=list)  # ["Monday", "Tuesday", etc.]
    schedule_start_time: str | None = None  # "HH:MM"
    schedule_end_time: str | None = None  # "HH:MM"

    # Automation triggers
    auto_trigger_location: str | None = None  # e.g., "Work", "Home"
    auto_trigger_app: str | None = None  # e.g., "Calendar" when certain app opens

    # Home Screen
    filter_home_screen: bool = False
    allowed_home_screen_pages: list[int] = field(default_factory=list)

    # Lock Screen
    lock_screen_appearance: str = "Default"  # Default, Dark, Custom

    def __str__(self):
        active_indicator = "🟢 ACTIVE" if self.is_active else "⚪ Inactive"
        enabled_indicator = "" if self.is_enabled else " (Disabled)"

        info = f"{active_indicator} {self.name}{enabled_indicator}\n"
        info += f"Type: {self.mode_type.value}\n"
        info += f"Notifications: {self.notification_setting.value}\n"

        if self.allowed_people:
            info += f"Allowed People: {', '.join(self.allowed_people[:3])}"
            if len(self.allowed_people) > 3:
                info += f" +{len(self.allowed_people) - 3} more"
            info += "\n"

        if self.allowed_apps:
            info += f"Allowed Apps: {', '.join(self.allowed_apps[:3])}"
            if len(self.allowed_apps) > 3:
                info += f" +{len(self.allowed_apps) - 3} more"
            info += "\n"

        if self.is_scheduled:
            info += f"Schedule: {', '.join(self.schedule_days)} at {self.schedule_start_time}-{self.schedule_end_time}\n"

        if self.auto_trigger_location:
            info += f"Auto-trigger at: {self.auto_trigger_location}\n"

        if self.dim_lock_screen:
            info += "Dims lock screen\n"

        if self.hide_notification_badges:
            info += "Hides notification badges\n"

        return info


@dataclass
class FocusModesApp(App):
    """
    iOS Focus Modes application for managing notification and screen time preferences.

    Manages different focus modes that control notifications, apps, and screen settings
    to help users stay focused and minimize distractions.

    Key Features:
        - Predefined Modes: Do Not Disturb, Sleep, Work, Personal, Driving, etc.
        - Custom Modes: Create your own focus modes
        - Notification Control: Allow/silence specific people and apps
        - Scheduling: Automatically activate based on time or day
        - Location Triggers: Auto-activate at certain locations
        - App Triggers: Activate when opening specific apps
        - Home Screen Filtering: Show only allowed app pages
        - Lock Screen Customization: Change appearance during focus
        - Critical Alerts: Always allow emergency notifications

    Notes:
        - Only one focus mode can be active at a time
        - Scheduled modes activate/deactivate automatically
        - Critical alerts (emergency) bypass all focus modes
        - Repeated calls from same person within 3 minutes can bypass focus
    """

    name: str | None = None
    focus_modes: dict[str, FocusMode] = field(default_factory=dict)
    current_active_mode: str | None = None  # mode_id of active mode

    def __post_init__(self):
        super().__init__(self.name)

        # Create default Do Not Disturb mode if none exist
        if not self.focus_modes:
            default_dnd = FocusMode(
                mode_id=uuid_hex(self.rng),
                name="Do Not Disturb",
                mode_type=FocusModeType.DO_NOT_DISTURB,
                notification_setting=NotificationSetting.NONE,
            )
            self.focus_modes[default_dnd.mode_id] = default_dnd

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(self, ["focus_modes", "current_active_mode"])

    def load_state(self, state_dict: dict[str, Any]):
        self.focus_modes = {k: FocusMode(**v) for k, v in state_dict.get("focus_modes", {}).items()}
        self.current_active_mode = state_dict.get("current_active_mode")

    def reset(self):
        super().reset()
        self.focus_modes = {}
        self.current_active_mode = None

    # Focus Mode Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_focus_mode(
        self,
        name: str,
        mode_type: str = "Custom",
        notification_setting: str = "Silence All",
        dim_lock_screen: bool = True,
    ) -> str:
        """
        Create a new focus mode.

        :param name: Name of the focus mode
        :param mode_type: Type of mode. Options: Do Not Disturb, Personal, Work, Sleep, Driving, Reading, Fitness, Gaming, Custom
        :param notification_setting: Notification behavior. Options: Allow All, Silence All, People Only, Apps Only
        :param dim_lock_screen: Whether to dim the lock screen
        :returns: mode_id of the created focus mode
        """
        mode_type_enum = FocusModeType[mode_type.upper().replace(" ", "_")]
        notification_enum = NotificationSetting[notification_setting.upper().replace(" ", "_")]

        mode = FocusMode(
            mode_id=uuid_hex(self.rng),
            name=name,
            mode_type=mode_type_enum,
            notification_setting=notification_enum,
            dim_lock_screen=dim_lock_screen,
        )

        self.focus_modes[mode.mode_id] = mode
        return mode.mode_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_focus_modes(self, show_disabled: bool = False) -> str:
        """
        List all focus modes.

        :param show_disabled: Whether to show disabled modes
        :returns: String representation of all focus modes
        """
        filtered_modes = [m for m in self.focus_modes.values() if show_disabled or m.is_enabled]

        if not filtered_modes:
            return "No focus modes found."

        # Sort: active first, then by name
        filtered_modes.sort(key=lambda m: (not m.is_active, m.name))

        result = f"Focus Modes ({len(filtered_modes)}):\n\n"
        for mode in filtered_modes:
            result += str(mode) + "-" * 60 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def activate_focus_mode(self, mode_id: str) -> str:
        """
        Activate a focus mode.

        :param mode_id: ID of the focus mode to activate
        :returns: Success or error message
        """
        if mode_id not in self.focus_modes:
            return f"Focus mode with ID {mode_id} not found."

        # Deactivate current mode
        if self.current_active_mode and self.current_active_mode in self.focus_modes:
            self.focus_modes[self.current_active_mode].is_active = False

        # Activate new mode
        mode = self.focus_modes[mode_id]
        mode.is_active = True
        self.current_active_mode = mode_id

        return f"✓ '{mode.name}' focus mode activated."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def deactivate_focus_mode(self) -> str:
        """
        Deactivate the current focus mode.

        :returns: Success or error message
        """
        if not self.current_active_mode:
            return "No focus mode is currently active."

        if self.current_active_mode in self.focus_modes:
            mode = self.focus_modes[self.current_active_mode]
            mode.is_active = False
            mode_name = mode.name
            self.current_active_mode = None
            return f"✓ '{mode_name}' focus mode deactivated."

        return "Error deactivating focus mode."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_focus_mode(self, mode_id: str) -> str:
        """
        Delete a focus mode.

        :param mode_id: ID of the focus mode to delete
        :returns: Success or error message
        """
        if mode_id not in self.focus_modes:
            return f"Focus mode with ID {mode_id} not found."

        mode = self.focus_modes[mode_id]

        # Cannot delete if active
        if mode.is_active:
            return f"Cannot delete '{mode.name}' while it is active. Deactivate it first."

        mode_name = mode.name
        del self.focus_modes[mode_id]

        return f"✓ Focus mode '{mode_name}' deleted."

    # Focus Mode Configuration

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_allowed_people(self, mode_id: str, people: list[str]) -> str:
        """
        Set which people can send notifications during this focus mode.

        :param mode_id: ID of the focus mode
        :param people: List of contact names allowed to notify
        :returns: Success or error message
        """
        if mode_id not in self.focus_modes:
            return f"Focus mode with ID {mode_id} not found."

        mode = self.focus_modes[mode_id]
        mode.allowed_people = people

        if mode.notification_setting != NotificationSetting.PEOPLE:
            mode.notification_setting = NotificationSetting.PEOPLE

        return f"✓ Allowed people updated for '{mode.name}': {len(people)} contact(s)."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_allowed_apps(self, mode_id: str, apps: list[str]) -> str:
        """
        Set which apps can send notifications during this focus mode.

        :param mode_id: ID of the focus mode
        :param apps: List of app names allowed to notify
        :returns: Success or error message
        """
        if mode_id not in self.focus_modes:
            return f"Focus mode with ID {mode_id} not found."

        mode = self.focus_modes[mode_id]
        mode.allowed_apps = apps

        if mode.notification_setting != NotificationSetting.APPS:
            mode.notification_setting = NotificationSetting.APPS

        return f"✓ Allowed apps updated for '{mode.name}': {len(apps)} app(s)."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_schedule(
        self,
        mode_id: str,
        days: list[str],
        start_time: str,
        end_time: str,
    ) -> str:
        """
        Schedule a focus mode to activate automatically.

        :param mode_id: ID of the focus mode
        :param days: List of days. Options: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday, or "Daily"
        :param start_time: Start time in HH:MM format (24-hour)
        :param end_time: End time in HH:MM format (24-hour)
        :returns: Success or error message
        """
        if mode_id not in self.focus_modes:
            return f"Focus mode with ID {mode_id} not found."

        mode = self.focus_modes[mode_id]

        # Handle "Daily"
        if "Daily" in days or "daily" in days:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        mode.is_scheduled = True
        mode.schedule_days = days
        mode.schedule_start_time = start_time
        mode.schedule_end_time = end_time

        days_str = "Daily" if len(days) == 7 else ", ".join(days)
        return f"✓ '{mode.name}' scheduled for {days_str} at {start_time}-{end_time}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def remove_schedule(self, mode_id: str) -> str:
        """
        Remove schedule from a focus mode.

        :param mode_id: ID of the focus mode
        :returns: Success or error message
        """
        if mode_id not in self.focus_modes:
            return f"Focus mode with ID {mode_id} not found."

        mode = self.focus_modes[mode_id]
        mode.is_scheduled = False
        mode.schedule_days = []
        mode.schedule_start_time = None
        mode.schedule_end_time = None

        return f"✓ Schedule removed from '{mode.name}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_location_trigger(self, mode_id: str, location: str) -> str:
        """
        Set location-based auto-activation for a focus mode.

        :param mode_id: ID of the focus mode
        :param location: Location name (e.g., "Work", "Home", "Gym")
        :returns: Success or error message
        """
        if mode_id not in self.focus_modes:
            return f"Focus mode with ID {mode_id} not found."

        mode = self.focus_modes[mode_id]
        mode.auto_trigger_location = location

        return f"✓ '{mode.name}' will auto-activate at '{location}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_app_trigger(self, mode_id: str, app_name: str) -> str:
        """
        Set app-based auto-activation for a focus mode.

        :param mode_id: ID of the focus mode
        :param app_name: App name that triggers this focus mode
        :returns: Success or error message
        """
        if mode_id not in self.focus_modes:
            return f"Focus mode with ID {mode_id} not found."

        mode = self.focus_modes[mode_id]
        mode.auto_trigger_app = app_name

        return f"✓ '{mode.name}' will auto-activate when opening '{app_name}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def enable_focus_mode(self, mode_id: str) -> str:
        """
        Enable a disabled focus mode.

        :param mode_id: ID of the focus mode to enable
        :returns: Success or error message
        """
        if mode_id not in self.focus_modes:
            return f"Focus mode with ID {mode_id} not found."

        mode = self.focus_modes[mode_id]
        mode.is_enabled = True

        return f"✓ '{mode.name}' focus mode enabled."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def disable_focus_mode(self, mode_id: str) -> str:
        """
        Disable a focus mode (it won't auto-activate).

        :param mode_id: ID of the focus mode to disable
        :returns: Success or error message
        """
        if mode_id not in self.focus_modes:
            return f"Focus mode with ID {mode_id} not found."

        mode = self.focus_modes[mode_id]

        if mode.is_active:
            return f"Cannot disable '{mode.name}' while it is active. Deactivate it first."

        mode.is_enabled = False

        return f"✓ '{mode.name}' focus mode disabled."

    # Status and Queries

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_active_focus_mode(self) -> str:
        """
        Get the currently active focus mode.

        :returns: Information about the active focus mode, or message if none active
        """
        if not self.current_active_mode:
            return "No focus mode is currently active."

        if self.current_active_mode in self.focus_modes:
            return str(self.focus_modes[self.current_active_mode])

        return "Error retrieving active focus mode."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_scheduled_modes(self) -> str:
        """
        Get all focus modes that have schedules.

        :returns: String representation of scheduled focus modes
        """
        scheduled = [m for m in self.focus_modes.values() if m.is_scheduled and m.is_enabled]

        if not scheduled:
            return "No scheduled focus modes found."

        result = f"Scheduled Focus Modes ({len(scheduled)}):\n\n"
        for mode in scheduled:
            result += str(mode) + "-" * 60 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def check_notification_allowed(self, source: str, source_type: str = "person") -> str:
        """
        Check if a notification from a source would be allowed in the current focus mode.

        :param source: Name of person or app
        :param source_type: Type of source. Options: person, app
        :returns: Whether notification is allowed and reason
        """
        if not self.current_active_mode:
            return f"✓ Notification from {source} would be allowed (no focus mode active)."

        if self.current_active_mode not in self.focus_modes:
            return "Error checking notification permissions."

        mode = self.focus_modes[self.current_active_mode]

        # Critical alerts always allowed
        if mode.allow_critical_alerts:
            result = f"Focus Mode: {mode.name}\n"
            result += "Note: Critical/emergency alerts are always allowed.\n\n"
        else:
            result = f"Focus Mode: {mode.name}\n\n"

        # Check notification setting
        if mode.notification_setting == NotificationSetting.ALL:
            return result + f"✓ Notification from {source} would be ALLOWED (all notifications allowed)."

        if mode.notification_setting == NotificationSetting.NONE:
            # Check for exceptions
            if source_type == "person" and source in mode.allowed_people:
                return result + f"✓ Notification from {source} would be ALLOWED (in allowed people list)."
            elif source_type == "app" and source in mode.allowed_apps:
                return result + f"✓ Notification from {source} would be ALLOWED (in allowed apps list)."
            else:
                return result + f"✗ Notification from {source} would be SILENCED (silence all setting)."

        if mode.notification_setting == NotificationSetting.PEOPLE:
            if source_type == "person" and source in mode.allowed_people:
                return result + f"✓ Notification from {source} would be ALLOWED (in allowed people list)."
            else:
                return result + f"✗ Notification from {source} would be SILENCED (not in allowed people)."

        if mode.notification_setting == NotificationSetting.APPS:
            if source_type == "app" and source in mode.allowed_apps:
                return result + f"✓ Notification from {source} would be ALLOWED (in allowed apps list)."
            else:
                return result + f"✗ Notification from {source} would be SILENCED (not in allowed apps)."

        return result + "Unable to determine notification permissions."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_focus_summary(self) -> str:
        """
        Get summary of focus modes configuration.

        :returns: Summary of all focus modes
        """
        total_modes = len(self.focus_modes)
        enabled_modes = sum(1 for m in self.focus_modes.values() if m.is_enabled)
        scheduled_modes = sum(1 for m in self.focus_modes.values() if m.is_scheduled and m.is_enabled)

        summary = "=== FOCUS MODES SUMMARY ===\n\n"
        summary += f"Total Focus Modes: {total_modes}\n"
        summary += f"Enabled: {enabled_modes}\n"
        summary += f"Scheduled: {scheduled_modes}\n\n"

        if self.current_active_mode and self.current_active_mode in self.focus_modes:
            mode = self.focus_modes[self.current_active_mode]
            summary += f"Currently Active: {mode.name}\n"
            summary += f"  Notifications: {mode.notification_setting.value}\n"

            if mode.allowed_people:
                summary += f"  Allowed People: {len(mode.allowed_people)}\n"
            if mode.allowed_apps:
                summary += f"  Allowed Apps: {len(mode.allowed_apps)}\n"
        else:
            summary += "Currently Active: None\n"

        if scheduled_modes > 0:
            summary += f"\nScheduled Modes:\n"
            for mode in self.focus_modes.values():
                if mode.is_scheduled and mode.is_enabled:
                    days_str = "Daily" if len(mode.schedule_days) == 7 else ", ".join(mode.schedule_days[:2])
                    if len(mode.schedule_days) > 2 and len(mode.schedule_days) < 7:
                        days_str += f" +{len(mode.schedule_days) - 2} more"
                    summary += f"  {mode.name}: {days_str} at {mode.schedule_start_time}-{mode.schedule_end_time}\n"

        return summary
