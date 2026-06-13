.. _audio:

============
Audio System
============

This page documents Pyrite's audio architecture: how sounds are organized, played, and extended.

Overview
--------

Pyrite uses Pygame's mixer for audio playback. The audio subsystem handles SFX (block break/place, footsteps), background music, and simple spatialization (left/right panning and volume falloff).

Primary implementation
----------------------

- `src/sounds.py` — main audio engine and sound mappings.
- `assets/audio/blocks/`, `assets/audio/music/`, `assets/audio/sfx/` — audio assets.

Key concepts
------------

- Channels: the engine initializes a pool of mixer channels (multiple concurrent SFX). Music uses a dedicated channel or the high-level mixer music API.
- Mapping: block voxel IDs are mapped to specific SFX sets (break, place, walk). See `src/sounds.py` for the mapping table.
- Randomization: footstep and break sounds are randomized from a small set to avoid repetition.

File formats & recommendations
------------------------------

- Use OGG or WAV. OGG is preferred for music/effects with smaller size and wide support.
- Keep short SFX under ~1s. Music tracks can be longer (ogg recommended).
- Stereo files are allowed; single-channel mono is slightly cheaper for positional panning.

How to add new sounds
---------------------

1. Add sound files into logical subfolder under `assets/audio/` (e.g., `assets/audio/blocks/dirt/`).
2. Update the mapping in `src/sounds.py` to reference the new file names or directory.
3. If adding a new block type, add its ID and mapping in the constants (see `src/settings.py` / API docs).
4. Restart the game (assets are loaded on startup) or call the loader functions from a running session.

Spatialization & volume
-----------------------

- Pyrite applies a simple distance-based attenuation and left/right panning based on the relative position between the sound source and the listener (player). See `src/sounds.py` for exact attenuation curve.

API usage
---------

Typical calls available in `src/sounds.py`:

- `Sounds.play_sfx(name, pos=None, volume=1.0)` — play a short effect; pass `pos` (world vec3) for panning/attenuation.
- `Sounds.play_music(track_name, loop=True)` — start background music.
- `Sounds.set_master_volume(0.0-1.0)` — adjust global volume.

Debugging
---------

- If a sound fails to play, verify the file path is correct and the format is supported by your platform's SDL mixer backend.
- The engine logs missing mappings to the console during startup (see main logs).

Next Steps
----------

With audio integrated, review the :doc:`assets` guide to understand how Pyrite packages its textures, models, and icons into atlases for the engine to use.
