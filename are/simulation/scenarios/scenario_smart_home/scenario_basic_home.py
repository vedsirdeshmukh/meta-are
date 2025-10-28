# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

"""
Smart Home Automation Scenario

This scenario tests an agent's ability to:
1. Understand context-aware triggers (time + location)
2. Create complex automations with multiple conditions
3. Control multiple smart home devices in coordination
4. Integrate across multiple apps (HomeKit, Location, Music)

Task: "When I arrive home after 6pm, turn on living room lights to 70%,
       set thermostat to 72°F, and start playing my jazz playlist"

Complexity: High
- Conditional logic (time AND location)
- Multi-device orchestration
- Cross-app integration
- Automation creation and validation
"""

from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.system import SystemApp
from are.simulation.scenarios.scenario import Scenario, ScenarioValidationResult
from are.simulation.scenarios.scenario_smart_home.homekit_app import (
    DeviceType,
    HomeKitApp,
)
from are.simulation.scenarios.scenario_smart_home.location_app import LocationApp
from are.simulation.scenarios.scenario_smart_home.music_app import MusicApp
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import Action, EventRegisterer, EventType


@register_scenario("scenario_smart_home")
class SmartHomeScenario(Scenario):
    """
    Smart Home Automation Scenario with context-aware device control.

    This scenario evaluates the agent's ability to:
    - Parse complex, multi-condition automation requests
    - Identify required devices and their target states
    - Create location and time-based triggers
    - Coordinate actions across multiple smart home apps
    - Verify the automation is properly configured
    """

    start_time: float | None = 0
    duration: float | None = 60  # 60 seconds simulation time

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """
        Initialize and populate smart home environment with devices, locations, and music.
        """
        # Initialize apps
        aui = AgentUserInterface()
        homekit = HomeKitApp()
        location = LocationApp()
        music = MusicApp()
        system = SystemApp()

        # ====================================================================
        # Populate HomeKit with Smart Devices
        # ====================================================================

        # Living room devices
        self.living_room_light_id = homekit.add_device(
            name="Living Room Light",
            device_type="Light",
            room="Living Room",
            initial_properties={"brightness": 0, "color_temperature": "warm"},
        )

        self.living_room_lamp_id = homekit.add_device(
            name="Living Room Lamp",
            device_type="Light",
            room="Living Room",
            initial_properties={"brightness": 0},
        )

        # Thermostat
        self.thermostat_id = homekit.add_device(
            name="Home Thermostat",
            device_type="Thermostat",
            room="Hallway",
            initial_properties={"temperature": 68, "mode": "auto", "unit": "F"},
        )

        # Other devices for realism
        homekit.add_device(
            name="Bedroom Light",
            device_type="Light",
            room="Bedroom",
            initial_properties={"brightness": 0},
        )

        homekit.add_device(
            name="Front Door Lock",
            device_type="Lock",
            room="Entrance",
            initial_properties={"locked": True},
        )

        homekit.add_device(
            name="Kitchen Light",
            device_type="Light",
            room="Kitchen",
            initial_properties={"brightness": 0},
        )

        # ====================================================================
        # Populate Location App
        # ====================================================================

        location.set_home_location(
            name="Home",
            address="123 Main Street, San Francisco, CA",
            latitude=37.7749,
            longitude=-122.4194,
        )

        # Start with user away from home
        location.update_location_state("away")

        # ====================================================================
        # Populate Music App with Jazz Playlist
        # ====================================================================

        # Add jazz songs to library
        song1_id = music.add_song(
            title="Take Five",
            artist="Dave Brubeck",
            album="Time Out",
            duration_seconds=324,
            genre="Jazz",
        )

        song2_id = music.add_song(
            title="So What",
            artist="Miles Davis",
            album="Kind of Blue",
            duration_seconds=562,
            genre="Jazz",
        )

        song3_id = music.add_song(
            title="My Favorite Things",
            artist="John Coltrane",
            album="My Favorite Things",
            duration_seconds=823,
            genre="Jazz",
        )

        song4_id = music.add_song(
            title="Round Midnight",
            artist="Thelonious Monk",
            album="Genius of Modern Music",
            duration_seconds=351,
            genre="Jazz",
        )

        song5_id = music.add_song(
            title="Blue in Green",
            artist="Miles Davis",
            album="Kind of Blue",
            duration_seconds=337,
            genre="Jazz",
        )

        # Create jazz playlist
        self.jazz_playlist_id = music.create_playlist(
            name="Jazz Playlist",
            description="My favorite jazz tracks for relaxing at home",
            song_ids=[song1_id, song2_id, song3_id, song4_id, song5_id],
        )

        # Add some non-jazz music for realism
        rock1 = music.add_song(
            title="Bohemian Rhapsody",
            artist="Queen",
            album="A Night at the Opera",
            duration_seconds=354,
            genre="Rock",
        )

        music.create_playlist(
            name="Rock Classics",
            description="Classic rock hits",
            song_ids=[rock1],
        )

        # Store apps
        self.apps = [aui, homekit, location, music, system]

    def build_events_flow(self) -> None:
        """
        Build the event flow with detailed, granular Oracle events.

        The Oracle events represent the EXACT step-by-step actions the agent
        should take to successfully complete the task. Each step is atomic
        and verifiable.
        """
        aui = self.get_typed_app(AgentUserInterface)
        homekit = self.get_typed_app(HomeKitApp)
        location = self.get_typed_app(LocationApp)
        music = self.get_typed_app(MusicApp)

        with EventRegisterer.capture_mode():
            # ================================================================
            # EVENT 1: User provides the automation request
            # ================================================================
            event1 = aui.send_message_to_agent(
                content="When I arrive home after 6pm, turn on living room lights to 70%, set thermostat to 72°F, and start playing my jazz playlist"
            ).depends_on(None, delay_seconds=2)

            # ================================================================
            # ORACLE STEP 1: Agent should first list available devices
            # to understand what "living room lights" refers to
            # ================================================================
            oracle1 = (
                homekit.list_devices(room="Living Room")
                .oracle()
                .depends_on(event1, delay_seconds=1)
            )

            # ================================================================
            # ORACLE STEP 2: Agent should check available playlists
            # to find the "jazz playlist"
            # ================================================================
            oracle2 = (
                music.list_playlists().oracle().depends_on(oracle1, delay_seconds=1)
            )

            # ================================================================
            # ORACLE STEP 3: Agent should verify the home location is set
            # for the location-based trigger
            # ================================================================
            oracle3 = (
                location.get_home_location()
                .oracle()
                .depends_on(oracle2, delay_seconds=1)
            )

            # ================================================================
            # ORACLE STEP 4: Create the automation with proper trigger
            # This is the CRITICAL step - the automation must have:
            # - Trigger type: Location
            # - Conditions: arriving home + after 6pm (18:00)
            # - Actions: 3 separate actions for lights, thermostat, music
            # ================================================================
            oracle4 = (
                homekit.create_automation(
                    name="Arrive Home Evening Automation",
                    trigger_type="Location",
                    trigger_conditions={
                        "location_state": "arriving",
                        "location": "home",
                        "time_condition": "after",
                        "time": "18:00",
                    },
                    actions=[
                        # Action 1: Turn on living room light to 70% brightness
                        {
                            "action_type": "set_device",
                            "parameters": {
                                "device_id": self.living_room_light_id,
                                "state": "on",
                                "properties": {"brightness": 70},
                            },
                        },
                        # Action 2: Set thermostat to 72°F
                        {
                            "action_type": "set_device",
                            "parameters": {
                                "device_id": self.thermostat_id,
                                "state": "on",
                                "properties": {"temperature": 72},
                            },
                        },
                        # Action 3: Play jazz playlist
                        {
                            "action_type": "play_playlist",
                            "parameters": {"playlist_id": self.jazz_playlist_id},
                        },
                    ],
                    description="When arriving home after 6pm, turn on lights to 70%, set thermostat to 72°F, and play jazz",
                )
                .oracle()
                .depends_on(oracle3, delay_seconds=2)
            )

            # ================================================================
            # ORACLE STEP 5: Agent should verify the automation was created
            # by listing automations
            # ================================================================
            oracle5 = (
                homekit.list_automations()
                .oracle()
                .depends_on(oracle4, delay_seconds=1)
            )

            # ================================================================
            # ORACLE STEP 6: Agent should report back to the user
            # confirming the automation is set up
            # ================================================================
            oracle6 = (
                aui.send_message_to_user(
                    content="I've set up your automation. When you arrive home after 6pm, your living room lights will turn on to 70% brightness, the thermostat will be set to 72°F, and your jazz playlist will start playing."
                )
                .oracle()
                .depends_on(oracle5, delay_seconds=1)
            )

            # ================================================================
            # EVENT 2: Simulate the user arriving home at 6:30pm
            # (This tests if the automation would trigger correctly)
            # ================================================================
            event2 = (
                location.update_location_state("arriving")
                .depends_on(oracle6, delay_seconds=5)
            )

            # Store all events
            self.events = [
                event1,
                oracle1,
                oracle2,
                oracle3,
                oracle4,
                oracle5,
                oracle6,
                event2,
            ]

    def validate(self, env) -> ScenarioValidationResult:
        """
        Validate that the agent successfully created the automation.

        Validation checks:
        1. An automation was created in HomeKit
        2. The automation has the correct trigger type (Location)
        3. The trigger conditions include both location (arriving) and time (after 6pm)
        4. The automation has exactly 3 actions
        5. Action 1: Sets living room light to on with 70% brightness
        6. Action 2: Sets thermostat to 72°F
        7. Action 3: Plays the jazz playlist
        8. The agent communicated success to the user
        """
        try:
            homekit = env.get_app("HomeKitApp")
            music = env.get_app("MusicApp")

            # Check 1: At least one automation was created
            if len(homekit.automations) == 0:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception("No automation was created"),
                )

            # Get the created automation (should be only one)
            automation = list(homekit.automations.values())[0]

            # Check 2: Automation has correct trigger type
            if automation.trigger.trigger_type.value != "Location":
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        f"Automation trigger type is {automation.trigger.trigger_type.value}, expected 'Location'"
                    ),
                )

            # Check 3: Trigger conditions include location and time
            conditions = automation.trigger.conditions
            if "location_state" not in conditions or conditions["location_state"] != "arriving":
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        "Automation trigger does not include 'arriving' location state"
                    ),
                )

            if "time" not in conditions:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        "Automation trigger does not include time condition"
                    ),
                )

            # Check 4: Automation has 3-4 actions (minimum: one light, thermostat, playlist)
            if len(automation.actions) < 3 or len(automation.actions) > 4:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        f"Automation has {len(automation.actions)} actions, expected 3-4"
                    ),
                )

            # Check 5: At least one living room light is turned on to 70%
            light_action_found = False
            for action in automation.actions:
                if (
                    action.action_type == "set_device"
                    and action.parameters.get("device_id") in [self.living_room_light_id, self.living_room_lamp_id]
                    and action.parameters.get("state") == "on"
                ):
                    properties = action.parameters.get("properties", {})
                    if properties.get("brightness") == 70:
                        light_action_found = True
                        break

            if not light_action_found:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        "No action found that turns on a living room light to 70% brightness"
                    ),
                )

            # Check 6: Thermostat is set to 72°F
            thermostat_action_found = False
            for action in automation.actions:
                if (
                    action.action_type == "set_device"
                    and action.parameters.get("device_id") == self.thermostat_id
                    and action.parameters.get("state") == "on"
                ):
                    thermostat_props = action.parameters.get("properties", {})
                    if thermostat_props.get("temperature") == 72:
                        thermostat_action_found = True
                        break

            if not thermostat_action_found:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        "No action found that sets the thermostat to 72°F"
                    ),
                )

            # Check 7: Jazz playlist is played
            playlist_action_found = False
            for action in automation.actions:
                if (
                    action.action_type == "play_playlist"
                    and action.parameters.get("playlist_id") == self.jazz_playlist_id
                ):
                    playlist_action_found = True
                    break

            if not playlist_action_found:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        "No action found that plays the jazz playlist"
                    ),
                )

            # Check 8: Agent sent a confirmation message to the user
            user_message_sent = any(
                event.event_type == EventType.AGENT
                and isinstance(event.action, Action)
                and event.action.function_name == "send_message_to_user"
                and event.action.class_name == "AgentUserInterface"
                for event in env.event_log.list_view()
            )

            if not user_message_sent:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        "Agent did not send confirmation message to user"
                    ),
                )

            # All checks passed!
            return ScenarioValidationResult(
                success=True,
                rationale="Agent successfully created a context-aware automation with correct trigger (location + time) and all required actions (living room lights to 70%, thermostat to 72°F, play jazz playlist)",
            )

        except Exception as e:
            return ScenarioValidationResult(
                success=False,
                exception=e,
                rationale=f"Validation failed with error: {str(e)}",
            )


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    # Run the scenario in oracle mode and validate
    run_and_validate(SmartHomeScenario())
