# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from are.simulation.apps.app import App
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import get_state_dict, type_check, uuid_hex


@dataclass
class Message:
    """Represents a single message in a conversation."""

    message_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    sender: str = "User"
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    is_read: bool = False

    def __str__(self):
        time_str = datetime.fromtimestamp(self.timestamp, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M"
        )
        read_indicator = "✓" if self.is_read else ""
        return f"[{time_str}] {self.sender}: {self.content} {read_indicator}"


@dataclass
class Conversation:
    """Represents a messaging conversation."""

    conversation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    participants: list[str] = field(
        default_factory=list
    )  # Names of participants (excluding current user)
    messages: list[Message] = field(default_factory=list)
    pinned: bool = False  # iOS pinning feature
    hide_alerts: bool = False  # iOS hide alerts feature
    last_message: str | None = None
    last_timestamp: float | None = None

    def __post_init__(self):
        if not self.conversation_id:
            self.conversation_id = uuid.uuid4().hex

        # Update last message info if not provided
        if self.messages and not self.last_message:
            last_msg = max(self.messages, key=lambda m: m.timestamp)
            self.last_message = last_msg.content
            self.last_timestamp = last_msg.timestamp

    def update_last_message(self, message: Message):
        """Update the last message information."""
        self.last_message = message.content
        self.last_timestamp = message.timestamp

    @property
    def display_name(self) -> str:
        """Get display name for the conversation."""
        if len(self.participants) == 0:
            return "Unknown"
        elif len(self.participants) == 1:
            return self.participants[0]
        else:
            return ", ".join(self.participants)

    def __str__(self):
        pin_indicator = "📌 " if self.pinned else ""
        alerts_indicator = "🔕 " if self.hide_alerts else ""

        info = f"{pin_indicator}{alerts_indicator}{self.display_name}\n"
        info += f"Conversation ID: {self.conversation_id}\n"
        info += f"Participants: {', '.join(self.participants)}\n"

        if self.last_message and self.last_timestamp:
            time_str = datetime.fromtimestamp(
                self.last_timestamp, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M")
            info += f"Last Message ({time_str}): {self.last_message}\n"

        info += f"Total Messages: {len(self.messages)}\n"
        info += f"Pinned: {'Yes' if self.pinned else 'No'}\n"
        info += f"Hide Alerts: {'Yes' if self.hide_alerts else 'No'}\n"

        return info


@dataclass
class MessagesApp(App):
    """
    iOS Messages application for managing text conversations.

    Manages conversations with iOS-specific features including pinning conversations,
    hiding alerts, and organizing messages.

    Key Features:
        - Conversations: Manage one-on-one and group conversations
        - Send/Receive Messages: Send and receive text messages
        - Pinning: Pin important conversations to the top of the list
        - Hide Alerts: Silence notifications for specific conversations
        - Message History: View message history with timestamps
        - Read Receipts: Track read status of messages
        - Search: Search messages by content or participant

    Notes:
        - Pinned conversations appear at the top of the conversation list
        - Hide Alerts silences notifications but messages still arrive
        - Hide Alerts is different from Do Not Disturb (which is system-wide)
        - Emergency Bypass (in Contacts) overrides Hide Alerts
    """

    name: str | None = None
    conversations: dict[str, Conversation] = field(default_factory=dict)
    current_user: str = "Me"  # Current user's display name

    def __post_init__(self):
        super().__init__(self.name)

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(self, ["conversations", "current_user"])

    def load_state(self, state_dict: dict[str, Any]):
        self.conversations = {
            k: Conversation(**v) for k, v in state_dict.get("conversations", {}).items()
        }
        self.current_user = state_dict.get("current_user", "Me")

    def reset(self):
        super().reset()
        self.conversations = {}

    # Conversation Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_conversation(self, participants: list[str]) -> str:
        """
        Create a new conversation with the specified participants.

        :param participants: List of participant names (excluding current user)
        :returns: conversation_id of the created conversation
        """
        if not participants:
            return "Error: Must specify at least one participant."

        # Check if conversation with same participants already exists
        for conv in self.conversations.values():
            if set(conv.participants) == set(participants):
                return f"Conversation with {', '.join(participants)} already exists. ID: {conv.conversation_id}"

        conversation = Conversation(
            conversation_id=uuid_hex(self.rng),
            participants=participants,
        )

        self.conversations[conversation.conversation_id] = conversation
        return conversation.conversation_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_conversations(
        self, show_pinned_only: bool = False, show_all: bool = False
    ) -> str:
        """
        List all conversations, sorted with pinned conversations first.

        :param show_pinned_only: If True, only show pinned conversations
        :param show_all: If True, show all conversations (overrides other filters)
        :returns: String representation of conversations
        """
        convs = list(self.conversations.values())

        if show_pinned_only and not show_all:
            convs = [c for c in convs if c.pinned]

        if not convs:
            return "No conversations found."

        # Sort: pinned first, then by last timestamp
        def sort_key(c):
            return (
                not c.pinned,  # Pinned first (False < True)
                -(c.last_timestamp if c.last_timestamp else 0),  # Most recent first
            )

        convs.sort(key=sort_key)

        result = f"Conversations ({len(convs)}):\n\n"
        for conv in convs:
            result += str(conv) + "-" * 60 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_conversation(self, conversation_id: str) -> str:
        """
        Get detailed information about a specific conversation.

        :param conversation_id: ID of the conversation
        :returns: Conversation details with recent messages
        """
        if conversation_id not in self.conversations:
            return f"Conversation with ID {conversation_id} not found."

        conv = self.conversations[conversation_id]
        info = str(conv)

        if conv.messages:
            info += "\nRecent Messages:\n"
            # Show last 10 messages
            recent_messages = sorted(conv.messages, key=lambda m: m.timestamp)[-10:]
            for msg in recent_messages:
                info += f"  {str(msg)}\n"

        return info

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def search_conversations(self, query: str) -> str:
        """
        Search conversations by participant name.

        :param query: Search query
        :returns: String representation of matching conversations
        """
        query_lower = query.lower()
        matches = []

        for conv in self.conversations.values():
            # Search in participants
            if any(query_lower in p.lower() for p in conv.participants):
                matches.append(conv)
                continue

            # Search in last message
            if conv.last_message and query_lower in conv.last_message.lower():
                matches.append(conv)
                continue

        if not matches:
            return f"No conversations found matching '{query}'."

        # Sort: pinned first, then by last timestamp
        def sort_key(c):
            return (
                not c.pinned,
                -(c.last_timestamp if c.last_timestamp else 0),
            )

        matches.sort(key=sort_key)

        result = f"Search Results for '{query}' ({len(matches)}):\n\n"
        for conv in matches:
            result += str(conv) + "-" * 60 + "\n"

        return result

    # Message Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def send_message(self, conversation_id: str, content: str) -> str:
        """
        Send a message to a conversation.

        :param conversation_id: ID of the conversation
        :param content: Message content
        :returns: Success or error message
        """
        if conversation_id not in self.conversations:
            return f"Conversation with ID {conversation_id} not found."

        conv = self.conversations[conversation_id]

        message = Message(
            message_id=uuid_hex(self.rng),
            sender=self.current_user,
            content=content,
            timestamp=self.time_manager.time(),
            is_read=True,
        )

        conv.messages.append(message)
        conv.update_last_message(message)

        return f"✓ Message sent to {conv.display_name}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def receive_message(
        self, conversation_id: str, sender: str, content: str
    ) -> str:
        """
        Receive a message in a conversation (used by environment/system).

        :param conversation_id: ID of the conversation
        :param sender: Name of the sender
        :param content: Message content
        :returns: Success or error message
        """
        if conversation_id not in self.conversations:
            return f"Conversation with ID {conversation_id} not found."

        conv = self.conversations[conversation_id]

        message = Message(
            message_id=uuid_hex(self.rng),
            sender=sender,
            content=content,
            timestamp=self.time_manager.time(),
            is_read=False,
        )

        conv.messages.append(message)
        conv.update_last_message(message)

        return f"✓ Message received from {sender}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def read_messages(
        self, conversation_id: str, limit: int = 20, mark_as_read: bool = True
    ) -> str:
        """
        Read messages from a conversation.

        :param conversation_id: ID of the conversation
        :param limit: Maximum number of recent messages to show (default: 20)
        :param mark_as_read: Whether to mark messages as read (default: True)
        :returns: String representation of messages
        """
        if conversation_id not in self.conversations:
            return f"Conversation with ID {conversation_id} not found."

        conv = self.conversations[conversation_id]

        if not conv.messages:
            return f"No messages in conversation with {conv.display_name}."

        # Get recent messages (sorted by timestamp)
        recent_messages = sorted(conv.messages, key=lambda m: m.timestamp)[-limit:]

        if mark_as_read:
            for msg in recent_messages:
                msg.is_read = True

        result = f"Messages with {conv.display_name}:\n\n"
        for msg in recent_messages:
            result += f"{str(msg)}\n"

        return result

    # iOS-Specific Features

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def pin_conversation(self, conversation_id: str) -> str:
        """
        Pin a conversation to the top of the conversation list.

        :param conversation_id: ID of the conversation to pin
        :returns: Success or error message
        """
        if conversation_id not in self.conversations:
            return f"Conversation with ID {conversation_id} not found."

        conv = self.conversations[conversation_id]

        if conv.pinned:
            return f"Conversation with {conv.display_name} is already pinned."

        conv.pinned = True

        return f"📌 Conversation with {conv.display_name} pinned."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def unpin_conversation(self, conversation_id: str) -> str:
        """
        Unpin a conversation.

        :param conversation_id: ID of the conversation to unpin
        :returns: Success or error message
        """
        if conversation_id not in self.conversations:
            return f"Conversation with ID {conversation_id} not found."

        conv = self.conversations[conversation_id]

        if not conv.pinned:
            return f"Conversation with {conv.display_name} is not pinned."

        conv.pinned = False

        return f"✓ Conversation with {conv.display_name} unpinned."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_hide_alerts(self, conversation_id: str, hide: bool) -> str:
        """
        Enable or disable Hide Alerts for a conversation.
        When Hide Alerts is on, you won't receive notifications for this conversation.

        :param conversation_id: ID of the conversation
        :param hide: True to hide alerts, False to show alerts
        :returns: Success or error message
        """
        if conversation_id not in self.conversations:
            return f"Conversation with ID {conversation_id} not found."

        conv = self.conversations[conversation_id]
        conv.hide_alerts = hide

        status = "enabled" if hide else "disabled"
        return f"✓ Hide Alerts {status} for conversation with {conv.display_name}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_pinned_conversations(self) -> str:
        """
        Get all pinned conversations.

        :returns: String representation of pinned conversations
        """
        pinned = [c for c in self.conversations.values() if c.pinned]

        if not pinned:
            return "No pinned conversations."

        # Sort by last timestamp
        pinned.sort(key=lambda c: -(c.last_timestamp if c.last_timestamp else 0))

        result = f"📌 Pinned Conversations ({len(pinned)}):\n\n"
        for conv in pinned:
            result += str(conv) + "-" * 60 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_unread_count(self) -> str:
        """
        Get count of conversations with unread messages.

        :returns: Count of conversations with unread messages
        """
        unread_convs = []

        for conv in self.conversations.values():
            unread_messages = [m for m in conv.messages if not m.is_read]
            if unread_messages:
                unread_convs.append((conv, len(unread_messages)))

        if not unread_convs:
            return "No unread messages."

        result = f"Unread Messages ({len(unread_convs)} conversations):\n\n"
        for conv, count in unread_convs:
            result += f"{conv.display_name}: {count} unread message{'s' if count != 1 else ''}\n"

        return result

    # Helper Methods

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_conversation(self, conversation_id: str) -> str:
        """
        Delete a conversation and all its messages.

        :param conversation_id: ID of the conversation to delete
        :returns: Success or error message
        """
        if conversation_id not in self.conversations:
            return f"Conversation with ID {conversation_id} not found."

        conv = self.conversations[conversation_id]
        display_name = conv.display_name
        del self.conversations[conversation_id]

        return f"✓ Conversation with {display_name} deleted."
