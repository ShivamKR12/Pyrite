---
name: pyrite-graphics
description: Strict guidelines and rendering context for AI agents modifying the Pyrite graphics pipeline.
---

# Pyrite Graphics & Shaders

When generating, modifying, or debugging shaders and graphics code in Pyrite, you must adhere to the following rules:

## 1. Texture Array Management
Pyrite uses 2D Texture Arrays to avoid texture binding overhead during chunk rendering.
- **Uniform:** `sampler2DArray u_texture_array_0` in `chunk.frag`.
- **Mapping:** Textures are mapped using `u_texture_map[256]`. Block IDs correspond to an index in this map, which returns the layer in the texture array.
- **DO NOT** attempt to bind individual 2D textures for standard blocks.

## 2. Vertex Data Layout
The Greedy Mesher packs vertex data to minimize VRAM usage.
- **Position & UVs:** Often packed together.
- **Normal:** Passed via a simple integer or compressed byte rather than a full `vec3` where possible.
- **Lighting:** Voxel light levels (0-15) are passed as vertex attributes and interpolated.

## 3. Generative UI Translation
When instructed to build a UI, do not write raw HTML/CSS for the final implementation.
- Use `src/ui/components.py`.
- Instantiate `VBox`, `Button`, and `TextInput` components.
- Rely on `ui_block.frag` and `ui_text.frag` for rendering.

## 4. Architectural Checks
If proposing changes to the rendering pipeline, you MUST refer to `docs/ARCHITECTURE.md` to ensure your data flow matches the `World` -> `mesh_queue` -> `VAO/VBO` pipeline.
