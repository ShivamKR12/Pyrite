.. _shaders:

=================================
Shader Systems and GLSL Breakdown
=================================

This document provides detailed explanations of Pyrite's OpenGL shaders (GLSL 3.3), including vertex and fragment processing, uniform bindings, and lighting integration. All shaders are located in ``src/shaders/``.

Shader Architecture Overview
----------------------------

Pyrite uses 10 distinct shader pairs (vertex + fragment), each rendering a specific component:

.. code-block:: text

    1. chunk.vert / chunk.frag                  → Voxel terrain (main geometry)
    2. item.vert / item.frag                    → Dropped items
    3. obj.vert / obj.frag                      → Wavefront .obj models (trees, structures)
    4. sky.vert / sky.frag                      → Procedural sky (Rayleigh scattering)
    5. clouds.vert / clouds.frag                → Procedural clouds
    6. ui_block.vert / ui_block.frag            → UI block icons (inventory, hotbar)
    7. ui_color.vert / ui_color.frag            → UI colored quads (backgrounds, menus)
    8. ui_text.vert / ui_text.frag              → Text rendering (glyph atlas)
    9. voxel_marker.vert / voxel_marker.frag    → Block selection highlight (mining indicator)
    10. quad.vert / quad.frag                   → 2D rendering (debug, UI geometry)

Chunk Shader (Main Terrain Rendering)
-------------------------------------

``chunk.vert`` - Vertex Shader

Purpose: Unpack vertex data, calculate world position, apply lighting, compute screen position.

.. code-block:: glsl

    #version 330 core

    layout (location = 0) in uint packed_data;
    layout (location = 1) in uint light_data;

    // Unpacked per-vertex
    int x, y, z;
    int ao_id;
    int flip_id;

    uniform mat4 m_proj;           // Projection matrix
    uniform mat4 m_view;           // View matrix (camera)
    uniform mat4 m_model;          // Model matrix (typically identity)
    uniform vec3 u_sun_direction;  // Sun position (normalized)

    // Output to fragment shader
    flat out int voxel_id;
    flat out int face_id;
    flat out int is_water_neighbor;
    out vec2 uv;
    out float shading;
    out vec3 frag_world_pos;
    out float sun_light;
    out float block_light;

    const float ao_values[4] = float[4](0.1, 0.25, 0.5, 1.0);

    const vec3 face_normals[6] = vec3[6](
        vec3( 0.0,  1.0,  0.0), // 0: top (+Y face)
        vec3( 0.0, -1.0,  0.0), // 1: bottom (-Y face)
        vec3( 1.0,  0.0,  0.0), // 2: right (+X face)
        vec3(-1.0,  0.0,  0.0), // 3: left (-X face)
        vec3( 0.0,  0.0, -1.0), // 4: back (-Z face)
        vec3( 0.0,  0.0,  1.0)  // 5: front (+Z face)
    );

**Unpacking Function:**

Instead of sending dozens of bytes per vertex, Pyrite sends a single 32-bit integer. The shader must manually decode this back into usable values using bitwise operations:

.. code-block:: glsl

    x = int((packed_data >> 26) & 0x3F);
    y = int((packed_data >> 20) & 0x3F);
    z = int((packed_data >> 14) & 0x3F);

* **Coordinates (x, y, z):** The bitshift (``>>``) pushes the target bits to the very right. The bitwise AND (``& 0x3F``) acts as a mask. ``0x3F`` in hexadecimal is ``63`` in decimal (or ``111111`` in binary). This strictly isolates 6 bits, returning a value from 0 to 63. Since chunks are 48x48x48, 6 bits is exactly what we need.

.. code-block:: glsl

    voxel_id = int((packed_data >> 6) & 0xFF);
    face_id  = int((packed_data >> 3) & 0x7);
    ao_id    = int((packed_data >> 1) & 0x3);
    flip_id  = int(packed_data & 0x1);

* **Attributes:** The same logic applies here. ``0xFF`` (255) isolates the 8-bit voxel ID. ``0x7`` (7) isolates the 3-bit face ID (values 0-5 for the six faces of a cube). ``0x3`` (3) grabs the 2-bit Ambient Occlusion level, and ``0x1`` simply grabs the very first bit to check if the face is diagonally flipped.

**Main Vertex Shader Logic:**

With the raw data unpacked, we calculate the vertex's visual properties before passing them to the fragment shader.

.. code-block:: glsl

    sun_light   = float((light_data >> 4) & 0xF) / 15.0;
    block_light = float(light_data & 0xF) / 15.0;

* **Light Levels:** The lighting data is sent identically to the coordinates, split into two 4-bit numbers (0-15). Dividing by ``15.0`` normalizes the light to a float between ``0.0`` and ``1.0``, which is essential for color multiplication later.

.. code-block:: glsl

    if (face_id < 2) {                          // ±X faces: use Y, Z
        uv = vec2(float(z), float(y)) / 48.0;
    } else if (face_id < 4) {                   // ±Y faces: use X, Z
        ...

* **UV Calculation:** Because Pyrite uses Greedy Meshing, we don't pass standard UV arrays. Instead, we derive UVs directly from the world dimensions of the quad. To map a 2D texture onto a 3D block face, we use the two physical axes that are coplanar with the face. For X-facing faces (left/right walls), the surface spans the Y and Z axes. We divide by ``48.0`` (the chunk size) to normalize the coordinates back to standard UV bounds (0.0 to 1.0).

.. code-block:: glsl

    if (flip_id == 1) {
        uv = vec2(1.0 - uv.x, 1.0 - uv.y);  // Reflect UV
    }

* **Diagonal UV Flip:** In greedy meshing, if lighting is heavily uneven across a quad, the diagonal cut connecting the two triangles can look harsh. The CPU calculates the brightest path and sets ``flip_id`` to rotate the quad's triangulation. If we don't invert the UVs here via ``1.0 - uv``, the texture will physically render upside-down on the flipped quad!

.. code-block:: glsl

    vec3 normal = face_normals[face_id];
    float diffuse = max(dot(normal, normalize(u_sun_direction)), 0.0);
    float base_light = 0.5 + diffuse * 0.5;

* **Diffuse Lighting:** The ``dot`` product calculates the angle between the face's surface normal and the sun. Using ``max(..., 0.0)`` ensures faces pointing away from the sun don't get negative light. We scale the directional light down (``diffuse * 0.5``) and add a permanent ambient base (``0.5``) so shadows are dark, but not pitch black.

.. code-block:: glsl

    shading = base_light * ao_values[ao_id];

* **Ambient Occlusion (AO):** ``ao_values`` is an array declared at the top of the file. It acts as a strict lookup table. If the CPU says this vertex is deeply occluded (``ao_id = 0``), we multiply the light by a massive 0.1 shadow penalty. If it's completely exposed (``ao_id = 3``), we multiply by 1.0, leaving it fully lit.

``chunk.frag`` - Fragment Shader

Purpose: Sample texture, apply lighting, handle day/night cycle, and apply fog.

**Fragment Processing:**

Once the vertex is situated, the fragment shader paints the individual pixels on screen.

.. code-block:: glsl

    int tex_layer = u_texture_map[voxel_id];
    vec4 tex_color = texture(u_texture_array_0, vec3(uv, float(tex_layer)));

* **Texture Lookups:** Pyrite does not swap textures mid-frame (that's incredibly slow). Instead, all block textures exist in a massive 3D OpenGL `Texture Array`. We query the ``u_texture_map`` uniform—which acts like a dictionary—to convert our ``voxel_id`` into a specific Z-layer index in that giant 3D atlas stack.

.. code-block:: glsl

    if (tex_color.a < 0.5) discard;

* **Alpha Masking:** For blocks like leaves or glass, any pixel with less than 50% opacity is completely skipped and not drawn to the screen.

.. code-block:: glsl

    float day_night = 0.5 + 0.5 * u_sun_direction.y;
    sun_light *= day_night;
    float light_intensity = max(sun_light, block_light);

* **Combining Light Sources:** Pyrite simulates two distinct light channels. We first scale the world's ``sun_light`` based on the time of day (derived from the sun's Y position). Then, instead of blindly adding sunlight and torchlight together (which blows out colors), we take the ``max()`` of the two. This naturally blends the warm glow of torches with the cold daylight above ground.

.. code-block:: glsl

    vec4 lit_color = tex_color * vec4(vec3(light_intensity * shading), 1.0);

* **Final Shading Application:** We multiply our raw texture color by our combined light intensity *and* our vertex-calculated ``shading`` (Diffuse + AO). This applies the hard corner shadows directly over the texture data.

.. code-block:: glsl

    float dist = length(frag_world_pos);
    float fog_factor = clamp((dist - u_fog_density) / 50.0, 0.0, u_fog_max_opacity);
    vec4 fogged = mix(lit_color, vec4(bg_color, 1.0), fog_factor);

* **Fog Blending:** To hide the harsh edges of unloaded chunks in the distance, we calculate linear fog. We find the pixel's distance from the camera, subtract the starting density, and ``clamp`` the result. ``mix()`` then linearly interpolates between our lit block color and the sky's ``bg_color`` based on that percentage.

.. code-block:: glsl

    fragColor = vec4(pow(fogged.rgb, vec3(2.2)), fogged.a);

* **Gamma Correction:** Computer monitors display colors using non-linear gamma curves. We use ``pow()`` to convert our linear math colors into the sRGB color space, resulting in deeply saturated and realistic color reproduction.

**Key Uniforms:**

.. code-block:: text

    u_texture_array_0:      256-layer 2D array texture (512x512 each layer)
    u_texture_map[256]:     Array mapping voxel ID to texture layer
    u_sun_direction:        Sun direction (affects lighting and day/night)
    u_time:                 Global time for animations (incremented each frame)
    u_fog_density:          Distance at which fog begins
    u_fog_max_opacity:      Maximum fog opacity (typically 0.85)
    u_underwater_tint:      Boolean enable/disable
    bg_color:               Background color (sky blue, RGB)

Item Shader (Dropped Items)
---------------------------

``item.vert`` - Similar to chunk.vert but for dropped item geometry.

**Vertex Processing:**

Dropped items are actual 3D entities in the world, so they must be rotated and positioned individually using a model matrix, unlike chunks which are static.

.. code-block:: glsl

    uv = in_tex_coord;
    face_id = int(in_face_id);

* **Passing Attributes:** Unlike the chunk shader, item meshes are simple and don't require bit-packing. We pass the UVs and face IDs directly.

.. code-block:: glsl

    vec3 normal = face_normals[face_id];
    float diffuse = max(dot(normal, normalize(u_sun_direction)), 0.0);
    shading = 0.5 + diffuse * 0.5;  // Ambient + diffuse

* **Basic Lighting:** Similar to the chunk shader, we compute the dot product between the face normal and the sun direction for directional lighting, adding a base ambient value of 0.5. Since items don't have ambient occlusion baked in, we just pass this shading multiplier directly.

.. code-block:: glsl

    gl_Position = m_proj * m_view * m_model * vec4(in_position, 1.0);

* **Model Transformation:** Dropped items have their own ``m_model`` matrix because they rotate, bounce, and move independently in the world. We multiply the vertex position by this matrix to position it correctly.

``item.frag`` - Same logic as chunk.frag but samples item-specific texture.

**Fragment Processing:**

.. code-block:: glsl

    int tex_layer = u_texture_map[voxel_id];
    vec4 tex_color = texture(u_texture_array_0, vec3(uv, float(tex_layer)));

    if (tex_color.a < 0.5) discard;

* **Texture Lookup & Alpha:** Reuses the global texture array and mapping to find the correct texture for the dropped item, instantly discarding invisible pixels.

.. code-block:: glsl

    vec4 lit_color = tex_color * vec4(vec3(shading), 1.0);

    // Apply fog
    float dist = length(frag_world_pos);
    float fog_factor = clamp((dist - u_fog_density) / 50.0, 0.0, u_fog_max_opacity);
    vec4 fogged = mix(lit_color, vec4(bg_color, 1.0), fog_factor);

* **Shading & Fog:** We apply the vertex-calculated shading value to the texture color, then mix it with the background sky color to match the environment's fog density so items fade out naturally in the distance.

Sky Shader (Procedural Atmosphere)
----------------------------------

``sky.vert`` - Minimalist vertex shader for full-screen quad.

**Vertex Processing:**

.. code-block:: glsl

    vec4 ray_clip = vec4(in_position, -1.0, 1.0);  // Z=-1 for far plane
    vec4 ray_eye = m_inv_proj * ray_clip;
    ray_eye = vec4(ray_eye.xy, -1.0, 0.0);         // Point at infinity

* **Ray Construction:** To draw the sky, we don't render a massive sphere. Instead, we draw a flat 2D quad over the screen. For each vertex, we calculate a "ray" shooting outwards from the camera into the world by reversing the projection matrix. Setting ``W`` and ``Z`` components to specific values creates a directional vector that points infinitely far away.

.. code-block:: glsl

    view_dir = normalize((m_inv_view * ray_eye).xyz);
    gl_Position = vec4(in_position, 0.0, 1.0);     // Full-screen quad

* **View Direction:** We multiply by the inverse view matrix to account for the camera's rotation. This ``view_dir`` is sent to the fragment shader to color the sky based on where the player is looking. ``gl_Position`` just locks the quad strictly to the 2D screen.

``sky.frag`` - Rayleigh scattering atmosphere.

**Fragment Processing:**

.. code-block:: glsl

    float sun_angle = dot(normalize(view_dir), normalize(u_sun_direction));
    float phase = 0.75 * (1.0 + sun_angle * sun_angle);

* **Rayleigh Scattering Approximation:** We calculate how close the pixel we're drawing is to the actual sun. The ``dot`` product gives us that angle, and the ``phase`` math creates a bright glowing halo that smoothly dissipates the further you look away from the sun.

.. code-block:: glsl

    float sun_height = u_sun_direction.y;  // -1 (night) to 1 (day)
    vec3 sky_color = mix(vec3(0.1, 0.1, 0.2), day_color, clamp(sun_height + 0.5, 0.0, 1.0));

* **Day/Night Cycle:** We dynamically transition the base sky color from a dark starry night blue (``0.1, 0.1, 0.2``) to the bright daylight blue depending on the sun's vertical position in the sky.

.. code-block:: glsl

    if (sun_height < 0.3) {
        sky_color = mix(sky_color, sunset_color, 0.5 * (0.3 - sun_height));
    }
    fragColor = vec4(sky_color * phase, 1.0);

* **Sunset Horizon:** If the sun is getting close to the horizon (``< 0.3``), we blend in a warm orange/red ``sunset_color``. We then multiply the final sky color by our scattering ``phase`` so the sun glow remains visible over the gradient.

Clouds Shader (Procedural)
---------------------------

``clouds.vert`` - Each cloud is a simple quad; vertex shader applies noise-based offset.

**Vertex Processing:**

.. code-block:: glsl

    world_pos.x += u_time * 0.1;  // Drift slowly
    world_pos.z += u_time * 0.05;

* **Cloud Drifting:** We continuously shift the X and Z coordinates of the cloud quad over time to simulate wind blowing them across the sky.

.. code-block:: glsl

    world_pos += player_pos;
    world_pos *= cloud_scale;
    gl_Position = m_proj * m_view * vec4(world_pos, 1.0);

* **Infinite Sky Illusion:** By adding the ``player_pos`` directly to the cloud quad, the clouds are perpetually centered above the player. They drift because of ``u_time``, but the player can never actually "reach" or outrun the cloud layer.

``clouds.frag`` - Noise-based cloud appearance.

**Fragment Processing:**

.. code-block:: glsl

    vec2 uv = gl_FragCoord.xy / 512.0;
    float noise = fract(sin(dot(uv, vec2(12.9898, 78.233))) * 43758.5453);

* **Procedural Noise:** Instead of using a heavy 2D texture for clouds, we generate pseudo-random noise directly on the GPU using the pixel's screen coordinates (``gl_FragCoord``). This math is a classic, ultra-fast GLSL random number generator trick.

.. code-block:: glsl

    vec3 cloud_color = vec3(1.0) * (0.8 + noise * 0.2);
    float day_night = 0.5 + 0.5 * u_sun_direction.y;
    cloud_color *= day_night;

* **Cloud Shading:** We base the cloud's brightness on the generated noise to give it fluffy texture, then dim the clouds globally as the sun sets.

.. code-block:: glsl

    float alpha = clamp(noise, 0.3, 0.8);
    fragColor = vec4(cloud_color, alpha);

* **Transparency:** We use the same noise value to dictate the cloud's alpha channel. The ``clamp`` ensures the clouds never become fully opaque (blocking the sky) and never vanish completely.

UI Block Shader (Inventory Icons)
---------------------------------

``ui_block.vert`` - 2D quad positioning.

**Vertex Processing:**

.. code-block:: glsl

    gl_Position = vec4(in_position * u_scale + u_offset, 0.0, 1.0);
    uv = in_tex_coord;

* **2D Positioning:** Since this is a 2D interface (inventory, hotbar), we don't need projection or view matrices. We just take a flat quad ``in_position``, scale it to the size we want, and offset it to the correct spot on the screen. The Z-axis is hardcoded to ``0.0``.

``ui_block.frag`` - Sample and display.

**Fragment Processing:**

.. code-block:: glsl

    int tex_layer = u_texture_map[voxel_id];
    vec4 color = texture(u_texture_array_0, vec3(uv, float(tex_layer)));

    if (color.a < 0.5) discard;
    fragColor = color;

* **Inventory Icons:** UI blocks reuse the exact same 3D texture array as the main 3D world. We lookup the layer for the specific block being held and render it flat onto the 2D quad.

UI Color Shader (Backgrounds, UI Quads)
---------------------------------------

``ui_color.vert`` - Simple 2D positioning.

**Vertex Processing:**

.. code-block:: glsl

    gl_Position = vec4(in_position * u_scale + u_offset, 0.0, 1.0);

* **Basic Shapes:** Used for rendering plain backgrounds, buttons, and selection frames.

**ui_color.frag** - Output uniform color.

**Fragment Processing:**

.. code-block:: glsl

    fragColor = u_color;

* **Flat Color:** Simply outputs the uniform ``u_color`` sent from Python. No lighting, no textures.

Uniform Management
------------------

All uniforms are set from Python via ModernGL's ``program`` object:

.. code-block:: python

    # Example: Setting chunk shader uniforms
    program['m_proj'].write(projection_matrix)
    program['m_view'].write(view_matrix)
    program['u_sun_direction'].value = sun_direction  # glm.vec3
    program['u_texture_map'].value = texture_map      # List[int]
    program['u_time'].value = current_time
    program['u_fog_density'].value = fog_start_distance
    program['bg_color'].value = (0.53, 0.81, 0.92)

Texture Atlas Binding
---------------------

All block textures are combined into a single ``sampler2DArray``:

.. code-block:: python

    # Load texture atlas
    atlas = ctx.texture_array(shape=(512, 512, 256), dtype='uint8')  # 256 layers, 512x512 each

    # Bind to shader
    atlas.use(location=0)
    program['u_texture_array_0'].value = 0

Debugging Tips
--------------

1. **Visualize Normals:** Replace fragment color with normal vector (for lighting issues).
2. **Show AO:** Output ao_id directly as grayscale to verify ambient occlusion.
3. **Show Lighting:** Output sun_light and block_light channels separately.

Next Steps
----------

Now that you understand the rendering pipeline and shaders, continue to the :doc:`player` documentation to understand how the user physically interacts with and navigates this 3D environment.
