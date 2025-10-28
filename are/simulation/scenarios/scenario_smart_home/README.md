# Smart Home Automation Scenario 🏠

A comprehensive scenario testing AI agent capabilities in smart home automation with context-aware triggers and multi-device orchestration.

## Overview

This scenario evaluates an agent's ability to:
- Parse complex, multi-condition automation requests
- Create location and time-based triggers
- Coordinate actions across multiple smart devices
- Integrate functionality across multiple apps (HomeKit, Location, Music)
- Verify and confirm automation setup

## Scenario Task

**User Request:**
> "When I arrive home after 6pm, turn on living room lights to 70%, set thermostat to 72°F, and start playing my jazz playlist"

## Complexity Level: High

### Key Challenges:
1. **Conditional Logic**: Requires understanding AND conditions (location + time)
2. **Multi-Device Orchestration**: Coordinates 3 different device types
3. **Cross-App Integration**: Uses HomeKitApp, LocationApp, and MusicApp
4. **Context Awareness**: Must interpret "after 6pm" and "arriving home"
5. **Device Discovery**: Must identify correct devices from descriptions
6. **State Management**: Must set specific device properties (brightness: 70%, temp: 72°F)

## Components

### 1. HomeKitApp (`homekit_app.py`)

Smart home control app managing devices, scenes, and automations.

**Data Models:**
- `Device`: Smart home devices (lights, thermostats, locks, etc.)
- `Scene`: Pre-configured device states
- `Automation`: Trigger-based action sequences
- `Trigger`: Conditions that activate automations
- `Action`: Individual operations to perform

**Key Tools:**
- `add_device()`: Add smart home devices
- `list_devices()`: Query available devices
- `set_device_state()`: Control device state and properties
- `create_automation()`: Create trigger-based automations
- `create_scene()`: Define device state collections
- `activate_scene()`: Apply scene configurations

### 2. LocationApp (`location_app.py`)

User location tracking for geofencing and context awareness.

**Data Models:**
- `Location`: Named geographic locations with coordinates
- `LocationState`: User's current location state (home/away/arriving/leaving)

**Key Tools:**
- `set_home_location()`: Configure home geofence
- `get_current_location_state()`: Query location status
- `update_location_state()`: Modify location state
- `list_locations()`: View configured locations

### 3. MusicApp (`music_app.py`)

Music playback and playlist management.

**Data Models:**
- `Song`: Music tracks with metadata
- `Playlist`: Collections of songs
- `PlaybackState`: Current playback status (playing/paused/stopped)

**Key Tools:**
- `create_playlist()`: Create new playlists
- `list_playlists()`: View available playlists
- `play_playlist()`: Start playlist playback
- `get_playback_status()`: Query current playback state
- `set_volume()`: Adjust volume level

## Oracle Actions (Ground Truth)

The scenario defines 6 granular Oracle steps representing the expected agent behavior:

1. **Discovery**: List living room devices to identify target lights
2. **Discovery**: List playlists to find the jazz playlist
3. **Verification**: Confirm home location is configured
4. **Creation**: Create automation with:
   - Trigger: Location-based (arriving home after 6pm)
   - Action 1: Turn on living room light (70% brightness)
   - Action 2: Set thermostat (72°F)
   - Action 3: Play jazz playlist
5. **Verification**: List automations to confirm creation
6. **Communication**: Notify user of successful setup

## Validation Criteria

The scenario passes if:
1. ✅ An automation was created in HomeKitApp
2. ✅ Automation trigger type is "Location"
3. ✅ Trigger includes both location state ("arriving") and time condition ("after 18:00")
4. ✅ Automation has exactly 3 actions
5. ✅ Action 1: Sets living room light to "on" with brightness=70
6. ✅ Action 2: Sets thermostat with temperature=72
7. ✅ Action 3: Plays the jazz playlist (correct playlist_id)
8. ✅ Agent sent confirmation message to user

## Initial Environment State

**Devices:**
- Living Room Light (Light, brightness: 0)
- Living Room Lamp (Light, brightness: 0)
- Home Thermostat (Thermostat, temp: 68°F)
- Bedroom Light (Light, brightness: 0)
- Front Door Lock (Lock, locked: true)
- Kitchen Light (Light, brightness: 0)

**Location:**
- Home: 123 Main Street, San Francisco, CA (37.7749, -122.4194)
- Current state: away

**Music:**
- Jazz Playlist: 5 songs (Take Five, So What, My Favorite Things, Round Midnight, Blue in Green)
- Rock Classics: 1 song (Bohemian Rhapsody)

## Running the Scenario

### From Python:
```python
from are.simulation.scenarios.scenario_smart_home import SmartHomeScenario
from are.simulation.scenarios.utils.cli_utils import run_and_validate

# Run in oracle mode to verify expected behavior
run_and_validate(SmartHomeScenario())
```

### From Command Line:
```bash
# Run with a specific agent
python -m are.simulation.scenarios.scenario_smart_home.scenario
```

## Integration Testing

This scenario is designed to test:
- **Agent reasoning**: Understanding multi-condition requests
- **Tool discovery**: Finding appropriate APIs across multiple apps
- **Parameter mapping**: Converting natural language to API parameters
- **State verification**: Confirming actions were executed correctly
- **User communication**: Providing clear feedback on automation setup

## Extension Ideas

1. **Additional Triggers**: Weather-based, time-of-day schedules
2. **Scene Management**: Create and activate device scenes
3. **Conflict Resolution**: Handle overlapping automations
4. **Dynamic Conditions**: Modify automations based on user feedback
5. **Multi-User**: Different automations for different household members
6. **Energy Management**: Optimize device usage based on utility rates

## Dependencies

- `are.simulation.apps.app.App`: Base app class
- `are.simulation.scenarios.scenario.Scenario`: Base scenario class
- `are.simulation.types`: Event handling and registration
- `are.simulation.tool_utils`: Tool decorators and utilities

## License

Copyright (c) Meta Platforms, Inc. and affiliates.
