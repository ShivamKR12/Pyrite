#version 330 core

layout (location = 0) out vec4 fragColor;

in vec3 marker_color;
in vec2 uv;

uniform sampler2D u_texture_0;
uniform sampler2D u_texture_breaking;
uniform float mining_progress;

void main() {
    // Base frame color (the black outline)
    vec4 frame_col = texture(u_texture_0, uv);
    frame_col.rgb += marker_color;
    
    // Breaking animation overlay
    vec4 break_col = vec4(0.0);
    if (mining_progress > 0.0) {
        // Calculate which of the 8 frames to use based on progress
        int frame = int(mining_progress * 8.0);
        frame = clamp(frame, 0, 7);

        // The texture is 16x128 (8 frames vertically). 
        // Each frame is 1/8th of the height (0.125)
        vec2 break_uv = vec2(uv.x, (uv.y + float(frame)) / 8.0);
        break_col = texture(u_texture_breaking, break_uv);
    }
    
    fragColor = frame_col;
    if (break_col.a > 0.1) {
        fragColor = vec4(mix(fragColor.rgb, break_col.rgb, break_col.a), 1.0);
    }
    fragColor.a = max(frame_col.a, break_col.a);
}