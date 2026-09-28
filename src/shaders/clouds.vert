#version 330 core

layout (location = 0) in vec3 in_position;

uniform mat4 m_proj;
uniform mat4 m_view;
uniform int center;
uniform float u_time;
uniform float cloud_scale;
uniform vec3 player_pos;


void main() {
    // Position scaling and centering
    vec3 position = vec3(in_position);
    position.xz -= center;
    position.xz *= cloud_scale;
    position.xz += player_pos.xz;

    // Wind animation and final position
    float time = 300 * sin(0.01 * u_time);
    position.xz += time;
    gl_Position = m_proj * m_view * vec4(position, 1.0);
}
