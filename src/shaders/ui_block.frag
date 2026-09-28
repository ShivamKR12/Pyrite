#version 330 core

layout (location = 0) out vec4 fragColor;

in vec2 uv;

uniform sampler2DArray u_texture_array_0;
uniform int voxel_id;
uniform int u_texture_map[256];


void main() {
    // Determine texture parameters based on voxel ID and UVs
    int texture_id = u_texture_map[voxel_id];
    vec2 face_uv = vec2(uv.x / 3.0, uv.y);

    // Sample the texture array and discard transparent pixels
    vec4 texture_sample = texture(u_texture_array_0, vec3(face_uv, texture_id));
    if (texture_sample.a < 0.1) {
        discard;
    }

    // Output final color
    fragColor = texture_sample;
}
