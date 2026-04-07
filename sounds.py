import pygame as pg
import random


class Sounds:
    def __init__(self, app):
        self.app = app
        pg.mixer.init()

        # Load multiple sounds into lists!
        # Update these strings to match the exact names of your downloaded files.
        self.footsteps = [
            pg.mixer.Sound('sounds/Grass_hit1.ogg'),
            # pg.mixer.Sound('sounds/Grass_hit2.ogg'),
            # pg.mixer.Sound('sounds/Grass_hit3.ogg'),
            # pg.mixer.Sound('sounds/Grass_hit4.ogg'),
            # pg.mixer.Sound('sounds/Grass_hit5.ogg'),
            # pg.mixer.Sound('sounds/Grass_hit6.ogg')
        ]
        
        self.break_blocks = [
            pg.mixer.Sound('sounds/Grass_break.mp3'),
            # pg.mixer.Sound('sounds/Grass_dig1.ogg'),
            # pg.mixer.Sound('sounds/Grass_dig2.ogg'),
            # pg.mixer.Sound('sounds/Grass_dig3.ogg'),
            # pg.mixer.Sound('sounds/Grass_dig4.ogg')
        ]
        
        self.jumps = [
            pg.mixer.Sound('sounds/Grass_jump1.wav.mp3'),
            # pg.mixer.Sound('sounds/Grass_jump2.wav.mp3'),
            # pg.mixer.Sound('sounds/Grass_jump3.wav.mp3'),
            # pg.mixer.Sound('sounds/Grass_jump4.wav.mp3')
        ]
        
        self.mining = [
            # pg.mixer.Sound('sounds/Grass_mining1.ogg'),
            pg.mixer.Sound('sounds/Grass_mining2.ogg'),
            # pg.mixer.Sound('sounds/Grass_mining3.ogg.mp3'),
            # pg.mixer.Sound('sounds/Grass_mining4.ogg'),
            # pg.mixer.Sound('sounds/Grass_mining5.ogg'),
            # pg.mixer.Sound('sounds/Grass_mining6.ogg')
        ]

        for sound in self.footsteps + self.jumps + self.mining:
            sound.set_volume(0.2)

    def play_footstep(self):
        random.choice(self.footsteps).play()

    def play_break_block(self):
        random.choice(self.break_blocks).play()

    def play_jump(self):
        random.choice(self.jumps).play()
        
    def play_mining(self):
        random.choice(self.mining).play()

    def play_place_block(self):
        random.choice(self.footsteps).play()