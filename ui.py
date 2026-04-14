from settings import *
from meshes.base_mesh import BaseMesh
import numpy as np
import moderngl as mgl
import pygame as pg
import glm
from meshes.item_mesh import ItemMesh

class CrosshairMesh(BaseMesh):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.quad
        self.vbo_format = '3f 3f'
        self.attrs = ('in_position', 'in_color')
        self.vao = self.get_vao()

    def get_vertex_data(self):
        w = 0.015
        h = w * ASPECT_RATIO
        # Creates a perfect '+' sign in the center of the screen
        vertices = [
            # Horizontal line
            (-w, -0.002 * ASPECT_RATIO, 0.0), (w, -0.002 * ASPECT_RATIO, 0.0), (w, 0.002 * ASPECT_RATIO, 0.0),
            (-w, -0.002 * ASPECT_RATIO, 0.0), (w, 0.002 * ASPECT_RATIO, 0.0), (-w, 0.002 * ASPECT_RATIO, 0.0),
            # Vertical line
            (-0.002, -h, 0.0), (0.002, -h, 0.0), (0.002, h, 0.0),
            (-0.002, -h, 0.0), (0.002, h, 0.0), (-0.002, h, 0.0)
        ]
        colors = [(0.9, 0.9, 0.9) for _ in vertices]
        return np.hstack([vertices, colors]).astype('float32')

class BlockIconMesh(BaseMesh):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.ui_block
        self.vbo_format = '2f 2f'
        self.attrs = ('in_position', 'in_tex_coord')
        self.vao = self.get_vao()

    def get_vertex_data(self):
        # Standard normalized quad [-1, 1]
        vertices = [
            (-1.0, -1.0), ( 1.0, -1.0), ( 1.0,  1.0),
            (-1.0, -1.0), ( 1.0,  1.0), (-1.0,  1.0)
        ]
        tex_coords = [(0, 0), (1, 0), (1, 1), (0, 0), (1, 1), (0, 1)]
        return np.hstack([vertices, tex_coords]).astype('float32')

class UIColorMesh(BaseMesh):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.ui_color
        self.vbo_format = '2f'
        self.attrs = ('in_position',)
        self.vao = self.get_vao()

    def get_vertex_data(self):
        vertices = [
            (-1.0, -1.0), ( 1.0, -1.0), ( 1.0,  1.0),
            (-1.0, -1.0), ( 1.0,  1.0), (-1.0,  1.0)
        ]
        return np.array(vertices, dtype='float32')

class UITextMesh(BaseMesh):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.ui_text
        self.vbo_format = '2f 2f'
        self.attrs = ('in_position', 'in_tex_coord')
        self.vao = self.get_vao()

    def get_vertex_data(self):
        vertices = [
            (-1.0, -1.0), ( 1.0, -1.0), ( 1.0,  1.0),
            (-1.0, -1.0), ( 1.0,  1.0), (-1.0,  1.0)
        ]
        tex_coords = [(0, 0), (1, 0), (1, 1), (0, 0), (1, 1), (0, 1)]
        return np.hstack([vertices, tex_coords]).astype('float32')

class TextRenderer:
    def __init__(self, app):
        self.app = app
        self.ctx = app.ctx
        pg.font.init()
        self.font = pg.font.SysFont('arial', 20, bold=True)
        self.textures = {}

    def get_texture(self, text):
        if text in self.textures:
            return self.textures[text]
        surf = self.font.render(text, True, (210, 210, 210)) # Light grey instead of pure white
        shadow_offset = max(2, self.font.get_height() // 15)
        bg_surf = pg.Surface((surf.get_width() + shadow_offset, surf.get_height() + shadow_offset), pg.SRCALPHA)
        shadow = self.font.render(text, True, (40, 40, 40))
        bg_surf.blit(shadow, (shadow_offset, shadow_offset))
        bg_surf.blit(surf, (0, 0))
        texture = self.ctx.texture(bg_surf.get_size(), 4, pg.image.tostring(bg_surf, 'RGBA', True))
        texture.build_mipmaps()
        texture.filter = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR)
        self.textures[text] = texture
        return texture

class Crosshair:
    def __init__(self, app):
        self.app = app
        self.mesh = CrosshairMesh(app)

    def render(self):
        self.mesh.render()

class Hotbar:
    def __init__(self, app):
        self.app = app
        self.block_mesh = BlockIconMesh(app)
        self.color_mesh = UIColorMesh(app)
        self.text_mesh = UITextMesh(app)
        self.text_renderer = TextRenderer(app)
        
    def render(self):
        player = self.app.player
        s = HOTBAR_SCALE
        slot_s = SLOT_SCALE
        gap = 0.01
        x_spacing = (slot_s * 2 + gap) / ASPECT_RATIO
        start_x = -4 * x_spacing
        y = HOTBAR_Y
        
        # 1. Draw the transparent slot backgrounds and selection frame
        for i in range(9):
            x = start_x + i * x_spacing
            is_selected = (i == player.hotbar_index)
            
            if is_selected:
                # Draw white outline frame
                sel_s = slot_s + 0.006
                self.color_mesh.program['u_scale'] = (sel_s / ASPECT_RATIO, sel_s)
                self.color_mesh.program['u_offset'] = (x, y)
                self.color_mesh.program['u_color'] = (0.9, 0.9, 0.9, 0.9)
                self.color_mesh.render()
                
                # Draw slightly lighter inner background
                self.color_mesh.program['u_scale'] = (slot_s / ASPECT_RATIO, slot_s)
                self.color_mesh.program['u_color'] = (0.5, 0.5, 0.5, 0.7)
                self.color_mesh.render()
            else:
                # Draw standard dark background
                self.color_mesh.program['u_scale'] = (slot_s / ASPECT_RATIO, slot_s)
                self.color_mesh.program['u_offset'] = (x, y)
                self.color_mesh.program['u_color'] = (0.2, 0.2, 0.2, 0.6)
                self.color_mesh.render()

        # 2. Draw the 3D block icons inside the slots
        for i in range(9):
            voxel_id = player.inventory[i]
            if voxel_id != 0:
                self.block_mesh.program['u_scale'] = (s / ASPECT_RATIO, s)
                self.block_mesh.program['u_offset'] = (start_x + i * x_spacing, y)
                self.block_mesh.program['voxel_id'] = voxel_id
                self.block_mesh.render()

        # 3. Draw the stack counts
        for i in range(9):
            count = player.inventory_counts[i]
            if count > 0:
                tex = self.text_renderer.get_texture(str(count))
                tex.use(location=4)
                
                tex_w, tex_h = tex.size
                scale_y = 0.025
                scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
                
                offset_x = start_x + i * x_spacing + 0.015
                offset_y = y - 0.025
                
                self.text_mesh.program['u_scale'] = (scale_x, scale_y)
                self.text_mesh.program['u_offset'] = (offset_x, offset_y)
                self.text_mesh.render()

        # 4. Draw Survival Stats (Health, Hunger, Oxygen)
        if player.game_mode == SURVIVAL:
            # Helper to draw a stat bar
            def draw_bar(ratio, offset_x, offset_y, bg_color, fg_color, text):
                # Background
                self.color_mesh.program['u_scale'] = (0.2, 0.01)
                self.color_mesh.program['u_offset'] = (offset_x, offset_y)
                self.color_mesh.program['u_color'] = bg_color
                self.color_mesh.render()
                
                # Foreground
                if ratio > 0:
                    self.color_mesh.program['u_scale'] = (0.2 * ratio, 0.01)
                    self.color_mesh.program['u_offset'] = (offset_x - 0.2*(1.0 - ratio), offset_y)
                    self.color_mesh.program['u_color'] = fg_color
                    self.color_mesh.render()
                    
                # Text
                tex = self.text_renderer.get_texture(text)
                tex.use(location=4)
                scale_y = 0.015
                scale_x = scale_y * (tex.size[0] / tex.size[1]) / ASPECT_RATIO
                self.text_mesh.program['u_scale'] = (scale_x, scale_y)
                self.text_mesh.program['u_offset'] = (offset_x, offset_y)
                self.text_mesh.render()

            health_ratio = max(0.0, player.health / player.max_health)
            draw_bar(health_ratio, -0.22, y + 0.08, (0.1, 0.1, 0.1, 0.8), (0.8, 0.1, 0.1, 0.9), 
                     f"HP: {int(player.health)}/{player.max_health}")

            hunger_ratio = max(0.0, player.hunger / player.max_hunger)
            draw_bar(hunger_ratio, 0.22, y + 0.08, (0.1, 0.1, 0.1, 0.8), (0.8, 0.5, 0.1, 0.9), 
                     f"Food: {int(player.hunger)}/{player.max_hunger}")

            if player.oxygen < player.max_oxygen:
                oxy_ratio = max(0.0, player.oxygen / player.max_oxygen)
                draw_bar(oxy_ratio, 0.22, y + 0.12, (0.1, 0.1, 0.1, 0.8), (0.1, 0.6, 0.9, 0.9), 
                         f"O2: {int(player.oxygen)}/{player.max_oxygen}")

class HeldBlock:
    def __init__(self, app):
        self.app = app
        self.mesh = ItemMesh(app)

    def render(self):
        player = self.app.player
        voxel_id = player.inventory[player.hotbar_index]
        if voxel_id == 0:
            return

        # 1. View bobbing
        bob_offset_y = glm.sin(player.step_counter) * 0.03
        bob_offset_x = glm.cos(player.step_counter * 0.5) * 0.02

        # 2. Swinging animation
        swing_offset_y = 0.0
        swing_offset_z = 0.0
        swing_rot_x = 0.0
        
        if player.mining_time > 0.0:
            swing_val = max(0, glm.sin(player.mining_time * 0.03))
            swing_offset_y = swing_val * 0.15
            swing_offset_z = -swing_val * 0.1
            swing_rot_x = swing_val * 0.4
        else:
            time_since_place = pg.time.get_ticks() - player.interaction_timer
            if time_since_place < player.interaction_delay:
                progress = time_since_place / player.interaction_delay
                swing_val = glm.sin(progress * glm.pi())
                swing_offset_y = swing_val * 0.2
                swing_rot_x = swing_val * 0.3

        # 3. Position the block in the bottom right (in local camera space)
        pos = glm.vec3(0.5 + bob_offset_x, -0.4 + bob_offset_y - swing_offset_y, -1.0 + swing_offset_z)
        
        # Compute Model Matrix in World Space for perfectly accurate lighting
        m_model = glm.inverse(player.m_view)
        m_model = glm.translate(m_model, pos)
        m_model = glm.rotate(m_model, glm.radians(-15.0) - swing_rot_x, glm.vec3(1, 0, 0)) # Tilt slightly down
        m_model = glm.rotate(m_model, glm.radians(45.0), glm.vec3(0, 1, 0))                # Rotate to show faces
        m_model = glm.scale(m_model, glm.vec3(0.35))

        self.mesh.program['m_proj'].write(player.m_proj)
        self.mesh.program['m_view'].write(player.m_view) 
        self.mesh.program['m_model'].write(m_model)
        self.mesh.program['voxel_id'] = voxel_id

        self.app.ctx.disable(mgl.DEPTH_TEST) # Draw on top of the world without depth clearing
        self.mesh.render()
        self.app.ctx.enable(mgl.DEPTH_TEST)

class InventoryUI:
    def __init__(self, app):
        self.app = app
        self.block_mesh = BlockIconMesh(app)
        self.color_mesh = UIColorMesh(app)
        self.text_mesh = UITextMesh(app)
        self.text_renderer = TextRenderer(app)
        
        self.drag_id = 0
        self.drag_count = 0
        self.drag_start_pos = (0, 0)

    def get_slot_pos(self, i):
        gap = 0.01
        x_spacing = (SLOT_SCALE * 2 + gap) / ASPECT_RATIO
        y_spacing = SLOT_SCALE * 2 + gap
        
        col = i % 9
        x = -4 * x_spacing + col * x_spacing
        if i < 9:
            y = HOTBAR_Y # Hotbar
        else:
            row = 2 - ((i - 9) // 9) # Map 9-17 to bottom row, 18-26 middle, 27-35 top
            y = HOTBAR_Y + (row + 1.5) * y_spacing
        return x, y

    def get_slot_at_mouse(self, mouse_pos):
        mx = (mouse_pos[0] / WIN_RES.x) * 2.0 - 1.0
        my = 1.0 - (mouse_pos[1] / WIN_RES.y) * 2.0
        
        slot_w = SLOT_SCALE / ASPECT_RATIO
        slot_h = SLOT_SCALE
        
        for i in range(36):
            sx, sy = self.get_slot_pos(i)
            if sx - slot_w < mx < sx + slot_w and sy - slot_h < my < sy + slot_h:
                return i
        return -1

    def get_closest_valid_slot(self, mouse_pos, drag_id, drag_count):
        mx = (mouse_pos[0] / WIN_RES.x) * 2.0 - 1.0
        my = 1.0 - (mouse_pos[1] / WIN_RES.y) * 2.0
        
        best_i = -1
        best_dist_sq = float('inf')
        gap = 0.01
        y_spacing = SLOT_SCALE * 2 + gap
        # Max snap distance based on UI scale
        max_dist_sq = (y_spacing * 1.5) ** 2 
        
        player = self.app.player
        
        for i in range(36):
            sx, sy = self.get_slot_pos(i)
            dx = (mx - sx) * ASPECT_RATIO
            dy = my - sy
            dist_sq = dx*dx + dy*dy
            
            if dist_sq < best_dist_sq and dist_sq < max_dist_sq:
                slot_id = player.inventory[i]
                if slot_id == 0 or (slot_id == drag_id and player.inventory_counts[i] < 64):
                    best_i = i
                    best_dist_sq = dist_sq
        return best_i

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            i = self.get_slot_at_mouse(pg.mouse.get_pos())
            if i != -1:
                player = self.app.player
                slot_id = player.inventory[i]
                slot_count = player.inventory_counts[i]
                
                if event.button == 1: # Left click (Pick up stack / Swap / Place stack)
                    if self.drag_id == 0:
                        if slot_id != 0:
                            self.drag_id = slot_id
                            self.drag_count = slot_count
                            player.inventory[i] = 0
                            player.inventory_counts[i] = 0
                            self.drag_start_pos = pg.mouse.get_pos()
                    else:
                        if slot_id == 0:
                            player.inventory[i] = self.drag_id
                            player.inventory_counts[i] = self.drag_count
                            self.drag_id = 0
                            self.drag_count = 0
                        elif slot_id == self.drag_id:
                            space = 64 - slot_count
                            if space >= self.drag_count:
                                player.inventory_counts[i] += self.drag_count
                                self.drag_id = 0
                                self.drag_count = 0
                            else:
                                player.inventory_counts[i] = 64
                                self.drag_count -= space
                        else:
                            player.inventory[i], self.drag_id = self.drag_id, slot_id
                            player.inventory_counts[i], self.drag_count = self.drag_count, slot_count
                            self.drag_start_pos = pg.mouse.get_pos()
                elif event.button == 3: # Right click (Split half / Place one)
                    if self.drag_id == 0:
                        if slot_id != 0:
                            half = slot_count - (slot_count // 2)
                            self.drag_id = slot_id
                            self.drag_count = half
                            player.inventory_counts[i] -= half
                            if player.inventory_counts[i] <= 0:
                                player.inventory[i] = 0
                            self.drag_start_pos = pg.mouse.get_pos()
                    else:
                        if slot_id == 0:
                            player.inventory[i] = self.drag_id
                            player.inventory_counts[i] = 1
                            self.drag_count -= 1
                            if self.drag_count <= 0: self.drag_id = 0
                        elif slot_id == self.drag_id and slot_count < 64:
                            player.inventory_counts[i] += 1
                            self.drag_count -= 1
                            if self.drag_count <= 0: self.drag_id = 0
        elif event.type == pg.MOUSEBUTTONUP:
            if event.button == 1 and self.drag_id != 0:
                mouse_pos = pg.mouse.get_pos()
                dx = mouse_pos[0] - self.drag_start_pos[0]
                dy = mouse_pos[1] - self.drag_start_pos[1]
                
                # Check if mouse moved more than 10 pixels (to separate drag from standard click)
                if dx*dx + dy*dy > 100: 
                    i = self.get_closest_valid_slot(mouse_pos, self.drag_id, self.drag_count)
                    if i != -1:
                        player = self.app.player
                        slot_id = player.inventory[i]
                        slot_count = player.inventory_counts[i]
                        
                        if slot_id == 0:
                            player.inventory[i] = self.drag_id
                            player.inventory_counts[i] = self.drag_count
                            self.drag_id = 0
                            self.drag_count = 0
                        elif slot_id == self.drag_id:
                            space = 64 - slot_count
                            if space >= self.drag_count:
                                player.inventory_counts[i] += self.drag_count
                                self.drag_id = 0
                                self.drag_count = 0
                            else:
                                player.inventory_counts[i] = 64
                                self.drag_count -= space

    def close(self):
        if self.drag_id != 0:
            player = self.app.player
            # Re-inject leftover dragged item or drop it!
            while self.drag_count > 0:
                if not player.add_item(self.drag_id):
                    # Inventory completely full, drop in the world
                    for _ in range(self.drag_count):
                        self.app.scene.item_manager.add_item(player.position, self.drag_id)
                    break
                self.drag_count -= 1
            self.drag_id = 0
            self.drag_count = 0

    def render(self):
        gap = 0.01
        x_spacing = (SLOT_SCALE * 2 + gap) / ASPECT_RATIO
        y_spacing = SLOT_SCALE * 2 + gap
        bg_w = 4.5 * x_spacing + 0.02
        bg_h = 1.5 * y_spacing + 0.02
        
        self.color_mesh.program['u_scale'] = (bg_w, bg_h)
        self.color_mesh.program['u_offset'] = (0.0, HOTBAR_Y + 2.5 * y_spacing)
        self.color_mesh.program['u_color'] = (0.2, 0.2, 0.2, 0.95)
        self.color_mesh.render()

        player = self.app.player
        hover_idx = self.get_slot_at_mouse(pg.mouse.get_pos())
        
        for i in range(36):
            x, y = self.get_slot_pos(i)
            s = SLOT_SCALE
            
            if i == hover_idx:
                self.color_mesh.program['u_scale'] = ((s+0.005) / ASPECT_RATIO, s+0.005)
                self.color_mesh.program['u_offset'] = (x, y)
                self.color_mesh.program['u_color'] = (0.9, 0.9, 0.9, 0.5)
                self.color_mesh.render()

            self.color_mesh.program['u_scale'] = (s / ASPECT_RATIO, s)
            self.color_mesh.program['u_offset'] = (x, y)
            self.color_mesh.program['u_color'] = (0.3, 0.3, 0.3, 0.8)
            self.color_mesh.render()

            voxel_id = player.inventory[i]
            if voxel_id != 0:
                self.block_mesh.program['u_scale'] = (HOTBAR_SCALE / ASPECT_RATIO, HOTBAR_SCALE)
                self.block_mesh.program['u_offset'] = (x, y)
                self.block_mesh.program['voxel_id'] = voxel_id
                self.block_mesh.render()

            count = player.inventory_counts[i]
            if count > 0:
                tex = self.text_renderer.get_texture(str(count))
                tex.use(location=4)
                scale_y = 0.025
                scale_x = scale_y * (tex.size[0] / tex.size[1]) / ASPECT_RATIO
                self.text_mesh.program['u_scale'] = (scale_x, scale_y)
                self.text_mesh.program['u_offset'] = (x + 0.015, y - 0.025)
                self.text_mesh.render()

        # Dragged Item Render (Follows Mouse Cursor)
        if self.drag_id != 0:
            mouse_pos = pg.mouse.get_pos()
            mx = (mouse_pos[0] / WIN_RES.x) * 2.0 - 1.0
            my = 1.0 - (mouse_pos[1] / WIN_RES.y) * 2.0
            
            self.block_mesh.program['u_scale'] = (HOTBAR_SCALE / ASPECT_RATIO, HOTBAR_SCALE)
            self.block_mesh.program['u_offset'] = (mx, my)
            self.block_mesh.program['voxel_id'] = self.drag_id
            self.block_mesh.render()
            
            if self.drag_count > 0:
                tex = self.text_renderer.get_texture(str(self.drag_count))
                tex.use(location=4)
                scale_y = 0.025
                scale_x = scale_y * (tex.size[0] / tex.size[1]) / ASPECT_RATIO
                self.text_mesh.program['u_scale'] = (scale_x, scale_y)
                self.text_mesh.program['u_offset'] = (mx + 0.015, my - 0.025)
                self.text_mesh.render()

class Button:
    def __init__(self, app, text, pos, size, action):
        self.app = app
        self.text = text
        self.pos = pos
        self.size = size
        self.action = action

        self.color_mesh = UIColorMesh(app)
        self.text_renderer = TextRenderer(app)
        self.text_renderer.font = pg.font.SysFont('arial', 40, bold=True)
        self.text_mesh = UITextMesh(app)

        self.is_hovered = False
        self.base_color = (0.2, 0.2, 0.2, 0.7)
        self.hover_color = (0.3, 0.3, 0.3, 0.8)

    def check_hover(self, mouse_pos):
        x, y = self.pos
        w, h = self.size
        
        # Convert normalized screen coords to pixel coords
        mouse_x, mouse_y = mouse_pos
        win_w, win_h = WIN_RES
        
        # Convert button normalized pos/size to pixel coords
        btn_x = (x + 1) * 0.5 * win_w
        btn_y = (-y + 1) * 0.5 * win_h
        btn_w = w * 0.5 * win_w
        btn_h = h * 0.5 * win_h
        
        self.is_hovered = btn_x - btn_w < mouse_x < btn_x + btn_w and \
                          btn_y - btn_h < mouse_y < btn_y + btn_h
        return self.is_hovered

    def render(self):
        # 1. Render background
        color = self.hover_color if self.is_hovered else self.base_color
        self.color_mesh.program['u_scale'] = (self.size[0], self.size[1])
        self.color_mesh.program['u_offset'] = self.pos
        self.color_mesh.program['u_color'] = color
        self.color_mesh.render()

        # 2. Render text
        tex = self.text_renderer.get_texture(self.text)
        tex.use(location=4)
        
        tex_w, tex_h = tex.size
        scale_y = self.size[1] * 0.5
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = self.pos
        self.text_mesh.render()

class Menu:
    def __init__(self, app):
        self.app = app
        self.title_renderer = TextRenderer(app)
        self.title_renderer.font = pg.font.SysFont('arial', 180, bold=True)
        self.title_mesh = UITextMesh(app)

        self.buttons = [
            Button(app, 'Start Game', (0, 0.15), (0.2, 0.07), self.app.init_game_session),
            Button(app, 'Options', (0, 0.0), (0.2, 0.07), self.open_options),
            Button(app, 'Quit', (0, -0.15), (0.2, 0.07), self.app.quit_game)
        ]

    def open_options(self):
        self.app.options_menu.previous_state = 'MAIN_MENU'
        self.app.game_state = 'OPTIONS'

    def update(self):
        mouse_pos = pg.mouse.get_pos()
        for button in self.buttons:
            button.check_hover(mouse_pos)

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.is_hovered:
                    button.action()
                    break

    def render(self):
        # Render title
        tex = self.title_renderer.get_texture("Voxel Engine")
        tex.use(location=4)
        
        tex_w, tex_h = tex.size
        scale_y = 0.1
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        self.title_mesh.program['u_scale'] = (scale_x, scale_y)
        self.title_mesh.program['u_offset'] = (0.0, 0.5)
        self.title_mesh.render()

        # Render buttons
        for button in self.buttons:
            button.render()

class PauseMenu:
    def __init__(self, app):
        self.app = app
        self.title_renderer = TextRenderer(app)
        self.title_renderer.font = pg.font.SysFont('arial', 160, bold=True)
        self.title_mesh = UITextMesh(app)
        self.bg_mesh = UIColorMesh(app)

        self.buttons = [
            Button(app, 'Resume', (0, 0.15), (0.3, 0.07), self.resume_game),
            Button(app, 'Options', (0, 0.0), (0.3, 0.07), self.open_options),
            Button(app, 'Quit to Menu', (0, -0.15), (0.3, 0.07), self.quit_to_menu)
        ]

    def open_options(self):
        self.app.options_menu.previous_state = 'PAUSED'
        self.app.game_state = 'OPTIONS'

    def resume_game(self):
        self.app.game_state = 'IN_GAME'
        pg.event.set_grab(True)
        pg.mouse.set_visible(False)

    def quit_to_menu(self):
        self.app.game_state = 'MAIN_MENU'
        if self.app.scene:
            self.app.scene.world.save()
            self.app.scene = None # Unload the world to free memory

    def update(self):
        mouse_pos = pg.mouse.get_pos()
        for button in self.buttons:
            button.check_hover(mouse_pos)

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.is_hovered:
                    button.action()
                    break

    def render(self):
        self.bg_mesh.program['u_scale'] = (1.0, 1.0)
        self.bg_mesh.program['u_offset'] = (0.0, 0.0)
        self.bg_mesh.program['u_color'] = (0.0, 0.0, 0.0, 0.6)
        self.bg_mesh.render()

        tex = self.title_renderer.get_texture("Game Paused")
        tex.use(location=4)
        tex_w, tex_h = tex.size
        scale_y = 0.08
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        self.title_mesh.program['u_scale'] = (scale_x, scale_y)
        self.title_mesh.program['u_offset'] = (0.0, 0.4)
        self.title_mesh.render()

        for button in self.buttons:
            button.render()

class Slider:
    def __init__(self, app, text, pos, size, min_val, max_val, config_key, action=None, is_int=False):
        self.app = app
        self.text = text
        self.pos = pos
        self.size = size
        self.min_val = min_val
        self.max_val = max_val
        self.config_key = config_key
        self.action = action
        self.is_int = is_int

        self.color_mesh = UIColorMesh(app)
        self.text_renderer = TextRenderer(app)
        self.text_renderer.font = pg.font.SysFont('arial', 30, bold=True)
        self.text_mesh = UITextMesh(app)

        self.is_hovered = False
        self.is_dragging = False

    def update(self):
        mouse_pos = pg.mouse.get_pos()
        x, y = self.pos
        w, h = self.size
        win_w, win_h = WIN_RES
        
        btn_x = (x + 1) * 0.5 * win_w
        btn_y = (-y + 1) * 0.5 * win_h
        btn_w = w * 0.5 * win_w
        btn_h = h * 0.5 * win_h
        
        self.is_hovered = btn_x - btn_w < mouse_pos[0] < btn_x + btn_w and \
                          btn_y - btn_h < mouse_pos[1] < btn_y + btn_h

        if self.is_dragging:
            if not pg.mouse.get_pressed()[0]:
                self.is_dragging = False
                self.app.save_config()
            else:
                progress = (mouse_pos[0] - (btn_x - btn_w)) / (btn_w * 2)
                progress = max(0.0, min(1.0, progress))
                val = self.min_val + progress * (self.max_val - self.min_val)
                
                if self.is_int:
                    val = int(round(val))
                elif self.config_key == 'sensitivity':
                    val = round(val, 4)
                    
                self.app.config[self.config_key] = val
                if self.action:
                    self.action(val)

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.is_dragging = True

    def render(self):
        self.color_mesh.program['u_scale'] = (self.size[0], self.size[1])
        self.color_mesh.program['u_offset'] = self.pos
        self.color_mesh.program['u_color'] = (0.1, 0.1, 0.1, 0.8)
        self.color_mesh.render()
        
        val = self.app.config[self.config_key]
        progress = (val - self.min_val) / (self.max_val - self.min_val)
        
        fill_w = self.size[0] * progress
        fill_x = self.pos[0] - self.size[0] + fill_w
        
        self.color_mesh.program['u_scale'] = (fill_w, self.size[1])
        self.color_mesh.program['u_offset'] = (fill_x, self.pos[1])
        self.color_mesh.program['u_color'] = (0.2, 0.6, 0.3, 0.8)
        self.color_mesh.render()

        if self.is_int or self.config_key == 'fov':
            display_val = int(val)
        else:
            display_val = f"{val:.4f}"
            
        tex = self.text_renderer.get_texture(f"{self.text}: {display_val}")
        tex.use(location=4)
        tex_w, tex_h = tex.size
        scale_y = self.size[1] * 0.6
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = self.pos
        self.text_mesh.render()

class OptionsMenu:
    def __init__(self, app):
        self.app = app
        self.title_renderer = TextRenderer(app)
        self.title_renderer.font = pg.font.SysFont('arial', 160, bold=True)
        self.title_mesh = UITextMesh(app)
        self.bg_mesh = UIColorMesh(app)

        self.sliders = [
            Slider(app, 'FOV', (0, 0.2), (0.3, 0.05), 30, 110, 'fov', self.update_fov, is_int=True),
            Slider(app, 'Sensitivity', (0, 0.0), (0.3, 0.05), 0.0005, 0.005, 'sensitivity'),
            Slider(app, 'Volume', (0, -0.2), (0.3, 0.05), 0, 100, 'volume', self.update_volume, is_int=True),
            Slider(app, 'Render Distance', (0, -0.4), (0.3, 0.05), 2, 14, 'render_distance', is_int=True)
        ]
        self.buttons = [
            Button(app, '', (0, -0.6), (0.3, 0.05), self.toggle_tint),
            Button(app, 'Back', (0, -0.8), (0.2, 0.07), self.go_back)
        ]
        self.previous_state = 'MAIN_MENU'

    def update_fov(self, val):
        if self.app.scene:
            self.app.player.fov = glm.radians(val)

    def update_volume(self, val):
        pg.mixer.music.set_volume(val / 100.0)

    def toggle_tint(self):
        current_val = self.app.config.get('underwater_tint', False)
        self.app.config['underwater_tint'] = not current_val
        self.app.save_config()

    def go_back(self):
        self.app.save_config()
        self.app.game_state = self.previous_state

    def update(self):
        for slider in self.sliders:
            slider.update()

        tint_on = self.app.config.get('underwater_tint', False)
        self.buttons[0].text = f"Underwater Tint: {'On' if tint_on else 'Off'}"

        mouse_pos = pg.mouse.get_pos()
        for button in self.buttons:
            button.check_hover(mouse_pos)

    def handle_event(self, event):
        for slider in self.sliders:
            slider.handle_event(event)
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.is_hovered:
                    button.action()
                    break

    def render(self):
        if self.previous_state == 'PAUSED':
            self.bg_mesh.program['u_scale'] = (1.0, 1.0)
            self.bg_mesh.program['u_offset'] = (0.0, 0.0)
            self.bg_mesh.program['u_color'] = (0.0, 0.0, 0.0, 0.8)
            self.bg_mesh.render()

        tex = self.title_renderer.get_texture("Options")
        tex.use(location=4)
        tex_w, tex_h = tex.size
        scale_y = 0.08
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        self.title_mesh.program['u_scale'] = (scale_x, scale_y)
        self.title_mesh.program['u_offset'] = (0.0, 0.45)
        self.title_mesh.render()

        for slider in self.sliders:
            slider.render()
        for button in self.buttons:
            button.render()

class DebugOverlay:
    def __init__(self, app):
        self.app = app
        self.font = pg.font.SysFont('arial', 18, bold=True)
        self.text_mesh = UITextMesh(app)
        self.dynamic_texture = None

    def render(self):
        player = self.app.player
        handler = self.app.scene.world.voxel_handler
        
        fps = self.app.clock.get_fps()
        x, y, z = player.position
        cx, cy, cz = int(x // CHUNK_SIZE), int(y // CHUNK_SIZE), int(z // CHUNK_SIZE)
        yaw, pitch = glm.degrees(player.yaw), glm.degrees(player.pitch)
        
        target = "Air"
        if handler.voxel_id:
            target = f"ID: {handler.voxel_id} at {int(handler.voxel_world_pos.x)} {int(handler.voxel_world_pos.y)} {int(handler.voxel_world_pos.z)}"

        lines = [
            f"Voxel Engine (FPS: {fps:.0f})",
            f"XYZ: {x:.3f} / {y:.5f} / {z:.3f}",
            f"Chunk: {cx} {cy} {cz}",
            f"Facing: Yaw {yaw:.1f} Pitch {pitch:.1f}",
            f"Time: {self.app.time:.2f}",
            f"Target Block: {target}",
            f"Game Mode: {'Survival' if player.game_mode == SURVIVAL else 'Creative'}"
        ]

        surfaces = []
        for line in lines:
            shadow = self.font.render(line, True, (60, 60, 60))
            text = self.font.render(line, True, (220, 220, 220))
            merged = pg.Surface((text.get_width() + 2, text.get_height() + 2), pg.SRCALPHA)
            merged.blit(shadow, (2, 2))
            merged.blit(text, (0, 0))
            surfaces.append(merged)
            
        max_w = max(s.get_width() for s in surfaces)
        total_h = sum(s.get_height() for s in surfaces)
        
        bg_surf = pg.Surface((max_w + 10, total_h + 10), pg.SRCALPHA)
        bg_surf.fill((0, 0, 0, 120))
        
        curr_y = 5
        for s in surfaces:
            bg_surf.blit(s, (5, curr_y))
            curr_y += s.get_height()
        
        if self.dynamic_texture:
            self.dynamic_texture.release() # Prevent VRAM leaks
            
        self.dynamic_texture = self.app.ctx.texture(bg_surf.get_size(), 4, pg.image.tostring(bg_surf, 'RGBA', True))
        self.dynamic_texture.filter = (mgl.NEAREST, mgl.NEAREST)
        self.dynamic_texture.use(location=4)
        
        tex_w, tex_h = self.dynamic_texture.size
        scale_y = (tex_h / WIN_RES.y)
        scale_x = (tex_w / WIN_RES.x)
        
        x_offset = -1.0 + scale_x
        y_offset = 1.0 - scale_y
        
        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = (x_offset, y_offset)
        self.text_mesh.render()