.. _rendering:

==================
Rendering Pipeline
==================

Rendering millions of individual block faces in Python is impossible. Pyrite solves this using a multi-stage, highly optimized rendering pipeline utilizing OpenGL 3.3.

Greedy Meshing
--------------
Instead of rendering 6 faces for every block, Pyrite uses a greedy meshing algorithm to collapse many adjacent block faces into larger quads. The algorithm walks through the chunk one 2D slice at a time, examining X, Y, and Z planes in turn.

For each plane, it identifies run-length groups of faces that are coplanar, have the same block ID, and share identical lighting/occlusion state. These groups are merged into a single rectangle, which means broad surfaces such as plains, walls, or ceilings can be rendered with far fewer polygons.

This is the most important rendering optimization in the engine because Python is too slow to emit millions of individual faces every frame. By reducing the draw call and vertex counts dramatically, greedy meshing makes real-time voxel rendering viable.

**The 32-bit Vertex Payload:**
To minimize GPU bandwidth, vertex data is heavily bit-packed into a single 32-bit integer:
``x: 6-bit, y: 6-bit, z: 6-bit, voxel_id: 8-bit, face_id: 3-bit, ao_id: 2-bit, flip_id: 1-bit``

Because the mesh builder must still preserve per-face lighting and ambient occlusion, the packed vertex includes only the data needed to reconstruct face position and appearance in the vertex shader. This compact format lets Pyrite send large batches of geometry to the GPU without blowing up memory bandwidth.

By combining greedy face merging with compact vertex encoding, the renderer reduces per-chunk vertex counts from millions to tens of thousands in most scenes.

Vectorized Frustum Culling
--------------------------
Before issuing OpenGL draw calls, the engine filters out chunks that are behind the player or out of the camera's field of view.

Instead of iterating through chunks in standard Python (which creates significant overhead), Pyrite extracts all active chunk centers into a single `Nx3` Numpy array. This array is passed to a parallelized Numba JIT function (`frustum_cull_fast`) which performs vectorized dot-product math against the camera's projection planes, culling thousands of chunks in a fraction of a millisecond.

Hardware Occlusion Queries
--------------------------
If a chunk is hidden deep underground or behind a massive mountain, it shouldn't be rendered, even if it is technically inside the camera's viewing frustum.

Pyrite leverages ModernGL's hardware Occlusion Queries. For invisible chunks, the engine submits a dirt-cheap wireframe Bounding Box to the GPU. If the GPU's depth-buffer reports that 0 pixels of the bounding box were visible on screen, the engine completely skips rendering the complex, high-poly greedy mesh for that chunk on the next frame.

Multi-Pass Transparency
-----------------------
To ensure that water and glass render correctly without depth-buffer sorting issues, the engine utilizes multi-pass rendering:

1. The engine first renders all opaque geometry (Stone, Dirt, Wood).
2. The Depth Buffer is preserved, but face-culling is adjusted.
3. The engine performs a second pass, rendering transparent geometry (Water, Glass) over the existing terrain, applying a time-based UV distortion to simulate flowing waves.

Texture Atlases
---------------
To prevent expensive texture-binding swaps mid-frame, all block textures are combined into a single `2D Texture Array` using `pygame.Surface`.

In OpenGL, a global `TEXTURE_MAP` array translates the block's `voxel_id` into a specific Z-layer index in the Texture Array, allowing the Fragment Shader to instantly look up the correct texture layer dynamically.

Ambient Occlusion
-----------------
Pyrite simulates soft shadows in the corners of blocks using **vertex-based Ambient Occlusion (AO)**.

Key pipeline point:

- **AO is computed during meshing** (CPU) from the local 3D block neighborhood.
- The result is encoded into the per-vertex packed attributes.
- The **shader** then simply interpolates/apply that AO during rendering.

This keeps AO effectively free at runtime (no ray tracing / no per-frame neighborhood queries).

Why this matters: AO adds depth and visual richness to blocky geometry without full ray tracing, and it does not require per-frame overhead because it is baked into the vertex data during mesh build.


Render Flow Summary
-------------------
The renderer is not a single monolithic loop; it is a sequence of stages. In broad terms:

1. **Scene culling:** Drop chunks outside the camera frustum.
2. **Opaque pass:** Render solid geometry first, populating the depth buffer.
3. **Transparent pass:** Render water and glass on top with blending enabled.
4. **UI pass:** Render HUD and menus last with depth test disabled.

This ordered approach is what allows Pyrite to keep the visible geometry count low and still present a coherent world each frame.

Next Steps
----------

With the world rendering pipeline established, move on to the :doc:`shaders` breakdown to understand how Pyrite's GLSL programs visually construct the atmosphere and geometry on the GPU.
