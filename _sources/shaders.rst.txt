.. _shaders:

Shader Systems and GLSL Breakdown
==================================

This document provides detailed explanations of Pyrite's OpenGL shaders (GLSL 3.3), including vertex and fragment processing, uniform bindings, and lighting integration. All shaders are located in ``src/shaders/``.

Shader Architecture Overview
----------------------------

Pyrite uses 8 distinct shader pairs (vertex + fragment), each rendering a specific component:

.. code-block:: text

    1. chunk.vert / chunk.frag       → Voxel terrain (main geometry)
    2. item.vert / item.frag         → Dropped items
    3. obj.vert / obj.frag           → Wavefront .obj models (trees, structures)
    4. sky.vert / sky.frag           → Procedural sky (Rayleigh scattering)
    5. clouds.vert / clouds.frag     → Procedural clouds
    6. ui_block.vert / ui_block.frag → UI block icons (inventory, hotbar)
    7. ui_color.vert / ui_color.frag → UI colored quads (backgrounds, menus)
    8. ui_text.vert / ui_text.frag   → Text rendering (not detailed; uses glyph atlas)
    9. quad.vert / quad.frag         → Debug wireframes (frustum bounds, voxel markers)

Chunk Shader (Main Terrain Rendering)
-------------------------------------

**chunk.vert** - Vertex Shader

Purpose: Unpack vertex data, calculate world position, apply lighting, compute screen position.

.. code-block:: glsl

    #version 330 core

    layout (location = 0) in uint packed_data;
    layout (location = 1) in uint light_data;

    // Unpacked per-vertex
    int x, y, z;
    int ao_id;
    int flip_id;

    uniform mat4 m_proj;     // Projection matrix
    uniform mat4 m_view;     // View matrix (camera)
    uniform mat4 m_model;    // Model matrix (typically identity)
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
        vec3( 1,  0,  0),  // +X face
        vec3(-1,  0,  0),  // -X face
        vec3( 0,  1,  0),  // +Y face
        vec3( 0, -1,  0),  // -Y face
        vec3( 0,  0,  1),  // +Z face
        vec3( 0,  0, -1)   // -Z face
    );

**Unpacking Function:**

.. code-block:: glsl

    void unpack(uint packed_data) {
        // Extract bit fields
        x = int((packed_data >> 26) & 0x3F);
        y = int((packed_data >> 20) & 0x3F);
        z = int((packed_data >> 14) & 0x3F);
        
        voxel_id = int((packed_data >> 6) & 0xFF);
        face_id = int((packed_data >> 3) & 0x7);
        ao_id = int((packed_data >> 1) & 0x3);
        flip_id = int(packed_data & 0x1);
    }

**Main Vertex Shader Logic:**

.. code-block:: glsl

    void main() {
        unpack(packed_data);
        
        // Unpack light (4-4 bit split)
        sun_light = float((light_data >> 4) & 0xF) / 15.0;      // Normalize 0-15 to 0.0-1.0
        block_light = float(light_data & 0xF) / 15.0;
        
        // World position
        frag_world_pos = vec3(float(x), float(y), float(z));
        
        // Compute UV coordinates (0-1 within face, varies by face_id)
        if (face_id < 2) {  // ±X faces: use Y, Z
            uv = vec2(float(z), float(y)) / 48.0;
        } else if (face_id < 4) {  // ±Y faces: use X, Z
            uv = vec2(float(x), float(z)) / 48.0;
        } else {  // ±Z faces: use X, Y
            uv = vec2(float(x), float(y)) / 48.0;
        }
        
        // Apply flip_id if needed (diagonal flip for lighting optimization)
        if (flip_id == 1) {
            uv = vec2(1.0 - uv.x, 1.0 - uv.y);  // Reflect UV
        }
        
        // Compute diffuse lighting (normal dot light direction)
        vec3 normal = face_normals[face_id];
        float diffuse = max(dot(normal, normalize(u_sun_direction)), 0.0);
        
        // Combine ambient (0.5) + diffuse (0.5x intensity)
        float base_light = 0.5 + diffuse * 0.5;
        
        // Apply AO darkening (ao_values maps 0-3 to brightness factors)
        shading = base_light * ao_values[ao_id];
        
        // Screen position
        gl_Position = m_proj * m_view * m_model * vec4(frag_world_pos, 1.0);
    }

**chunk.frag** - Fragment Shader

Purpose: Sample texture, apply lighting, handle day/night cycle, and apply fog.

.. code-block:: glsl

    #version 330 core

    layout (location = 0) out vec4 fragColor;

    const vec3 gamma = vec3(2.2);
    const vec3 inv_gamma = 1.0 / gamma;

    uniform sampler2DArray u_texture_array_0;  // Texture atlas (256 layers, one per voxel ID)
    uniform vec3 bg_color;                     // Background color (sky blue)
    uniform bool u_underwater_tint;            // Apply underwater blue tint
    uniform float u_fog_density;               // Fog thickness (0.0-1.0)
    uniform float u_fog_max_opacity;           // Max fog opacity
    uniform float u_time;                      // Time in seconds (for animations)
    uniform vec3 u_sun_direction;              // Sun direction (for day/night)
    uniform int u_texture_map[256];            // Voxel ID → texture layer mapping

    in vec2 uv;
    in float shading;
    in vec3 frag_world_pos;
    in float sun_light;
    in float block_light;

    flat in int face_id;
    flat in int voxel_id;
    flat in int is_water_neighbor;

**Fragment Processing:**

.. code-block:: glsl

    void main() {
        // Get texture layer from voxel ID
        int tex_layer = u_texture_map[voxel_id];
        
        // Sample texture with 3D coordinate (u, v, layer)
        vec4 tex_color = texture(u_texture_array_0, vec3(uv, float(tex_layer)));
        
        // Discard transparent pixels (alpha < 0.5)
        if (tex_color.a < 0.5) discard;
        
        // Combine sunlight and blocklight (take max for better visuals)
        float light_intensity = max(sun_light, block_light);
        
        // Day/night cycle: multiply sunlight by time-based factor
        // Ranges 0.5 (night, u_sun_direction.y = -1) to 1.0 (day, u_sun_direction.y = 1)
        float day_night = 0.5 + 0.5 * u_sun_direction.y;
        sun_light *= day_night;
        
        light_intensity = max(sun_light, block_light);
        
        // Apply ambient occlusion (via shading variable from vertex shader)
        vec4 lit_color = tex_color * vec4(vec3(light_intensity * shading), 1.0);
        
        // Apply fog (linear fog)
        float dist = length(frag_world_pos);  // Distance from camera (simplified)
        float fog_factor = clamp((dist - u_fog_density) / 50.0, 0.0, u_fog_max_opacity);
        vec4 fogged = mix(lit_color, vec4(bg_color, 1.0), fog_factor);
        
        // Apply underwater tint if enabled and in water
        if (u_underwater_tint && is_water_neighbor > 0) {
            fogged = mix(fogged, vec4(0.2, 0.5, 1.0, 1.0), 0.3);  // Blue tint, 30% opacity
        }
        
        // Gamma correction (convert from linear to sRGB for display)
        fragColor = vec4(pow(fogged.rgb, gamma), fogged.a);
    }

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

**item.vert** - Similar to chunk.vert but for dropped item geometry.

.. code-block:: glsl

    #version 330 core

    layout (location = 0) in vec3 in_position;
    layout (location = 1) in vec2 in_tex_coord;
    layout (location = 2) in float in_face_id;

    uniform mat4 m_proj;
    uniform mat4 m_view;
    uniform mat4 m_model;     // Item-specific transform (position, rotation, scale)
    uniform vec3 u_sun_direction;

    out vec2 uv;
    flat out int face_id;
    out float shading;

    const vec3 face_normals[6] = vec3[6](...);

    void main() {
        uv = in_tex_coord;
        face_id = int(in_face_id);
        
        vec3 normal = face_normals[face_id];
        float diffuse = max(dot(normal, normalize(u_sun_direction)), 0.0);
        shading = 0.5 + diffuse * 0.5;  // Ambient + diffuse
        
        gl_Position = m_proj * m_view * m_model * vec4(in_position, 1.0);
    }

**item.frag** - Same logic as chunk.frag but samples item-specific texture.

.. code-block:: glsl

    #version 330 core

    layout (location = 0) out vec4 fragColor;

    uniform sampler2DArray u_texture_array_0;
    uniform int voxel_id;          // Current item ID
    uniform vec3 bg_color;
    uniform float u_fog_density;
    uniform float u_fog_max_opacity;
    uniform int u_texture_map[256];

    in vec2 uv;
    flat out int face_id;
    in float shading;

    const vec3 gamma = vec3(2.2);
    const vec3 inv_gamma = 1.0 / gamma;

    void main() {
        int tex_layer = u_texture_map[voxel_id];
        vec4 tex_color = texture(u_texture_array_0, vec3(uv, float(tex_layer)));
        
        if (tex_color.a < 0.5) discard;
        
        vec4 lit_color = tex_color * vec4(vec3(shading), 1.0);
        
        // Apply fog (same as chunk shader)
        float dist = length(frag_world_pos);
        float fog_factor = clamp((dist - u_fog_density) / 50.0, 0.0, u_fog_max_opacity);
        vec4 fogged = mix(lit_color, vec4(bg_color, 1.0), fog_factor);
        
        fragColor = vec4(pow(fogged.rgb, gamma), fogged.a);
    }

Sky Shader (Procedural Atmosphere)
----------------------------------

**sky.vert** - Minimalist vertex shader for full-screen quad.

.. code-block:: glsl

    #version 330 core

    layout (location = 0) in vec2 in_position;

    out vec3 view_dir;

    uniform mat4 m_inv_proj;   // Inverse projection matrix
    uniform mat4 m_inv_view;   // Inverse view matrix

    void main() {
        // Construct ray direction from NDC position to world space
        vec4 ray_clip = vec4(in_position, -1.0, 1.0);  // Z=-1 for far plane
        vec4 ray_eye = m_inv_proj * ray_clip;
        ray_eye = vec4(ray_eye.xy, -1.0, 0.0);         // Point at infinity
        
        view_dir = normalize((m_inv_view * ray_eye).xyz);
        
        gl_Position = vec4(in_position, 0.0, 1.0);     // Full-screen quad
    }

**sky.frag** - Rayleigh scattering atmosphere.

.. code-block:: glsl

    #version 330 core

    out vec4 fragColor;
    in vec3 view_dir;

    uniform vec3 u_sun_direction;
    uniform vec3 bg_color;

    void main() {
        // Rayleigh scattering: intensity based on angle to sun
        float sun_angle = dot(normalize(view_dir), normalize(u_sun_direction));
        
        // Phase function (Rayleigh-like, but simplified)
        float phase = 0.75 * (1.0 + sun_angle * sun_angle);
        
        // Color sky based on sun angle
        float height = view_dir.y;  // Vertical component
        
        // Sunrise/sunset color shift
        vec3 day_color = vec3(0.53, 0.81, 0.92);      // Bright blue
        vec3 sunset_color = vec3(1.0, 0.6, 0.3);      // Orange/red
        
        // Interpolate based on sun height
        float sun_height = u_sun_direction.y;  // -1 (night) to 1 (day)
        vec3 sky_color = mix(vec3(0.1, 0.1, 0.2), day_color, clamp(sun_height + 0.5, 0.0, 1.0));
        
        // Add sunset glow near horizon
        if (sun_height < 0.3) {
            sky_color = mix(sky_color, sunset_color, 0.5 * (0.3 - sun_height));
        }
        
        fragColor = vec4(sky_color * phase, 1.0);
    }

Clouds Shader (Procedural)
---------------------------

**clouds.vert** - Each cloud is a simple quad; vertex shader applies noise-based offset.

.. code-block:: glsl

    #version 330 core

    layout (location = 0) in vec3 in_position;

    uniform mat4 m_proj;
    uniform mat4 m_view;
    uniform int center;            // 0 or 1, alternates between two layers
    uniform float u_time;          // For animation
    uniform float cloud_scale;     // Size of clouds
    uniform vec3 player_pos;       // For camera-relative positioning

    void main() {
        vec3 world_pos = in_position;
        
        // Offset clouds with time for drifting effect
        world_pos.x += u_time * 0.1;  // Drift slowly
        world_pos.z += u_time * 0.05;
        
        // Camera-relative positioning (clouds centered on player)
        world_pos += player_pos;
        
        // Apply scale
        world_pos *= cloud_scale;
        
        gl_Position = m_proj * m_view * vec4(world_pos, 1.0);
    }

**clouds.frag** - Noise-based cloud appearance.

.. code-block:: glsl

    #version 330 core

    layout (location = 0) out vec4 fragColor;

    uniform vec3 bg_color;
    uniform vec3 u_sun_direction;
    uniform float u_fog_density;
    uniform float u_fog_max_opacity;

    void main() {
        // Procedural noise (simplified: use gl_FragCoord for pseudo-randomness)
        vec2 uv = gl_FragCoord.xy / 512.0;
        float noise = fract(sin(dot(uv, vec2(12.9898, 78.233))) * 43758.5453);
        
        // Cloud color: white with some shading
        vec3 cloud_color = vec3(1.0) * (0.8 + noise * 0.2);
        
        // Day/night shading
        float day_night = 0.5 + 0.5 * u_sun_direction.y;
        cloud_color *= day_night;
        
        // Transparency based on noise (cloudy areas more opaque)
        float alpha = clamp(noise, 0.3, 0.8);
        
        fragColor = vec4(cloud_color, alpha);
    }

UI Block Shader (Inventory Icons)
---------------------------------

**ui_block.vert** - 2D quad positioning.

.. code-block:: glsl

    #version 330 core

    layout (location = 0) in vec2 in_position;
    layout (location = 1) in vec2 in_tex_coord;

    out vec2 uv;

    uniform vec2 u_offset;   // Screen position (-1 to 1)
    uniform vec2 u_scale;    // Size

    void main() {
        gl_Position = vec4(in_position * u_scale + u_offset, 0.0, 1.0);
        uv = in_tex_coord;
    }

**ui_block.frag** - Sample and display.

.. code-block:: glsl

    #version 330 core

    layout (location = 0) out vec4 fragColor;

    in vec2 uv;

    uniform sampler2DArray u_texture_array_0;
    uniform int voxel_id;
    uniform int u_texture_map[256];

    void main() {
        int tex_layer = u_texture_map[voxel_id];
        vec4 color = texture(u_texture_array_0, vec3(uv, float(tex_layer)));
        
        if (color.a < 0.5) discard;
        
        fragColor = color;
    }

UI Color Shader (Backgrounds, UI Quads)
---------------------------------------

**ui_color.vert** - Simple 2D positioning.

.. code-block:: glsl

    #version 330 core

    layout (location = 0) in vec2 in_position;

    uniform vec2 u_offset;
    uniform vec2 u_scale;

    void main() {
        gl_Position = vec4(in_position * u_scale + u_offset, 0.0, 1.0);
    }

**ui_color.frag** - Output uniform color.

.. code-block:: glsl

    #version 330 core

    layout (location = 0) out vec4 fragColor;
    uniform vec4 u_color;  // RGBA color

    void main() {
        fragColor = u_color;
    }

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
4. **Wireframe:** Use ``glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)`` in Python to see mesh structure.

