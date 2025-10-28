# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from are.simulation.apps.app import App
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import get_state_dict, type_check, uuid_hex


class DeviceType(Enum):
    LIGHT = "Light"
    THERMOSTAT = "Thermostat"
    LOCK = "Lock"
    CAMERA = "Camera"
    OUTLET = "Outlet"
    SWITCH = "Switch"
    SENSOR = "Sensor"
    GARAGE_DOOR = "Garage Door"
    WINDOW_COVERING = "Window Covering"
    FAN = "Fan"


class DeviceStatus(Enum):
    ON = "On"
    OFF = "Off"
    LOCKED = "Locked"
    UNLOCKED = "Unlocked"
    OPEN = "Open"
    CLOSED = "Closed"
    RECORDING = "Recording"
    IDLE = "Idle"


@dataclass
class SmartDevice:
    """Represents a smart home device in the HomeKit ecosystem."""

    device_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Device"
    device_type: DeviceType = DeviceType.LIGHT
    room: str = "Living Room"
    status: DeviceStatus = DeviceStatus.OFF

    # Device-specific attributes
    brightness: int | None = None  # 0-100 for lights
    temperature: float | None = None  # For thermostats
    target_temperature: float | None = None  # For thermostats
    color: str | None = None  # For lights (e.g., "warm white", "blue")
    battery_level: int | None = None  # 0-100 for battery-powered devices
    is_reachable: bool = True  # Network connectivity status
    is_critical: bool = False  # If device should not be turned off (e.g., aquarium light, medical device)
    critical_reason: str | None = None  # Why device is critical
    manufacturer: str | None = None
    model: str | None = None

    def __post_init__(self):
        if not self.device_id:
            self.device_id = uuid.uuid4().hex

        # Validate device-specific constraints
        if self.brightness is not None and not 0 <= self.brightness <= 100:
            raise ValueError(f"Brightness must be between 0 and 100, got {self.brightness}")

        if self.battery_level is not None and not 0 <= self.battery_level <= 100:
            raise ValueError(f"Battery level must be between 0 and 100, got {self.battery_level}")

    def __str__(self):
        status_info = f"\nDevice ID: {self.device_id}\nName: {self.name}\nType: {self.device_type.value}\nRoom: {self.room}\nStatus: {self.status.value}"

        if self.brightness is not None:
            status_info += f"\nBrightness: {self.brightness}%"
        if self.temperature is not None:
            status_info += f"\nCurrent Temperature: {self.temperature}°F"
        if self.target_temperature is not None:
            status_info += f"\nTarget Temperature: {self.target_temperature}°F"
        if self.color:
            status_info += f"\nColor: {self.color}"
        if self.battery_level is not None:
            status_info += f"\nBattery: {self.battery_level}%"
        if not self.is_reachable:
            status_info += "\n⚠️ Not Reachable"
        if self.is_critical:
            status_info += f"\n🚨 CRITICAL DEVICE: {self.critical_reason}"

        return status_info

    @property
    def summary(self):
        return f"{self.name} ({self.device_type.value}) in {self.room}: {self.status.value}"


@dataclass
class Scene:
    """Represents a HomeKit scene - a collection of device states."""

    scene_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Scene"
    device_states: dict[str, dict[str, Any]] = field(default_factory=dict)  # device_id -> {attribute: value}

    def __str__(self):
        return f"Scene: {self.name} (affects {len(self.device_states)} devices)"


@dataclass
class Automation:
    """Represents a HomeKit automation rule."""

    automation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Automation"
    trigger_type: str = "time"  # "time", "location", "device", "sensor"
    trigger_value: str = ""  # e.g., "7:00 AM", "arrive home", etc.
    actions: list[dict[str, Any]] = field(default_factory=list)
    is_enabled: bool = True

    def __str__(self):
        return f"Automation: {self.name}\nTrigger: {self.trigger_type} - {self.trigger_value}\nEnabled: {self.is_enabled}\nActions: {len(self.actions)}"


@dataclass
class HomeKitApp(App):
    """
    HomeKit smart home management application.

    Manages smart home devices including lights, thermostats, locks, cameras, and more.
    Supports scenes, automations, and room-based organization.

    Key Features:
        - Device Management: Control lights, thermostats, locks, cameras, and other smart devices
        - Room Organization: Group devices by room
        - Scenes: Create and activate scenes with multiple device states
        - Automations: Set up time-based and event-based automations
        - Safety Features: Critical device protection (e.g., aquarium lights, medical devices)
        - Status Monitoring: Check device battery, connectivity, and status

    Notes:
        - Some devices may be marked as critical and should not be turned off
        - Devices can be grouped into rooms for easier management
        - Scenes allow activating multiple device states at once
        - Automations can trigger actions based on time, location, or device events
    """

    name: str | None = None
    devices: dict[str, SmartDevice] = field(default_factory=dict)
    scenes: dict[str, Scene] = field(default_factory=dict)
    automations: dict[str, Automation] = field(default_factory=dict)
    home_name: str = "Home"

    def __post_init__(self):
        super().__init__(self.name)

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(self, ["devices", "scenes", "automations", "home_name"])

    def load_state(self, state_dict: dict[str, Any]):
        self.devices = {k: SmartDevice(**v) for k, v in state_dict.get("devices", {}).items()}
        self.scenes = {k: Scene(**v) for k, v in state_dict.get("scenes", {}).items()}
        self.automations = {k: Automation(**v) for k, v in state_dict.get("automations", {}).items()}
        self.home_name = state_dict.get("home_name", "Home")

    def reset(self):
        super().reset()
        self.devices = {}
        self.scenes = {}
        self.automations = {}

    # Device Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_device(
        self,
        name: str,
        device_type: str,
        room: str = "Living Room",
        is_critical: bool = False,
        critical_reason: str | None = None,
    ) -> str:
        """
        Add a new smart home device to HomeKit.

        :param name: Name of the device (e.g., "Living Room Light", "Front Door Lock")
        :param device_type: Type of device. Options: Light, Thermostat, Lock, Camera, Outlet, Switch, Sensor, Garage Door, Window Covering, Fan
        :param room: Room where the device is located
        :param is_critical: Whether this device is critical and should not be turned off (e.g., aquarium light, medical device monitor)
        :param critical_reason: Reason why the device is critical (required if is_critical is True)
        :returns: device_id of the created device
        """
        device_type_enum = DeviceType[device_type.upper().replace(" ", "_")]

        device = SmartDevice(
            device_id=uuid_hex(self.rng),
            name=name,
            device_type=device_type_enum,
            room=room,
            is_critical=is_critical,
            critical_reason=critical_reason,
        )

        self.devices[device.device_id] = device
        return device.device_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_devices(self, room: str | None = None, device_type: str | None = None) -> str:
        """
        List all smart home devices, optionally filtered by room or type.

        :param room: Filter by room name (optional)
        :param device_type: Filter by device type (optional)
        :returns: String representation of all matching devices
        """
        filtered_devices = self.devices.values()

        if room:
            filtered_devices = [d for d in filtered_devices if d.room.lower() == room.lower()]

        if device_type:
            device_type_enum = DeviceType[device_type.upper().replace(" ", "_")]
            filtered_devices = [d for d in filtered_devices if d.device_type == device_type_enum]

        if not filtered_devices:
            return "No devices found matching the criteria."

        result = f"Found {len(filtered_devices)} device(s):\n\n"
        for device in filtered_devices:
            result += str(device) + "\n" + "-" * 40 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_device_status(self, device_id: str) -> str:
        """
        Get detailed status of a specific device.

        :param device_id: ID of the device
        :returns: Detailed device information
        """
        if device_id not in self.devices:
            return f"Device with ID {device_id} not found."

        return str(self.devices[device_id])

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def turn_on_device(self, device_id: str) -> str:
        """
        Turn on a device.

        :param device_id: ID of the device to turn on
        :returns: Success or error message
        """
        if device_id not in self.devices:
            return f"Device with ID {device_id} not found."

        device = self.devices[device_id]

        if device.device_type == DeviceType.LOCK:
            return "Cannot turn on a lock. Use unlock_device instead."
        elif device.device_type == DeviceType.GARAGE_DOOR:
            return "Cannot turn on a garage door. Use open_garage_door instead."

        device.status = DeviceStatus.ON
        return f"✓ {device.name} turned on."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def turn_off_device(self, device_id: str) -> str:
        """
        Turn off a device. WARNING: Check if device is critical before turning off.

        :param device_id: ID of the device to turn off
        :returns: Success or error message
        """
        if device_id not in self.devices:
            return f"Device with ID {device_id} not found."

        device = self.devices[device_id]

        if device.is_critical:
            return f"⚠️ CANNOT TURN OFF: {device.name} is a critical device. Reason: {device.critical_reason}"

        if device.device_type == DeviceType.LOCK:
            return "Cannot turn off a lock. Use lock_device instead."
        elif device.device_type == DeviceType.GARAGE_DOOR:
            return "Cannot turn off a garage door. Use close_garage_door instead."

        device.status = DeviceStatus.OFF
        return f"✓ {device.name} turned off."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_light_brightness(self, device_id: str, brightness: int) -> str:
        """
        Set brightness level for a light.

        :param device_id: ID of the light device
        :param brightness: Brightness level (0-100)
        :returns: Success or error message
        """
        if device_id not in self.devices:
            return f"Device with ID {device_id} not found."

        device = self.devices[device_id]

        if device.device_type != DeviceType.LIGHT:
            return f"{device.name} is not a light."

        if not 0 <= brightness <= 100:
            return "Brightness must be between 0 and 100."

        device.brightness = brightness
        if brightness > 0:
            device.status = DeviceStatus.ON
        else:
            device.status = DeviceStatus.OFF

        return f"✓ {device.name} brightness set to {brightness}%."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_thermostat_temperature(self, device_id: str, temperature: float) -> str:
        """
        Set target temperature for a thermostat.

        :param device_id: ID of the thermostat device
        :param temperature: Target temperature in Fahrenheit
        :returns: Success or error message
        """
        if device_id not in self.devices:
            return f"Device with ID {device_id} not found."

        device = self.devices[device_id]

        if device.device_type != DeviceType.THERMOSTAT:
            return f"{device.name} is not a thermostat."

        if not 50 <= temperature <= 90:
            return "Temperature must be between 50°F and 90°F."

        device.target_temperature = temperature
        device.status = DeviceStatus.ON

        return f"✓ {device.name} temperature set to {temperature}°F."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def lock_device(self, device_id: str) -> str:
        """
        Lock a smart lock.

        :param device_id: ID of the lock device
        :returns: Success or error message
        """
        if device_id not in self.devices:
            return f"Device with ID {device_id} not found."

        device = self.devices[device_id]

        if device.device_type != DeviceType.LOCK:
            return f"{device.name} is not a lock."

        device.status = DeviceStatus.LOCKED
        return f"✓ {device.name} locked."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def unlock_device(self, device_id: str) -> str:
        """
        Unlock a smart lock.

        :param device_id: ID of the lock device
        :returns: Success or error message
        """
        if device_id not in self.devices:
            return f"Device with ID {device_id} not found."

        device = self.devices[device_id]

        if device.device_type != DeviceType.LOCK:
            return f"{device.name} is not a lock."

        device.status = DeviceStatus.UNLOCKED
        return f"✓ {device.name} unlocked."

    # Scene Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_scene(self, name: str) -> str:
        """
        Create a new scene (a collection of device states that can be activated together).

        :param name: Name of the scene (e.g., "Good Night", "Movie Time")
        :returns: scene_id of the created scene
        """
        scene = Scene(
            scene_id=uuid_hex(self.rng),
            name=name,
        )

        self.scenes[scene.scene_id] = scene
        return scene.scene_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_device_to_scene(
        self, scene_id: str, device_id: str, status: str, **additional_attrs
    ) -> str:
        """
        Add a device with specific settings to a scene.

        :param scene_id: ID of the scene
        :param device_id: ID of the device to add
        :param status: Desired status for the device in this scene (On, Off, Locked, Unlocked, etc.)
        :param additional_attrs: Additional attributes like brightness=50, temperature=72, etc.
        :returns: Success or error message
        """
        if scene_id not in self.scenes:
            return f"Scene with ID {scene_id} not found."

        if device_id not in self.devices:
            return f"Device with ID {device_id} not found."

        scene = self.scenes[scene_id]
        device = self.devices[device_id]

        device_state = {"status": status}
        device_state.update(additional_attrs)

        scene.device_states[device_id] = device_state

        return f"✓ {device.name} added to scene '{scene.name}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def activate_scene(self, scene_id: str) -> str:
        """
        Activate a scene, applying all device states configured in it.

        :param scene_id: ID of the scene to activate
        :returns: Success or error message with details of applied changes
        """
        if scene_id not in self.scenes:
            return f"Scene with ID {scene_id} not found."

        scene = self.scenes[scene_id]
        results = []

        for device_id, device_state in scene.device_states.items():
            if device_id not in self.devices:
                results.append(f"⚠️ Device {device_id} not found, skipping.")
                continue

            device = self.devices[device_id]

            # Apply status
            if "status" in device_state:
                try:
                    device.status = DeviceStatus[device_state["status"].upper()]
                except KeyError:
                    results.append(f"⚠️ Invalid status for {device.name}, skipping.")
                    continue

            # Apply additional attributes
            for attr, value in device_state.items():
                if attr != "status" and hasattr(device, attr):
                    setattr(device, attr, value)

            results.append(f"✓ {device.name}: {device.status.value}")

        return f"Scene '{scene.name}' activated:\n" + "\n".join(results)

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_scenes(self) -> str:
        """
        List all scenes.

        :returns: String representation of all scenes
        """
        if not self.scenes:
            return "No scenes found."

        result = f"Found {len(self.scenes)} scene(s):\n\n"
        for scene in self.scenes.values():
            result += str(scene) + "\n" + "-" * 40 + "\n"

        return result

    # Automation Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_automation(
        self, name: str, trigger_type: str, trigger_value: str
    ) -> str:
        """
        Create a new automation.

        :param name: Name of the automation
        :param trigger_type: Type of trigger: time, location, device, sensor
        :param trigger_value: Trigger value (e.g., "7:00 AM", "arrive home")
        :returns: automation_id of the created automation
        """
        automation = Automation(
            automation_id=uuid_hex(self.rng),
            name=name,
            trigger_type=trigger_type,
            trigger_value=trigger_value,
        )

        self.automations[automation.automation_id] = automation
        return automation.automation_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def disable_automation(self, automation_id: str) -> str:
        """
        Disable an automation.

        :param automation_id: ID of the automation to disable
        :returns: Success or error message
        """
        if automation_id not in self.automations:
            return f"Automation with ID {automation_id} not found."

        automation = self.automations[automation_id]
        automation.is_enabled = False

        return f"✓ Automation '{automation.name}' disabled."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_automations(self) -> str:
        """
        List all automations.

        :returns: String representation of all automations
        """
        if not self.automations:
            return "No automations found."

        result = f"Found {len(self.automations)} automation(s):\n\n"
        for automation in self.automations.values():
            result += str(automation) + "\n" + "-" * 40 + "\n"

        return result

    # Utility Functions

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_rooms(self) -> str:
        """
        List all rooms that have devices.

        :returns: List of room names
        """
        rooms = set(device.room for device in self.devices.values())

        if not rooms:
            return "No rooms found."

        result = "Rooms:\n"
        for room in sorted(rooms):
            device_count = sum(1 for d in self.devices.values() if d.room == room)
            result += f"- {room} ({device_count} device{'s' if device_count != 1 else ''})\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_critical_devices(self) -> str:
        """
        Get list of all critical devices that should not be turned off.

        :returns: List of critical devices with reasons
        """
        critical = [d for d in self.devices.values() if d.is_critical]

        if not critical:
            return "No critical devices found."

        result = f"Found {len(critical)} critical device(s):\n\n"
        for device in critical:
            result += f"🚨 {device.name} ({device.device_type.value}) in {device.room}\n"
            result += f"   Reason: {device.critical_reason}\n"
            result += "-" * 40 + "\n"

        return result
