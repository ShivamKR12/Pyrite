#version 330 core

layout (location = 0) out vec4 fragColor;

const vec3 gamma = vec3(2.2);
const vec3 inv_gamma = 1 / gamma;

in vec2 uv;

uniform sampler2D u_texture_0;
uniform float water_line;
uniform float u_time;


void main() {
    vec2 animated_uv = uv + vec2(u_time * 0.2, u_time * 0.2);
    vec3 tex_col = texture(u_texture_0, animated_uv).rgb;
    tex_col = pow(tex_col, gamma);

    // fog
    float fog_dist = gl_FragCoord.z / gl_FragCoord.w;
    float alpha = mix(0.5, 0.0, 1.0 - exp(-0.000002 * fog_dist * fog_dist));

    // gamma corretion
    tex_col = pow(tex_col, inv_gamma);
    fragColor = vec4(tex_col, alpha);
}