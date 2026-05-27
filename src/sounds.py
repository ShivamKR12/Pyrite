import pygame as pg
import random
from settings import *
from profiler import global_profiler


class Sounds:
    """
    Manages all audio assets, sound effects, and background music.
    Handles loading sounds, randomizing playback for variety, and mapping specific
    blocks to their respective material sound effects.
    """
    @global_profiler.profile_func("Sounds_Init")
    def __init__(self, app):
        """
        Initializes the Pygame mixer, loads all block sounds, and starts the background music loop.
        """
        self.app = app
        
        pg.mixer.init()
        pg.mixer.set_num_channels(32)

        def load(filename):
            s = pg.mixer.Sound(get_path(f'assets/sounds/{filename}'))
            return s

        self.sounds = {}
        
        # SAND
        self.sounds[SAND] = {
            'break': [load(f"sand/Sand_dig{i}.ogg") for i in range(1, 5)],
            'place': [load(f"sand/Sand_dig{i}.ogg") for i in range(1, 5)],
            'breaking': [load(f"sand/Sand_mining{i}.ogg") for i in range(1, 6)],
            'jump': [load(f"sand/Sand_hit{i}.ogg") for i in range(1, 5)],
            'walk': [load(f"sand/Sand_hit{i}.ogg") for i in range(1, 6)]
        }
        
        # GRASS
        self.sounds[GRASS] = {
            'break': [load(f"grass/Grass_dig{i}.ogg") for i in range(1, 5)],
            'place': [load(f"grass/Grass_dig{i}.ogg") for i in range(1, 5)],
            'breaking': [load(f"grass/Grass_mining{i}.ogg") for i in range(1, 7)],
            'jump': [load(f"grass/Grass_hit{i}.ogg") for i in range(1, 5)],
            'walk': [load(f"grass/Grass_hit{i}.ogg") for i in range(1, 7)]
        }

        # GRAVEL ( gravel and dirt have the same sounds in Minecraft )
        self.sounds[GRAVEL] = {
            'break': [load(f"gravel/Gravel_dig{i}.ogg") for i in range(1, 5)],
            'place': [load(f"gravel/Gravel_dig{i}.ogg") for i in range(1, 5)],
            'breaking': [load(f"gravel/Gravel_mining{i}.ogg") for i in range(1, 5)],
            'jump': [load(f"gravel/Gravel_hit{i}.ogg") for i in range(1, 5)],
            'walk': [load(f"gravel/Gravel_hit{i}.ogg") for i in range(1, 5)]
        }
        
        # STONE
        self.sounds[STONE] = {
            'break': [load(f"stone/Stone_dig{i}.ogg") for i in range(1, 5)],
            'place': [load(f"stone/Stone_dig{i}.ogg") for i in range(1, 5)],
            'breaking': [load(f"stone/Stone_mining{i}.ogg") for i in range(1, 7)],
            'jump': [load(f"stone/Stone_hit{i}.ogg") for i in range(1, 7)],
            'walk': [load(f"stone/Stone_hit{i}.ogg") for i in range(1, 7)]
        }

        # SNOW
        self.sounds[SNOW] = {
            'break': [load(f"snow/Snow_dig{i}.ogg") for i in range(1, 5)],
            'place': [load(f"snow/Snow_dig{i}.ogg") for i in range(1, 5)],
            'breaking': [load(f"snow/Snow_dig{i}.ogg") for i in range(1, 5)],
            'jump': [load(f"snow/Snow_dig{i}.ogg") for i in range(1, 5)],
            'walk': [load(f"snow/Snow_dig{i}.ogg") for i in range(1, 5)]
        }

        # LEAVES
        self.sounds[LEAVES] = self.sounds[GRASS]
        
        # WOOD
        self.sounds[WOOD] = {
            'break': [load(f"wood/Wood_dig{i}.ogg") for i in range(1, 5)],
            'place': [load(f"wood/Wood_dig{i}.ogg") for i in range(1, 5)],
            'breaking': [load(f"wood/Wood_mining{i}.ogg") for i in range(1, 7)],
            'jump': [load(f"wood/Wood_hit{i}.ogg") for i in range(1, 7)],
            'walk': [load(f"wood/Wood_hit{i}.ogg") for i in range(1, 7)]
        }

        # DIRT
        self.sounds[DIRT] = self.sounds[GRAVEL]

        # GLASS
        self.sounds[GLASS] = {
            'break': [load(f"glass/Glass_dig{i}.ogg") for i in range(1, 4)],
            'place': [load(f"stone/Stone_dig{i}.ogg") for i in range(1, 5)],
            'breaking': [load(f"ice/Ice_mining{i}.ogg") for i in range(1, 7)],
            'jump': [load(f"stone/Stone_hit{i}.ogg") for i in range(1, 7)],
            'walk': [load(f"stone/Stone_hit{i}.ogg") for i in range(1, 7)]
        }

        # WOOD PLANKS
        self.sounds[WOOD_PLANKS] = self.sounds[WOOD]

        # COBBELSTONE
        self.sounds[COBBELSTONE] = self.sounds[STONE]
        
        # GLOWSTONE
        self.sounds[GLOWSTONE] = {
            'break': [load(f"glass/Glass_dig{i}.ogg") for i in range(1, 4)],
            'place': [load(f"stone/Stone_dig{i}.ogg") for i in range(1, 5)],
            'breaking': [load(f"ice/Ice_mining{i}.ogg") for i in range(1, 7)],
            'jump': [load(f"stone/Stone_hit{i}.ogg") for i in range(1, 7)],
            'walk': [load(f"stone/Stone_hit{i}.ogg") for i in range(1, 7)]
        }

        # GLASS
        self.sounds[GLASS] = {
            'break': [load(f"glass/Glass_dig{i}.ogg") for i in range(1, 4)],
            'place': [load(f"stone/Stone_dig{i}.ogg") for i in range(1, 5)],
            'breaking': [load(f"ice/Ice_mining{i}.ogg") for i in range(1, 7)],
            'jump': [load(f"stone/Stone_hit{i}.ogg") for i in range(1, 7)],
            'walk': [load(f"stone/Stone_hit{i}.ogg") for i in range(1, 7)]
        }

        # CACTUS
        self.sounds[CACTUS] = {
            'break': [load(f"cloth/Cloth_dig{i}.ogg") for i in range(1, 5)],
            'place': [load(f"cloth/Cloth_dig{i}.ogg") for i in range(1, 5)],
            'breaking': [load(f"cloth/Cloth_dig{i}.ogg") for i in range(1, 5)],
            'jump': [load(f"cloth/Cloth_dig{i}.ogg") for i in range(1, 5)],
            'walk': [load(f"cloth/Cloth_dig{i}.ogg") for i in range(1, 5)]
        }

        # STONE BRICKS
        self.sounds[STONE_BRICKS] = self.sounds[STONE]

        self.hit_index = 0
        self.last_hit_time = 0
        self.mining_index = -1
        
        self.pop_sound = pg.mixer.Sound(get_path('assets/sounds/others/pickup-sound.ogg'))
        
        # Apply initial SFX volume
        self.set_sfx_volume(self.app.config.get('sfx_volume', 20))
        
        # Background Music
        self.music_tracks = [
            get_path('assets/sounds/background/c418-aria-math-(minecraft-volume-beta).ogg'),
            get_path('assets/sounds/background/c418-minecraft.ogg')
        ]
        
        pg.mixer.music.load(random.choice(self.music_tracks))
        pg.mixer.music.set_volume(self.app.config.get('music_volume', 50) / 100.0)
        pg.mixer.music.play(-1) # Loop forever in the background

    @global_profiler.profile_func("Sounds_SetSFXVolume")
    def set_sfx_volume(self, val):
        """Updates the volume for all loaded sound effects."""
        vol = val / 100.0
        
        if hasattr(self, 'pop_sound'):
            self.pop_sound.set_volume(min(1.0, vol * 5.0))
        
        for category_dict in self.sounds.values():
            for sound_list in category_dict.values():
                for s in sound_list:
                    s.set_volume(vol)

    @global_profiler.profile_func("Sounds_PlayWalk")
    def play_walk(self, voxel_id):
        """
        Plays a walking footstep sound based on the material of the block the player is standing on.
        Automatically cycles through the available footstep variations.
        """
        current_time = pg.time.get_ticks()
        
        if current_time - self.last_hit_time > 500: # Reset to 1 if you stop walking
            self.hit_index = 0
            
        s_dict = self.sounds.get(voxel_id, self.sounds[GRASS])
        hits = s_dict['walk']
        
        if self.hit_index >= len(hits):
            self.hit_index = 0
            
        hits[self.hit_index].play()
        self.hit_index += 1
        self.last_hit_time = current_time

    @global_profiler.profile_func("Sounds_PlayBreak")
    def play_break(self, voxel_id):
        """
        Plays a hard breaking sound when a block is fully destroyed.
        """
        s_dict = self.sounds.get(voxel_id, self.sounds[GRASS])
        random.choice(s_dict['break']).play()
    
    @global_profiler.profile_func("Sounds_PlayPlace")
    def play_place(self, voxel_id):
        """
        Plays a block placement sound when adding a new block to the world.
        """
        s_dict = self.sounds.get(voxel_id, self.sounds[GRASS])
        random.choice(s_dict['place']).play()

    @global_profiler.profile_func("Sounds_PlayJump")
    def play_jump(self, voxel_id):
        """
        Plays a jump sound when the player jumps.
        """
        s_dict = self.sounds.get(voxel_id, self.sounds[GRASS])
        random.choice(s_dict['jump']).play()
        
    @global_profiler.profile_func("Sounds_PlayBreaking")
    def play_breaking(self, voxel_id, mining_time, mining_duration):
        """
        Plays a continuous sequence of hitting sounds mapped to the progress of mining a block.
        """
        if mining_time == 0.0:
            self.mining_index = -1
            
        s_dict = self.sounds.get(voxel_id, self.sounds[GRASS])
        mining_sounds = s_dict['breaking']
        num_sounds = len(mining_sounds)
        
        progress = mining_time / mining_duration
        target_index = int(progress * num_sounds)
        target_index = min(target_index, num_sounds - 1)
        
        if target_index > self.mining_index:
            mining_sounds[target_index].play()
            self.mining_index = target_index

    @global_profiler.profile_func("Sounds_PlayPlaceBlock")
    def play_place_block(self):
        """
        Plays a pop sound effect when a dropped item entity is collected and added 
        to the player's inventory.
        """
        self.pop_sound.play()
