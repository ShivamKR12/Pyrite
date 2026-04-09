#version 330 core

layout (location = 0) in uint packed_data;

int x, y, z;
int ao_id;
int flip_id;

uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model;
uniform vec3 u_sun_direction;

flat out int voxel_id;
flat out int face_id;

//out vec3 voxel_color;
out vec2 uv;
out float shading;
out vec3 frag_world_pos;

const float ao_values[4] = float[4](0.1, 0.25, 0.5, 1.0);

const vec3 face_normals[6] = vec3[6](
    vec3( 0.0,  1.0,  0.0), // top
    vec3( 0.0, -1.0,  0.0), // bottom
    vec3( 1.0,  0.0,  0.0), // right
    vec3(-1.0,  0.0,  0.0), // left
    vec3( 0.0,  0.0, -1.0), // back
    vec3( 0.0,  0.0,  1.0)  // front
);


vec3 hash31(float p) {
    vec3 p3 = fract(vec3(p * 21.2) * vec3(0.1031, 0.1030, 0.0973));
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.xxy + p3.yzz) * p3.zyx) + 0.05;
}


void unpack(uint packed_data) {
    // a, b, c, d, e, f, g = x, y, z, voxel_id, face_id, ao_id, flip_id
    uint b_bit = 6u, c_bit = 6u, d_bit = 8u, e_bit = 3u, f_bit = 2u, g_bit = 1u;
    uint b_mask = 63u, c_mask = 63u, d_mask = 255u, e_mask = 7u, f_mask = 3u, g_mask = 1u;
    //
    uint fg_bit = f_bit + g_bit;
    uint efg_bit = e_bit + fg_bit;
    uint defg_bit = d_bit + efg_bit;
    uint cdefg_bit = c_bit + defg_bit;
    uint bcdefg_bit = b_bit + cdefg_bit;
    // unpacking vertex data
    x = int(packed_data >> bcdefg_bit);
    y = int((packed_data >> cdefg_bit) & b_mask);
    z = int((packed_data >> defg_bit) & c_mask);
    //
    voxel_id = int((packed_data >> efg_bit) & d_mask);
    face_id = int((packed_data >> fg_bit) & e_mask);
    ao_id = int((packed_data >> g_bit) & f_mask);
    flip_id = int(packed_data & g_mask);
}


void main() {
    unpack(packed_data);

    vec3 in_position = vec3(x, y, z);
    // Generate naturally tiling UVs scaled to the size of the greedy quad!
    if (face_id == 0)      uv = vec2(x, -z);
    else if (face_id == 1) uv = vec2(x, z);
    else if (face_id == 2) uv = vec2(-z, -y);
    else if (face_id == 3) uv = vec2(z, -y);
    else if (face_id == 4) uv = vec2(x, -y);
    else                   uv = vec2(-x, -y);

    vec3 normal = face_normals[face_id];
    float diffuse = max(0.0, dot(normal, u_sun_direction));
    float ambient = max(0.05, 0.3 * (u_sun_direction.y + 0.5)); // smooth transition for night
    shading = (ambient + diffuse * 0.7) * ao_values[ao_id];

    frag_world_pos = (m_model * vec4(in_position, 1.0)).xyz;

    gl_Position = m_proj * m_view * vec4(frag_world_pos, 1.0);
}
