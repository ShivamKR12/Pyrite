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

in vec2 uv;
in float shading;
in vec3 frag_world_pos;

flat in int face_id;
flat in int voxel_id;
flat in int is_water_neighbor;


void main() {
    vec2 dx = dFdx(uv);
    vec2 dy = dFdy(uv);

    vec3 tex_col;
    if (voxel_id == 9) { // 9 is WATER
        vec2 water_uv = fract(uv) + vec2(u_time * 0.2, u_time * 0.2);
        tex_col = texture(u_texture_water, water_uv).rgb;
    } else {
        vec2 face_uv = fract(uv);
        face_uv.x = face_uv.x / 3.0 - min(face_id, 2) / 3.0;
        tex_col = textureGrad(u_texture_array_0, vec3(face_uv, voxel_id), vec2(dx.x / 3.0, dx.y), vec2(dy.x / 3.0, dy.y)).rgb;
    }
    
    tex_col = pow(tex_col, gamma);
    tex_col *= shading;

    // underwater effect
    if (u_underwater_tint && is_water_neighbor == 1 && voxel_id != 9) {
        tex_col *= vec3(0.0, 0.3, 1.0);
    }

    tex_col = pow(tex_col, inv_gamma);

    //fog
    float fog_dist = gl_FragCoord.z / gl_FragCoord.w;
    float fog_factor = min(1.0 - exp2(-u_fog_density * fog_dist * fog_dist), u_fog_max_opacity);
    tex_col = mix(tex_col, bg_color, fog_factor);

    float alpha = 1.0;
    if (voxel_id == 9) {
        alpha = mix(0.5, 0.0, 1.0 - exp(-u_fog_density * fog_dist * fog_dist));
    }

    fragColor = vec4(tex_col, alpha);
}
