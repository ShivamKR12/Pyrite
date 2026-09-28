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
    // Texture sampling and alpha test
    int texture_id = u_texture_map[voxel_id];
    vec2 face_uv = vec2(uv.x / 3.0 - min(face_id, 2) / 3.0, uv.y);
    vec4 texture_sample = texture(u_texture_array_0, vec3(face_uv, texture_id));
    if (texture_sample.a < 0.1) {
        discard;
    }

    // Shading and gamma correction
    vec3 texture_color = texture_sample.rgb;
    texture_color = pow(texture_color, gamma) * shading;
    texture_color = pow(texture_color, inv_gamma);

    // Fog application
    float fog_distance = gl_FragCoord.z / gl_FragCoord.w;
    float fog_factor = min(1.0 - exp2(-u_fog_density * fog_distance * fog_distance), u_fog_max_opacity);
    texture_color = mix(texture_color, bg_color, fog_factor);

    // Final color output
    fragColor = vec4(texture_color, 1.0);
}
