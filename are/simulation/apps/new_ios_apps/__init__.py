# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

"""
iOS Apps Module for Agent Research Environment

This module contains implementations of various iOS apps for testing
agent interactions in iOS ecosystem scenarios.
"""

from are.simulation.apps.new_ios_apps.contacts import Contact, ContactsApp
from are.simulation.apps.new_ios_apps.messages import Conversation, Message, MessagesApp
from are.simulation.apps.new_ios_apps.homekit import HomeKitApp
from are.simulation.apps.new_ios_apps.health import HealthApp
from are.simulation.apps.new_ios_apps.fitness import FitnessApp
from are.simulation.apps.new_ios_apps.reminders import RemindersApp
from are.simulation.apps.new_ios_apps.notes import NotesApp
from are.simulation.apps.new_ios_apps.focus_modes import FocusModesApp
from are.simulation.apps.new_ios_apps.facetime import FaceTimeApp
from are.simulation.apps.new_ios_apps.phone import PhoneApp
from are.simulation.apps.new_ios_apps.music import MusicApp
from are.simulation.apps.new_ios_apps.photos import PhotosApp
from are.simulation.apps.new_ios_apps.podcasts import PodcastsApp
from are.simulation.apps.new_ios_apps.tv import TVApp
from are.simulation.apps.new_ios_apps.books import BooksApp
from are.simulation.apps.new_ios_apps.wallet import WalletApp
# from are.simulation.apps.new_ios_apps.maps import MapsApp
# from are.simulation.apps.new_ios_apps.weather import WeatherApp
# from are.simulation.apps.new_ios_apps.find_my import FindMyApp
# from are.simulation.apps.new_ios_apps.screen_time import ScreenTimeApp

__all__ = [
    "Contact",
    "ContactsApp",
    "Conversation",
    "Message",
    "MessagesApp",
    "HomeKitApp",
    "HealthApp",
    "FitnessApp",
    "RemindersApp",
    "NotesApp",
    "FocusModesApp",
    "FaceTimeApp",
    "PhoneApp",
    "MusicApp",
    "PhotosApp",
    "PodcastsApp",
    "TVApp",
    "BooksApp",
    "WalletApp",
    "MapsApp",
    "WeatherApp",
    "FindMyApp",
    "ScreenTimeApp",
]
