#version 330 core

layout (location = 0) in vec2 in_position;
layout (location = 1) in vec2 in_tex_coord;

out vec2 uv;

void main() {
    uv = in_tex_coord;
    gl_Position = vec4(in_position, 0.0, 1.0);
}