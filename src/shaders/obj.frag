#version 330 core

layout (location = 0) out vec4 fragColor;

in vec2 uv;
in float shading;
in vec3 frag_color;

uniform sampler2D u_texture_0;
uniform bool u_use_texture;
uniform vec3 bg_color;
uniform float u_fog_density;
uniform float u_fog_max_opacity;

const vec3 gamma = vec3(2.2);
const vec3 inv_gamma = 1 / gamma;


void main() {
    // Determine base color and alpha
    vec3 base_color;
    float alpha = 1.0;
    if (u_use_texture) {
        vec4 texture_color = texture(u_texture_0, uv);
        if (texture_color.a < 0.1) {
            discard;
        }
        base_color = texture_color.rgb;
        alpha = texture_color.a;
    } else {
        base_color = frag_color;
    }

    // Shading and gamma correction
    vec3 rgb = pow(base_color, gamma) * shading;
    rgb = pow(rgb, inv_gamma);

    // Fog application
    float fog_distance = gl_FragCoord.z / gl_FragCoord.w;
    float fog_factor = min(1.0 - exp2(-u_fog_density * fog_distance * fog_distance), u_fog_max_opacity);
    rgb = mix(rgb, bg_color, fog_factor);

    // Final color output
    fragColor = vec4(rgb, alpha);
}
