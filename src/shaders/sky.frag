#version 330 core

in vec3 view_dir;

out vec4 fragColor;

uniform vec3 u_sun_direction;
uniform vec3 bg_color;


void main() {
    // Calculate base sky gradient colors based on view direction
    vec3 direction = normalize(view_dir);
    vec3 horizon_color = bg_color;
    vec3 zenith_color = horizon_color * 0.3;
    float blend_factor = max(0.0, direction.y);
    vec3 color = mix(horizon_color, zenith_color, blend_factor);

    // Render the sun using smoothstep for a soft glowing halo
    float sun_distance = distance(direction, u_sun_direction);
    if (sun_distance < 0.08) {
        float glow = smoothstep(0.08, 0.02, sun_distance);
        color += vec3(1.0, 0.9, 0.6) * glow;
    }

    // Render the moon on the opposite side of the sky from the sun
    vec3 moon_direction = -u_sun_direction;
    float moon_distance = distance(direction, moon_direction);
    if (moon_distance < 0.08) {
        float glow = smoothstep(0.08, 0.02, moon_distance);
        color += vec3(0.5, 0.6, 0.9) * glow;
    }

    // Generate procedural stars dynamically at night time
    float sun_y = u_sun_direction.y;
    if (sun_y < 0.2 && direction.y > 0.0 && moon_distance > 0.06 && sun_distance > 0.06) {
        vec3 star_grid = floor(direction * 800.0);
        float star_noise = fract(sin(dot(star_grid, vec3(12.9898, 78.233, 45.164))) * 43758.5453);
        if (star_noise > 0.999) {
            float star_brightness = smoothstep(0.2, -0.2, sun_y) * direction.y;
            color += vec3(1.0) * star_brightness;
        }
    }

    // Output final fragment color
    fragColor = vec4(color, 1.0);
}
