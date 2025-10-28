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


class PhoneCallType(Enum):
    VOICE = "Voice"
    VIDEO = "Video"  # Some carriers support video calling


class PhoneCallStatus(Enum):
    INCOMING = "Incoming"
    OUTGOING = "Outgoing"
    MISSED = "Missed"
    DECLINED = "Declined"
    COMPLETED = "Completed"
    FAILED = "Failed"
    VOICEMAIL = "Voicemail"
    BLOCKED = "Blocked"


@dataclass
class PhoneCall:
    """Represents a phone call record."""

    call_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    contact_name: str | None = None
    phone_number: str = ""
    call_type: PhoneCallType = PhoneCallType.VOICE
    status: PhoneCallStatus = PhoneCallStatus.COMPLETED
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    duration_seconds: float = 0.0

    # Call details
    is_emergency: bool = False  # Emergency services call
    carrier: str | None = None
    location: str | None = None  # Location when call was made

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
        status_icons = {
            PhoneCallStatus.INCOMING: "📲",
            PhoneCallStatus.OUTGOING: "📞",
            PhoneCallStatus.MISSED: "❌",
            PhoneCallStatus.DECLINED: "🚫",
            PhoneCallStatus.COMPLETED: "✓",
            PhoneCallStatus.FAILED: "⚠️",
            PhoneCallStatus.VOICEMAIL: "📧",
            PhoneCallStatus.BLOCKED: "🛑"
        }

        icon = status_icons.get(self.status, "📞")
        display_name = self.contact_name if self.contact_name else self.phone_number

        info = f"{icon} {display_name}\n"
        info += f"Number: {self.phone_number}\n"
        info += f"Status: {self.status.value}\n"
        info += f"Time: {time.ctime(self.start_time)}\n"

        if self.status == PhoneCallStatus.COMPLETED:
            info += f"Duration: {self.duration_formatted}\n"

        if self.is_emergency:
            info += "🚨 EMERGENCY CALL\n"

        if self.location:
            info += f"Location: {self.location}\n"

        return info


@dataclass
class Voicemail:
    """Represents a voicemail message."""

    voicemail_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_contact: str | None = None
    from_number: str = ""
    timestamp: float = field(default_factory=time.time)
    duration_seconds: float = 0.0
    is_listened: bool = False
    transcript: str | None = None  # Voicemail transcription
    is_deleted: bool = False

    @property
    def duration_formatted(self) -> str:
        """Format duration as MM:SS."""
        minutes = int(self.duration_seconds // 60)
        seconds = int(self.duration_seconds % 60)
        return f"{minutes}:{seconds:02d}"

    def __str__(self):
        listened_icon = "▶️" if self.is_listened else "🔵"
        display_name = self.from_contact if self.from_contact else self.from_number

        info = f"{listened_icon} Voicemail from {display_name}\n"
        info += f"Number: {self.from_number}\n"
        info += f"Time: {time.ctime(self.timestamp)}\n"
        info += f"Duration: {self.duration_formatted}\n"

        if self.transcript:
            info += f"Transcript: {self.transcript[:100]}...\n" if len(self.transcript) > 100 else f"Transcript: {self.transcript}\n"

        return info


@dataclass
class SpamFilter:
    """Represents spam/fraud call filtering configuration."""

    blocked_numbers: list[str] = field(default_factory=list)
    silence_unknown_callers: bool = False
    block_suspected_spam: bool = True
    block_specific_area_codes: list[str] = field(default_factory=list)
    whitelist_numbers: list[str] = field(default_factory=list)  # Always allow these


@dataclass
class PhoneApp(App):
    """
    iOS Phone application for making and managing phone calls.

    Manages voice calls, call history, voicemail, spam filtering, and emergency calls.

    Key Features:
        - Voice Calls: Make and receive phone calls
        - Call History: Complete record of all calls (incoming, outgoing, missed)
        - Voicemail: Receive and manage voicemail messages with transcription
        - Spam Filtering: Block spam/fraud calls and unknown callers
        - Emergency Calls: Support for emergency services (911, etc.)
        - Call Blocking: Block specific numbers or area codes
        - Recent Calls: Quick access to recent call history
        - Favorites: Quick dial for important contacts
        - Call Forwarding: Forward calls to another number
        - Do Not Disturb Integration: Respect focus modes

    Notes:
        - Emergency calls always go through, bypassing all filters
        - Voicemail transcription may not be 100% accurate
        - Spam filtering uses heuristics to identify potential spam
        - Blocked numbers cannot call or leave voicemail
    """

    name: str | None = None
    call_history: dict[str, PhoneCall] = field(default_factory=dict)
    voicemails: dict[str, Voicemail] = field(default_factory=dict)
    favorites: list[str] = field(default_factory=list)  # Contact names or numbers
    spam_filter: SpamFilter = field(default_factory=SpamFilter)

    # Call settings
    call_forwarding_enabled: bool = False
    call_forwarding_number: str | None = None
    show_my_caller_id: bool = True
    call_waiting_enabled: bool = True

    def __post_init__(self):
        super().__init__(self.name)

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(
            self,
            ["call_history", "voicemails", "favorites", "spam_filter",
             "call_forwarding_enabled", "call_forwarding_number",
             "show_my_caller_id", "call_waiting_enabled"]
        )

    def load_state(self, state_dict: dict[str, Any]):
        self.call_history = {k: PhoneCall(**v) for k, v in state_dict.get("call_history", {}).items()}
        self.voicemails = {k: Voicemail(**v) for k, v in state_dict.get("voicemails", {}).items()}
        self.favorites = state_dict.get("favorites", [])
        spam_filter_dict = state_dict.get("spam_filter", {})
        self.spam_filter = SpamFilter(**spam_filter_dict) if spam_filter_dict else SpamFilter()
        self.call_forwarding_enabled = state_dict.get("call_forwarding_enabled", False)
        self.call_forwarding_number = state_dict.get("call_forwarding_number")
        self.show_my_caller_id = state_dict.get("show_my_caller_id", True)
        self.call_waiting_enabled = state_dict.get("call_waiting_enabled", True)

    def reset(self):
        super().reset()
        self.call_history = {}
        self.voicemails = {}
        self.favorites = []
        self.spam_filter = SpamFilter()

    # Making Calls

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def make_call(
        self,
        phone_number: str,
        contact_name: str | None = None,
        duration_minutes: float | None = None,
        is_emergency: bool = False,
    ) -> str:
        """
        Make a phone call.

        :param phone_number: Phone number to call
        :param contact_name: Name of contact (optional)
        :param duration_minutes: Duration of call in minutes (for simulation, optional)
        :param is_emergency: Whether this is an emergency call (911, etc.)
        :returns: call_id of the initiated call
        """
        # Check if number is blocked
        if not is_emergency and phone_number in self.spam_filter.blocked_numbers:
            return f"Cannot call blocked number: {phone_number}"

        call_type = PhoneCallType.VOICE

        current_time = self.time_manager.time()
        end_time = None
        duration = 0.0

        if duration_minutes is not None:
            duration = duration_minutes * 60
            end_time = current_time + duration

        call = PhoneCall(
            call_id=uuid_hex(self.rng),
            contact_name=contact_name,
            phone_number=phone_number,
            call_type=call_type,
            status=PhoneCallStatus.OUTGOING if not duration_minutes else PhoneCallStatus.COMPLETED,
            start_time=current_time,
            end_time=end_time,
            duration_seconds=duration,
            is_emergency=is_emergency,
        )

        self.call_history[call.call_id] = call

        if is_emergency:
            return f"🚨 EMERGENCY CALL to {phone_number} initiated."
        elif duration_minutes:
            return f"✓ Call to {contact_name or phone_number} completed ({call.duration_formatted})."
        else:
            return f"📞 Calling {contact_name or phone_number}..."

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

        if call.status == PhoneCallStatus.COMPLETED:
            return "Call has already ended."

        call.end_time = self.time_manager.time()
        call.duration_seconds = call.end_time - call.start_time
        call.status = PhoneCallStatus.COMPLETED

        return f"✓ Call ended. Duration: {call.duration_formatted}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def answer_call(self, call_id: str, duration_minutes: float) -> str:
        """
        Answer an incoming call.

        :param call_id: ID of the incoming call
        :param duration_minutes: Duration of call in minutes (for simulation)
        :returns: Success message
        """
        if call_id not in self.call_history:
            return f"Call with ID {call_id} not found."

        call = self.call_history[call_id]

        if call.status != PhoneCallStatus.INCOMING:
            return "This is not an incoming call."

        call.status = PhoneCallStatus.COMPLETED
        call.end_time = self.time_manager.time() + (duration_minutes * 60)
        call.duration_seconds = duration_minutes * 60

        return f"✓ Answered call from {call.contact_name or call.phone_number}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def decline_call(self, call_id: str, send_to_voicemail: bool = False) -> str:
        """
        Decline an incoming call.

        :param call_id: ID of the call to decline
        :param send_to_voicemail: Whether to send to voicemail
        :returns: Success message
        """
        if call_id not in self.call_history:
            return f"Call with ID {call_id} not found."

        call = self.call_history[call_id]
        call.status = PhoneCallStatus.DECLINED if not send_to_voicemail else PhoneCallStatus.VOICEMAIL

        return f"✓ Call from {call.contact_name or call.phone_number} declined."

    # Call History

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_call_history(
        self,
        status: str | None = None,
        contact_name: str | None = None,
        limit: int = 50,
    ) -> str:
        """
        Get phone call history.

        :param status: Filter by status (Incoming, Outgoing, Missed, Completed, etc.) (optional)
        :param contact_name: Filter by contact name (optional)
        :param limit: Maximum number of calls to return (default 50)
        :returns: String representation of call history
        """
        filtered_calls = list(self.call_history.values())

        if status:
            status_enum = PhoneCallStatus[status.upper()]
            filtered_calls = [c for c in filtered_calls if c.status == status_enum]

        if contact_name:
            filtered_calls = [c for c in filtered_calls
                            if c.contact_name and contact_name.lower() in c.contact_name.lower()]

        # Sort by start time (most recent first)
        filtered_calls.sort(key=lambda c: c.start_time, reverse=True)
        filtered_calls = filtered_calls[:limit]

        if not filtered_calls:
            return "No call history found."

        result = f"Phone Call History ({len(filtered_calls)}):\n\n"
        for call in filtered_calls:
            result += str(call) + "-" * 60 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_recent_calls(self, limit: int = 10) -> str:
        """
        Get most recent calls.

        :param limit: Maximum number of calls to return (default 10)
        :returns: String representation of recent calls
        """
        recent_calls = sorted(self.call_history.values(), key=lambda c: c.start_time, reverse=True)[:limit]

        if not recent_calls:
            return "No recent calls."

        result = f"Recent Calls ({len(recent_calls)}):\n\n"
        for call in recent_calls:
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
        missed_calls = [c for c in self.call_history.values() if c.status == PhoneCallStatus.MISSED]

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

        return f"✓ Call with {call.contact_name or call.phone_number} deleted from history."

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

    # Voicemail Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_voicemails(self, unlistened_only: bool = False) -> str:
        """
        List voicemail messages.

        :param unlistened_only: Only show unlistened voicemails
        :returns: String representation of voicemails
        """
        filtered_voicemails = [v for v in self.voicemails.values() if not v.is_deleted]

        if unlistened_only:
            filtered_voicemails = [v for v in filtered_voicemails if not v.is_listened]

        if not filtered_voicemails:
            return "No voicemails found."

        # Sort by timestamp (most recent first)
        filtered_voicemails.sort(key=lambda v: v.timestamp, reverse=True)

        result = f"Voicemails ({len(filtered_voicemails)}):\n\n"
        for voicemail in filtered_voicemails:
            result += str(voicemail) + "-" * 60 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def listen_to_voicemail(self, voicemail_id: str) -> str:
        """
        Mark a voicemail as listened.

        :param voicemail_id: ID of the voicemail
        :returns: Voicemail details including transcript
        """
        if voicemail_id not in self.voicemails:
            return f"Voicemail with ID {voicemail_id} not found."

        voicemail = self.voicemails[voicemail_id]
        voicemail.is_listened = True

        info = str(voicemail)

        if voicemail.transcript:
            info += f"\nFull Transcript:\n{voicemail.transcript}\n"

        return info

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_voicemail(self, voicemail_id: str) -> str:
        """
        Delete a voicemail.

        :param voicemail_id: ID of the voicemail to delete
        :returns: Success or error message
        """
        if voicemail_id not in self.voicemails:
            return f"Voicemail with ID {voicemail_id} not found."

        voicemail = self.voicemails[voicemail_id]
        voicemail.is_deleted = True

        return f"✓ Voicemail from {voicemail.from_contact or voicemail.from_number} deleted."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def call_back_voicemail(self, voicemail_id: str, duration_minutes: float) -> str:
        """
        Call back the person who left a voicemail.

        :param voicemail_id: ID of the voicemail
        :param duration_minutes: Duration of call in minutes (for simulation)
        :returns: call_id of the initiated call
        """
        if voicemail_id not in self.voicemails:
            return f"Voicemail with ID {voicemail_id} not found."

        voicemail = self.voicemails[voicemail_id]

        return self.make_call(
            phone_number=voicemail.from_number,
            contact_name=voicemail.from_contact,
            duration_minutes=duration_minutes,
        )

    # Favorites Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_favorite(self, contact_identifier: str) -> str:
        """
        Add a contact or number to favorites for quick dialing.

        :param contact_identifier: Contact name or phone number
        :returns: Success message
        """
        if contact_identifier in self.favorites:
            return f"'{contact_identifier}' is already in favorites."

        self.favorites.append(contact_identifier)

        return f"✓ Added '{contact_identifier}' to favorites."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def remove_favorite(self, contact_identifier: str) -> str:
        """
        Remove a contact or number from favorites.

        :param contact_identifier: Contact name or phone number
        :returns: Success or error message
        """
        if contact_identifier not in self.favorites:
            return f"'{contact_identifier}' is not in favorites."

        self.favorites.remove(contact_identifier)

        return f"✓ Removed '{contact_identifier}' from favorites."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_favorites(self) -> str:
        """
        List all favorite contacts.

        :returns: String representation of favorites
        """
        if not self.favorites:
            return "No favorites found."

        result = "⭐ Favorites:\n\n"
        for i, favorite in enumerate(self.favorites, 1):
            result += f"{i}. {favorite}\n"

        return result

    # Spam/Blocking Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def block_number(self, phone_number: str) -> str:
        """
        Block a phone number from calling.

        :param phone_number: Phone number to block
        :returns: Success message
        """
        if phone_number in self.spam_filter.blocked_numbers:
            return f"'{phone_number}' is already blocked."

        self.spam_filter.blocked_numbers.append(phone_number)

        return f"✓ Blocked {phone_number} from calling."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def unblock_number(self, phone_number: str) -> str:
        """
        Unblock a previously blocked phone number.

        :param phone_number: Phone number to unblock
        :returns: Success or error message
        """
        if phone_number not in self.spam_filter.blocked_numbers:
            return f"'{phone_number}' is not blocked."

        self.spam_filter.blocked_numbers.remove(phone_number)

        return f"✓ Unblocked {phone_number}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_blocked_numbers(self) -> str:
        """
        List all blocked phone numbers.

        :returns: String representation of blocked numbers
        """
        if not self.spam_filter.blocked_numbers:
            return "No blocked numbers."

        result = "🛑 Blocked Numbers:\n\n"
        for number in sorted(self.spam_filter.blocked_numbers):
            result += f"  {number}\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_silence_unknown_callers(self, enabled: bool) -> str:
        """
        Enable or disable silencing calls from unknown/unsaved numbers.

        :param enabled: Whether to silence unknown callers
        :returns: Success message
        """
        self.spam_filter.silence_unknown_callers = enabled

        if enabled:
            return "✓ Unknown callers will be silenced and sent to voicemail."
        else:
            return "✓ Unknown callers will ring normally."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_block_spam(self, enabled: bool) -> str:
        """
        Enable or disable automatic spam call blocking.

        :param enabled: Whether to block suspected spam calls
        :returns: Success message
        """
        self.spam_filter.block_suspected_spam = enabled

        if enabled:
            return "✓ Suspected spam calls will be automatically blocked."
        else:
            return "✓ Spam filtering disabled."

    # Call Settings

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def enable_call_forwarding(self, forward_to_number: str) -> str:
        """
        Enable call forwarding to another number.

        :param forward_to_number: Phone number to forward calls to
        :returns: Success message
        """
        self.call_forwarding_enabled = True
        self.call_forwarding_number = forward_to_number

        return f"✓ Call forwarding enabled. Calls will be forwarded to {forward_to_number}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def disable_call_forwarding(self) -> str:
        """
        Disable call forwarding.

        :returns: Success message
        """
        self.call_forwarding_enabled = False
        self.call_forwarding_number = None

        return "✓ Call forwarding disabled."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_show_caller_id(self, enabled: bool) -> str:
        """
        Show or hide your caller ID when making calls.

        :param enabled: Whether to show your caller ID
        :returns: Success message
        """
        self.show_my_caller_id = enabled

        if enabled:
            return "✓ Your phone number will be shown when you call."
        else:
            return "✓ Your phone number will be hidden when you call."

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
        outgoing_calls = sum(1 for c in recent_calls if c.status == PhoneCallStatus.OUTGOING or c.status == PhoneCallStatus.COMPLETED)
        incoming_calls = sum(1 for c in recent_calls if c.status == PhoneCallStatus.INCOMING)
        completed_calls = [c for c in recent_calls if c.status == PhoneCallStatus.COMPLETED]
        missed_calls = sum(1 for c in recent_calls if c.status == PhoneCallStatus.MISSED)
        blocked_calls = sum(1 for c in recent_calls if c.status == PhoneCallStatus.BLOCKED)
        total_duration = sum(c.duration_seconds for c in completed_calls)

        # Average duration
        avg_duration = total_duration / len(completed_calls) if completed_calls else 0

        # Format durations
        total_hours = int(total_duration // 3600)
        total_minutes = int((total_duration % 3600) // 60)

        avg_minutes = int(avg_duration // 60)
        avg_seconds = int(avg_duration % 60)

        summary = f"=== PHONE STATISTICS (Last {days} Days) ===\n\n"
        summary += f"Total Calls: {total_calls}\n"
        summary += f"  Outgoing: {outgoing_calls}\n"
        summary += f"  Incoming: {incoming_calls}\n"
        summary += f"  Missed: {missed_calls}\n"
        summary += f"  Blocked: {blocked_calls}\n\n"

        if completed_calls:
            summary += f"Completed Calls: {len(completed_calls)}\n"
            summary += f"Total Talk Time: {total_hours}h {total_minutes}m\n"
            summary += f"Average Call Duration: {avg_minutes}m {avg_seconds}s\n\n"

        # Voicemail stats
        recent_voicemails = [v for v in self.voicemails.values() if v.timestamp >= cutoff_time and not v.is_deleted]
        unlistened = sum(1 for v in recent_voicemails if not v.is_listened)

        summary += f"Voicemails: {len(recent_voicemails)}\n"
        if unlistened > 0:
            summary += f"  Unlistened: {unlistened}\n"

        return summary

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_phone_settings_summary(self) -> str:
        """
        Get summary of phone settings and configuration.

        :returns: Summary of phone settings
        """
        summary = "=== PHONE SETTINGS ===\n\n"

        summary += f"Call Forwarding: {'Enabled' if self.call_forwarding_enabled else 'Disabled'}\n"
        if self.call_forwarding_enabled:
            summary += f"  Forward to: {self.call_forwarding_number}\n"

        summary += f"Show Caller ID: {'Yes' if self.show_my_caller_id else 'No'}\n"
        summary += f"Call Waiting: {'Enabled' if self.call_waiting_enabled else 'Disabled'}\n\n"

        summary += "Spam & Blocking:\n"
        summary += f"  Silence Unknown Callers: {'Yes' if self.spam_filter.silence_unknown_callers else 'No'}\n"
        summary += f"  Block Suspected Spam: {'Yes' if self.spam_filter.block_suspected_spam else 'No'}\n"
        summary += f"  Blocked Numbers: {len(self.spam_filter.blocked_numbers)}\n\n"

        summary += f"Favorites: {len(self.favorites)}\n"

        # Unlistened voicemails
        unlistened = sum(1 for v in self.voicemails.values() if not v.is_listened and not v.is_deleted)
        if unlistened > 0:
            summary += f"\n⚠️ {unlistened} unlistened voicemail(s)\n"

        return summary
