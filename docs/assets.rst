.. _assets:

================================
Assets (Textures, Models, Icons)
================================

This guide explains the repository asset layout, texture atlas/array pipeline, model conventions, and recommended formats and sizes for artists and tools.

Folder layout
-------------

- `assets/textures/` — block textures, effects, atlases, and arrays. Textures used by the renderer are packed into a GPU `2D Texture Array`.
- `assets/textures/arrays/` — generated texture arrays (created by tools/scripts).
- `assets/textures/atlases/` — legacy or editor atlases.
- `assets/models/` — Wavefront `.obj` models and `.mtl` material files used for items and special objects.
- `assets/icons/` — inventory and UI icons (PNG preferred).

Primary tooling
---------------

- `create_texture_array.py` / `append_texture.py` — scripts in repository root used to assemble 2D texture arrays and atlases. Run these when adding new block textures.

Texture conventions
-------------------

- Tile size: textures are expected to share a consistent tile size (e.g., 16×16, 32×32). Check the existing assets to match the project's atlas size.
- Texture Array: the engine maps `voxel_id` → `texture layer index` at startup. See `src/textures.py` and `src/shader_program.py` for the mapping mechanism.
- Mipmaps: generate mipmaps for texture arrays to improve distant LOD rendering.
- Alpha: use premultiplied alpha if blending artifacts appear; ensure shaders expect the chosen alpha convention.

Models
------

- Format: Wavefront `.obj` with a matching `.mtl` for materials.
- Scale & origin: models should be authored in world units; the import pipeline expects item models to be small (roughly 0.5–2.0 units) and centered at origin.
- Normals/UVs: export per-vertex normals and unwrapped UVs. The engine expects UVs in 0.0–1.0 range and uses the global texture array for texturing.

Icons & UI images
------------------

- Use PNG with alpha for UI; keep sizes small (e.g., 64×64 or 128×128) to conserve memory.
- When adding new icons, update the UI texture packing if applicable and the `u_texture_map` in shader bindings.

Adding or updating assets
-------------------------

1. Place source art in a clear subfolder under `assets/`.
2. If adding textures, run `create_texture_array.py` to integrate new tiles into the texture array.
3. Update mappings in `src/textures.py` or the texture manifest (if present).
4. Test in-game to verify UVs, atlas layer indices, and shading.

Versioning and artist workflow
------------------------------

- Keep source PSD/EXR files (layered) outside `assets/` in an artist repo; commit generated atlases/arrays only when necessary.
- Document texture IDs and changes in a simple manifest (e.g., `assets/textures/README.md`) for consistency between artists and engine.
