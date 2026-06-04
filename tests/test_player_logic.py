"""
Unit tests for the Player entity's business logic and event handling.

This module utilizes headless testing and mocked dependencies to simulate 
user inputs and verify the underlying data structures (inventory, health, 
game state) in complete isolation from the Pygame/OpenGL rendering loops.
"""

import pytest
import pygame as pg
from pyglm import glm
from unittest.mock import MagicMock

from player import Player
from settings import MAX_HEALTH, SURVIVAL, CREATIVE


@pytest.fixture
def mock_app() -> MagicMock:
    """
    Generates a headless, mocked version of the main Pyrite application.
    Bypasses the need for an active OpenGL context or Pygame display.
    """
    app = MagicMock()
    app.config = {'fov': 70.0, 'sensitivity': 0.1}
    app.delta_time = 16.0
    # Mock the sounds subsystem so take_damage doesn't crash trying to play audio
    app.sounds = MagicMock()
    return app


def test_player_take_damage_and_respawn(mock_app: MagicMock) -> None:
    """
    Verifies that the player correctly loses health when taking damage 
    in survival mode, and triggers a full stat reset (respawn) upon death.
    """
    player = Player(mock_app, position=glm.vec3(0, 100, 0))
    player.game_mode = SURVIVAL
    
    # Test taking partial damage
    initial_health = player.health
    player.take_damage(5)
    assert player.health == initial_health - 5, "Player did not take the correct amount of damage."
    
    # Test respawn trigger when health drops to/below 0
    player.take_damage(999)
    assert player.health == MAX_HEALTH, "Player health did not reset upon respawning."
    assert player.spawn_immunity is True, "Player was not granted spawn immunity after respawning."


def test_player_handle_event_gamemode(mock_app: MagicMock) -> None:
    """
    Programmatically injects a Pygame KEYDOWN event to verify that the 
    player successfully toggles between Survival and Creative game modes.
    """
    player = Player(mock_app, position=glm.vec3(0, 100, 0))
    player.game_mode = SURVIVAL
    
    # Programmatically mock a keypress (F key)
    event = MagicMock()
    event.type = pg.KEYDOWN
    event.key = pg.K_f
    
    player.handle_event(event)
    assert player.game_mode == CREATIVE, "Player failed to toggle into Creative mode."


def test_player_handle_event_hotbar(mock_app: MagicMock) -> None:
    """
    Simulates a keyboard input (pressing the '3' key) to ensure the 
    player's hotbar index updates correctly.
    """
    player = Player(mock_app, position=glm.vec3(0, 100, 0))
    player.hotbar_index = 0
    
    event = MagicMock()
    event.type = pg.KEYDOWN
    event.key = pg.K_3
    
    player.handle_event(event)
    assert player.hotbar_index == 2, "Hotbar index did not update to 2 when pressing the '3' key."