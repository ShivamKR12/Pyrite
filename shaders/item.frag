#version 330 core

layout (location = 0) out vec4 fragColor;

in vec2 uv;
flat in int face_id;
in float shading;

uniform sampler2DArray u_texture_array_0;
uniform int voxel_id;
uniform vec3 bg_color;

const vec3 gamma = vec3(2.2);
const vec3 inv_gamma = 1 / gamma;

void main() {
    vec2 face_uv = vec2(uv.x / 3.0 - min(face_id, 2) / 3.0, uv.y);
    vec3 tex_col = texture(u_texture_array_0, vec3(face_uv, voxel_id)).rgb;
    
    tex_col = pow(tex_col, gamma) * shading;
    float fog_dist = gl_FragCoord.z / gl_FragCoord.w;
    tex_col = mix(tex_col, bg_color, (1.0 - exp2(-0.00001 * fog_dist * fog_dist)));

    fragColor = vec4(pow(tex_col, inv_gamma), 1.0);
}