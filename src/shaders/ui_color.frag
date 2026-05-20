#version 330 core

layout (location = 0) out vec4 fragColor;

in vec2 v_position;  // the world-space coordinate passed from your vertex shader

uniform vec4 u_color;
uniform vec4 u_clip; // (x_min, y_min, x_max, y_max)


void main() {
    
    // Inside your void main() block:
    if (v_position.x < u_clip.x || v_position.y < u_clip.y || v_position.x > u_clip.z || v_position.y > u_clip.w) {
        discard;
    }

    fragColor = u_color;
}
