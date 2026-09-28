#version 330 core

layout (location = 0) out vec4 fragColor;

const vec3 gamma = vec3(2.2);
const vec3 inv_gamma = 1 / gamma;

uniform sampler2DArray u_texture_array_0;
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
    // UV calculation and animation
    vec2 delta_x = dFdx(uv);
    vec2 delta_y = dFdy(uv);
    vec2 face_uv = fract(uv);
    if (voxel_id == 11) {
        face_uv = fract(face_uv + vec2(u_time * 0.2, u_time * 0.2));
    }
    face_uv.x = face_uv.x / 3.0 - min(face_id, 2) / 3.0;

    // Texture sampling and gamma correction
    int texture_id = u_texture_map[voxel_id];
    vec4 texture_sample = textureGrad(u_texture_array_0, vec3(face_uv, texture_id), vec2(delta_x.x / 3.0, delta_x.y), vec2(delta_y.x / 3.0, delta_y.y));
    if (texture_sample.a < 0.1) {
        discard;
    }
    vec3 texture_color = texture_sample.rgb;
    texture_color = pow(texture_color, gamma);

    // Lighting calculation
    float day_light = max(0.05, u_sun_direction.y + 0.2);
    float final_light = max(sun_light * day_light, block_light);
    final_light = max(0.02, pow(final_light, 1.5));
    texture_color *= shading * final_light;

    // Underwater tint and inverse gamma correction
    if (u_underwater_tint && is_water_neighbor == 1 && voxel_id != 11) {
        texture_color *= vec3(0.0, 0.3, 1.0);
    }
    texture_color = pow(texture_color, inv_gamma);

    // Fog calculation
    float fog_distance = gl_FragCoord.z / gl_FragCoord.w;
    float fog_factor = min(1.0 - exp2(-u_fog_density * fog_distance * fog_distance), u_fog_max_opacity);
    texture_color = mix(texture_color, bg_color, fog_factor);

    // Alpha calculation and final output
    float alpha = 1.0;
    if (voxel_id == 11) {
        alpha = mix(0.5, 0.0, 1.0 - exp(-u_fog_density * fog_distance * fog_distance));
    }
    fragColor = vec4(texture_color, alpha);
}
