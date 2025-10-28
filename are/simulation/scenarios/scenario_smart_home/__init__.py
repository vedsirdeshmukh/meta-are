# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

"""
Smart Home Automation Scenario Package

This package contains comprehensive smart home automation scenarios that test:
- Context-aware automation creation (time + location triggers)
- Multi-device orchestration
- Cross-app integration (HomeKit, Location, Music)
- Complex conditional logic
- High-level reasoning and goal inference

Components:
- HomeKitApp: Smart home device control and automation management
- LocationApp: User location tracking for geofencing
- MusicApp: Music playback and playlist management
- SmartHomeScenario: Integration scenario testing agent capabilities
- VacationModeScenario: High-level reasoning scenario for energy/security balance
"""

from are.simulation.scenarios.scenario_smart_home.homekit_app import HomeKitApp
from are.simulation.scenarios.scenario_smart_home.location_app import LocationApp
from are.simulation.scenarios.scenario_smart_home.music_app import MusicApp
from are.simulation.scenarios.scenario_smart_home.scenario_basic_home import SmartHomeScenario
from are.simulation.scenarios.scenario_smart_home.scenario_vacation_mode import VacationModeScenario
from are.simulation.scenarios.scenario_smart_home.scenario_vacation_mode import (
    VacationModeScenario,
)

__all__ = [
    "HomeKitApp",
    "LocationApp",
    "MusicApp",
    "SmartHomeScenario",
    "VacationModeScenario",
]
