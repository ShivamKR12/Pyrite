#version 330 core

layout (location = 0) in vec2 in_tex_coord;
layout (location = 1) in vec3 in_position;

uniform mat4 m_proj;
uniform mat4 m_view;
uniform int water_area;
uniform float water_line;
uniform vec3 player_pos;

out vec2 uv;


void main() {
    vec3 pos = in_position;
    pos.xz *= water_area;
    pos.xz -= 0.33 * water_area;

    // Center the water quad around the player horizontally
    pos.xz += player_pos.xz;

    pos.y += water_line;
    // Shift the UV coordinates so the texture doesn't slide with the player
    uv = (in_tex_coord * water_area) + (player_pos.xz * 0.5);
    gl_Position = m_proj * m_view * vec4(pos, 1.0);
}