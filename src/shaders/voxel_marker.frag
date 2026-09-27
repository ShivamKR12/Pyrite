#version 330 core

layout (location = 0) out vec4 fragColor;

in vec3 marker_color;
in vec2 uv;

uniform sampler2D u_texture_0;
uniform sampler2D u_texture_breaking;
uniform float mining_progress;
uniform int is_bbox;


void main() {
    // Handle bounding box early exit
    if (is_bbox == 1) {
        fragColor = vec4(0.0);
        return;
    }

    // Calculate base frame color and marker overlay
    vec4 frame_col = texture(u_texture_0, uv);
    frame_col.rgb += marker_color;

    // Apply mining progress breaking animation if applicable
    vec4 break_col = vec4(0.0);
    if (mining_progress > 0.0) {
        int frame = clamp(int(mining_progress * 8.0), 0, 7);
        vec2 break_uv = vec2(uv.x, (uv.y + float(frame)) / 8.0);
        break_col = texture(u_texture_breaking, break_uv);
    }

    // Combine colors and set final fragment output
    fragColor = frame_col;
    if (break_col.a > 0.1) {
        fragColor = vec4(mix(fragColor.rgb, break_col.rgb, break_col.a), 1.0);
    }
    fragColor.a = max(frame_col.a, break_col.a);
}
