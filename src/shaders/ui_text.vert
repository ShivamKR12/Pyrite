#version 330 core

layout (location = 0) in vec2 in_position;
layout (location = 1) in vec2 in_tex_coord;

out vec2 uv;
out vec2 v_position;

uniform vec2 u_offset;
uniform vec2 u_scale;

void main() {
    uv = in_tex_coord;
    gl_Position = vec4((in_position * u_scale) + u_offset, 0.0, 1.0);
    v_position = gl_Position.xy;
}