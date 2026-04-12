import pygame as pg
import random
from settings import *


class Sounds:
    def __init__(self, app):
        self.app = app
        pg.mixer.init()
        pg.mixer.set_num_channels(32)

        def load(filename):
            s = pg.mixer.Sound(f'sounds/{filename}')
            s.set_volume(0.2)
            return s

        self.sounds = {}
        
        # SAND
        self.sounds[SAND] = {
            'dig': [load(f"sand/Sand_dig{i}.ogg") for i in range(1, 5)],
            'hit': [load(f"sand/Sand_hit{i}.ogg") for i in range(1, 6)],
            'jump': [load(f"sand/Sand_jump{i}.ogg") for i in range(1, 5)],
            'mining': [load(f"sand/Sand_mining{i}.ogg") for i in range(1, 6)]
        }
        
        # GRASS
        self.sounds[GRASS] = {
            'dig': [load(f"grass/Grass_dig{i}.ogg") for i in range(1, 5)],
            'hit': [load(f"grass/Grass_hit{i}.ogg") for i in range(1, 7)],
            'jump': [load(f"grass/Grass_jump{i}.ogg") for i in range(1, 5)],
            'mining': [load(f"grass/Grass_mining{i}.ogg") for i in range(1, 7)]
        }
        
        # WOOD
        self.sounds[WOOD] = {
            'dig': [load(f"wood/Wood_dig{i}.ogg") for i in range(1, 5)],
            'hit': [load(f"wood/Wood_hit{i}.ogg") for i in range(1, 7)],
            'jump': [load(f"wood/Wood_jump{i}.ogg") for i in range(1, 5)],
            'mining': [load(f"wood/Wood_mining{i}.ogg") for i in range(1, 7)]
        }

        # DIRT ( gravel and dirt have the same sounds in Minecraft )
        self.sounds[DIRT] = {
            'dig': [load(f"dirt/Gravel_dig{i}.ogg") for i in range(1, 5)],
            'hit': [load(f"dirt/Gravel_hit{i}.ogg") for i in range(1, 5)],
            'jump': [load(f"dirt/Gravel_jump{i}.ogg") for i in range(1, 5)],
            'mining': [load(f"dirt/Gravel_mining{i}.ogg") for i in range(1, 5)]
        }
        
        # STONE
        self.sounds[STONE] = {
            'dig': [load(f"stone/Stone_dig{i}.ogg") for i in range(1, 5)],
            'hit': [load(f"stone/Stone_hit{i}.ogg") for i in range(1, 7)],
            'jump': [load(f"stone/Stone_jump{i}.ogg") for i in range(1, 5)],
            'mining': [load(f"stone/Stone_mining{i}.ogg") for i in range(1, 7)]
        }

        # SNOW
        self.sounds[SNOW] = {
            'dig': [load(f"snow/Snow_dig{i}.ogg") for i in range(1, 5)],
            'hit': [load(f"snow/Snow_dig{i}.ogg") for i in range(1, 5)],
            'jump': [load(f"snow/Snow_jump{i}.ogg") for i in range(1, 5)],
            'mining': [load(f"snow/Snow_dig{i}.ogg") for i in range(1, 5)]
        }

        # LEAVES
        self.sounds[LEAVES] = self.sounds[GRASS]

        self.hit_index = 0
        self.last_hit_time = 0
        self.mining_index = -1
        
        self.pop_sound = pg.mixer.Sound('sounds/pickup-sound.ogg')
        self.pop_sound.set_volume(1.0)
        
        # Background Music
        self.music_tracks = [
            'sounds/c418-aria-math-(minecraft-volume-beta).ogg',
            'sounds/c418-minecraft.ogg'
        ]
        pg.mixer.music.load(random.choice(self.music_tracks))
        pg.mixer.music.set_volume(self.app.config['volume'] / 100.0)
        pg.mixer.music.play(-1) # Loop forever in the background

    def play_hit(self, voxel_id):
        current_time = pg.time.get_ticks()
        if current_time - self.last_hit_time > 500: # Reset to 1 if you stop walking
            self.hit_index = 0
            
        s_dict = self.sounds.get(voxel_id, self.sounds[GRASS])
        hits = s_dict['hit']
        
        if self.hit_index >= len(hits):
            self.hit_index = 0
            
        hits[self.hit_index].play()
        self.hit_index += 1
        self.last_hit_time = current_time

    def play_dig(self, voxel_id):
        s_dict = self.sounds.get(voxel_id, self.sounds[GRASS])
        random.choice(s_dict['dig']).play()

    def play_jump(self, voxel_id):
        s_dict = self.sounds.get(voxel_id, self.sounds[GRASS])
        random.choice(s_dict['jump']).play()
        
    def play_mining(self, voxel_id, mining_time, mining_duration):
        if mining_time == 0.0:
            self.mining_index = -1
            
        s_dict = self.sounds.get(voxel_id, self.sounds[GRASS])
        mining_sounds = s_dict['mining']
        num_sounds = len(mining_sounds)
        
        progress = mining_time / mining_duration
        target_index = int(progress * num_sounds)
        target_index = min(target_index, num_sounds - 1)
        
        if target_index > self.mining_index:
            mining_sounds[target_index].play()
            self.mining_index = target_index

    def play_place_block(self): # Played when items pop into the player's inventory
        self.pop_sound.play()