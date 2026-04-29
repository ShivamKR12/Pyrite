from settings import *
import moderngl as mgl
import pygame as pg
from pyglm import glm
from meshes.item_mesh import ItemMesh
from meshes.obj_mesh import ObjMesh
from .meshes import CrosshairMesh, BlockIconMesh, UIColorMesh, UITextMesh
from .text import TextRenderer


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
        for i in range(HOTBAR_SIZE):
            x = start_x + i * x_spacing
            is_selected = (i == player.hotbar_index)
            
            if is_selected:
                # Draw white outline frame
                sel_s = slot_s + 0.006
                self.color_mesh.program['u_scale'] = (sel_s / ASPECT_RATIO, sel_s)
                self.color_mesh.program['u_offset'] = (x, y)
                self.color_mesh.program['u_color'] = UI_SLOT_SELECTED_FRAME_COLOR
                self.color_mesh.render()
                
                # Draw slightly lighter inner background
                self.color_mesh.program['u_scale'] = (slot_s / ASPECT_RATIO, slot_s)
                self.color_mesh.program['u_color'] = UI_SLOT_SELECTED_BG_COLOR
                self.color_mesh.render()
            else:
                # Draw standard dark background
                self.color_mesh.program['u_scale'] = (slot_s / ASPECT_RATIO, slot_s)
                self.color_mesh.program['u_offset'] = (x, y)
                self.color_mesh.program['u_color'] = UI_SLOT_BG_COLOR
                self.color_mesh.render()

        # 2. Draw the 3D block icons inside the slots
        for i in range(HOTBAR_SIZE):
            voxel_id = player.inventory[i]
            if voxel_id != 0:
                if voxel_id in (STICK, WOODEN_PICKAXE):
                    self.text_mesh.program['u_scale'] = (s / ASPECT_RATIO, s)
                    self.text_mesh.program['u_offset'] = (start_x + i * x_spacing, y)
                    self.text_mesh.program['u_texture_0'] = 5 if voxel_id == STICK else 6
                    self.text_mesh.render()
                    self.text_mesh.program['u_texture_0'] = 4 # Restore font texture
                else:
                    self.block_mesh.program['u_scale'] = (s / ASPECT_RATIO, s)
                    self.block_mesh.program['u_offset'] = (start_x + i * x_spacing, y)
                    self.block_mesh.program['voxel_id'] = voxel_id
                    self.block_mesh.render()

        # 3. Draw the stack counts
        for i in range(HOTBAR_SIZE):
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
        self.stick_mesh = ObjMesh(app, get_path('assets/stick/stick.obj'), tex_id=5)
        self.pickaxe_mesh = ObjMesh(app, get_path('assets/wooden_pickaxe/wooden_pickaxe.obj'))

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
        # Render the held block in static Camera Space instead of World Space
        # m_model = glm.translate(glm.mat4(), pos)

        if voxel_id == STICK:
            m_model = glm.translate(m_model, glm.vec3(0.0, 0.15, 0.0))
            m_model = glm.rotate(m_model, glm.radians(-45.0) - swing_rot_x, glm.vec3(1, 0, 0))
            m_model = glm.rotate(m_model, glm.radians(90.0), glm.vec3(0, 0, 1))
            m_model = glm.scale(m_model, glm.vec3(0.5))
            mesh = self.stick_mesh
        elif voxel_id == WOODEN_PICKAXE:
            m_model = glm.translate(m_model, glm.vec3(0.0, 0.15, 0.0))
            m_model = glm.rotate(m_model, glm.radians(10.0) - swing_rot_x, glm.vec3(1, 0, 0))
            m_model = glm.rotate(m_model, glm.radians(90.0), glm.vec3(0, 0, 1))
            m_model = glm.scale(m_model, glm.vec3(0.2))
            mesh = self.pickaxe_mesh
        else:
            m_model = glm.rotate(m_model, glm.radians(-15.0) - swing_rot_x, glm.vec3(1, 0, 0))
            m_model = glm.rotate(m_model, glm.radians(45.0), glm.vec3(0, 1, 0))
            m_model = glm.scale(m_model, glm.vec3(0.35))
            mesh = self.mesh

        mesh.program['m_proj'].write(player.m_proj)
        mesh.program['m_view'].write(player.m_view) 
        # mesh.program['m_view'].write(glm.mat4()) # Lock view matrix!
        mesh.program['m_model'].write(m_model)
        if 'voxel_id' in mesh.program:
            mesh.program['voxel_id'] = voxel_id

        # # Override lighting & fog specifically for the held item so it stays fully bright and visible
        # if 'u_sun_direction' in mesh.program:
        #     mesh.program['u_sun_direction'].write(glm.normalize(glm.vec3(0.3, 1.0, 0.3)))
        # if 'u_fog_density' in mesh.program:
        #     mesh.program['u_fog_density'] = 0.0

        self.app.ctx.disable(mgl.DEPTH_TEST) # Draw on top of the world without depth clearing
        self.app.ctx.enable(mgl.CULL_FACE)   # Toggle this to enable/disable backfaces!
        mesh.render()
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

    def update_crafting(self):
        player = self.app.player
        grid = tuple(player.inventory[36:40]) # Tuple is hashable for dictionary lookup
        
        recipes = {
            # Wood -> 4 Planks
            (WOOD, 0, 0, 0): (WOOD_PLANKS, 4), (0, WOOD, 0, 0): (WOOD_PLANKS, 4),
            (0, 0, WOOD, 0): (WOOD_PLANKS, 4), (0, 0, 0, WOOD): (WOOD_PLANKS, 4),
            # 2 Planks -> 4 Sticks (Vertical)
            (WOOD_PLANKS, 0, WOOD_PLANKS, 0): (STICK, 4),
            (0, WOOD_PLANKS, 0, WOOD_PLANKS): (STICK, 4),
            # Wooden Pickaxe -> Top row planks, Bottom left stick
            (WOOD_PLANKS, WOOD_PLANKS, STICK, 0): (WOODEN_PICKAXE, 1),
            # Glowstone!
            (SAND, SAND, SAND, SAND): (GLOWSTONE, 4),
            # Glass
            (SAND, 0, 0, 0): (GLASS, 1), (0, SAND, 0, 0): (GLASS, 1),
            (0, 0, SAND, 0): (GLASS, 1), (0, 0, 0, SAND): (GLASS, 1),
            # Stone Bricks
            (STONE, STONE, STONE, STONE): (STONE_BRICKS, 4)
        }
        
        if grid in recipes:
            player.inventory[40], player.inventory_counts[40] = recipes[grid]
        else:
            player.inventory[40], player.inventory_counts[40] = 0, 0

    def get_slot_pos(self, i):
        gap = 0.01
        x_spacing = (SLOT_SCALE * 2 + gap) / ASPECT_RATIO
        y_spacing = SLOT_SCALE * 2 + gap
        
        if i < HOTBAR_SIZE:
            col = i % HOTBAR_SIZE
            x = -4 * x_spacing + col * x_spacing
            y = HOTBAR_Y # Hotbar
        elif i < 36:
            col = i % HOTBAR_SIZE
            row = 2 - ((i - HOTBAR_SIZE) // HOTBAR_SIZE) 
            y = HOTBAR_Y + (row + 1.5) * y_spacing
            x = -4 * x_spacing + col * x_spacing
        elif i < 40: # 2x2 Crafting Grid
            grid_idx = i - 36
            x = 0.5 * x_spacing + (grid_idx % 2) * x_spacing
            y = HOTBAR_Y + (6.0 - (grid_idx // 2)) * y_spacing
        else: # Output Slot
            x = 3.0 * x_spacing
            y = HOTBAR_Y + 5.5 * y_spacing
        return x, y

    def get_slot_at_mouse(self, mouse_pos):
        mx = (mouse_pos[0] / WIN_RES.x) * 2.0 - 1.0
        my = 1.0 - (mouse_pos[1] / WIN_RES.y) * 2.0
        
        slot_w = SLOT_SCALE / ASPECT_RATIO
        slot_h = SLOT_SCALE
        
        for i in range(INVENTORY_SIZE):
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
        
        for i in range(INVENTORY_SIZE):
            if i == 40: continue # Prevent dropping items into the output slot
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
                    if i == 40: # Output slot logic
                        if slot_id != 0:
                            can_take = False
                            if self.drag_id == 0:
                                self.drag_id = slot_id
                                self.drag_count = slot_count
                                can_take = True
                            elif self.drag_id == slot_id and self.drag_count + slot_count <= 64:
                                self.drag_count += slot_count
                                can_take = True
                                
                            if can_take: # Consume 1 from each crafting input!
                                for c in range(36, 40):
                                    if player.inventory_counts[c] > 0:
                                        player.inventory_counts[c] -= 1
                                        if player.inventory_counts[c] <= 0:
                                            player.inventory[c] = 0
                                self.drag_start_pos = pg.mouse.get_pos()
                    else:
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
                    self.update_crafting()
                elif event.button == 3: # Right click (Split half / Place one)
                    if i != 40:
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
                    self.update_crafting()
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
                    self.update_crafting()

    def close(self):
        if self.drag_id != 0:
            player = self.app.player
            
            # Eject crafting items back into inventory (or drop them!)
            for i in range(36, 40):
                if player.inventory[i] != 0:
                    for _ in range(player.inventory_counts[i]):
                        if not player.add_item(player.inventory[i]):
                            self.app.scene.item_manager.add_item(player.position, player.inventory[i])
                    player.inventory[i], player.inventory_counts[i] = 0, 0
            self.update_crafting()
            
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
        
        # Unified background for the entire inventory and crafting menu
        bg_w = 4.5 * x_spacing + 0.02
        bg_h = 3.0 * y_spacing + 0.02

        self.color_mesh.program['u_scale'] = (bg_w, bg_h)
        self.color_mesh.program['u_offset'] = (0.0, HOTBAR_Y + 4.0 * y_spacing)
        self.color_mesh.program['u_color'] = UI_BG_COLOR
        self.color_mesh.render()

        player = self.app.player
        hover_idx = self.get_slot_at_mouse(pg.mouse.get_pos())
        
        for i in range(INVENTORY_SIZE):
            x, y = self.get_slot_pos(i)
            s = SLOT_SCALE
            
            if i == hover_idx:
                self.color_mesh.program['u_scale'] = ((s+0.005) / ASPECT_RATIO, s+0.005)
                self.color_mesh.program['u_offset'] = (x, y)
                self.color_mesh.program['u_color'] = UI_SLOT_HOVER_COLOR
                self.color_mesh.render()

            self.color_mesh.program['u_scale'] = (s / ASPECT_RATIO, s)
            self.color_mesh.program['u_offset'] = (x, y)
            self.color_mesh.program['u_color'] = UI_SLOT_BG_COLOR
            self.color_mesh.render()

            voxel_id = player.inventory[i]
            if voxel_id != 0:
                if voxel_id in (STICK, WOODEN_PICKAXE):
                    self.text_mesh.program['u_scale'] = (HOTBAR_SCALE / ASPECT_RATIO, HOTBAR_SCALE)
                    self.text_mesh.program['u_offset'] = (x, y)
                    self.text_mesh.program['u_texture_0'] = 5 if voxel_id == STICK else 6
                    self.text_mesh.render()
                    self.text_mesh.program['u_texture_0'] = 4
                else:
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
            
            if self.drag_id in (STICK, WOODEN_PICKAXE):
                self.text_mesh.program['u_scale'] = (HOTBAR_SCALE / ASPECT_RATIO, HOTBAR_SCALE)
                self.text_mesh.program['u_offset'] = (mx, my)
                self.text_mesh.program['u_texture_0'] = 5 if self.drag_id == STICK else 6
                self.text_mesh.render()
                self.text_mesh.program['u_texture_0'] = 4
            else:
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


class DebugOverlay:
    def __init__(self, app):
        self.app = app
        self.font = pg.font.SysFont('arial', FONT_SIZE_DEBUG, bold=True)
        self.text_mesh = UITextMesh(app)
        self.dynamic_texture = None
        self.last_update = 0

    def render(self):
        current_time = pg.time.get_ticks()
        if current_time - self.last_update > 250 or self.dynamic_texture is None:
            self.last_update = current_time
            
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
                f"Pyrite (FPS: {fps:.0f})",
                f"XYZ: {x:.3f} / {y:.5f} / {z:.3f}",
                f"Chunk: {cx} {cy} {cz}",
                f"Facing: Yaw {yaw:.1f} Pitch {pitch:.1f}",
                f"Time: {self.app.world_session_time:.2f}",
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
                
            self.dynamic_texture = self.app.ctx.texture(bg_surf.get_size(), 4, pg.image.tobytes(bg_surf, 'RGBA', True))
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
