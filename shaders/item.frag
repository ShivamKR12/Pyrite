#version 330 core

layout (location = 0) out vec4 fragColor;

in vec2 uv;
flat in int face_id;
in float shading;

uniform sampler2DArray u_texture_array_0;
uniform int voxel_id;
uniform vec3 bg_color;
uniform float u_fog_density;
uniform float u_fog_max_opacity;
uniform int u_texture_map[256];

const vec3 gamma = vec3(2.2);
const vec3 inv_gamma = 1 / gamma;

void main() {
    int tex_id = u_texture_map[voxel_id];
    vec2 face_uv = vec2(uv.x / 3.0 - min(face_id, 2) / 3.0, uv.y);
    vec4 tex_sample = texture(u_texture_array_0, vec3(face_uv, tex_id));
    
    if (tex_sample.a < 0.1) {
        discard;
    }
    vec3 tex_col = tex_sample.rgb;
    tex_col = pow(tex_col, gamma) * shading;
    tex_col = pow(tex_col, inv_gamma);

    float fog_dist = gl_FragCoord.z / gl_FragCoord.w;
    float fog_factor = min(1.0 - exp2(-u_fog_density * fog_dist * fog_dist), u_fog_max_opacity);
    tex_col = mix(tex_col, bg_color, fog_factor);

    fragColor = vec4(tex_col, 1.0);
}