"""
Sound and music management for the game.

This module handles the loading, mixing, and playback of all audio assets,
including background music tracks, block-specific interaction sounds (mining,
placing, walking), and UI sound effects.
"""

import random
from typing import Any, Dict, List

import pygame as pg

from profiler import global_profiler
from settings import (
    CACTUS,
    COBBELSTONE,
    DIRT,
    GLASS,
    GLOWSTONE,
    GRASS,
    GRAVEL,
    LEAVES,
    SAND,
    SNOW,
    STONE,
    STONE_BRICKS,
    WOOD,
    WOOD_PLANKS,
    get_path,
)


class Sounds:
    """
    Manages all audio assets, sound effects, and background music.

    Handles loading sounds, randomizing playback for variety, and mapping specific
    blocks to their respective material sound effects.

    Args:
        app (Any): The main application context.
    """

    @global_profiler.profile_func('Sounds_Init')
    def __init__(self, app: Any) -> None:
        """
        Initializes the Pygame mixer, loads all block sounds, and starts the background music loop.
        """
        # Variable assignments
        self.app: Any = app

        # Execute expressions
        pg.mixer.init()
        pg.mixer.set_num_channels(32)

        # Define function
        def load(filename: str) -> pg.mixer.Sound:
            # Variable assignments
            # Variable assignments
            s: pg.mixer.Sound = pg.mixer.Sound(get_path(f'assets/audio/blocks/{filename}'))
            # Return result
            # Return result
            return s

        # Variable assignments
        self.sounds: Dict[int, Dict[str, List[pg.mixer.Sound]]] = {}

        self.sounds[SAND] = {
            'break': [load(f'sand/Sand_dig{i}.ogg') for i in range(1, 5)],
            'place': [load(f'sand/Sand_dig{i}.ogg') for i in range(1, 5)],
            'breaking': [load(f'sand/Sand_mining{i}.ogg') for i in range(1, 6)],
            'jump': [load(f'sand/Sand_hit{i}.ogg') for i in range(1, 5)],
            'walk': [load(f'sand/Sand_hit{i}.ogg') for i in range(1, 6)],
        }

        self.sounds[GRASS] = {
            'break': [load(f'grass/Grass_dig{i}.ogg') for i in range(1, 5)],
            'place': [load(f'grass/Grass_dig{i}.ogg') for i in range(1, 5)],
            'breaking': [load(f'grass/Grass_mining{i}.ogg') for i in range(1, 7)],
            'jump': [load(f'grass/Grass_hit{i}.ogg') for i in range(1, 5)],
            'walk': [load(f'grass/Grass_hit{i}.ogg') for i in range(1, 7)],
        }

        self.sounds[GRAVEL] = {
            'break': [load(f'gravel/Gravel_dig{i}.ogg') for i in range(1, 5)],
            'place': [load(f'gravel/Gravel_dig{i}.ogg') for i in range(1, 5)],
            'breaking': [load(f'gravel/Gravel_mining{i}.ogg') for i in range(1, 5)],
            'jump': [load(f'gravel/Gravel_hit{i}.ogg') for i in range(1, 5)],
            'walk': [load(f'gravel/Gravel_hit{i}.ogg') for i in range(1, 5)],
        }

        self.sounds[STONE] = {
            'break': [load(f'stone/Stone_dig{i}.ogg') for i in range(1, 5)],
            'place': [load(f'stone/Stone_dig{i}.ogg') for i in range(1, 5)],
            'breaking': [load(f'stone/Stone_mining{i}.ogg') for i in range(1, 7)],
            'jump': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
            'walk': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
        }

        self.sounds[SNOW] = {
            'break': [load(f'snow/Snow_dig{i}.ogg') for i in range(1, 5)],
            'place': [load(f'snow/Snow_dig{i}.ogg') for i in range(1, 5)],
            'breaking': [load(f'snow/Snow_dig{i}.ogg') for i in range(1, 5)],
            'jump': [load(f'snow/Snow_dig{i}.ogg') for i in range(1, 5)],
            'walk': [load(f'snow/Snow_dig{i}.ogg') for i in range(1, 5)],
        }

        self.sounds[LEAVES] = self.sounds[GRASS]

        self.sounds[WOOD] = {
            'break': [load(f'wood/Wood_dig{i}.ogg') for i in range(1, 5)],
            'place': [load(f'wood/Wood_dig{i}.ogg') for i in range(1, 5)],
            'breaking': [load(f'wood/Wood_mining{i}.ogg') for i in range(1, 7)],
            'jump': [load(f'wood/Wood_hit{i}.ogg') for i in range(1, 7)],
            'walk': [load(f'wood/Wood_hit{i}.ogg') for i in range(1, 7)],
        }

        self.sounds[DIRT] = self.sounds[GRAVEL]

        self.sounds[GLASS] = {
            'break': [load(f'glass/Glass_dig{i}.ogg') for i in range(1, 4)],
            'place': [load(f'stone/Stone_dig{i}.ogg') for i in range(1, 5)],
            'breaking': [load(f'ice/Ice_mining{i}.ogg') for i in range(1, 7)],
            'jump': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
            'walk': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
        }

        self.sounds[WOOD_PLANKS] = self.sounds[WOOD]

        self.sounds[COBBELSTONE] = self.sounds[STONE]

        self.sounds[GLOWSTONE] = {
            'break': [load(f'glass/Glass_dig{i}.ogg') for i in range(1, 4)],
            'place': [load(f'stone/Stone_dig{i}.ogg') for i in range(1, 5)],
            'breaking': [load(f'ice/Ice_mining{i}.ogg') for i in range(1, 7)],
            'jump': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
            'walk': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
        }

        self.sounds[GLASS] = {
            'break': [load(f'glass/Glass_dig{i}.ogg') for i in range(1, 4)],
            'place': [load(f'stone/Stone_dig{i}.ogg') for i in range(1, 5)],
            'breaking': [load(f'ice/Ice_mining{i}.ogg') for i in range(1, 7)],
            'jump': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
            'walk': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
        }

        self.sounds[CACTUS] = {
            'break': [load(f'cloth/Cloth_dig{i}.ogg') for i in range(1, 5)],
            'place': [load(f'cloth/Cloth_dig{i}.ogg') for i in range(1, 5)],
            'breaking': [load(f'cloth/Cloth_dig{i}.ogg') for i in range(1, 5)],
            'jump': [load(f'cloth/Cloth_dig{i}.ogg') for i in range(1, 5)],
            'walk': [load(f'cloth/Cloth_dig{i}.ogg') for i in range(1, 5)],
        }

        self.sounds[STONE_BRICKS] = self.sounds[STONE]

        self.hit_index: int = 0
        self.last_hit_time: int = 0
        self.mining_index: int = -1

        self.pop_sound: pg.mixer.Sound = pg.mixer.Sound(get_path('assets/audio/sfx/pickup-sound.ogg'))

        # Execute expressions
        self.set_sfx_volume(self.app.config.get('sfx_volume', 20))

        # Variable assignments
        self.music_tracks: List[str] = [
            get_path('assets/audio/music/c418-aria-math-(minecraft-volume-beta).ogg'),
            get_path('assets/audio/music/c418-minecraft.ogg'),
        ]

        # Execute expressions
        pg.mixer.music.load(random.choice(self.music_tracks))
        pg.mixer.music.set_volume(self.app.config.get('music_volume', 50) / 100.0)
        pg.mixer.music.play(-1)

    @global_profiler.profile_func('Sounds_SetSFXVolume')
    def set_sfx_volume(self, value: float) -> None:
        """Updates the volume for all loaded sound effects."""
        # Variable assignments
        vol: float = value / 100.0

        # Conditional logic
        if hasattr(self, 'pop_sound'):
            # Execute expressions
            self.pop_sound.set_volume(min(1.0, vol * 5.0))

        # Loop processing
        for category_dict in self.sounds.values():
            # Loop processing
            for sound_list in category_dict.values():
                # Loop processing
                for s in sound_list:
                    # Execute expressions
                    s.set_volume(vol)

    @global_profiler.profile_func('Sounds_PlayWalk')
    def play_walk(self, voxel_id: int) -> None:
        """
        Plays a walking footstep sound based on the material of the block the player is standing on.
        Automatically cycles through the available footstep variations.
        """
        # Variable assignments
        current_time: int = pg.time.get_ticks()

        # Conditional logic
        if current_time - self.last_hit_time > 500:
            # Variable assignments
            self.hit_index = 0

        # Variable assignments
        s_dict: Dict[str, List[pg.mixer.Sound]] = self.sounds.get(voxel_id, self.sounds[GRASS])
        hits: List[pg.mixer.Sound] = s_dict['walk']

        # Conditional logic
        if self.hit_index >= len(hits):
            # Variable assignments
            self.hit_index = 0

        # Execute expressions
        hits[self.hit_index].play()
        # Variable assignments
        self.hit_index += 1
        self.last_hit_time = current_time

    @global_profiler.profile_func('Sounds_PlayBreak')
    def play_break(self, voxel_id: int) -> None:
        """
        Plays a hard breaking sound when a block is fully destroyed.
        """
        # Variable assignments
        s_dict: Dict[str, List[pg.mixer.Sound]] = self.sounds.get(voxel_id, self.sounds[GRASS])
        # Execute expressions
        random.choice(s_dict['break']).play()

    @global_profiler.profile_func('Sounds_PlayPlace')
    def play_place(self, voxel_id: int) -> None:
        """
        Plays a block placement sound when adding a new block to the world.
        """
        # Variable assignments
        s_dict: Dict[str, List[pg.mixer.Sound]] = self.sounds.get(voxel_id, self.sounds[GRASS])
        # Execute expressions
        random.choice(s_dict['place']).play()

    @global_profiler.profile_func('Sounds_PlayJump')
    def play_jump(self, voxel_id: int) -> None:
        """
        Plays a jump sound when the player jumps.
        """
        # Variable assignments
        s_dict: Dict[str, List[pg.mixer.Sound]] = self.sounds.get(voxel_id, self.sounds[GRASS])
        # Execute expressions
        random.choice(s_dict['jump']).play()

    @global_profiler.profile_func('Sounds_PlayBreaking')
    def play_breaking(self, voxel_id: int, mining_time: float, mining_duration: float) -> None:
        """
        Plays a continuous sequence of hitting sounds mapped to the progress of mining a block.
        """
        # Conditional logic
        if mining_time == 0.0:
            # Variable assignments
            self.mining_index = -1

        # Variable assignments
        s_dict: Dict[str, List[pg.mixer.Sound]] = self.sounds.get(voxel_id, self.sounds[GRASS])
        mining_sounds: List[pg.mixer.Sound] = s_dict['breaking']
        num_sounds: int = len(mining_sounds)

        progress: float = mining_time / mining_duration
        target_index: int = int(progress * num_sounds)
        target_index = min(target_index, num_sounds - 1)

        # Conditional logic
        if target_index > self.mining_index:
            # Execute expressions
            mining_sounds[target_index].play()
            # Variable assignments
            self.mining_index = target_index

    @global_profiler.profile_func('Sounds_PlayPlaceBlock')
    def play_place_block(self) -> None:
        """
        Plays a pop sound effect when a dropped item entity is collected and added
        to the player's inventory.
        """
        # Execute expressions
        self.pop_sound.play()
