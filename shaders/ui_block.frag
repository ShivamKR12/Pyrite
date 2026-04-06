#version 330 core

layout (location = 0) out vec4 fragColor;

in vec2 uv;

uniform sampler2DArray u_texture_array_0;
uniform int voxel_id;

void main() {
    vec2 face_uv = vec2(uv.x / 3.0, uv.y); // Sample the top face of the block
    fragColor = texture(u_texture_array_0, vec3(face_uv, voxel_id));
}