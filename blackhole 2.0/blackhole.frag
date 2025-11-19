#version 330
// File: blackhole.frag
// (Perbaikan: Menghapus fisika 'Kerr' yang tidak stabil, 
//  kembali ke 'Post-Newtonian' murni yang stabil)

out vec4 f_color;

// ... (Uniforms SAMA) ...
uniform vec2 u_resolution;
uniform float u_time;
uniform vec3 u_cam_pos;
uniform vec3 u_cam_lookat;
uniform sampler2D u_sky_tex;

// --- Konstanta Fisika ---
const float G = 1.0;
const float M = 10.0;
const float C = 10.0; 
const float C2 = C * C; 
const float RS = 2.0 * G * M / C2; // (RS = 0.2)
// --- HAPUS KONSTANTA KERR ---
// const float SPIN_A = 0.9 * M; (Dihapus)
// const vec3 SPIN_AXIS = vec3(0.0, 1.0, 0.0); (Dihapus)
// ------------------------
const float SHADOW_R = RS * 2.5; // (SHADOW_R = 0.5)
const int MAX_STEPS = 3000;
const float MAX_DIST = 100.0;
const float DT = 0.0007;

// ... (Konstanta Disk SAMA) ...
const float MIN_DISK_R = RS * 9.0; 
const float MAX_DISK_R = 9.5;
const float DISK_V_MAX = C * 0.8;

// ... (Fungsi-fungsi noise, fbm, setup_camera, sample_sky, sample_disk SAMA) ...
// [Fungsi-fungsi ini tidak perlu disalin ulang, tidak ada perubahan]
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec3 permute(vec3 x) { return mod289(((x*34.0)+1.0)*x); }
float snoise(vec2 v) {
    const vec4 C = vec4(0.211324865405187, 0.366025403784439, -0.577350269189626, 0.024390243902439);
    vec2 i  = floor(v + dot(v, C.yy)); vec2 x0 = v - i + dot(i, C.xx);
    vec2 i1; i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz; x12.xy -= i1; i = mod289(i);
    vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
    vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
    m = m*m; m = m*m;
    vec3 x = 2.0 * fract(p * C.www) - 1.0; vec3 h = abs(x) - 0.5; vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox; m *= (1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h));
    vec3 g; g.x = a0.x * x0.x + h.x * x0.y; g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
}
float fbm(vec2 uv) {
    float value = 0.0; float amplitude = 0.5; float frequency = 2.0;
    int octaves = 6;
    for (int i = 0; i < octaves; i++) {
        value += amplitude * snoise(uv * frequency);
        amplitude *= 0.5; frequency *= 2.0;
    }
    return (value + 1.0) * 0.5;
}
vec3 setup_camera(vec2 uv) {
    vec3 w = normalize(u_cam_lookat - u_cam_pos);
    vec3 u = normalize(cross(w, vec3(0.0, 1.0, 0.0)));
    vec3 v = cross(u, w);
    float fov = 1.0; 
    vec3 dir = normalize(uv.x * u + uv.y * v + fov * w);
    return dir;
}
vec4 sample_sky(vec3 dir) {
    float u = 0.5 + atan(dir.z, dir.x) / (2.0 * 3.14159265);
    float v = 0.5 - asin(dir.y) / 3.14159265;
    return texture(u_sky_tex, vec2(u, v));
}
vec4 sample_disk(vec3 pos, float r, vec3 view_dir) {
    float theta = atan(pos.z, pos.x);
    float v_scalar = DISK_V_MAX * sqrt(MIN_DISK_R / r);
    vec3 v_dir = normalize(vec3(-pos.z, 0.0, pos.x));
    float gamma = 1.0 / sqrt(1.0 - (v_scalar * v_scalar) / C2);
    float v_dot_d = dot(v_dir * v_scalar, view_dir);
    float doppler_factor = 1.0 / (gamma * (1.0 - v_dot_d / C));
    float brightness_scale = pow(doppler_factor, 3.0);
    vec2 noise_uv = vec2(theta * 1.5, r * 0.5);
    noise_uv.x += (u_time * -0.5) / (log(r) + 1.0);
    float noise_val = fbm(noise_uv);
    float noise_contrast = pow(noise_val, 3.0);
    float temp_t = (r - MIN_DISK_R) / (MAX_DISK_R - MIN_DISK_R);
    temp_t = clamp(1.0 - temp_t, 0.0, 1.0); 
    vec3 color_hot_base = vec3(0.6, 0.1, 0.0);
    vec3 color_hot_highlight = vec3(1.0, 1.0, 0.8);
    vec3 color_cool_base = vec3(0.1, 0.0, 0.0);
    vec3 color_cool_highlight = vec3(0.8, 0.2, 0.0);
    vec3 color_base = mix(color_cool_base, color_hot_base, temp_t);
    vec3 color_highlight = mix(color_cool_highlight, color_hot_highlight, temp_t);
    vec3 color = mix(color_base, color_highlight, noise_contrast);
    color *= brightness_scale;
    float fade_in = smoothstep(MIN_DISK_R, MIN_DISK_R + 0.2, r);
    float fade_out = 1.0 - smoothstep(MAX_DISK_R - 0.5, MAX_DISK_R, r);
    float alpha = fade_in * fade_out;
    return vec4(color, alpha);
}

// --- FUNGSI FISIKA: Disederhanakan ke Post-Newtonian (STABIL) ---
// (Ganti nama kembali ke 'get_acceleration_GR')
vec3 get_acceleration_GR(vec3 pos, vec3 vel) {
    float r2 = dot(pos, pos);
    float r = sqrt(r2);

    // Guard (Jaga-jaga, tapi sekarang seharusnya aman)
    if (r < RS + 0.01) {
        return vec3(0.0);
    }

    float newton_force = -G * M / r2;
    
    // 1. Gaya Gravitasi (Post-Newtonian / Lensing)
    vec3 L = cross(pos, vel);
    float L2 = dot(L, L);
    // Ini adalah koreksi GR yang stabil untuk LENSING
    float gr_correction = (1.0 + (3.0 * L2) / (r2 * C2));
    vec3 accel_gravity = normalize(pos) * newton_force * gr_correction;

    // --- HAPUS GAYA KERR YANG TIDAK STABIL ---
    // (Semua kode 'drag_strength' dan 'accel_drag' dihapus)
    // ---------------------------------
    
    return accel_gravity;
}

// --- FUNGSI INTEGRATOR RK4 ---
struct Derivative { vec3 d_pos; vec3 d_vel; };
struct State { vec3 pos; vec3 vel; };

Derivative get_derivative(State s) {
    Derivative d;
    d.d_pos = s.vel;
    // Panggil fungsi fisika yang sudah stabil
    d.d_vel = get_acceleration_GR(s.pos, s.vel);
    return d;
}

// (Fungsi 'rk4_step' SAMA PERSIS)
State rk4_step(State s, float dt) {
    Derivative k1 = get_derivative(s);
    State s_k2;
    s_k2.pos = s.pos + k1.d_pos * 0.5 * dt;
    s_k2.vel = s.vel + k1.d_vel * 0.5 * dt;
    Derivative k2 = get_derivative(s_k2);
    State s_k3;
    s_k3.pos = s.pos + k2.d_pos * 0.5 * dt;
    s_k3.vel = s.vel + k2.d_vel * 0.5 * dt;
    Derivative k3 = get_derivative(s_k3);
    State s_k4;
    s_k4.pos = s.pos + k3.d_pos * dt;
    s_k4.vel = s.vel + k3.d_vel * dt;
    Derivative k4 = get_derivative(s_k4);

    State s_new;
    s_new.pos = s.pos + (k1.d_pos + 2.0*k2.d_pos + 2.0*k3.d_pos + k4.d_pos) * (dt / 6.0);
    s_new.vel = s.vel + (k1.d_vel + 2.0*k2.d_vel + 2.0*k3.d_vel + k4.d_vel) * (dt / 6.0);
    return s_new;
}

// --- FUNGSI UTAMA (main) ---
// (Tidak berubah)
void main() {
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    State s;
    s.pos = u_cam_pos;
    s.vel = setup_camera(uv) * C;
    
    State s_prev = s; 

    for (int i = 0; i < MAX_STEPS; i++) {
        float r = length(s.pos);
        
        if (r <= SHADOW_R) { // (SHADOW_R = 0.5)
            f_color = vec4(0.0, 0.0, 0.0, 1.0); 
            return;
        }
        
        bool crossed_plane = (s_prev.pos.y > 0.0 && s.pos.y <= 0.0) || 
                             (s_prev.pos.y < 0.0 && s.pos.y >= 0.0);
                             
        if (crossed_plane && r > MIN_DISK_R && r < MAX_DISK_R) {
            vec3 view_dir = normalize(s.vel);
            vec4 disk_color = sample_disk(s.pos, r, view_dir);
            vec4 sky_color = sample_sky(view_dir); 
            f_color = mix(sky_color, disk_color, disk_color.a);
            return;
        }

        if (r > MAX_DIST) {
            f_color = sample_sky(normalize(s.vel));
            return;
        }
        
        s_prev = s; 
        s = rk4_step(s, DT); // Integrasi RK4
    }
    
    f_color = sample_sky(normalize(s.vel));
}