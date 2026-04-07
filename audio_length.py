import pygame

pygame.mixer.init()

sounds = [
    "Grass_break.mp3",
    "Grass_dig1.ogg",
    "Grass_dig2.ogg",
    "Grass_dig3.ogg",
    "Grass_dig4.ogg",
    "Grass_hit1.ogg",
    "Grass_hit2.ogg",
    "Grass_hit3.ogg",
    "Grass_hit4.ogg",
    "Grass_hit5.ogg",
    "Grass_hit6.ogg",
    "Grass_jump1.wav.mp3",
    "Grass_jump2.wav.mp3",
    "Grass_jump3.wav.mp3",
    "Grass_jump4.wav.mp3",
    "Grass_mining1.ogg",
    "Grass_mining2.ogg",
    "Grass_mining3.ogg.mp3",
    "Grass_mining4.ogg",
    "Grass_mining5.ogg",
    "Grass_mining6.ogg"
]

for sound in sounds:
    Sound = pygame.mixer.Sound(f"sounds/{sound}")
    length = Sound.get_length()
    print(f"Audio length for {sound}: {length} seconds")