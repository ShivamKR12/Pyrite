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
        # Store a reference to the main application context so we can access config and global state
        self.app: Any = app

        # Initialize the pygame mixer module which handles all audio hardware interfacing
        pg.mixer.init()
        # Allocate 32 distinct audio channels so we don't drop sounds when many blocks break at once
        pg.mixer.set_num_channels(32)

        # Helper function to load a sound file from disk, convert it to a pygame Sound object
        def load(filename: str) -> pg.mixer.Sound:
            # Resolve the absolute path to the asset using our path utility, then load the .ogg file
            s: pg.mixer.Sound = pg.mixer.Sound(get_path(f'assets/audio/blocks/{filename}'))
            # Return the loaded sound object back to the caller
            return s

        # Dictionary to store all our sound categories mapped to voxel block IDs
        self.sounds: Dict[int, Dict[str, List[pg.mixer.Sound]]] = {}

        # Load sound assets for SAND blocks
        # We store lists of sounds for different actions to provide variation and reduce audio fatigue
        self.sounds[SAND] = {
            # Load 4 different digging sounds (when the block is fully broken)
            'break': [load(f'sand/Sand_dig{i}.ogg') for i in range(1, 5)],
            # Load 4 different placement sounds (which reuse the dig sounds for sand)
            'place': [load(f'sand/Sand_dig{i}.ogg') for i in range(1, 5)],
            # Load 5 different continuous mining sounds (played progressively while holding click)
            'breaking': [load(f'sand/Sand_mining{i}.ogg') for i in range(1, 6)],
            # Load 4 different jump/landing sounds
            'jump': [load(f'sand/Sand_hit{i}.ogg') for i in range(1, 5)],
            # Load 5 different footstep sounds for walking on this material
            'walk': [load(f'sand/Sand_hit{i}.ogg') for i in range(1, 6)],
        }

        # Load sound assets for GRASS blocks
        self.sounds[GRASS] = {
            # Load 4 digging sound variations
            'break': [load(f'grass/Grass_dig{i}.ogg') for i in range(1, 5)],
            # Reusing digging sounds for grass placement
            'place': [load(f'grass/Grass_dig{i}.ogg') for i in range(1, 5)],
            # Grass has 6 distinct mining progress sounds
            'breaking': [load(f'grass/Grass_mining{i}.ogg') for i in range(1, 7)],
            # Load 4 landing thud sounds for grass
            'jump': [load(f'grass/Grass_hit{i}.ogg') for i in range(1, 5)],
            # Grass walking has 6 step variations for highly varied footstep pacing
            'walk': [load(f'grass/Grass_hit{i}.ogg') for i in range(1, 7)],
        }

        # Load sound assets for GRAVEL blocks
        # As noted in the original code, gravel and dirt share the same sound pool
        self.sounds[GRAVEL] = {
            # 4 distinct gravel crunching sounds for breaks
            'break': [load(f'gravel/Gravel_dig{i}.ogg') for i in range(1, 5)],
            # 4 gravel crunches for placements
            'place': [load(f'gravel/Gravel_dig{i}.ogg') for i in range(1, 5)],
            # 4 continuous gravel mining scraping sounds
            'breaking': [load(f'gravel/Gravel_mining{i}.ogg') for i in range(1, 5)],
            # 4 gravel impacts when the player lands a jump
            'jump': [load(f'gravel/Gravel_hit{i}.ogg') for i in range(1, 5)],
            # 4 sequential crunching steps for walking
            'walk': [load(f'gravel/Gravel_hit{i}.ogg') for i in range(1, 5)],
        }

        # Load sound assets for STONE blocks
        self.sounds[STONE] = {
            # Stone breaking has 4 distinct cracking noises
            'break': [load(f'stone/Stone_dig{i}.ogg') for i in range(1, 5)],
            # Placement reuses the cracking noises
            'place': [load(f'stone/Stone_dig{i}.ogg') for i in range(1, 5)],
            # Stone mining takes longer so it uses 6 progressing pickaxe strike sounds
            'breaking': [load(f'stone/Stone_mining{i}.ogg') for i in range(1, 7)],
            # 6 heavy landing variations on solid rock
            'jump': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
            # 6 heavy footstep variations on stone surfaces
            'walk': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
        }

        # Load sound assets for SNOW blocks
        self.sounds[SNOW] = {
            # Snow breaking has a soft 4-variation crunch
            'break': [load(f'snow/Snow_dig{i}.ogg') for i in range(1, 5)],
            # Snow placement uses the soft crunch
            'place': [load(f'snow/Snow_dig{i}.ogg') for i in range(1, 5)],
            # Mining snow is quick so it reuses the 4 dig sounds rather than special long strikes
            'breaking': [load(f'snow/Snow_dig{i}.ogg') for i in range(1, 5)],
            # Snow landings use the soft dig sound pool as a fallback impact
            'jump': [load(f'snow/Snow_dig{i}.ogg') for i in range(1, 5)],
            # Snow walking reuses the 4 dig crunches
            'walk': [load(f'snow/Snow_dig{i}.ogg') for i in range(1, 5)],
        }

        # Leaves map directly to the GRASS sound profile for organic rustling and breaking
        self.sounds[LEAVES] = self.sounds[GRASS]

        # Load sound assets for WOOD blocks
        self.sounds[WOOD] = {
            # 4 splintering wood sounds for destruction
            'break': [load(f'wood/Wood_dig{i}.ogg') for i in range(1, 5)],
            # 4 wood thuds for placing blocks
            'place': [load(f'wood/Wood_dig{i}.ogg') for i in range(1, 5)],
            # 6 rhythmic chopping sounds for axe mining progression
            'breaking': [load(f'wood/Wood_mining{i}.ogg') for i in range(1, 7)],
            # 6 hollow landing impacts on wood
            'jump': [load(f'wood/Wood_hit{i}.ogg') for i in range(1, 7)],
            # 6 wooden creaking footsteps
            'walk': [load(f'wood/Wood_hit{i}.ogg') for i in range(1, 7)],
        }

        # Dirt uses the gravel sound configuration for gritty earth noises
        self.sounds[DIRT] = self.sounds[GRAVEL]

        # Load sound assets for GLASS blocks
        self.sounds[GLASS] = {
            # Glass has 3 unique shattering sounds when broken
            'break': [load(f'glass/Glass_dig{i}.ogg') for i in range(1, 4)],
            # Placing glass actually sounds like placing light stone (4 variations)
            'place': [load(f'stone/Stone_dig{i}.ogg') for i in range(1, 5)],
            # Mining glass uses the high pitched ice mining sounds (6 variations)
            'breaking': [load(f'ice/Ice_mining{i}.ogg') for i in range(1, 7)],
            # Jumping onto glass sounds like jumping on stone
            'jump': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
            # Walking on glass sounds like walking on stone
            'walk': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
        }

        # Wood Planks map exactly to the unrefined WOOD sound properties
        self.sounds[WOOD_PLANKS] = self.sounds[WOOD]

        # Cobblestone behaves identically to smooth STONE audibly
        self.sounds[COBBELSTONE] = self.sounds[STONE]

        # Glowstone mimics the brittle acoustic properties of GLASS
        self.sounds[GLOWSTONE] = {
            # 3 glass shatters for glowstone destruction
            'break': [load(f'glass/Glass_dig{i}.ogg') for i in range(1, 4)],
            # Placing glowstone sounds like placing stone
            'place': [load(f'stone/Stone_dig{i}.ogg') for i in range(1, 5)],
            # Mining glowstone uses the ice cracking sounds
            'breaking': [load(f'ice/Ice_mining{i}.ogg') for i in range(1, 7)],
            # Jumping on glowstone sounds like jumping on stone
            'jump': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
            # Walking on glowstone sounds like walking on stone
            'walk': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
        }

        # (Redundant entry for GLASS kept for exact parity with the original codebase structure)
        self.sounds[GLASS] = {
            # 3 glass shatters
            'break': [load(f'glass/Glass_dig{i}.ogg') for i in range(1, 4)],
            # 4 stone placement sounds
            'place': [load(f'stone/Stone_dig{i}.ogg') for i in range(1, 5)],
            # 6 ice mining sounds
            'breaking': [load(f'ice/Ice_mining{i}.ogg') for i in range(1, 7)],
            # 6 stone landing sounds
            'jump': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
            # 6 stone step sounds
            'walk': [load(f'stone/Stone_hit{i}.ogg') for i in range(1, 7)],
        }

        # Load sound assets for CACTUS blocks
        self.sounds[CACTUS] = {
            # Cactus destruction sounds like tearing cloth (4 variations)
            'break': [load(f'cloth/Cloth_dig{i}.ogg') for i in range(1, 5)],
            # Placing cactus also sounds like soft cloth
            'place': [load(f'cloth/Cloth_dig{i}.ogg') for i in range(1, 5)],
            # Mining cactus reuses the soft cloth tearing sounds
            'breaking': [load(f'cloth/Cloth_dig{i}.ogg') for i in range(1, 5)],
            # Landing on cactus makes a soft thud
            'jump': [load(f'cloth/Cloth_dig{i}.ogg') for i in range(1, 5)],
            # Walking on cactus makes soft thuds
            'walk': [load(f'cloth/Cloth_dig{i}.ogg') for i in range(1, 5)],
        }

        # Stone bricks use standard stone sounds
        self.sounds[STONE_BRICKS] = self.sounds[STONE]

        # Initialize the cyclic counter to track which step variation to play next
        self.hit_index: int = 0
        # Timestamp (in milliseconds) of the last footstep to determine if we should reset the sequence
        self.last_hit_time: int = 0
        # Keeps track of the current stage of mining (from 0 to N-1) to avoid re-triggering the same audio tick
        self.mining_index: int = -1

        # Load the distinctive item collection pop sound effect
        self.pop_sound: pg.mixer.Sound = pg.mixer.Sound(get_path('assets/audio/sfx/pickup-sound.ogg'))

        # Retrieve the user's SFX volume preference from the config, defaulting to 20 if unset
        # and immediately apply this volume to all loaded sound buffers in memory
        self.set_sfx_volume(self.app.config.get('sfx_volume', 20))

        # Define the absolute file paths for our background music tracks
        self.music_tracks: List[str] = [
            get_path('assets/audio/music/c418-aria-math-(minecraft-volume-beta).ogg'),
            get_path('assets/audio/music/c418-minecraft.ogg'),
        ]

        # Load a randomly selected music track from our track list into the pygame music streaming buffer
        pg.mixer.music.load(random.choice(self.music_tracks))
        # Fetch user music volume preference (0-100), scale it down to (0.0-1.0) and apply to the music mixer
        pg.mixer.music.set_volume(self.app.config.get('music_volume', 50) / 100.0)
        # Start streaming the background music and loop infinitely (indicated by -1)
        pg.mixer.music.play(-1)

    @global_profiler.profile_func('Sounds_SetSFXVolume')
    def set_sfx_volume(self, value: float) -> None:
        """Updates the volume for all loaded sound effects."""
        # Convert the integer percentage (0-100) into a normalized float (0.0-1.0) for the pygame API
        vol: float = value / 100.0

        # Check if the pop sound has been initialized before applying volume
        if hasattr(self, 'pop_sound'):
            # The pop sound is boosted by a factor of 5 but clamped to a maximum of 1.0 to stay audible
            self.pop_sound.set_volume(min(1.0, vol * 5.0))

        # Iterate over all block types in the sounds dictionary
        for category_dict in self.sounds.values():
            # Iterate over each action type (break, place, walk, etc.) for this block
            for sound_list in category_dict.values():
                # Iterate over all individual pygame.Sound objects within this action category
                for s in sound_list:
                    # Apply the normalized volume to this specific sound buffer
                    s.set_volume(vol)

    @global_profiler.profile_func('Sounds_PlayWalk')
    def play_walk(self, voxel_id: int) -> None:
        """
        Plays a walking footstep sound based on the material of the block the player is standing on.
        Automatically cycles through the available footstep variations.
        """
        # Fetch the current game time in milliseconds from pygame's internal clock
        current_time: int = pg.time.get_ticks()

        # If more than half a second has passed since the last step, we assume the player paused
        # and reset the footstep sequence back to the first variation
        if current_time - self.last_hit_time > 500:
            self.hit_index = 0

        # Retrieve the dictionary of sounds for this specific block material, defaulting to GRASS if unknown
        s_dict: Dict[str, List[pg.mixer.Sound]] = self.sounds.get(voxel_id, self.sounds[GRASS])
        # Get the list of footstep sounds specific to walking on this block
        hits: List[pg.mixer.Sound] = s_dict['walk']

        # Ensure our sequence index does not exceed the available sound variations; loop back if it does
        if self.hit_index >= len(hits):
            self.hit_index = 0

        # Dispatch the sound for playback on an available mixer channel automatically
        hits[self.hit_index].play()
        # Increment the index so the next step uses the next sound in the sequence
        self.hit_index += 1
        # Update our last step timestamp to the current time for gap tracking
        self.last_hit_time = current_time

    @global_profiler.profile_func('Sounds_PlayBreak')
    def play_break(self, voxel_id: int) -> None:
        """
        Plays a hard breaking sound when a block is fully destroyed.
        """
        # Retrieve the specific sound set for the broken voxel, defaulting to GRASS
        s_dict: Dict[str, List[pg.mixer.Sound]] = self.sounds.get(voxel_id, self.sounds[GRASS])
        # Randomly select one variation from the block's break sounds and play it instantly
        random.choice(s_dict['break']).play()

    @global_profiler.profile_func('Sounds_PlayPlace')
    def play_place(self, voxel_id: int) -> None:
        """
        Plays a block placement sound when adding a new block to the world.
        """
        # Fetch the sound configurations for the placed voxel type, falling back to GRASS
        s_dict: Dict[str, List[pg.mixer.Sound]] = self.sounds.get(voxel_id, self.sounds[GRASS])
        # Pick a random sound from the placement pool to break monotony and play it
        random.choice(s_dict['place']).play()

    @global_profiler.profile_func('Sounds_PlayJump')
    def play_jump(self, voxel_id: int) -> None:
        """
        Plays a jump sound when the player jumps.
        """
        # Retrieve the block-specific sound pool for the voxel jumped from (or landed on), default to GRASS
        s_dict: Dict[str, List[pg.mixer.Sound]] = self.sounds.get(voxel_id, self.sounds[GRASS])
        # Randomly choose one of the jump/landing thuds and fire it off
        random.choice(s_dict['jump']).play()

    @global_profiler.profile_func('Sounds_PlayBreaking')
    def play_breaking(self, voxel_id: int, mining_time: float, mining_duration: float) -> None:
        """
        Plays a continuous sequence of hitting sounds mapped to the progress of mining a block.
        """
        # If the block has just started being mined, reset our sequence index state machine
        if mining_time == 0.0:
            self.mining_index = -1

        # Look up the sound array for this block, defaulting to GRASS if missing
        s_dict: Dict[str, List[pg.mixer.Sound]] = self.sounds.get(voxel_id, self.sounds[GRASS])
        # Extract the sequence list specifically mapped to the continuous 'breaking' action
        mining_sounds: List[pg.mixer.Sound] = s_dict['breaking']
        # Cache the length of this sound list to properly map mining progress across it
        num_sounds: int = len(mining_sounds)

        # Calculate a normalized float (0.0 to 1.0) representing how close we are to breaking the block
        progress: float = mining_time / mining_duration
        # Multiply progress by the number of sounds to figure out which discrete segment we are currently in
        target_index: int = int(progress * num_sounds)
        # Clamp the target index to prevent array out-of-bounds access in case progress exceeds 1.0
        target_index = min(target_index, num_sounds - 1)

        # Only play a sound if we have transitioned to a new chunk of mining progress
        if target_index > self.mining_index:
            # Dispatch the progressive strike sound
            mining_sounds[target_index].play()
            # Update our state machine tracker to avoid playing this same segment again
            self.mining_index = target_index

    @global_profiler.profile_func('Sounds_PlayPlaceBlock')
    def play_place_block(self) -> None:
        """
        Plays a pop sound effect when a dropped item entity is collected and added
        to the player's inventory.
        """
        # Directly play the single preloaded pop sound object
        self.pop_sound.play()
