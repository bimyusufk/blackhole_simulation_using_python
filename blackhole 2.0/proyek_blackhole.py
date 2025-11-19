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
                         caption="Proyek Black Hole 3D (Kerr Approx + RK4)", 
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
            
        # 5. Set Uniform Awal
        self.prog['u_resolution'].value = (self.width, self.height)
        self.start_time = 0.0

        # 6. Status Kamera Orbit
        self.cam_radius = 20.0
        self.cam_azimuth = np.pi / 4.0
        self.cam_elevation = np.pi / 6.0
        
        self.mouse_pressed = False
        self.mouse_sensitivity = 0.005
        self.zoom_sensitivity = 1.0

    def on_draw(self):
        if not hasattr(self, 'prog'):
            return 
        
        self.clear()
        
        # Update uniform waktu
        self.prog['u_time'].value = self.start_time
        self.start_time += 0.005 
        
        # Logika Kamera Orbit
        cam_x = self.cam_radius * np.cos(self.cam_elevation) * np.sin(self.cam_azimuth)
        cam_y = self.cam_radius * np.sin(self.cam_elevation)
        cam_z = self.cam_radius * np.cos(self.cam_elevation) * np.cos(self.cam_azimuth)
        
        self.prog['u_cam_pos'].value = (cam_x, cam_y, cam_z)
        self.prog['u_cam_lookat'].value = (0.0, 0.0, 0.0)

        # Render quad
        self.vao.render()

    def on_resize(self, width, height):
        if hasattr(self, 'prog'):
            self.ctx.viewport = (0, 0, width, height)
            self.prog['u_resolution'].value = (width, height)

    # --- Kontrol Kamera ---
    def on_mouse_press(self, x, y, button, modifiers):
        if button == mouse.LEFT: self.mouse_pressed = True
    
    def on_mouse_release(self, x, y, button, modifiers):
        if button == mouse.LEFT: self.mouse_pressed = False
            
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.mouse_pressed:
            self.cam_azimuth += dx * self.mouse_sensitivity
            self.cam_elevation -= dy * self.mouse_sensitivity
            self.cam_elevation = np.clip(self.cam_elevation, -np.pi/2 + 0.01, np.pi/2 - 0.01)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.cam_radius -= scroll_y * self.zoom_sensitivity
        self.cam_radius = max(3.0, self.cam_radius)

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ESCAPE: pyglet.app.exit()

if __name__ == "__main__":
    app = BlackHoleRenderer()
    pyglet.app.run()