# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

"""
HomeKit App for Smart Home Control

This app simulates a smart home ecosystem with devices, scenes, and automations.
It supports conditional logic based on time, location, and other triggers.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from are.simulation.apps.app import App
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import get_state_dict, type_check


# ============================================================================
# Data Models
# ============================================================================


class DeviceType(Enum):
    """Types of smart home devices"""

    LIGHT = "Light"
    THERMOSTAT = "Thermostat"
    LOCK = "Lock"
    CAMERA = "Camera"
    SPEAKER = "Speaker"
    OUTLET = "Outlet"
    SENSOR = "Sensor"


class DeviceState(Enum):
    """Device power states"""

    ON = "on"
    OFF = "off"


class TriggerType(Enum):
    """Types of automation triggers"""

    TIME = "Time"
    LOCATION = "Location"
    DEVICE_STATE = "DeviceState"
    SENSOR_VALUE = "SensorValue"


class LocationState(Enum):
    """User location states"""

    HOME = "home"
    AWAY = "away"
    ARRIVING = "arriving"
    LEAVING = "leaving"


@dataclass
class Device:
    """
    Represents a smart home device with controllable properties.
    """

    name: str
    device_type: DeviceType
    room: str
    device_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state: DeviceState = DeviceState.OFF
    # Device-specific properties (brightness for lights, temperature for thermostats, etc.)
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name or len(self.name.strip()) == 0:
            raise ValueError("Device name cannot be empty")

        if isinstance(self.device_type, str):
            self.device_type = DeviceType(self.device_type)

        if isinstance(self.state, str):
            self.state = DeviceState(self.state)

    def __str__(self):
        return f"{self.name} ({self.device_type.value}) in {self.room} - {self.state.value}"


@dataclass
class Scene:
    """
    A scene is a collection of device states that can be activated together.
    """

    name: str
    device_states: dict[str, dict[str, Any]]  # device_id -> {state, properties}
    scene_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str = ""

    def __post_init__(self):
        if not self.name or len(self.name.strip()) == 0:
            raise ValueError("Scene name cannot be empty")

    def __str__(self):
        return f"Scene: {self.name} ({len(self.device_states)} devices)"


@dataclass
class Trigger:
    """
    A trigger defines when an automation should execute.
    """

    trigger_type: TriggerType
    conditions: dict[str, Any]  # Type-specific conditions
    trigger_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self):
        if isinstance(self.trigger_type, str):
            self.trigger_type = TriggerType(self.trigger_type)


@dataclass
class Action:
    """
    An action to be performed when an automation triggers.
    """

    action_type: str  # "set_device", "activate_scene", "notify", etc.
    parameters: dict[str, Any]
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass
class Automation:
    """
    An automation links triggers to actions.
    """

    name: str
    trigger: Trigger
    actions: list[Action]
    automation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    enabled: bool = True
    description: str = ""

    def __post_init__(self):
        if not self.name or len(self.name.strip()) == 0:
            raise ValueError("Automation name cannot be empty")

    def __str__(self):
        return f"Automation: {self.name} ({'enabled' if self.enabled else 'disabled'})"


# ============================================================================
# HomeKit App
# ============================================================================


@dataclass
class HomeKitApp(App):
    """
    Smart Home Control App with device management, scenes, and automations.

    This app manages:
    - Smart devices (lights, thermostats, locks, etc.)
    - Scenes (pre-configured device states)
    - Automations (trigger-based actions)

    Key Features:
    - Device control (on/off, brightness, temperature, etc.)
    - Scene management and activation
    - Automation creation with conditional triggers
    - Multi-device orchestration
    """

    name: str | None = "HomeKitApp"
    devices: dict[str, Device] = field(default_factory=dict)
    scenes: dict[str, Scene] = field(default_factory=dict)
    automations: dict[str, Automation] = field(default_factory=dict)

    def __post_init__(self):
        super().__init__(self.name)

    # ========================================================================
    # State Management
    # ========================================================================

    def get_state(self) -> dict[str, Any]:
        """Return serializable state"""
        return get_state_dict(self, ["devices", "scenes", "automations"])

    def load_state(self, state_dict: dict[str, Any]):
        """Restore state from saved data"""
        self.devices = {}
        self.scenes = {}
        self.automations = {}

        # Restore devices
        for device_id, device_data in state_dict.get("devices", {}).items():
            device = Device(
                name=device_data["name"],
                device_type=DeviceType(device_data["device_type"]),
                room=device_data["room"],
                device_id=device_data.get("device_id", device_id),
                state=DeviceState(device_data.get("state", "off")),
                properties=device_data.get("properties", {}),
            )
            self.devices[device_id] = device

        # Restore scenes
        for scene_id, scene_data in state_dict.get("scenes", {}).items():
            scene = Scene(
                name=scene_data["name"],
                device_states=scene_data["device_states"],
                scene_id=scene_data.get("scene_id", scene_id),
                description=scene_data.get("description", ""),
            )
            self.scenes[scene_id] = scene

        # Restore automations
        for auto_id, auto_data in state_dict.get("automations", {}).items():
            trigger = Trigger(
                trigger_type=TriggerType(auto_data["trigger"]["trigger_type"]),
                conditions=auto_data["trigger"]["conditions"],
                trigger_id=auto_data["trigger"].get(
                    "trigger_id", uuid.uuid4().hex
                ),
            )

            actions = [
                Action(
                    action_type=action_data["action_type"],
                    parameters=action_data["parameters"],
                    action_id=action_data.get("action_id", uuid.uuid4().hex),
                )
                for action_data in auto_data["actions"]
            ]

            automation = Automation(
                name=auto_data["name"],
                trigger=trigger,
                actions=actions,
                automation_id=auto_data.get("automation_id", auto_id),
                enabled=auto_data.get("enabled", True),
                description=auto_data.get("description", ""),
            )
            self.automations[auto_id] = automation

    def reset(self):
        """Reset app to initial state"""
        super().reset()
        self.devices = {}
        self.scenes = {}
        self.automations = {}

    # ========================================================================
    # Device Management Tools
    # ========================================================================

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_device(
        self,
        name: str,
        device_type: str,
        room: str,
        initial_properties: dict[str, Any] | None = None,
    ) -> str:
        """
        Add a new smart home device.

        :param name: Name of the device (e.g., "Living Room Light")
        :param device_type: Type of device (Light, Thermostat, Lock, Camera, Speaker, Outlet, Sensor)
        :param room: Room where the device is located
        :param initial_properties: Optional initial properties (e.g., brightness, temperature)
        :returns: The device_id of the created device
        """
        if initial_properties is None:
            initial_properties = {}

        device = Device(
            name=name,
            device_type=DeviceType(device_type),
            room=room,
            properties=initial_properties,
        )
        self.devices[device.device_id] = device
        return device.device_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_devices(self, room: str | None = None) -> list[dict[str, Any]]:
        """
        List all devices, optionally filtered by room.

        :param room: Optional room name to filter devices
        :returns: List of device information dictionaries
        """
        devices = list(self.devices.values())

        if room:
            devices = [d for d in devices if d.room.lower() == room.lower()]

        return [
            {
                "device_id": d.device_id,
                "name": d.name,
                "device_type": d.device_type.value,
                "room": d.room,
                "state": d.state.value,
                "properties": d.properties,
            }
            for d in devices
        ]

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_device(self, device_id: str) -> dict[str, Any]:
        """
        Get detailed information about a specific device.

        :param device_id: The unique identifier of the device
        :returns: Device information dictionary
        """
        if device_id not in self.devices:
            raise KeyError(f"Device {device_id} not found")

        device = self.devices[device_id]
        return {
            "device_id": device.device_id,
            "name": device.name,
            "device_type": device.device_type.value,
            "room": device.room,
            "state": device.state.value,
            "properties": device.properties,
        }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_device_state(
        self, device_id: str, state: str, properties: dict[str, Any] | None = None
    ) -> str:
        """
        Control a device by setting its state and properties.

        :param device_id: The device to control
        :param state: Device state (on/off)
        :param properties: Optional properties to set (e.g., {"brightness": 70, "color": "warm"})
        :returns: Success message
        """
        if device_id not in self.devices:
            raise KeyError(f"Device {device_id} not found")

        device = self.devices[device_id]
        device.state = DeviceState(state)

        if properties:
            device.properties.update(properties)

        return f"Device '{device.name}' set to {state}" + (
            f" with properties {properties}" if properties else ""
        )

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def turn_on_device(
        self, device_id: str, properties: dict[str, Any] | None = None
    ) -> str:
        """
        Turn on a device with optional properties.

        :param device_id: The device to turn on
        :param properties: Optional properties (e.g., {"brightness": 70} for lights)
        :returns: Success message
        """
        return self.set_device_state(device_id, "on", properties)

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def turn_off_device(self, device_id: str) -> str:
        """
        Turn off a device.

        :param device_id: The device to turn off
        :returns: Success message
        """
        return self.set_device_state(device_id, "off")

    # ========================================================================
    # Scene Management Tools
    # ========================================================================

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_scene(
        self,
        name: str,
        device_states: dict[str, dict[str, Any]],
        description: str = "",
    ) -> str:
        """
        Create a scene with predefined device states.

        :param name: Name of the scene
        :param device_states: Dictionary mapping device_id to {state, properties}
        :param description: Optional description of the scene
        :returns: The scene_id of the created scene
        """
        # Validate that all devices exist
        for device_id in device_states.keys():
            if device_id not in self.devices:
                raise KeyError(f"Device {device_id} not found")

        scene = Scene(
            name=name, device_states=device_states, description=description
        )
        self.scenes[scene.scene_id] = scene
        return scene.scene_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_scenes(self) -> list[dict[str, Any]]:
        """
        List all configured scenes.

        :returns: List of scene information dictionaries
        """
        return [
            {
                "scene_id": s.scene_id,
                "name": s.name,
                "description": s.description,
                "num_devices": len(s.device_states),
            }
            for s in self.scenes.values()
        ]

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def activate_scene(self, scene_id: str) -> str:
        """
        Activate a scene, applying all device states.

        :param scene_id: The scene to activate
        :returns: Success message with details
        """
        if scene_id not in self.scenes:
            raise KeyError(f"Scene {scene_id} not found")

        scene = self.scenes[scene_id]
        devices_updated = []

        for device_id, desired_state in scene.device_states.items():
            if device_id not in self.devices:
                continue

            device = self.devices[device_id]
            device.state = DeviceState(desired_state.get("state", "on"))
            if "properties" in desired_state:
                device.properties.update(desired_state["properties"])

            devices_updated.append(device.name)

        return f"Scene '{scene.name}' activated. Updated {len(devices_updated)} devices: {', '.join(devices_updated)}"

    # ========================================================================
    # Automation Management Tools
    # ========================================================================

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_automation(
        self,
        name: str,
        trigger_type: str,
        trigger_conditions: dict[str, Any],
        actions: list[dict[str, Any]],
        description: str = "",
    ) -> str:
        """
        Create an automation with a trigger and actions.

        :param name: Name of the automation
        :param trigger_type: Type of trigger (Time, Location, DeviceState, SensorValue)
        :param trigger_conditions: Conditions for the trigger. The format depends on trigger_type:
            - Time: {"time": "HH:MM"} (24-hour format)
            - Location: {"location_state": "arriving"|"leaving"|"home"|"away", "location": "home",
                        "time_condition": "after"|"before" (optional), "time": "HH:MM" (optional)}
            - DeviceState: {"device_id": "...", "state": "on"|"off", "property": "..." (optional)}
            - SensorValue: {"device_id": "...", "property": "...", "operator": ">"|"<"|"==", "value": ...}

            For Location triggers with time constraints, use:
            {"location_state": "arriving", "location": "home", "time_condition": "after", "time": "18:00"}
        :param actions: List of actions to perform. Each action is a dict with:
            - "action_type": "set_device" | "activate_scene" | "play_playlist" | "notify"
            - "parameters": dict with action-specific parameters
            Examples:
            - Set device: {"action_type": "set_device", "parameters": {"device_id": "...", "state": "on", "properties": {"brightness": 70}}}
            - Play playlist: {"action_type": "play_playlist", "parameters": {"playlist_id": "..."}}
        :param description: Optional description
        :returns: The automation_id of the created automation
        """
        trigger = Trigger(
            trigger_type=TriggerType(trigger_type), conditions=trigger_conditions
        )

        action_objects = [
            Action(action_type=a["action_type"], parameters=a["parameters"])
            for a in actions
        ]

        automation = Automation(
            name=name,
            trigger=trigger,
            actions=action_objects,
            description=description,
        )

        self.automations[automation.automation_id] = automation
        return automation.automation_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_automations(self) -> list[dict[str, Any]]:
        """
        List all configured automations.

        :returns: List of automation information dictionaries
        """
        return [
            {
                "automation_id": a.automation_id,
                "name": a.name,
                "description": a.description,
                "enabled": a.enabled,
                "trigger_type": a.trigger.trigger_type.value,
                "num_actions": len(a.actions),
            }
            for a in self.automations.values()
        ]

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_automation(self, automation_id: str) -> dict[str, Any]:
        """
        Get detailed information about an automation.

        :param automation_id: The automation to retrieve
        :returns: Automation details including trigger and actions
        """
        if automation_id not in self.automations:
            raise KeyError(f"Automation {automation_id} not found")

        automation = self.automations[automation_id]
        return {
            "automation_id": automation.automation_id,
            "name": automation.name,
            "description": automation.description,
            "enabled": automation.enabled,
            "trigger": {
                "trigger_type": automation.trigger.trigger_type.value,
                "conditions": automation.trigger.conditions,
            },
            "actions": [
                {"action_type": a.action_type, "parameters": a.parameters}
                for a in automation.actions
            ],
        }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def enable_automation(self, automation_id: str) -> str:
        """
        Enable an automation.

        :param automation_id: The automation to enable
        :returns: Success message
        """
        if automation_id not in self.automations:
            raise KeyError(f"Automation {automation_id} not found")

        self.automations[automation_id].enabled = True
        return f"Automation '{self.automations[automation_id].name}' enabled"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def disable_automation(self, automation_id: str) -> str:
        """
        Disable an automation.

        :param automation_id: The automation to disable
        :returns: Success message
        """
        if automation_id not in self.automations:
            raise KeyError(f"Automation {automation_id} not found")

        self.automations[automation_id].enabled = False
        return f"Automation '{self.automations[automation_id].name}' disabled"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_automation(self, automation_id: str) -> str:
        """
        Delete an automation.

        :param automation_id: The automation to delete
        :returns: Success message
        """
        if automation_id not in self.automations:
            raise KeyError(f"Automation {automation_id} not found")

        name = self.automations[automation_id].name
        del self.automations[automation_id]
        return f"Automation '{name}' deleted"

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def find_device_by_name(self, name: str) -> Device | None:
        """Find a device by name (case-insensitive)"""
        for device in self.devices.values():
            if device.name.lower() == name.lower():
                return device
        return None

    def find_scene_by_name(self, name: str) -> Scene | None:
        """Find a scene by name (case-insensitive)"""
        for scene in self.scenes.values():
            if scene.name.lower() == name.lower():
                return scene
        return None
