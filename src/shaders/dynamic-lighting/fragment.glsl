// Placeholder fragment shader for dynamic sunlight.
varying vec2 v_uv;
uniform float u_time;
void main() {
    float light = 0.6 + 0.4 * (1.0 - v_uv.y);
    gl_FragColor = vec4(vec3(light), 0.25);
}