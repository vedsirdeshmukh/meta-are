# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

"""
ACC-COMM-EB-002: Accessibility Considerations - Communication & Social

Scenario testing agent's ability to configure Emergency Bypass for critical medical
contacts and prioritize their Messages thread for a user with hearing impairment.

Key Challenge: Distinguish clinically urgent contact (RN Desk) from similar non-urgent
contacts (Billing, Clinic) and enable proper notification overrides for Silent/Focus mode.
"""

from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.new_ios_apps.contacts import Contact, ContactsApp
from are.simulation.apps.new_ios_apps.messages import Conversation, Message, MessagesApp
from are.simulation.apps.system import SystemApp
from are.simulation.scenarios.scenario import Scenario, ScenarioValidationResult
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer


@register_scenario("scenario_hearing_aid_user_setup")
class ACCCommEB002Scenario(Scenario):
    """
    Accessibility scenario testing Emergency Bypass configuration for medical contacts.

    User has hearing impairment and needs critical communications from dialysis nurses
    to break through Silent/Focus modes. Multiple similarly named contacts exist,
    requiring agent to correctly identify the urgent contact.
    """

    start_time: float | None = 0
    duration: float | None = 300  # 5 minutes

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize and populate Contacts and Messages apps with scenario data."""

        # Initialize apps
        aui = AgentUserInterface()
        contacts_app = ContactsApp()
        contacts_app.name = "Contacts"
        messages_app = MessagesApp()
        messages_app.name = "Messages"
        system = SystemApp()

        # Populate Contacts app
        # 1. Dialysis Center RN Desk - CRITICAL URGENT CONTACT
        rn_desk_contact = Contact(
            contact_id="rn_desk_001",
            name="Dialysis Center RN Desk",
            phone_numbers=[
                {"label": "RN Desk", "number": "(555) 014-2001"}
            ],
            ringtone="Default",
            text_tone="Chord",
            emergency_bypass_calls=False,  # Initially OFF
            emergency_bypass_texts=False,  # Initially OFF
            notes="Urgent schedule changes; may text early morning.",
        )
        contacts_app.contacts[rn_desk_contact.contact_id] = rn_desk_contact

        # 2. Dialysis Unit - Billing - DECOY (administrative, not urgent)
        billing_contact = Contact(
            contact_id="billing_001",
            name="Dialysis Unit - Billing",
            phone_numbers=[
                {"label": "phone", "number": "(555) 014-2002"}
            ],
            emergency_bypass_calls=False,
            emergency_bypass_texts=False,
        )
        contacts_app.contacts[billing_contact.contact_id] = billing_contact

        # 3. Nephrology Clinic Front Desk - DECOY (general clinic line)
        clinic_contact = Contact(
            contact_id="clinic_001",
            name="Nephrology Clinic Front Desk",
            phone_numbers=[
                {"label": "phone", "number": "(555) 014-1990"}
            ],
            emergency_bypass_calls=False,
        )
        contacts_app.contacts[clinic_contact.contact_id] = clinic_contact

        # 4. Dr. Patel - Nephrology - DECOY (provider office)
        doctor_contact = Contact(
            contact_id="doctor_001",
            name="Dr. Patel - Nephrology",
            phone_numbers=[
                {"label": "phone", "number": "(555) 014-2112"}
            ],
            emergency_bypass_calls=False,
        )
        contacts_app.contacts[doctor_contact.contact_id] = doctor_contact

        # 5. Mia (Daughter) - DECOY (personal contact)
        mia_contact = Contact(
            contact_id="mia_001",
            name="Mia (Daughter)",
            phone_numbers=[
                {"label": "mobile", "number": "(555) 010-7788"}
            ],
            emergency_bypass_calls=False,
        )
        contacts_app.contacts[mia_contact.contact_id] = mia_contact

        # Populate Messages app
        # 1. Dialysis Center RN Desk conversation - CRITICAL
        rn_desk_conv_id = messages_app.create_conversation(
            participants=["Dialysis Center RN Desk"]
        )
        rn_desk_conv = messages_app.conversations[rn_desk_conv_id]
        rn_desk_conv.pinned = False  # Initially not pinned
        rn_desk_conv.hide_alerts = False  # Initially not hidden
        # Add last message
        rn_desk_msg = Message(
            sender="Dialysis Center RN Desk",
            content="Tomorrow's session moved earlier to 6:30 AM. Reply YES to confirm.",
            timestamp=1729623840.0,  # 2025-10-22 17:04
            is_read=False,
        )
        rn_desk_conv.messages.append(rn_desk_msg)
        rn_desk_conv.update_last_message(rn_desk_msg)

        # 2. Dialysis Unit - Billing conversation - DECOY
        billing_conv_id = messages_app.create_conversation(
            participants=["Dialysis Unit - Billing"]
        )
        billing_conv = messages_app.conversations[billing_conv_id]
        billing_conv.pinned = False
        billing_conv.hide_alerts = True  # This one has Hide Alerts ON (decoy)
        billing_msg = Message(
            sender="Dialysis Unit - Billing",
            content="Your statement is ready.",
            timestamp=1729520000.0,
            is_read=False,
        )
        billing_conv.messages.append(billing_msg)
        billing_conv.update_last_message(billing_msg)

        # 3. Nephrology Clinic Front Desk conversation - DECOY
        clinic_conv_id = messages_app.create_conversation(
            participants=["Nephrology Clinic Front Desk"]
        )
        clinic_conv = messages_app.conversations[clinic_conv_id]
        clinic_conv.pinned = False
        clinic_conv.hide_alerts = False

        # 4. Mia (Daughter) conversation - DECOY
        mia_conv_id = messages_app.create_conversation(
            participants=["Mia (Daughter)"]
        )
        mia_conv = messages_app.conversations[mia_conv_id]
        mia_conv.pinned = False
        mia_conv.hide_alerts = False

        # 5. Work - Front Desk conversation - DECOY
        work_conv_id = messages_app.create_conversation(
            participants=["Work - Front Desk"]
        )
        work_conv = messages_app.conversations[work_conv_id]
        work_conv.pinned = False
        work_conv.hide_alerts = False

        # Store IDs for validation
        self.rn_desk_contact_id = rn_desk_contact.contact_id
        self.rn_desk_conv_id = rn_desk_conv_id

        # List of all initialized applications
        self.apps = [aui, contacts_app, messages_app, system]

    def build_events_flow(self) -> None:
        """Build the scenario by defining events and actions."""

        aui = self.get_typed_app(AgentUserInterface)

        # Use capture_mode to create events using regular function calls
        with EventRegisterer.capture_mode():
            # User task: Ensure communications from dialysis nurses are noticed
            # even when phone is on Silent
            user_task = aui.send_message_to_agent(
                content="I wear hearing aids and miss rings. Make sure I always catch calls or texts from the dialysis nurses, even when my phone's on Silent.",
            ).depends_on(None, delay_seconds=5)

        # Add all events to the scenario
        self.events = [user_task]

    def validate(self, env) -> ScenarioValidationResult:
        """
        Validate the scenario using LLM-Rubric approach.

        Validation checks:
        1. Emergency Bypass for calls enabled on RN Desk contact (0.4 weight)
        2. Emergency Bypass for texts enabled on RN Desk contact (0.4 weight)
        3. RN Desk Messages thread is pinned OR Hide Alerts is confirmed OFF (0.2 weight)

        Args:
            env: The environment containing all apps and their final states

        Returns:
            ScenarioValidationResult with success status and rationale
        """
        try:
            contacts_app = env.get_app("Contacts")
            messages_app = env.get_app("Messages")

            validation_results = []
            scores = []

            # Check 1: Emergency Bypass for calls (0.4 weight)
            rn_contact = contacts_app.contacts.get(self.rn_desk_contact_id)
            if rn_contact:
                if rn_contact.emergency_bypass_calls:
                    validation_results.append(
                        "✅ Emergency Bypass for calls ENABLED on 'Dialysis Center RN Desk'"
                    )
                    scores.append(0.4)
                else:
                    validation_results.append(
                        "❌ Emergency Bypass for calls NOT enabled on 'Dialysis Center RN Desk'"
                    )
                    scores.append(0.0)

                # Check for incorrect enabling on other contacts
                incorrect_bypass = []
                for contact_id, contact in contacts_app.contacts.items():
                    if contact_id != self.rn_desk_contact_id and (
                        contact.emergency_bypass_calls or contact.emergency_bypass_texts
                    ):
                        incorrect_bypass.append(contact.name)

                if incorrect_bypass:
                    validation_results.append(
                        f"⚠️ WARNING: Emergency Bypass enabled on non-urgent contacts: {', '.join(incorrect_bypass)}"
                    )
            else:
                validation_results.append(
                    "❌ 'Dialysis Center RN Desk' contact not found"
                )
                scores.append(0.0)

            # Check 2: Emergency Bypass for texts (0.4 weight)
            if rn_contact:
                if rn_contact.emergency_bypass_texts:
                    validation_results.append(
                        "✅ Emergency Bypass for texts ENABLED on 'Dialysis Center RN Desk'"
                    )
                    scores.append(0.4)
                else:
                    validation_results.append(
                        "❌ Emergency Bypass for texts NOT enabled on 'Dialysis Center RN Desk'"
                    )
                    scores.append(0.0)

            # Check 3: Messages prioritization (0.2 weight)
            rn_conv = messages_app.conversations.get(self.rn_desk_conv_id)
            if rn_conv:
                if rn_conv.pinned:
                    validation_results.append(
                        "✅ 'Dialysis Center RN Desk' conversation is PINNED"
                    )
                    scores.append(0.2)
                elif not rn_conv.hide_alerts:
                    validation_results.append(
                        "✅ 'Dialysis Center RN Desk' conversation has Hide Alerts OFF (acceptable)"
                    )
                    scores.append(0.2)
                else:
                    validation_results.append(
                        "❌ 'Dialysis Center RN Desk' conversation is NOT pinned AND has Hide Alerts ON"
                    )
                    scores.append(0.0)

                # Check for incorrect actions
                if rn_conv.hide_alerts:
                    validation_results.append(
                        "⚠️ WARNING: Hide Alerts is ON for RN Desk thread (should be OFF)"
                    )
            else:
                validation_results.append(
                    "❌ 'Dialysis Center RN Desk' conversation not found"
                )
                scores.append(0.0)

            # Calculate overall success
            total_score = sum(scores)
            success = total_score >= 0.8  # Need at least 80% to pass

            # Build rationale
            rationale = f"=== ACC-COMM-EB-002 Validation Results ===\n\n"
            rationale += f"Total Score: {total_score:.2f} / 1.00\n\n"
            rationale += "Detailed Results:\n"
            for result in validation_results:
                rationale += f"{result}\n"

            if success:
                rationale += "\n✅ SCENARIO PASSED: Agent correctly configured Emergency Bypass for critical medical contact."
            else:
                rationale += "\n❌ SCENARIO FAILED: Agent did not fully configure Emergency Bypass or Messages prioritization."

            return ScenarioValidationResult(
                success=success,
                rationale=rationale,
            )

        except Exception as e:
            return ScenarioValidationResult(
                success=False,
                exception=e,
                rationale=f"Validation failed with exception: {str(e)}",
            )

if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    # Run the scenario in oracle mode and validate
    run_and_validate(ACCCommEB002Scenario())

