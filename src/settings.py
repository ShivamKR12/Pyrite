"""
Global settings and configuration constants for the Pyrite voxel engine.

This module acts as the central repository for engine configurations, including
OpenGL parameters, camera constraints, player physics, terrain thresholds, block IDs,
color palettes, and performance caps (e.g., ThreadPool limits and VRAM pool sizes).
It also provides a helper for resolving absolute asset paths in bundled PyInstaller builds.
"""

from pyglm import glm
import math
import pygame
import os
import sys
from typing import Any, Dict, Set, Tuple


def get_path(relative_path: str) -> str:
    """Get absolute path to resource"""
    try:
        base_path: str = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.join(base_path, relative_path)


# OpenGL settings
MAJOR_VER: int = 3
MINOR_VER: int = 3
DEPTH_SIZE: int = 24
NUM_SAMPLES: int = 1  # antialiasing

# resolution
pygame.init()
info: Any = pygame.display.Info()
WIN_RES: Any = glm.vec2(info.current_w, info.current_h)
pygame.quit()

# ray casting
MAX_RAY_DIST: int = 6

# chunk
CHUNK_SIZE: int = 48
H_CHUNK_SIZE: int = CHUNK_SIZE // 2
CHUNK_AREA: int = CHUNK_SIZE * CHUNK_SIZE
CHUNK_VOL: int = CHUNK_AREA * CHUNK_SIZE
CHUNK_SPHERE_RADIUS: float = H_CHUNK_SIZE * math.sqrt(3)

# world
WORLD_W: int = 30
WORLD_H: int = 5
WORLD_D: int = WORLD_W
WORLD_AREA: int = WORLD_W * WORLD_D
WORLD_VOL: int = WORLD_AREA * WORLD_H
CENTER_XZ: float = WORLD_W * H_CHUNK_SIZE
CENTER_Y: int = 48

# camera
ASPECT_RATIO: float = WIN_RES.x / WIN_RES.y
FOV_DEG: int = 50
V_FOV: float = glm.radians(FOV_DEG)  # vertical FOV
H_FOV: float = 2 * math.atan(math.tan(V_FOV * 0.5) * ASPECT_RATIO)  # horizontal FOV
NEAR: float = 0.1
FAR: float = 2000.0
PITCH_MAX: float = glm.radians(89)

# player
PLAYER_SPEED: float = 0.005
PLAYER_ROT_SPEED: float = 0.003
PLAYER_SPRINT_MULTIPLIER: float = 1.5
PLAYER_WATER_DRAG_MULTIPLIER: float = 0.5
PLAYER_DOLPHIN_LEAP_MULTIPLIER: float = 1.05
PLAYER_UNDERWATER_GRAVITY_MULTIPLIER: float = 0.2
PLAYER_VERTICAL_WATER_DRAG: float = 0.005
PLAYER_POS: Any = glm.vec3(CENTER_XZ, CHUNK_SIZE, CENTER_XZ)
MOUSE_SENSITIVITY: float = 0.002
SPAWN_SEARCH_RADIUS: int = 500

# View Bobbing
VIEW_BOBBING_STEP_FREQUENCY: float = 2.5
VIEW_BOBBING_AMPLITUDE: float = 0.05
SPRINT_FOV_BOOST: float = 10.0  # degrees
SPRINT_FOV_LERP_SPEED: float = 0.01

# Mining
PICKAXE_MINING_MULTIPLIER: float = 5.0
BAREHAND_MINING_PENALTY: float = 5.0

# Queue Processing
MESH_BUILD_LIMIT_INGAME: int = 4
MESH_BUILD_LIMIT_LOADING: int = 64
MAIN_THREAD_MESH_PROCESS_LIMIT_INGAME: int = 2
MAIN_THREAD_MESH_PROCESS_LIMIT_LOADING: int = 10
MAIN_THREAD_CHUNK_PROCESS_LIMIT_INGAME: int = 1
MAIN_THREAD_CHUNK_PROCESS_LIMIT_LOADING: int = 10

# Memory Caps
VBO_POOL_CAP: int = 150
LIGHTING_QUEUE_SIZE: int = 200000
ITEM_ENTITY_CAP: int = 256

# RENDERING & ENVIRONMENT
DAY_NIGHT_SPEED: float = 0.01
FOG_DENSITY_BASE: float = 0.002
CLOUD_FOG_DENSITY_BASE: float = 0.000036
UNDERWATER_FOG_COLOR: Any = glm.vec3(0.0, 0.1, 0.4)
UNDERWATER_FOG_DENSITY: float = 0.0015
UNDERWATER_FOG_MAX_OPACITY: float = 0.85
ITEM_RENDER_DISTANCE_SQUARED: float = 1024.0  # 32 * 32
ITEM_SPAWN_VELOCITY_MULTIPLIER: float = 0.002

# Held Item / Viewmodel
HELD_ITEM_POS: Any = glm.vec3(0.5, -0.4, -1.0)
HELD_ITEM_BOB_OFFSET_Y_MULT: float = 0.03
HELD_ITEM_BOB_OFFSET_X_MULT: float = 0.02
HELD_ITEM_SWING_ROT_X: float = 0.4
HELD_ITEM_SWING_OFFSET_Y: float = 0.15
HELD_ITEM_SWING_OFFSET_Z: float = -0.1
HELD_ITEM_PLACE_SWING_ROTATION_X: float = 0.3
HELD_ITEM_PLACE_SWING_OFFSET_Y: float = 0.2
HELD_STICK_POS_OFFSET: Any = glm.vec3(0.0, 0.15, 0.0)
HELD_STICK_ROT_X: float = glm.radians(-45.0)
HELD_STICK_ROT_Z: float = glm.radians(90.0)
HELD_STICK_SCALE: Any = glm.vec3(0.5)
HELD_PICKAXE_POS_OFFSET: Any = glm.vec3(0.0, 0.15, 0.0)
HELD_PICKAXE_ROT_X: float = glm.radians(10.0)
HELD_PICKAXE_ROT_Z: float = glm.radians(90.0)
HELD_PICKAXE_SCALE: Any = glm.vec3(0.2)
HELD_BLOCK_ROT_X: float = glm.radians(-15.0)
HELD_BLOCK_ROT_Y: float = glm.radians(45.0)
HELD_BLOCK_SCALE: Any = glm.vec3(0.35)

# colors
BG_COLOR: Any = glm.vec3(0.58, 0.83, 0.99)

# UIDs for blocks and items
AIR: int = 0
SAND: int = 1
GRASS: int = 2
DIRT: int = 3
STONE: int = 4
SNOW: int = 5
LEAVES: int = 6
WOOD: int = 7
GRAVEL: int = 8
WOOD_PLANKS: int = 9
COBBELSTONE: int = 10
WATER: int = 11
GLOWSTONE: int = 12
GLASS: int = 13
CACTUS: int = 14
STONE_BRICKS: int = 15
# 16-32 are reserved for other blocks, 33+ are items
STICK: int = 33
WOODEN_PICKAXE: int = 34

NON_PLACEABLE: Set[int] = {STICK, WOODEN_PICKAXE}

# Texture Array Mapping (Global UID -> Row in tex_array_2.png)
TEXTURE_MAP: Dict[int, int] = {
    SAND: 1,
    GRASS: 2,
    DIRT: 3,
    STONE: 4,
    SNOW: 5,
    LEAVES: 6,
    WOOD: 7,
    GRAVEL: 8,
    WOOD_PLANKS: 9,
    COBBELSTONE: 10,
    WATER: 11,
    GLOWSTONE: 12,
    GLASS: 13,
    CACTUS: 14,
    STONE_BRICKS: 15,
}

# terrain levels
SNOW_LVL: int = 54
STONE_LVL: int = 49
DIRT_LVL: int = 40
GRASS_LVL: int = 8
SAND_LVL: int = 7

# tree settings
TREE_PROBABILITY: float = 0.02
TREE_WIDTH: int = 4
TREE_HEIGHT: int = 8
TREE_H_WIDTH: int = TREE_WIDTH // 2
TREE_H_HEIGHT: int = TREE_HEIGHT // 2

# block hardness (ms to break)
BLOCK_HARDNESS: Dict[int, int] = {
    SAND: 300,
    GRASS: 450,
    DIRT: 400,
    STONE: 1500,
    SNOW: 200,
    LEAVES: 150,
    WOOD: 1000,
    WATER: 0,  # Water can't be normally mined
    GLOWSTONE: 100,
    GLASS: 100,
    CACTUS: 150,
    STONE_BRICKS: 1500,
}

# game modes
CREATIVE: int = 0
SURVIVAL: int = 1

# player interaction
INTERACTION_DELAY: int = 150  # ms delay for continuous mining/placing

# ui
HOTBAR_SCALE: float = 0.045
SLOT_SCALE: float = 0.05
HOTBAR_SPACING: float = 0.1
HOTBAR_Y: float = -0.85

# water
WATER_LINE: int = 6
WATER_AREA: int = 5 * CHUNK_SIZE * WORLD_W

# cloud
CLOUD_SCALE: int = 25
CLOUD_HEIGHT: int = 200

PLAYER_WIDTH: float = 0.6
PLAYER_HEIGHT: float = 1.8
PLAYER_HALF_W: float = PLAYER_WIDTH / 2
PLAYER_EYE_HEIGHT: float = 1.6

GRAVITY: float = -0.000025
JUMP_VELOCITY: float = 0.0095

# survival mechanics
MAX_HEALTH: int = 20
MAX_HUNGER: int = 20
MAX_OXYGEN: int = 20
FALL_DAMAGE_THRESHOLD: float = 3.0
VOID_DEATH_Y: int = -20
VOID_DAMAGE: int = 4
VOID_DAMAGE_INTERVAL: int = 500
HUNGER_DRAIN_SPRINT: float = 0.002
HUNGER_DRAIN_WALK: float = 0.0005
OXYGEN_LOSE_TIMER: int = 1000
OXYGEN_GAIN_TIMER: int = 200

# inventory
INVENTORY_SIZE: int = 41  # 36 main + 4 crafting grid + 1 output
HOTBAR_SIZE: int = 9

# item drops
ITEM_PICKUP_RADIUS: float = 2.5
ITEM_PICKUP_DELAY: int = 200
ITEM_SCALE: float = 0.25

# ui palette & fonts
FONT_SIZE_STATS: int = 20
FONT_SIZE_SLIDERS: int = 30
FONT_SIZE_BUTTONS: int = 40
FONT_SIZE_SUBTITLE: int = 60
FONT_SIZE_LOADING: int = 140
FONT_SIZE_PAUSED: int = 160
FONT_SIZE_TITLE: int = 180
FONT_SIZE_DEBUG: int = 18

UI_BG_COLOR: Tuple[float, float, float, float] = (0.85, 0.85, 0.85, 0.5)
# UI_BG_COLOR = (0.1, 0.12, 0.15, 0.7)
UI_HOVER_COLOR: Tuple[float, float, float, float] = (0.85, 0.65, 0.13, 0.9)  # Pyrite Gold
UI_BUTTON_COLOR: Tuple[float, float, float, float] = (0.15, 0.20, 0.25, 0.9)  # Slate Blue
UI_SLOT_BG_COLOR: Tuple[float, float, float, float] = (0.2, 0.2, 0.2, 0.6)
UI_SLOT_HOVER_COLOR: Tuple[float, float, float, float] = (0.9, 0.9, 0.9, 0.5)
UI_SLOT_SELECTED_FRAME_COLOR: Tuple[float, float, float, float] = (0.9, 0.9, 0.9, 0.9)
UI_SLOT_SELECTED_BG_COLOR: Tuple[float, float, float, float] = (0.5, 0.5, 0.5, 0.7)
# UI_SLOT_BG_COLOR = (0.1, 0.12, 0.15, 0.7)
# UI_SLOT_HOVER_COLOR = (0.85, 0.65, 0.13, 0.4)
# UI_SLOT_SELECTED_FRAME_COLOR = (0.85, 0.65, 0.13, 1.0)
# UI_SLOT_SELECTED_BG_COLOR = (0.15, 0.20, 0.25, 0.8)
UI_TEXT_COLOR: Tuple[int, int, int] = (245, 245, 245)
UI_SHADOW_COLOR: Tuple[int, int, int] = (15, 20, 25)
