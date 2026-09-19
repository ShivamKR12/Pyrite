#version 330 core

// Input vertex attribute 0: 32-bit unsigned integer containing packed spatial and block identity data
layout (location = 0) in uint packed_data;
// Input vertex attribute 1: 32-bit unsigned integer containing packed sunlight and block light data
layout (location = 1) in uint light_data;

// Integer to store the extracted local X coordinate of the vertex
int x;
// Integer to store the extracted local Y coordinate of the vertex
int y;
// Integer to store the extracted local Z coordinate of the vertex
int z;
// Integer to store the extracted ambient occlusion level ID (0 to 3)
int ao_id;
// Integer to store the extracted quad flip flag (0 or 1) for anisotropic triangulation
int flip_id;

// The 4x4 projection matrix to transform coordinates from camera space to clip space
uniform mat4 m_proj;
// The 4x4 view matrix to transform coordinates from world space to camera space
uniform mat4 m_view;
// The 4x4 model matrix to transform coordinates from local chunk space to world space
uniform mat4 m_model;
// The normalized 3D directional vector pointing towards the sun for lighting dot products
uniform vec3 u_sun_direction;

// Output flat integer representing the block type ID to be passed directly to the fragment shader
flat out int voxel_id;
// Output flat integer representing the face direction (0-5) to be passed to the fragment shader
flat out int face_id;
// Output flat integer (boolean) indicating if this block is adjacent to water
flat out int is_water_neighbor;

// Output 2D vector for texture mapping coordinates, sent to the fragment shader
out vec2 uv;
// Output float representing the pre-computed vertex shading (ambient + diffuse + ambient occlusion)
out float shading;
// Output 3D vector representing the absolute world-space position of the vertex
out vec3 frag_world_pos;
// Output float representing the extracted sunlight level (0.0 to 1.0)
out float sun_light;
// Output float representing the extracted block light level (0.0 to 1.0)
out float block_light;

// Array of 4 predefined ambient occlusion multiplier float values mapped to ao_id indices
const float ao_values[4] = float[4](0.1, 0.25, 0.5, 1.0);

// Array of 6 predefined 3D normal vectors corresponding to the 6 cubic face directions
const vec3 face_normals[6] = vec3[6](
    vec3( 0.0,  1.0,  0.0), // Face 0: Top face pointing straight up along positive Y axis
    vec3( 0.0, -1.0,  0.0), // Face 1: Bottom face pointing straight down along negative Y axis
    vec3( 1.0,  0.0,  0.0), // Face 2: Right face pointing straight right along positive X axis
    vec3(-1.0,  0.0,  0.0), // Face 3: Left face pointing straight left along negative X axis
    vec3( 0.0,  0.0, -1.0), // Face 4: Back face pointing straight back along negative Z axis
    vec3( 0.0,  0.0,  1.0)  // Face 5: Front face pointing straight forward along positive Z axis
);

// Hash function to generate pseudo-random 3D noise based on a single floating point seed
vec3 hash31(float p) {
    // Multiply seed by 21.2, extract fractional part, and multiply by 3 unique constant primes
    vec3 p3 = fract(vec3(p * 21.2) * vec3(0.1031, 0.1030, 0.0973));
    // Add the dot product of p3 and a swizzled, offset version of itself to scramble the bits further
    p3 += dot(p3, p3.yzx + 33.33);
    // Multiply combinations of swizzled p3 components, extract the fraction, and add a baseline 0.05
    return fract((p3.xxy + p3.yzz) * p3.zyx) + 0.05;
}

// Function to unpack the 32-bit unsigned integer into spatial coordinates and block metadata
void unpack(uint packed_data) {
    // Define the bit lengths for each packed component: Y, Z, Voxel ID, Face ID, AO ID, Flip Flag
    uint b_bit = 6u, c_bit = 6u, d_bit = 8u, e_bit = 3u, f_bit = 2u, g_bit = 1u;
    // Define the bitmasks to extract values of exact bit widths using logical AND operations
    uint b_mask = 63u, c_mask = 63u, d_mask = 255u, e_mask = 7u, f_mask = 3u, g_mask = 1u;
    
    // Pre-calculate the cumulative bit shifts needed to correctly isolate each packed variable
    uint fg_bit = f_bit + g_bit;
    uint efg_bit = e_bit + fg_bit;
    uint defg_bit = d_bit + efg_bit;
    uint cdefg_bit = c_bit + defg_bit;
    uint bcdefg_bit = b_bit + cdefg_bit;
    
    // Right-shift by the total lower bits to isolate the local X coordinate (unmasked as it occupies the remaining top bits)
    x = int(packed_data >> bcdefg_bit);
    // Right-shift past the lower variables and apply the 6-bit mask to isolate the local Y coordinate
    y = int((packed_data >> cdefg_bit) & b_mask);
    // Right-shift past the lower variables and apply the 6-bit mask to isolate the local Z coordinate
    z = int((packed_data >> defg_bit) & c_mask);
    
    // Right-shift past the lower variables and apply the 8-bit mask to isolate the raw combined voxel ID
    int raw_voxel_id = int((packed_data >> efg_bit) & d_mask);
    // Determine if the block borders water by checking if the highest bit (128) of the raw voxel ID is set
    is_water_neighbor = (raw_voxel_id >= 128) ? 1 : 0;
    
    // Strip the water-neighbor bit (128) from the raw ID using a bitwise AND with 127 to get the actual block type ID
    voxel_id = raw_voxel_id & 127;
    
    // Right-shift past the AO and flip bits and apply the 3-bit mask to isolate the 0-5 face direction ID
    face_id = int((packed_data >> fg_bit) & e_mask);
    
    // Right-shift past the flip bit and apply the 2-bit mask to isolate the 0-3 ambient occlusion intensity ID
    ao_id = int((packed_data >> g_bit) & f_mask);
    
    // Apply the 1-bit mask directly to the lowest bit to extract the quad triangulation flip flag
    flip_id = int(packed_data & g_mask);
}

void main() {
    // Call the unpack function to decode the 32-bit packed spatial and metadata integer into global variables
    unpack(packed_data);

    // Right-shift the light data by 4 bits and apply a 4-bit mask (15), then normalize to 0.0-1.0 to get sunlight
    sun_light = float((light_data >> 4u) & 15u) / 15.0;
    // Apply a 4-bit mask (15) directly to the lowest bits and normalize to 0.0-1.0 to get block light
    block_light = float(light_data & 15u) / 15.0;

    // Assemble the unpacked local X, Y, and Z integer coordinates into a 3D float vector for math operations
    vec3 in_position = vec3(x, y, z);
    
    // Assign 2D texture coordinates based on the block face ID, mapping world coordinates to UVs for greedy meshing tiling
    if (face_id == 0)      uv = vec2(x, -z); // Top face uses X and negative Z axes for texture mapping
    else if (face_id == 1) uv = vec2(x, z);  // Bottom face uses X and positive Z axes for texture mapping
    else if (face_id == 2) uv = vec2(-z, -y);// Right face uses negative Z and negative Y axes for texture mapping
    else if (face_id == 3) uv = vec2(z, -y); // Left face uses positive Z and negative Y axes for texture mapping
    else if (face_id == 4) uv = vec2(x, -y); // Back face uses positive X and negative Y axes for texture mapping
    else                   uv = vec2(-x, -y);// Front face uses negative X and negative Y axes for texture mapping

    // Retrieve the pre-defined 3D normal vector from the lookup array using the unpacked face ID
    vec3 normal = face_normals[face_id];
    
    // Calculate the diffuse lighting multiplier using the dot product of the face normal and sun vector, clamped above 0.0
    float diffuse = max(0.0, dot(normal, u_sun_direction));
    
    // Calculate base ambient light based on the sun's height (Y axis), shifted by 0.5 and scaled by 0.4, clamped above 0.2
    float ambient = max(0.2, 0.4 * (u_sun_direction.y + 0.5));
    
    // Combine ambient and scaled diffuse light, then multiply by the ambient occlusion multiplier for the final vertex shading
    shading = (ambient + diffuse * 0.4) * ao_values[ao_id];

    // Multiply the model matrix by the local position vector to transform the vertex into absolute world-space coordinates
    frag_world_pos = (m_model * vec4(in_position, 1.0)).xyz;

    // Multiply the projection and view matrices by the world-space position to calculate final normalized clip-space coordinates
    gl_Position = m_proj * m_view * vec4(frag_world_pos, 1.0);
}
