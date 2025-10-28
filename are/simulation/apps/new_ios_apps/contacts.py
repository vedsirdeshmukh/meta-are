# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import uuid
from dataclasses import dataclass, field
from typing import Any

from are.simulation.apps.app import App
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import get_state_dict, type_check, uuid_hex


@dataclass
class Contact:
    """Represents a contact in iOS Contacts app."""

    contact_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Contact"
    company: str | None = None
    phone_numbers: list[dict[str, str]] = field(
        default_factory=list
    )  # [{"label": "mobile", "number": "555-1234"}]
    email_addresses: list[dict[str, str]] = field(
        default_factory=list
    )  # [{"label": "home", "email": "test@example.com"}]
    notes: str | None = None
    address: str | None = None

    # iOS-specific notification settings
    ringtone: str = "Default"
    text_tone: str = "Note"
    emergency_bypass_calls: bool = False  # Bypass Silent/Focus for calls
    emergency_bypass_texts: bool = False  # Bypass Silent/Focus for texts
    vibration: str = "Default"

    # Additional metadata
    is_favorite: bool = False
    photo_url: str | None = None

    def __post_init__(self):
        if not self.contact_id:
            self.contact_id = uuid.uuid4().hex

    def __str__(self):
        info = f"Contact ID: {self.contact_id}\n"
        info += f"Name: {self.name}\n"

        if self.company:
            info += f"Company: {self.company}\n"

        if self.phone_numbers:
            info += "Phone Numbers:\n"
            for phone in self.phone_numbers:
                label = phone.get("label", "phone")
                number = phone.get("number", "")
                info += f"  {label}: {number}\n"

        if self.email_addresses:
            info += "Email Addresses:\n"
            for email in self.email_addresses:
                label = email.get("label", "email")
                address = email.get("email", "")
                info += f"  {label}: {address}\n"

        if self.address:
            info += f"Address: {self.address}\n"

        if self.notes:
            info += f"Notes: {self.notes}\n"

        # Notification settings
        info += f"\nNotification Settings:\n"
        info += f"  Ringtone: {self.ringtone}\n"
        info += f"  Text Tone: {self.text_tone}\n"
        info += f"  Vibration: {self.vibration}\n"
        info += f"  Emergency Bypass (Calls): {'ON' if self.emergency_bypass_calls else 'OFF'}\n"
        info += f"  Emergency Bypass (Texts): {'ON' if self.emergency_bypass_texts else 'OFF'}\n"

        if self.is_favorite:
            info += "⭐ Favorite\n"

        return info

    @property
    def summary(self):
        return f"{self.name} - ID: {self.contact_id}"


@dataclass
class ContactsApp(App):
    """
    iOS Contacts application for managing contact information.

    Manages contacts with iOS-specific features including Emergency Bypass for calls
    and texts, custom ringtones, and notification preferences.

    Key Features:
        - Contact Management: Create, read, update, delete contacts
        - Multiple Phone Numbers: Support for labeled phone numbers (mobile, home, work, etc.)
        - Multiple Email Addresses: Support for labeled email addresses
        - Emergency Bypass: Per-contact setting to bypass Silent/Focus modes
        - Custom Ringtones: Set custom ringtones and text tones per contact
        - Notes: Add notes to contacts
        - Favorites: Mark contacts as favorites
        - Search: Search contacts by name, phone, or email

    Notes:
        - Emergency Bypass allows critical contacts to ring/vibrate even in Silent/Focus mode
        - Emergency Bypass must be enabled separately for calls and texts
        - This is crucial for accessibility and medical emergency scenarios
    """

    name: str | None = None
    contacts: dict[str, Contact] = field(default_factory=dict)

    def __post_init__(self):
        super().__init__(self.name)

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(self, ["contacts"])

    def load_state(self, state_dict: dict[str, Any]):
        self.contacts = {
            k: Contact(**v) for k, v in state_dict.get("contacts", {}).items()
        }

    def reset(self):
        super().reset()
        self.contacts = {}

    # Contact Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_contact(
        self,
        name: str,
        company: str | None = None,
        phone_numbers: list[dict[str, str]] | None = None,
        email_addresses: list[dict[str, str]] | None = None,
        notes: str | None = None,
        address: str | None = None,
        is_favorite: bool = False,
    ) -> str:
        """
        Create a new contact.

        :param name: Name of the contact
        :param company: Company name (optional)
        :param phone_numbers: List of phone numbers with labels, e.g., [{"label": "mobile", "number": "555-1234"}]
        :param email_addresses: List of email addresses with labels, e.g., [{"label": "home", "email": "test@example.com"}]
        :param notes: Notes about the contact (optional)
        :param address: Physical address (optional)
        :returns: contact_id of the created contact
        """
        if phone_numbers is None:
            phone_numbers = []
        if email_addresses is None:
            email_addresses = []

        contact = Contact(
            contact_id=uuid_hex(self.rng),
            name=name,
            company=company,
            phone_numbers=phone_numbers,
            email_addresses=email_addresses,
            notes=notes,
            address=address,
            is_favorite=is_favorite,
        )

        self.contacts[contact.contact_id] = contact
        return contact.contact_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_contacts(self, search_query: str | None = None) -> str:
        """
        List all contacts, optionally filtered by search query.

        :param search_query: Optional search query to filter contacts by name
        :returns: String representation of matching contacts
        """
        contacts_list = list(self.contacts.values())

        if search_query:
            query_lower = search_query.lower()
            contacts_list = [
                c for c in contacts_list if query_lower in c.name.lower()
            ]

        if not contacts_list:
            return "No contacts found."

        # Sort alphabetically by name
        contacts_list.sort(key=lambda c: c.name.lower())

        result = f"Contacts ({len(contacts_list)}):\n\n"
        for contact in contacts_list:
            result += str(contact) + "-" * 60 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_contact(self, contact_id: str) -> str:
        """
        Get detailed information about a specific contact.

        :param contact_id: ID of the contact
        :returns: Complete contact information
        """
        if contact_id not in self.contacts:
            return f"Contact with ID {contact_id} not found."

        return str(self.contacts[contact_id])

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def search_contacts(self, query: str) -> str:
        """
        Search contacts by name, phone number, or email.

        :param query: Search query
        :returns: String representation of matching contacts
        """
        query_lower = query.lower()
        matches = []

        for contact in self.contacts.values():
            # Search in name
            if query_lower in contact.name.lower():
                matches.append(contact)
                continue

            # Search in company
            if contact.company and query_lower in contact.company.lower():
                matches.append(contact)
                continue

            # Search in phone numbers
            if any(
                query_lower in phone.get("number", "").lower()
                for phone in contact.phone_numbers
            ):
                matches.append(contact)
                continue

            # Search in email addresses
            if any(
                query_lower in email.get("email", "").lower()
                for email in contact.email_addresses
            ):
                matches.append(contact)
                continue

        if not matches:
            return f"No contacts found matching '{query}'."

        matches.sort(key=lambda c: c.name.lower())

        result = f"Search Results for '{query}' ({len(matches)}):\n\n"
        for contact in matches:
            result += str(contact) + "-" * 60 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def update_contact(
        self,
        contact_id: str,
        name: str | None = None,
        company: str | None = None,
        phone_numbers: list[dict[str, str]] | None = None,
        email_addresses: list[dict[str, str]] | None = None,
        notes: str | None = None,
        address: str | None = None,
    ) -> str:
        """
        Update an existing contact's basic information.

        :param contact_id: ID of the contact to update
        :param name: New name (optional)
        :param company: New company (optional)
        :param phone_numbers: New phone numbers list (optional)
        :param email_addresses: New email addresses list (optional)
        :param notes: New notes (optional)
        :param address: New address (optional)
        :returns: Success or error message
        """
        if contact_id not in self.contacts:
            return f"Contact with ID {contact_id} not found."

        contact = self.contacts[contact_id]
        changes = []

        if name is not None:
            contact.name = name
            changes.append("name")

        if company is not None:
            contact.company = company
            changes.append("company")

        if phone_numbers is not None:
            contact.phone_numbers = phone_numbers
            changes.append("phone numbers")

        if email_addresses is not None:
            contact.email_addresses = email_addresses
            changes.append("email addresses")

        if notes is not None:
            contact.notes = notes
            changes.append("notes")

        if address is not None:
            contact.address = address
            changes.append("address")

        if not changes:
            return "No changes specified."

        return f"✓ Contact '{contact.name}' updated: {', '.join(changes)}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_contact(self, contact_id: str) -> str:
        """
        Delete a contact.

        :param contact_id: ID of the contact to delete
        :returns: Success or error message
        """
        if contact_id not in self.contacts:
            return f"Contact with ID {contact_id} not found."

        contact = self.contacts[contact_id]
        del self.contacts[contact_id]

        return f"✓ Contact '{contact.name}' deleted."

    # iOS-Specific Notification Settings

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_emergency_bypass_calls(self, contact_id: str, enabled: bool) -> str:
        """
        Enable or disable Emergency Bypass for calls from this contact.
        Emergency Bypass allows calls from this contact to ring even when Silent or Focus mode is on.

        :param contact_id: ID of the contact
        :param enabled: True to enable Emergency Bypass, False to disable
        :returns: Success or error message
        """
        if contact_id not in self.contacts:
            return f"Contact with ID {contact_id} not found."

        contact = self.contacts[contact_id]
        contact.emergency_bypass_calls = enabled

        status = "enabled" if enabled else "disabled"
        return f"✓ Emergency Bypass for calls {status} for '{contact.name}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_emergency_bypass_texts(self, contact_id: str, enabled: bool) -> str:
        """
        Enable or disable Emergency Bypass for texts from this contact.
        Emergency Bypass allows texts from this contact to alert even when Silent or Focus mode is on.

        :param contact_id: ID of the contact
        :param enabled: True to enable Emergency Bypass, False to disable
        :returns: Success or error message
        """
        if contact_id not in self.contacts:
            return f"Contact with ID {contact_id} not found."

        contact = self.contacts[contact_id]
        contact.emergency_bypass_texts = enabled

        status = "enabled" if enabled else "disabled"
        return f"✓ Emergency Bypass for texts {status} for '{contact.name}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_ringtone(self, contact_id: str, ringtone: str) -> str:
        """
        Set a custom ringtone for a contact.

        :param contact_id: ID of the contact
        :param ringtone: Name of the ringtone
        :returns: Success or error message
        """
        if contact_id not in self.contacts:
            return f"Contact with ID {contact_id} not found."

        contact = self.contacts[contact_id]
        contact.ringtone = ringtone

        return f"✓ Ringtone for '{contact.name}' set to '{ringtone}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_text_tone(self, contact_id: str, text_tone: str) -> str:
        """
        Set a custom text tone for a contact.

        :param contact_id: ID of the contact
        :param text_tone: Name of the text tone
        :returns: Success or error message
        """
        if contact_id not in self.contacts:
            return f"Contact with ID {contact_id} not found."

        contact = self.contacts[contact_id]
        contact.text_tone = text_tone

        return f"✓ Text tone for '{contact.name}' set to '{text_tone}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_vibration(self, contact_id: str, vibration: str) -> str:
        """
        Set a custom vibration pattern for a contact.

        :param contact_id: ID of the contact
        :param vibration: Name of the vibration pattern
        :returns: Success or error message
        """
        if contact_id not in self.contacts:
            return f"Contact with ID {contact_id} not found."

        contact = self.contacts[contact_id]
        contact.vibration = vibration

        return f"✓ Vibration for '{contact.name}' set to '{vibration}'."

    # Favorites

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_to_favorites(self, contact_id: str) -> str:
        """
        Add a contact to favorites.

        :param contact_id: ID of the contact
        :returns: Success or error message
        """
        if contact_id not in self.contacts:
            return f"Contact with ID {contact_id} not found."

        contact = self.contacts[contact_id]
        contact.is_favorite = True

        return f"⭐ '{contact.name}' added to favorites."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def remove_from_favorites(self, contact_id: str) -> str:
        """
        Remove a contact from favorites.

        :param contact_id: ID of the contact
        :returns: Success or error message
        """
        if contact_id not in self.contacts:
            return f"Contact with ID {contact_id} not found."

        contact = self.contacts[contact_id]
        contact.is_favorite = False

        return f"✓ '{contact.name}' removed from favorites."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_favorites(self) -> str:
        """
        List all favorite contacts.

        :returns: String representation of favorite contacts
        """
        favorites = [c for c in self.contacts.values() if c.is_favorite]

        if not favorites:
            return "No favorite contacts."

        favorites.sort(key=lambda c: c.name.lower())

        result = f"⭐ Favorite Contacts ({len(favorites)}):\n\n"
        for contact in favorites:
            result += str(contact) + "-" * 60 + "\n"

        return result

    # Helper Methods

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_emergency_bypass_status(self, contact_id: str) -> str:
        """
        Get the Emergency Bypass status for a contact.

        :param contact_id: ID of the contact
        :returns: Emergency Bypass status for calls and texts
        """
        if contact_id not in self.contacts:
            return f"Contact with ID {contact_id} not found."

        contact = self.contacts[contact_id]

        status = f"Emergency Bypass Status for '{contact.name}':\n"
        status += f"  Calls: {'ON' if contact.emergency_bypass_calls else 'OFF'}\n"
        status += f"  Texts: {'ON' if contact.emergency_bypass_texts else 'OFF'}\n"

        return status
