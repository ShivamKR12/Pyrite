#version 330 core

in vec3 view_dir;

out vec4 fragColor;

uniform vec3 u_sun_direction;
uniform vec3 bg_color;


void main() {
    // Normalize the interpolated view direction so its length is exactly 1.0 (a unit vector)
    vec3 dir = normalize(view_dir);
    
    // Use the application's computed fog background color for the horizon
    vec3 horizon_color = bg_color;
    
    // Make the zenith (top of the sky) a slightly darker/deeper shade
    vec3 zenith_color = horizon_color * 0.3; 
    
    // Hemisphere Gradient Calculation
    // `dir.y` represents how far "up" we are looking (0.0 is the horizon, 1.0 is straight up).
    // We use `max(0.0, dir.y)` to ignore looking down into the ground.
    // `mix()` performs a linear interpolation (lerp). As we look higher (t approaches 1.0), 
    // the color smoothly transitions from the horizon color to the dark zenith color.
    float t = max(0.0, dir.y);
    vec3 color = mix(horizon_color, zenith_color, t);
    
    // Sun Rendering (Euclidean Distance)
    // We calculate the 3D spatial distance between where we are currently looking (`dir`) 
    // and where the sun is positioned (`u_sun_direction`).
    float sun_dist = distance(dir, u_sun_direction);
    
    // If we are looking within a radius of 0.08 units from the sun's center...
    if (sun_dist < 0.08) {
        // `smoothstep` creates a smooth curve (Hermite interpolation) between 0.08 (edge) 
        // and 0.02 (core). This creates a soft, glowing halo instead of a hard pixelated circle.
        float glow = smoothstep(0.08, 0.02, sun_dist);
        color += vec3(1.0, 0.9, 0.6) * glow;
    }
    
    // Moon Rendering (Opposite Vector)
    // The moon is strictly locked to the opposite side of the sky from the sun.
    // We simply negate the sun's direction vector (-u_sun_direction).
    vec3 moon_dir = -u_sun_direction;
    float moon_dist = distance(dir, moon_dir);
    
    if (moon_dist < 0.08) {
        float glow = smoothstep(0.08, 0.02, moon_dist);
        color += vec3(0.5, 0.6, 0.9) * glow;
    }
    
    // Procedural Star Generation (GLSL Hashing)
    float sun_y = u_sun_direction.y;
    
    // Only draw stars if the sun is setting/set (sun_y < 0.2), we are looking at the sky (dir.y > 0.0),
    // and we aren't accidentally drawing a star directly over the sun or moon masks.
    if (sun_y < 0.2 && dir.y > 0.0 && moon_dist > 0.06 && sun_dist > 0.06) {
    
        // 1. Grid Discretization: We multiply the continuous view direction by 800 and `floor()` it. 
        //    This chops the smooth sky dome into 800x800 chunky, distinct coordinate blocks.
        vec3 star_grid = floor(dir * 800.0);
        
        // 2. The GLSL Hash Function: We take the dot product of our grid coordinate against 
        //    an arbitrary "magic" vector (12.9898, 78.233, 45.164). This scrambles the coordinates.
        // 3. We take the `sin()` of that scrambled number to make it wave, multiply it by a 
        //    massive number (43758.5453) to amplify the tiny wave fluctuations, and take the 
        //    `fract()` (decimal remainder). This generates a perfectly deterministic pseudo-random 
        //    number between 0.0 and 1.0 for every single grid block!
        float star_noise = fract(sin(dot(star_grid, vec3(12.9898, 78.233, 45.164))) * 43758.5453);
        
        // If the random number for this specific grid block is > 0.999, it becomes a star.
        // This gives exactly a 0.1% probability of a star spawning per patch of sky.
        if (star_noise > 0.999) { 
            // The stars fade in smoothly as the sun sets (smoothstep on sun_y).
            // They also fade out as they get close to the horizon (multiplied by dir.y) 
            // to simulate atmospheric thickness hiding them.
            float star_brightness = smoothstep(0.2, -0.2, sun_y) * dir.y;
            color += vec3(1.0) * star_brightness;
        }
    
    }
    
    fragColor = vec4(color, 1.0);
}
