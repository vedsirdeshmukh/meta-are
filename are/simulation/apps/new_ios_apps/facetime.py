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


class CallType(Enum):
    VIDEO = "Video"
    AUDIO = "Audio"


class CallStatus(Enum):
    INCOMING = "Incoming"
    OUTGOING = "Outgoing"
    MISSED = "Missed"
    DECLINED = "Declined"
    COMPLETED = "Completed"
    FAILED = "Failed"


@dataclass
class FaceTimeCall:
    """Represents a FaceTime call record."""

    call_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    call_type: CallType = CallType.VIDEO
    status: CallStatus = CallStatus.COMPLETED
    participant_names: list[str] = field(default_factory=list)  # Contact names
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    duration_seconds: float = 0.0
    is_group_call: bool = False

    def __post_init__(self):
        if self.end_time and self.duration_seconds == 0.0:
            self.duration_seconds = self.end_time - self.start_time

    @property
    def duration_formatted(self) -> str:
        """Format duration as HH:MM:SS."""
        hours = int(self.duration_seconds // 3600)
        minutes = int((self.duration_seconds % 3600) // 60)
        seconds = int(self.duration_seconds % 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    def __str__(self):
        type_icon = "📹" if self.call_type == CallType.VIDEO else "🎧"
        status_icon = {
            CallStatus.INCOMING: "📥",
            CallStatus.OUTGOING: "📤",
            CallStatus.MISSED: "❌",
            CallStatus.DECLINED: "🚫",
            CallStatus.COMPLETED: "✓",
            CallStatus.FAILED: "⚠️"
        }.get(self.status, "")

        participants = ", ".join(self.participant_names) if self.participant_names else "Unknown"
        info = f"{type_icon} {status_icon} FaceTime {self.call_type.value} - {participants}\n"
        info += f"Status: {self.status.value}\n"
        info += f"Time: {time.ctime(self.start_time)}\n"

        if self.status == CallStatus.COMPLETED:
            info += f"Duration: {self.duration_formatted}\n"

        if self.is_group_call:
            info += f"Group Call ({len(self.participant_names)} participants)\n"

        return info


@dataclass
class FaceTimeLink:
    """Represents a FaceTime link for video calls."""

    link_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    link_url: str = ""
    name: str = "FaceTime Call"
    created_date: float = field(default_factory=time.time)
    expiration_date: float | None = None
    is_active: bool = True

    def __post_init__(self):
        if not self.link_url:
            self.link_url = f"https://facetime.apple.com/{self.link_id}"

    def __str__(self):
        info = f"🔗 FaceTime Link: {self.name}\n"
        info += f"URL: {self.link_url}\n"
        info += f"Created: {time.ctime(self.created_date)}\n"

        if self.expiration_date:
            info += f"Expires: {time.ctime(self.expiration_date)}\n"

        info += f"Status: {'Active' if self.is_active else 'Inactive'}\n"

        return info


@dataclass
class FaceTimeApp(App):
    """
    iOS FaceTime application for video and audio calls.

    Manages FaceTime video and audio calls, including one-on-one and group calls,
    call history, and FaceTime links.

    Key Features:
        - Video Calls: Make and receive video calls
        - Audio Calls: Make and receive audio-only calls
        - Group Calls: Support for multi-person calls (up to 32 people)
        - Call History: Track all incoming, outgoing, and missed calls
        - FaceTime Links: Create shareable links for calls
        - Contact Integration: Call contacts directly by name
        - Screen Sharing: Share screen during calls (simulated)
        - Effects: Apply filters and effects during calls

    Notes:
        - FaceTime requires internet connection (WiFi or cellular)
        - Group calls support up to 32 participants
        - FaceTime links can be shared with anyone
        - Call history tracks all calls with duration and status
    """

    name: str | None = None
    call_history: dict[str, FaceTimeCall] = field(default_factory=dict)
    facetime_links: dict[str, FaceTimeLink] = field(default_factory=dict)
    blocked_contacts: list[str] = field(default_factory=list)  # Contact names

    def __post_init__(self):
        super().__init__(self.name)

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(self, ["call_history", "facetime_links", "blocked_contacts"])

    def load_state(self, state_dict: dict[str, Any]):
        self.call_history = {k: FaceTimeCall(**v) for k, v in state_dict.get("call_history", {}).items()}
        self.facetime_links = {k: FaceTimeLink(**v) for k, v in state_dict.get("facetime_links", {}).items()}
        self.blocked_contacts = state_dict.get("blocked_contacts", [])

    def reset(self):
        super().reset()
        self.call_history = {}
        self.facetime_links = {}
        self.blocked_contacts = []

    # Making Calls

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def start_call(
        self,
        contacts: list[str],
        call_type: str = "Video",
        duration_minutes: float | None = None,
    ) -> str:
        """
        Start a FaceTime call with one or more contacts.

        :param contacts: List of contact names to call
        :param call_type: Type of call. Options: Video, Audio
        :param duration_minutes: Duration of call in minutes (for simulation, optional)
        :returns: call_id of the initiated call
        """
        if not contacts:
            return "Error: No contacts specified for the call."

        # Check for blocked contacts
        blocked_in_call = [c for c in contacts if c in self.blocked_contacts]
        if blocked_in_call:
            return f"Cannot call blocked contact(s): {', '.join(blocked_in_call)}"

        call_type_enum = CallType[call_type.upper()]

        current_time = self.time_manager.time()
        end_time = None
        duration = 0.0

        if duration_minutes is not None:
            duration = duration_minutes * 60
            end_time = current_time + duration

        call = FaceTimeCall(
            call_id=uuid_hex(self.rng),
            call_type=call_type_enum,
            status=CallStatus.OUTGOING if not duration_minutes else CallStatus.COMPLETED,
            participant_names=contacts,
            start_time=current_time,
            end_time=end_time,
            duration_seconds=duration,
            is_group_call=len(contacts) > 1,
        )

        self.call_history[call.call_id] = call

        if duration_minutes:
            return f"✓ {call_type} call with {', '.join(contacts)} completed ({call.duration_formatted})."
        else:
            return f"📞 Starting {call_type} call with {', '.join(contacts)}..."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def end_call(self, call_id: str) -> str:
        """
        End an ongoing call.

        :param call_id: ID of the call to end
        :returns: Success message with call duration
        """
        if call_id not in self.call_history:
            return f"Call with ID {call_id} not found."

        call = self.call_history[call_id]

        if call.status == CallStatus.COMPLETED:
            return "Call has already ended."

        call.end_time = self.time_manager.time()
        call.duration_seconds = call.end_time - call.start_time
        call.status = CallStatus.COMPLETED

        return f"✓ Call ended. Duration: {call.duration_formatted}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def decline_call(self, call_id: str) -> str:
        """
        Decline an incoming call.

        :param call_id: ID of the call to decline
        :returns: Success message
        """
        if call_id not in self.call_history:
            return f"Call with ID {call_id} not found."

        call = self.call_history[call_id]
        call.status = CallStatus.DECLINED

        return f"✓ Call from {', '.join(call.participant_names)} declined."

    # Call History

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_call_history(
        self,
        call_type: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> str:
        """
        Get FaceTime call history.

        :param call_type: Filter by call type (Video, Audio) (optional)
        :param status: Filter by status (Incoming, Outgoing, Missed, Completed, etc.) (optional)
        :param limit: Maximum number of calls to return (default 20)
        :returns: String representation of call history
        """
        filtered_calls = list(self.call_history.values())

        if call_type:
            call_type_enum = CallType[call_type.upper()]
            filtered_calls = [c for c in filtered_calls if c.call_type == call_type_enum]

        if status:
            status_enum = CallStatus[status.upper()]
            filtered_calls = [c for c in filtered_calls if c.status == status_enum]

        # Sort by start time (most recent first)
        filtered_calls.sort(key=lambda c: c.start_time, reverse=True)
        filtered_calls = filtered_calls[:limit]

        if not filtered_calls:
            return "No call history found."

        result = f"FaceTime Call History ({len(filtered_calls)}):\n\n"
        for call in filtered_calls:
            result += str(call) + "-" * 60 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_missed_calls(self) -> str:
        """
        Get all missed calls.

        :returns: String representation of missed calls
        """
        missed_calls = [c for c in self.call_history.values() if c.status == CallStatus.MISSED]

        if not missed_calls:
            return "No missed calls."

        # Sort by start time (most recent first)
        missed_calls.sort(key=lambda c: c.start_time, reverse=True)

        result = f"❌ Missed Calls ({len(missed_calls)}):\n\n"
        for call in missed_calls:
            result += str(call) + "-" * 60 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_call_from_history(self, call_id: str) -> str:
        """
        Delete a call from call history.

        :param call_id: ID of the call to delete
        :returns: Success or error message
        """
        if call_id not in self.call_history:
            return f"Call with ID {call_id} not found."

        call = self.call_history[call_id]
        del self.call_history[call_id]

        return f"✓ Call with {', '.join(call.participant_names)} deleted from history."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def clear_call_history(self) -> str:
        """
        Clear all call history.

        :returns: Success message with count of deleted calls
        """
        count = len(self.call_history)
        self.call_history = {}

        return f"✓ Cleared {count} call(s) from history."

    # FaceTime Links

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_facetime_link(
        self,
        name: str = "FaceTime Call",
        expiration_hours: float | None = None,
    ) -> str:
        """
        Create a FaceTime link that can be shared with others.

        :param name: Name for the FaceTime link
        :param expiration_hours: Hours until link expires (optional, default: no expiration)
        :returns: link_id and URL of the created link
        """
        expiration = None
        if expiration_hours:
            expiration = self.time_manager.time() + (expiration_hours * 3600)

        link = FaceTimeLink(
            link_id=uuid_hex(self.rng),
            name=name,
            created_date=self.time_manager.time(),
            expiration_date=expiration,
        )

        self.facetime_links[link.link_id] = link

        return f"✓ FaceTime link created!\n\n{str(link)}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_facetime_links(self, active_only: bool = True) -> str:
        """
        List all FaceTime links.

        :param active_only: Only show active (non-expired) links
        :returns: String representation of FaceTime links
        """
        current_time = self.time_manager.time()

        filtered_links = list(self.facetime_links.values())

        if active_only:
            filtered_links = [
                link for link in filtered_links
                if link.is_active and (link.expiration_date is None or link.expiration_date > current_time)
            ]

        if not filtered_links:
            return "No FaceTime links found."

        # Sort by created date (most recent first)
        filtered_links.sort(key=lambda l: l.created_date, reverse=True)

        result = f"FaceTime Links ({len(filtered_links)}):\n\n"
        for link in filtered_links:
            result += str(link) + "-" * 60 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def deactivate_facetime_link(self, link_id: str) -> str:
        """
        Deactivate a FaceTime link.

        :param link_id: ID of the link to deactivate
        :returns: Success or error message
        """
        if link_id not in self.facetime_links:
            return f"FaceTime link with ID {link_id} not found."

        link = self.facetime_links[link_id]
        link.is_active = False

        return f"✓ FaceTime link '{link.name}' deactivated."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_facetime_link(self, link_id: str) -> str:
        """
        Delete a FaceTime link.

        :param link_id: ID of the link to delete
        :returns: Success or error message
        """
        if link_id not in self.facetime_links:
            return f"FaceTime link with ID {link_id} not found."

        link = self.facetime_links[link_id]
        del self.facetime_links[link_id]

        return f"✓ FaceTime link '{link.name}' deleted."

    # Contact Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def block_contact(self, contact_name: str) -> str:
        """
        Block a contact from calling you on FaceTime.

        :param contact_name: Name of contact to block
        :returns: Success message
        """
        if contact_name in self.blocked_contacts:
            return f"'{contact_name}' is already blocked."

        self.blocked_contacts.append(contact_name)

        return f"✓ '{contact_name}' blocked from FaceTime."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def unblock_contact(self, contact_name: str) -> str:
        """
        Unblock a previously blocked contact.

        :param contact_name: Name of contact to unblock
        :returns: Success or error message
        """
        if contact_name not in self.blocked_contacts:
            return f"'{contact_name}' is not blocked."

        self.blocked_contacts.remove(contact_name)

        return f"✓ '{contact_name}' unblocked from FaceTime."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_blocked_contacts(self) -> str:
        """
        List all blocked contacts.

        :returns: String representation of blocked contacts
        """
        if not self.blocked_contacts:
            return "No blocked contacts."

        result = "Blocked Contacts:\n\n"
        for contact in sorted(self.blocked_contacts):
            result += f"  🚫 {contact}\n"

        return result

    # Statistics

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_call_statistics(self, days: int = 30) -> str:
        """
        Get call statistics for specified time period.

        :param days: Number of days to include in statistics (default 30)
        :returns: Detailed call statistics
        """
        current_time = self.time_manager.time()
        cutoff_time = current_time - (days * 24 * 60 * 60)

        recent_calls = [c for c in self.call_history.values() if c.start_time >= cutoff_time]

        if not recent_calls:
            return f"No calls found in the last {days} days."

        # Calculate statistics
        total_calls = len(recent_calls)
        video_calls = sum(1 for c in recent_calls if c.call_type == CallType.VIDEO)
        audio_calls = sum(1 for c in recent_calls if c.call_type == CallType.AUDIO)
        completed_calls = [c for c in recent_calls if c.status == CallStatus.COMPLETED]
        missed_calls = sum(1 for c in recent_calls if c.status == CallStatus.MISSED)
        total_duration = sum(c.duration_seconds for c in completed_calls)

        # Average duration
        avg_duration = total_duration / len(completed_calls) if completed_calls else 0

        # Format average duration
        avg_hours = int(avg_duration // 3600)
        avg_minutes = int((avg_duration % 3600) // 60)
        avg_seconds = int(avg_duration % 60)

        summary = f"=== FACETIME STATISTICS (Last {days} Days) ===\n\n"
        summary += f"Total Calls: {total_calls}\n"
        summary += f"  Video: {video_calls} ({video_calls/total_calls*100:.1f}%)\n"
        summary += f"  Audio: {audio_calls} ({audio_calls/total_calls*100:.1f}%)\n\n"

        summary += f"Completed Calls: {len(completed_calls)}\n"
        summary += f"Missed Calls: {missed_calls}\n\n"

        if completed_calls:
            summary += f"Total Talk Time: {int(total_duration//3600)}h {int((total_duration%3600)//60)}m\n"
            summary += f"Average Call Duration: {avg_hours}h {avg_minutes}m {avg_seconds}s\n"

        return summary
