#version 330 core

layout (location = 0) out vec4 fragColor;

in vec2 uv;
uniform sampler2D u_texture_0;
uniform float u_alpha;

void main() {
    vec4 col = texture(u_texture_0, uv);
    fragColor = vec4(col.rgb, col.a * u_alpha);
}