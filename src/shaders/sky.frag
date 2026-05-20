#version 330 core

in vec3 view_dir;

out vec4 fragColor;

uniform vec3 u_sun_direction;
uniform vec3 bg_color;


void main() {
    vec3 dir = normalize(view_dir);
    
    // Use the application's computed fog background color for the horizon
    vec3 horizon_color = bg_color;
    
    // Make the zenith (top of the sky) a slightly darker/deeper shade
    vec3 zenith_color = horizon_color * 0.3; 
    
    // Gradient factor based on looking up
    float t = max(0.0, dir.y);
    vec3 color = mix(horizon_color, zenith_color, t);
    
    // Draw the Sun
    float sun_dist = distance(dir, u_sun_direction);
    
    if (sun_dist < 0.08) {
        float glow = smoothstep(0.08, 0.02, sun_dist);
        color += vec3(1.0, 0.9, 0.6) * glow;
    }
    
    // Draw the Moon (positioned strictly opposite to the sun)
    vec3 moon_dir = -u_sun_direction;
    float moon_dist = distance(dir, moon_dir);
    
    if (moon_dist < 0.08) {
        float glow = smoothstep(0.08, 0.02, moon_dist);
        color += vec3(0.5, 0.6, 0.9) * glow;
    }
    
    // Draw Stars (only visible when looking up, when the sun is down, and not over the sun/moon)
    float sun_y = u_sun_direction.y;
    
    if (sun_y < 0.2 && dir.y > 0.0 && moon_dist > 0.06 && sun_dist > 0.06) {
    
        // Discretize the view direction to create stable, locked-in point stars
        vec3 star_grid = floor(dir * 800.0);
        float star_noise = fract(sin(dot(star_grid, vec3(12.9898, 78.233, 45.164))) * 43758.5453);
        
        if (star_noise > 0.999) { // 0.1% chance of a star per patch of sky
            // Fade stars in as sun goes down, and fade out gently towards the horizon
            float star_brightness = smoothstep(0.2, -0.2, sun_y) * dir.y;
            color += vec3(1.0) * star_brightness;
        }
    
    }
    
    fragColor = vec4(color, 1.0);
}
