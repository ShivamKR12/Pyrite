Rendering Pipeline
==================

Rendering millions of individual block faces in Python is impossible. Pyrite solves this using a multi-stage, highly optimized rendering pipeline utilizing OpenGL 3.3.

Greedy Meshing
--------------
Instead of rendering 6 faces for every block, Pyrite utilizes a Greedy Meshing algorithm. The Numba compiler scans the chunk 2D slice by 2D slice across the X, Y, and Z planes.

It groups adjacent, coplanar block faces of the *exact same ID and Lighting Data* into massive, single polygons. A flat grassy plain that would normally require 4,096 separate quads is compressed into a single massive quad, drastically reducing the vertex payload sent to the GPU.

**The 32-bit Vertex Payload:**
To minimize GPU bandwidth, vertex data is heavily bit-packed into a single 32-bit integer:
`x: 6-bit, y: 6-bit, z: 6-bit, voxel_id: 8-bit, face_id: 3-bit, ao_id: 2-bit, flip_id: 1-bit`

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
Pyrite simulates soft shadows in the corners of blocks using Vertex-based Ambient Occlusion (AO). The engine checks the adjacent diagonal blocks of a face during meshing. Depending on how many blocks surround the corner, it assigns an `ao_id` (0 to 3). The shader interpolates this value across the face to create a smooth darkening effect.
