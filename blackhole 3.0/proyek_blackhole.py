import pyglet
import moderngl
import numpy as np
from PIL import Image
from pyglet.window import key, mouse

# --- Konfigurasi Jendela ---
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

class BlackHoleRenderer(pyglet.window.Window):
    def __init__(self):
        super().__init__(width=WINDOW_WIDTH, height=WINDOW_HEIGHT,
                         caption="Proyek Black Hole 3D (Euler Stabil + Kontrol Penuh)", 
                         resizable=True)
        
        # 1. Konteks ModernGL
        self.ctx = moderngl.create_context(require=330)

        # 2. Muat Shader UTAMA
        try:
            with open('blackhole.vert', 'r') as f:
                vertex_shader_source = f.read()
            with open('blackhole.frag', 'r') as f:
                fragment_shader_source = f.read()
            self.prog = self.ctx.program(
                vertex_shader=vertex_shader_source,
                fragment_shader=fragment_shader_source
            )
        except Exception as e:
            print("Error saat kompilasi shader (blackhole.vert/frag):")
            print(e); pyglet.app.exit(); return

        # 3. Geometri (Quad Layar Penuh)
        vertices = np.array([-1.0, -1.0, 1.0, -1.0, -1.0,  1.0, 1.0,  1.0], dtype='f4')
        indices = np.array([0, 1, 2, 1, 3, 2], dtype='i4')
        vbo = self.ctx.buffer(vertices.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())
        self.vao = self.ctx.vertex_array(self.prog, [(vbo, '2f', 'in_vert')], ibo)

        # 4. Muat Tekstur Skybox
        try:
            img_sky = Image.open('skybox.jpg').convert('RGB')
            self.sky_texture = self.ctx.texture(img_sky.size, 3, img_sky.tobytes())
            self.sky_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self.sky_texture.use(0) # Bind ke unit 0
            self.prog['u_sky_tex'].value = 0
            
        except FileNotFoundError as e:
            print(f"Error: File tekstur 'skybox.jpg' tidak ditemukan."); pyglet.app.exit(); return
        except KeyError:
             print("Error: Gagal menemukan uniform 'u_sky_tex'. Pastikan shader tidak error.");
             pass
            
        # 5. Set Uniform Awal
        try:
            self.prog['u_resolution'].value = (self.width, self.height)
        except KeyError: pass 
        
        self.start_time = 0.0

        # --- DIPERBARUI: 6. Status Kamera Orbit ---
        
        # Simpan nilai default untuk reset
        self.DEFAULT_CAM_RADIUS = 20.0
        self.DEFAULT_CAM_AZIMUTH = np.pi / 4.0
        self.DEFAULT_CAM_ELEVATION = np.pi / 6.0
        self.DEFAULT_CAM_TARGET = np.array([0.0, 0.0, 0.0], dtype='f4')

        # Variabel status saat ini
        self.cam_radius = self.DEFAULT_CAM_RADIUS
        self.cam_azimuth = self.DEFAULT_CAM_AZIMUTH
        self.cam_elevation = self.DEFAULT_CAM_ELEVATION
        self.cam_target = np.copy(self.DEFAULT_CAM_TARGET) # Target pan
        
        # Vektor arah kamera (untuk pan)
        self.camera_right = np.array([1.0, 0.0, 0.0], dtype='f4')
        self.camera_up = np.array([0.0, 1.0, 0.0], dtype='f4')
        
        # Status mouse
        self.mouse_pressed = False # Klik kiri (rotasi)
        self.pan_pressed = False   # Klik kanan (pan)
        self.mouse_sensitivity = 0.005
        self.pan_sensitivity = 0.01 # Kecepatan pan bisa diatur
        self.zoom_sensitivity = 1.0

    def on_draw(self):
        if not hasattr(self, 'prog'):
            return 
        
        self.clear()
        
        # --- DIPERBARUI: Error Handling Terisolasi ---
        try:
            self.prog['u_time'].value = self.start_time
            self.start_time += 0.005 
        except KeyError: pass # Abaikan jika 'u_time' dioptimalkan

        # --- TAMBAHAN BARU: Rotasi Otomatis ---
        if not self.mouse_pressed and not self.pan_pressed:
            self.cam_azimuth += 0.0005 
        # ------------------------------------
        
        # 1. Hitung posisi orbit relatif terhadap target
        cam_x_rel = self.cam_radius * np.cos(self.cam_elevation) * np.sin(self.cam_azimuth)
        cam_y_rel = self.cam_radius * np.sin(self.cam_elevation)
        cam_z_rel = self.cam_radius * np.cos(self.cam_elevation) * np.cos(self.cam_azimuth)
        
        cam_pos_relative = np.array([cam_x_rel, cam_y_rel, cam_z_rel])
        
        # 2. Hitung posisi kamera final (orbit + pan target)
        cam_pos_final = cam_pos_relative + self.cam_target

        # 3. Hitung vektor 'kanan' dan 'atas' untuk logika pan
        forward_vec = -cam_pos_relative
        norm = np.linalg.norm(forward_vec)
        if norm > 0.001:
            forward_vec /= norm
        
        world_up = np.array([0.0, 1.0, 0.0])
        self.camera_right = np.cross(forward_vec, world_up)
        norm = np.linalg.norm(self.camera_right)
        if norm < 0.001: # Jika melihat lurus ke atas/bawah (gimbal lock)
            self.camera_right = np.array([np.cos(self.cam_azimuth), 0.0, -np.sin(self.cam_azimuth)])
        else:
            self.camera_right /= norm
            
        self.camera_up = np.cross(self.camera_right, forward_vec)

        # 4. Kirim data ke shader (HARUS BERHASIL)
        try:
            self.prog['u_cam_pos'].value = tuple(cam_pos_final)
            self.prog['u_cam_lookat'].value = tuple(self.cam_target)
        except KeyError as e:
            print(f"CRITICAL ERROR: Tidak dapat mengatur uniform kamera: {e}")
            # (Jika ini gagal, layar akan hitam)
            pass 

        # 5. Render
        self.vao.render()

    def on_resize(self, width, height):
        if hasattr(self, 'prog'):
            self.ctx.viewport = (0, 0, width, height)
            try:
                self.prog['u_resolution'].value = (width, height)
            except KeyError: pass

    # --- Kontrol Kamera ---
    def on_mouse_press(self, x, y, button, modifiers):
        if button == mouse.LEFT: 
            self.mouse_pressed = True
        elif button == mouse.RIGHT: # Tambahan untuk pan
            self.pan_pressed = True
    
    def on_mouse_release(self, x, y, button, modifiers):
        if button == mouse.LEFT: 
            self.mouse_pressed = False
        elif button == mouse.RIGHT: # Tambahan untuk pan
            self.pan_pressed = False
            
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        # Logika Rotasi (Klik Kiri)
        if self.mouse_pressed:
            self.cam_azimuth += dx * self.mouse_sensitivity
            self.cam_elevation -= dy * self.mouse_sensitivity
            self.cam_elevation = np.clip(self.cam_elevation, -np.pi/2 + 0.01, np.pi/2 - 0.01)
        
        # Logika Pan/Geser (Klik Kanan)
        if self.pan_pressed:
            self.cam_target -= self.camera_right * dx * self.pan_sensitivity
            self.cam_target += self.camera_up * dy * self.pan_sensitivity

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.cam_radius -= scroll_y * self.zoom_sensitivity
        self.cam_radius = max(3.0, self.cam_radius)

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ESCAPE: 
            pyglet.app.exit()
        
        # Tambahan untuk Reset Kamera
        if symbol == key.SPACE:
            self.cam_radius = self.DEFAULT_CAM_RADIUS
            self.cam_azimuth = self.DEFAULT_CAM_AZIMUTH
            self.cam_elevation = self.DEFAULT_CAM_ELEVATION
            self.cam_target = np.copy(self.DEFAULT_CAM_TARGET)

if __name__ == "__main__":
    app = BlackHoleRenderer()
    pyglet.app.run()