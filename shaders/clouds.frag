#version 330 core

layout (location = 0) out vec4 fragColor;

uniform vec3 bg_color;
uniform vec3 u_sun_direction;
uniform float u_fog_density;
uniform float u_fog_max_opacity;

void main() {
    vec3 cloud_color = vec3(1.0); // Base daytime color
    
    // If the sun is getting low, apply sunset and night colors!
    if (u_sun_direction.y < 0.4) {
        float sunset_blend = smoothstep(0.4, -0.1, u_sun_direction.y);
        float night_blend  = smoothstep(0.1, -0.3, u_sun_direction.y);
        
        cloud_color = mix(cloud_color, vec3(1.0, 0.5, 0.3), sunset_blend); // Orange sunset glow
        cloud_color = mix(cloud_color, vec3(0.05, 0.05, 0.08), night_blend); // Dark night silhouette
    }

    float fog_dist = gl_FragCoord.z / gl_FragCoord.w;
    float fog_factor = min(1.0 - exp(-u_fog_density * fog_dist * fog_dist), u_fog_max_opacity);
    vec3 col = mix(cloud_color, bg_color, fog_factor);

    fragColor = vec4(col, 0.8);
}