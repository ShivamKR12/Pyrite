#version 330 core

layout (location = 0) out vec4 fragColor;

const vec3 gamma = vec3(2.2);
const vec3 inv_gamma = 1 / gamma;

uniform sampler2DArray u_texture_array_0;
uniform sampler2D u_texture_water;
uniform vec3 bg_color;
uniform bool u_underwater_tint;
uniform float u_fog_density;
uniform float u_fog_max_opacity;
uniform float u_time;
uniform vec3 u_sun_direction;
uniform int u_texture_map[256];

in vec2 uv;
in float shading;
in vec3 frag_world_pos;
in float sun_light;
in float block_light;

flat in int face_id;
flat in int voxel_id;
flat in int is_water_neighbor;


void main() {
    vec4 tex_sample;
    vec2 dx = dFdx(uv);
    vec2 dy = dFdy(uv);
    vec2 face_uv = fract(uv);

    if (voxel_id == 36) { // 36 is WATER
        // Animate water texture by selecting one of 32 vertical frames over time.
        float animation_speed = 15.0; // Frames per second
        int frame_count = 32;
        
        int current_frame = int(u_time * animation_speed) % frame_count;
        float frame_height = 1.0 / float(frame_count);
        
        vec2 water_uv = vec2(face_uv.x, (face_uv.y * frame_height) + (float(current_frame) * frame_height));
        tex_sample = texture(u_texture_water, water_uv);

    } else {
        // Standard block texture lookup from the main atlas
        face_uv.x = face_uv.x / 3.0 - min(face_id, 2) / 3.0;
        int tex_id = u_texture_map[voxel_id];
        tex_sample = textureGrad(u_texture_array_0, vec3(face_uv, tex_id), vec2(dx.x / 3.0, dx.y), vec2(dy.x / 3.0, dy.y));
    }

    if (tex_sample.a < 0.1) {
        discard;
    }
    
    vec3 tex_col = tex_sample.rgb;
    tex_col = pow(tex_col, gamma);
    
    // Apply Day/Night cycle to sunlight
    float day_light = max(0.05, u_sun_direction.y + 0.2); 
    
    // Final combined light
    float final_light = max(sun_light * day_light, block_light);
    final_light = max(0.02, pow(final_light, 1.5)); // Gamma curve for natural darkness

    tex_col *= shading * final_light;

    // underwater effect
    if (u_underwater_tint && is_water_neighbor == 1 && voxel_id != 36) {
        tex_col *= vec3(0.0, 0.3, 1.0);
    }

    tex_col = pow(tex_col, inv_gamma);

    //fog
    float fog_dist = gl_FragCoord.z / gl_FragCoord.w;
    float fog_factor = min(1.0 - exp2(-u_fog_density * fog_dist * fog_dist), u_fog_max_opacity);
    
    tex_col = mix(tex_col, bg_color, fog_factor);

    float alpha = 1.0;
    if (voxel_id == 36) {
        alpha = mix(0.5, 0.0, 1.0 - exp(-u_fog_density * fog_dist * fog_dist));
    }

    fragColor = vec4(tex_col, alpha);
}
