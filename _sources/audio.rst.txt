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

Pyrite currently uses a **simple spatialization model** on top of Pygame's mixer.

The audio subsystem uses:

- **Mixer channel pool:** a pool of **32 mixer channels** (see ``pg.mixer.set_num_channels(32)`` in ``src/sounds.py``). If too many SFX play at once, additional sounds may be dropped by the mixer.
- **Volume scaling:** an exposed ``sfx_volume`` value (0-100), mapped internally to a per-sample volume multiplier (see ``Sounds.set_sfx_volume()``).

In-game spatialization (distance/left-right) is supported at the engine level via the positional API. If you need the exact attenuation/panning math, treat the doc as a high-level overview unless the formulas are explicitly documented in this page.

Next Steps
----------

With audio integrated, review the :doc:`assets` guide to understand how Pyrite packages its textures, models, and icons into atlases for the engine to use.
