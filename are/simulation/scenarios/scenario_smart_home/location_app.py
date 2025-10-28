# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

"""
Location App for User Location Tracking

This app tracks the user's location and provides context for location-based automations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from are.simulation.apps.app import App
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import get_state_dict, type_check


class LocationState(Enum):
    """User location states"""

    HOME = "home"
    AWAY = "away"
    ARRIVING = "arriving"
    LEAVING = "leaving"


@dataclass
class Location:
    """Represents a named location"""

    name: str
    address: str
    latitude: float
    longitude: float
    radius_meters: float = 100.0  # Geofence radius

    def __str__(self):
        return f"{self.name} at {self.address}"


@dataclass
class LocationApp(App):
    """
    Location tracking app for context-aware automations.

    Tracks:
    - Current location state (home, away, arriving, leaving)
    - Named locations (home, work, etc.)
    - Location history
    """

    name: str | None = "LocationApp"
    current_state: LocationState = LocationState.AWAY
    home_location: Location | None = None
    locations: dict[str, Location] = field(default_factory=dict)
    location_history: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        super().__init__(self.name)

    # ========================================================================
    # State Management
    # ========================================================================

    def get_state(self) -> dict[str, Any]:
        """Return serializable state"""
        return get_state_dict(
            self, ["current_state", "home_location", "locations", "location_history"]
        )

    def load_state(self, state_dict: dict[str, Any]):
        """Restore state from saved data"""
        self.current_state = LocationState(
            state_dict.get("current_state", "away")
        )

        home_data = state_dict.get("home_location")
        if home_data:
            self.home_location = Location(
                name=home_data["name"],
                address=home_data["address"],
                latitude=home_data["latitude"],
                longitude=home_data["longitude"],
                radius_meters=home_data.get("radius_meters", 100.0),
            )

        self.locations = {}
        for name, loc_data in state_dict.get("locations", {}).items():
            self.locations[name] = Location(
                name=loc_data["name"],
                address=loc_data["address"],
                latitude=loc_data["latitude"],
                longitude=loc_data["longitude"],
                radius_meters=loc_data.get("radius_meters", 100.0),
            )

        self.location_history = state_dict.get("location_history", [])

    def reset(self):
        """Reset app to initial state"""
        super().reset()
        self.current_state = LocationState.AWAY
        self.home_location = None
        self.locations = {}
        self.location_history = []

    # ========================================================================
    # Location Management Tools
    # ========================================================================

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_home_location(
        self, name: str, address: str, latitude: float, longitude: float
    ) -> str:
        """
        Set the user's home location for geofencing.

        :param name: Name of the location (e.g., "Home")
        :param address: Street address
        :param latitude: Latitude coordinate
        :param longitude: Longitude coordinate
        :returns: Success message
        """
        self.home_location = Location(
            name=name, address=address, latitude=latitude, longitude=longitude
        )
        self.locations["home"] = self.home_location
        return f"Home location set to {name} at {address}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_location(
        self,
        name: str,
        address: str,
        latitude: float,
        longitude: float,
        radius_meters: float = 100.0,
    ) -> str:
        """
        Add a named location for tracking.

        :param name: Name of the location (e.g., "Work", "Gym")
        :param address: Street address
        :param latitude: Latitude coordinate
        :param longitude: Longitude coordinate
        :param radius_meters: Geofence radius in meters
        :returns: Success message
        """
        location = Location(
            name=name,
            address=address,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
        )
        self.locations[name.lower()] = location
        return f"Added location '{name}' at {address}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_current_location_state(self) -> str:
        """
        Get the current location state.

        :returns: Current location state (home, away, arriving, leaving)
        """
        return self.current_state.value

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_home_location(self) -> dict[str, Any]:
        """
        Get the configured home location.

        :returns: Home location details
        """
        if not self.home_location:
            raise ValueError("Home location not configured")

        return {
            "name": self.home_location.name,
            "address": self.home_location.address,
            "latitude": self.home_location.latitude,
            "longitude": self.home_location.longitude,
        }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_locations(self) -> list[dict[str, Any]]:
        """
        List all configured locations.

        :returns: List of location details
        """
        return [
            {
                "name": loc.name,
                "address": loc.address,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "radius_meters": loc.radius_meters,
            }
            for loc in self.locations.values()
        ]

    # ========================================================================
    # Location State Updates (typically triggered by system/environment)
    # ========================================================================

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def update_location_state(self, new_state: str) -> str:
        """
        Update the current location state.
        This would typically be called by the environment/system, not the agent.

        :param new_state: New location state (home, away, arriving, leaving)
        :returns: Success message
        """
        old_state = self.current_state
        self.current_state = LocationState(new_state)

        # Log the state change
        self.location_history.append(
            {
                "old_state": old_state.value,
                "new_state": self.current_state.value,
                "timestamp": None,  # Would be set by environment
            }
        )

        return f"Location state changed from {old_state.value} to {self.current_state.value}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_location_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent location state changes.

        :param limit: Maximum number of history entries to return
        :returns: List of location state changes
        """
        return self.location_history[-limit:]
