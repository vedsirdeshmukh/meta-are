# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

"""
Smart Home Vacation Mode Scenario

This scenario tests an agent's ability to:
1. Reason about implicit requirements from high-level goals
2. Balance competing objectives (security vs energy efficiency)
3. Make intelligent device control decisions
4. Design multiple coordinated automations

Task: "I'm going on vacation for 2 weeks. Set up my home to save energy but maintain security."

Complexity: Very High
- Requires inferring specific actions from abstract goals
- Must balance trade-offs (security lighting vs energy savings)
- Needs domain knowledge about home security and energy efficiency
- Multiple automations with different triggers required
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

from dotenv import load_dotenv
load_dotenv(override=True)

import os
from openai import OpenAI
from pydantic import BaseModel

from typing import Literal

class JudgeAnswer(BaseModel):
    assessment: str
    reasoning: str
    final_verdict: Literal["Pass", "Fail"]


@register_scenario("scenario_vacation_mode")
class VacationModeScenario(Scenario):
    """
    Vacation Mode Scenario requiring high-level reasoning about home automation.

    This scenario evaluates the agent's ability to:
    - Infer specific actions from abstract goals ("save energy", "maintain security")
    - Understand domain knowledge (what devices affect energy/security)
    - Balance competing objectives
    - Design multiple coordinated automations
    - Make context-appropriate device settings
    """

    start_time: float | None = 0
    duration: float | None = 120  # 120 seconds simulation time

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """
        Initialize smart home with various devices across multiple rooms.
        """
        # Initialize apps
        aui = AgentUserInterface()
        homekit = HomeKitApp()
        location = LocationApp()
        music = MusicApp()
        system = SystemApp()

        # ====================================================================
        # Populate HomeKit with Diverse Smart Devices
        # ====================================================================

        # Living room devices
        self.living_room_light_id = homekit.add_device(
            name="Living Room Light",
            device_type="Light",
            room="Living Room",
            initial_properties={"brightness": 80},
        )
        homekit.turn_on_device(self.living_room_light_id)

        self.living_room_lamp_id = homekit.add_device(
            name="Living Room Lamp",
            device_type="Light",
            room="Living Room",
            initial_properties={"brightness": 60},
        )
        homekit.turn_on_device(self.living_room_lamp_id)
        
        # Bedroom devices
        self.bedroom_light_id = homekit.add_device(
            name="Bedroom Light",
            device_type="Light",
            room="Bedroom",
            initial_properties={"brightness": 70},
        )
        homekit.turn_on_device(self.bedroom_light_id)

        self.bedroom_lamp_id = homekit.add_device(
            name="Bedroom Lamp",
            device_type="Light",
            room="Bedroom",
            initial_properties={"brightness": 50},
        )

        # Kitchen devices
        self.kitchen_light_id = homekit.add_device(
            name="Kitchen Light",
            device_type="Light",
            room="Kitchen",
            initial_properties={"brightness": 100},
        )

        # Thermostat
        self.thermostat_id = homekit.add_device(
            name="Home Thermostat",
            device_type="Thermostat",
            room="Hallway",
            initial_properties={"temperature": 72, "mode": "auto", "unit": "F"},
        )

        # Security devices - should NOT be turned off
        self.front_door_lock_id = homekit.add_device(
            name="Front Door Lock",
            device_type="Lock",
            room="Entrance",
            initial_properties={"locked": True},
        )

        self.camera_id = homekit.add_device(
            name="Front Door Camera",
            device_type="Camera",
            room="Entrance",
            initial_properties={"recording": True, "motion_detection": True},
        )

        # Other devices
        self.smart_outlet_id = homekit.add_device(
            name="Living Room Outlet",
            device_type="Outlet",
            room="Living Room",
            initial_properties={},
        )

        # ====================================================================
        # Populate Location App
        # ====================================================================

        location.set_home_location(
            name="Home",
            address="456 Oak Avenue, Portland, OR",
            latitude=45.5231,
            longitude=-122.6765,
        )

        # User is currently home
        location.update_location_state("home")

        # ====================================================================
        # Store Apps
        # ====================================================================

        self.apps = [aui, homekit, location, music, system]

    def build_events_flow(self) -> None:
        """
        Build the event flow. Note: This scenario is less prescriptive about
        the exact steps, as the agent needs to reason about the solution.
        """
        aui = self.get_typed_app(AgentUserInterface)
        homekit = self.get_typed_app(HomeKitApp)
        location = self.get_typed_app(LocationApp)

        with EventRegisterer.capture_mode():
            # ================================================================
            # EVENT 1: User provides the high-level vacation request
            # ================================================================
            event1 = aui.send_message_to_agent(
                content="I'm going on vacation for 2 weeks. Set up my home to save energy but maintain security."
            ).depends_on(None, delay_seconds=2)

            # ================================================================
            # Note: We don't define strict oracle steps here, as the agent
            # needs to reason about the solution. The validation will check
            # the end state rather than specific action sequences.
            # ================================================================

            # Store events
            self.events = [event1]

    def validate(self, env) -> ScenarioValidationResult:
        """
        Validate agent's vacation mode setup using LLM-based evaluation with a rubric.

        The agent should demonstrate:
        1. Energy efficiency - thermostat lowered, unnecessary lights off
        2. Security awareness - security devices remain on, some lighting for deterrence
        3. Temporal reasoning - security lights only at night
        4. Domain knowledge - understanding what affects energy/security
        """
        try:
            from are.simulation.agents.are_simulation_agent_config import LLMEngineConfig
            from are.simulation.validation.configs import create_judge_engine

            homekit = env.get_app("HomeKitApp")

            # ================================================================
            # Collect agent's actions and current state
            # ================================================================
            agent_actions = []
            for event in env.event_log.list_view():
                if event.event_type == EventType.AGENT and isinstance(event.action, Action):
                    agent_actions.append({
                        "function": event.action.function_name,
                        "app": event.action.class_name,
                        "args": event.action.args,
                        "timestamp": event.event_time,
                    })

            # Get current device states
            device_states = {}
            for device_id, device in homekit.devices.items():
                device_states[device.name] = {
                    "state": device.state.value,
                    "properties": device.properties,
                    "room": device.room,
                    "type": device.device_type.value,
                }

            # Get automations created
            automations_info = []
            for auto_id, automation in homekit.automations.items():
                automations_info.append({
                    "name": automation.name,
                    "trigger_type": automation.trigger.trigger_type.value,
                    "trigger_conditions": automation.trigger.conditions,
                    "actions": [
                        {
                            "action_type": action.action_type,
                            "parameters": action.parameters,
                        }
                        for action in automation.actions
                    ],
                    "enabled": automation.enabled,
                })

            # ================================================================
            # Create LLM evaluation prompt with placeholder rubric
            # ================================================================

            EVALUATION_RUBRIC = """
**1. Energy Efficiency**
- The agent should turn off at least one light for energy savings.
- The agent should lower the thermostat temperature.

**2. Security Measures**
- The agent should keep the front door lock and camera on for security. The camera should be recording and motion detection should be enabled.

**3. Communication**
- The agent should communicate the success of the task to the user.

**4. Automation**
- The agent should create an automation to turn on a light in the evening/night to simulate occupancy for added security.

### Scoring Guidelines:
- **PASS**: The agent met all the criteria.
- **FAIL**: The agent did not meet all the criteria.
"""

            validation_prompt = f"""
You are evaluating an AI agent's performance on the task: "I'm going on vacation for 2 weeks. Set up my home to save energy but maintain security."

### Agent's Actions Taken:
{self._format_actions(agent_actions)}

### Resulting Device States:
{self._format_device_states(device_states)}

### Automations Created:
{self._format_automations(automations_info)}

### Evaluation Rubric:
{EVALUATION_RUBRIC}

### Your Evaluation:
Analyze the agent's actions against the rubric above.

Output Format:
- Assessment: Detailed analysis of each criterion.
- Reasoning: Explain whether the agent met the requirements.
- Final Verdict: Pass or Fail.
"""

            # ================================================================
            # Call LLM judge for evaluation
            # ================================================================
            client = OpenAI(
                api_key=os.getenv("LB_API_KEY"),
                base_url=os.getenv("LB_BASE_URL"),
            )

            response = client.responses.parse(
                model="openai/gpt-5",
                input=validation_prompt,
                text_format=JudgeAnswer
            )

            evaluation = response.output_parsed

            # Extract the assessment, reasoning, and final verdict
            assessment = evaluation.assessment if evaluation else "No assessment"
            reasoning = evaluation.reasoning if evaluation else "No reasoning"
            final_verdict = evaluation.final_verdict if evaluation else "No final verdict"

            if final_verdict == "Pass":
                success = True
                rationale = assessment + "\n" + reasoning
            elif final_verdict == "Fail":
                success = False
                rationale = assessment + "\n" + reasoning
            else:
                success = False
                rationale = f"LLM judge response unclear. Response: {assessment}\n{reasoning}"

            return ScenarioValidationResult(
                success=success,
                rationale=rationale,
            )

        except Exception as e:
            return ScenarioValidationResult(
                success=False,
                exception=e,
                rationale=f"Validation failed with error: {str(e)}",
            )

    def _format_actions(self, actions: list[dict]) -> str:
        """Format agent actions for the LLM prompt."""
        if not actions:
            return "No actions taken"

        formatted = []
        for i, action in enumerate(actions, 1):
            args_str = ", ".join(f"{k}={v}" for k, v in action["args"].items())
            formatted.append(
                f"{i}. [{action['timestamp']:.1f}s] {action['app']}.{action['function']}({args_str})"
            )
        return "\n".join(formatted)

    def _format_device_states(self, states: dict) -> str:
        """Format device states for the LLM prompt."""
        if not states:
            return "No device states available"

        formatted = []
        for device_name, state in states.items():
            props_str = ", ".join(f"{k}={v}" for k, v in state["properties"].items())
            formatted.append(
                f"- {device_name} ({state['type']} in {state['room']}): "
                f"state={state['state']}"
                + (f", {props_str}" if props_str else "")
            )
        return "\n".join(formatted)

    def _format_automations(self, automations: list[dict]) -> str:
        """Format automations for the LLM prompt."""
        if not automations:
            return "No automations created"

        formatted = []
        for i, auto in enumerate(automations, 1):
            actions_str = "\n    ".join(
                f"- {act['action_type']}: {act['parameters']}"
                for act in auto["actions"]
            )
            formatted.append(
                f"{i}. {auto['name']} ({'enabled' if auto['enabled'] else 'disabled'})\n"
                f"   Trigger: {auto['trigger_type']} - {auto['trigger_conditions']}\n"
                f"   Actions:\n    {actions_str}"
            )
        return "\n".join(formatted)


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    # Run the scenario in oracle mode and validate
    run_and_validate(VacationModeScenario())
