"""
Heads-Up Display (HUD) elements and dynamic overlays for the game.

This module constructs the in-game overlay, rendering the crosshair, the
interactive drag-and-drop inventory, the hotbar with survival statistics,
the 3D view-bobbing held item, and the F3 debug screen.
"""

from typing import Any, Dict, List, Tuple

import moderngl as mgl
import pygame as pg
from pyglm import glm

from meshes.item_mesh import ItemMesh
from meshes.obj_mesh import ObjMesh
from profiler import global_profiler
from settings import (
    ASPECT_RATIO,
    CHUNK_SIZE,
    FONT_SIZE_DEBUG,
    GLASS,
    GLOWSTONE,
    HELD_BLOCK_ROT_X,
    HELD_BLOCK_ROT_Y,
    HELD_BLOCK_SCALE,
    HELD_ITEM_BOB_OFFSET_X_MULT,
    HELD_ITEM_BOB_OFFSET_Y_MULT,
    HELD_ITEM_PLACE_SWING_OFFSET_Y,
    HELD_ITEM_PLACE_SWING_ROTATION_X,
    HELD_ITEM_POS,
    HELD_ITEM_SWING_OFFSET_Y,
    HELD_ITEM_SWING_OFFSET_Z,
    HELD_ITEM_SWING_ROT_X,
    HELD_PICKAXE_POS_OFFSET,
    HELD_PICKAXE_ROT_X,
    HELD_PICKAXE_ROT_Z,
    HELD_PICKAXE_SCALE,
    HELD_STICK_POS_OFFSET,
    HELD_STICK_ROT_X,
    HELD_STICK_ROT_Z,
    HELD_STICK_SCALE,
    HOTBAR_SCALE,
    HOTBAR_SIZE,
    HOTBAR_Y,
    INVENTORY_SIZE,
    SAND,
    SLOT_SCALE,
    STICK,
    STONE,
    STONE_BRICKS,
    SURVIVAL,
    UI_BG_COLOR,
    UI_SLOT_BG_COLOR,
    UI_SLOT_HOVER_COLOR,
    UI_SLOT_SELECTED_BG_COLOR,
    UI_SLOT_SELECTED_FRAME_COLOR,
    WIN_RES,
    WOOD,
    WOOD_PLANKS,
    WOODEN_PICKAXE,
    get_path,
)

from .meshes import BlockIconMesh, CrosshairMesh, UIColorMesh, UITextMesh
from .text import TextRenderer


class Crosshair:
    """
    Renders a simple fixed crosshair at the center of the screen.

    Args:
        app (Any): The main application context.
    """

    @global_profiler.profile_func('Crosshair_Init')
    def __init__(self, app: Any) -> None:
        self.app: Any = app
        self.mesh: Any = CrosshairMesh(app)

    @global_profiler.profile_func('Crosshair_Render')
    def render(self) -> None:
        """Issues the draw call to render the crosshair mesh."""
        self.mesh.render()


class Hotbar:
    """
    Renders the bottom-screen hotbar, including the transparent slot backgrounds,
    active selection frame, 3D block/item icons, stack counts, and survival status bars.

    Args:
        app (Any): The main application context.
    """

    @global_profiler.profile_func('Hotbar_Init')
    def __init__(self, app: Any) -> None:
        self.app: Any = app
        self.block_mesh: Any = BlockIconMesh(app)
        self.color_mesh: Any = UIColorMesh(app)
        self.text_mesh: Any = UITextMesh(app)
        self.text_renderer: Any = TextRenderer(app)
        self.count_textures: Dict[int, Any] = {i: self.text_renderer.get_texture(str(i)) for i in range(1, 65)}
        self.cached_health_str: str = ''
        self.health_tex: Any = None
        self.cached_hunger_str: str = ''
        self.hunger_tex: Any = None
        self.cached_oxy_str: str = ''
        self.oxy_tex: Any = None

    @global_profiler.profile_func('Hotbar_Render')
    def render(self) -> None:
        """Dynamically draws the hotbar slots, items, counts, and survival bars."""
        player: Any = self.app.player
        s: float = HOTBAR_SCALE
        slot_s: float = SLOT_SCALE

        gap: float = 0.01
        x_spacing: float = (slot_s * 2 + gap) / ASPECT_RATIO
        start_x: float = -4 * x_spacing

        y: float = HOTBAR_Y

        # 1. Draw the transparent slot backgrounds and selection frame
        for i in range(HOTBAR_SIZE):
            x: float = start_x + i * x_spacing
            is_selected: bool = i == player.hotbar_index

            if is_selected:
                # Draw white outline frame
                sel_s: float = slot_s + 0.006
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
            voxel_id: int = player.inventory[i]

            if voxel_id != 0:
                if voxel_id in (STICK, WOODEN_PICKAXE):
                    self.text_mesh.program['u_scale'] = (s / ASPECT_RATIO, s)
                    self.text_mesh.program['u_offset'] = (start_x + i * x_spacing, y)
                    self.text_mesh.program['u_texture_0'] = 5 if voxel_id == STICK else 6
                    self.text_mesh.render()
                    self.text_mesh.program['u_texture_0'] = 4  # Restore font texture

                else:
                    self.block_mesh.program['u_scale'] = (s / ASPECT_RATIO, s)
                    self.block_mesh.program['u_offset'] = (start_x + i * x_spacing, y)
                    self.block_mesh.program['voxel_id'] = voxel_id
                    self.block_mesh.render()

        # 3. Draw the stack counts
        for i in range(HOTBAR_SIZE):
            count: int = player.inventory_counts[i]

            if count > 0:
                tex: Any = self.count_textures.get(count)
                if tex:
                    tex.use(location=4)

                    tex_w: int = tex.size[0]
                    tex_h: int = tex.size[1]
                    scale_y: float = 0.025
                    scale_x: float = scale_y * (tex_w / tex_h) / ASPECT_RATIO

                    offset_x: float = start_x + i * x_spacing + 0.015
                    offset_y: float = y - 0.025

                    self.text_mesh.program['u_scale'] = (scale_x, scale_y)
                    self.text_mesh.program['u_offset'] = (offset_x, offset_y)
                    self.text_mesh.render()

        # 4. Draw Survival Stats (Health, Hunger, Oxygen)
        if player.game_mode == SURVIVAL:
            # Helper to draw a stat bar
            def draw_bar(
                ratio: float,
                offset_x: float,
                offset_y: float,
                bg_color: Tuple[float, float, float, float],
                fg_color: Tuple[float, float, float, float],
                tex: Any,
            ) -> None:
                # Background
                self.color_mesh.program['u_scale'] = (0.2, 0.01)
                self.color_mesh.program['u_offset'] = (offset_x, offset_y)
                self.color_mesh.program['u_color'] = bg_color
                self.color_mesh.render()

                # Foreground
                if ratio > 0:
                    self.color_mesh.program['u_scale'] = (0.2 * ratio, 0.01)
                    self.color_mesh.program['u_offset'] = (offset_x - 0.2 * (1.0 - ratio), offset_y)
                    self.color_mesh.program['u_color'] = fg_color
                    self.color_mesh.render()

                # Text
                tex.use(location=4)
                scale_y: float = 0.015
                scale_x: float = scale_y * (tex.size[0] / tex.size[1]) / ASPECT_RATIO
                self.text_mesh.program['u_scale'] = (scale_x, scale_y)
                self.text_mesh.program['u_offset'] = (offset_x, offset_y)
                self.text_mesh.render()

            health_ratio: float = max(0.0, float(player.health) / player.max_health)
            health_str: str = f'HP: {int(player.health)}/{player.max_health}'
            if health_str != self.cached_health_str or self.health_tex is None:
                if self.health_tex:
                    self.health_tex.release()
                self.health_tex = self.text_renderer.get_dynamic_texture(health_str)
                self.cached_health_str = health_str

            draw_bar(health_ratio, -0.22, y + 0.08, (0.1, 0.1, 0.1, 0.8), (0.8, 0.1, 0.1, 0.9), self.health_tex)

            hunger_ratio: float = max(0.0, float(player.hunger) / player.max_hunger)
            hunger_str: str = f'Food: {int(player.hunger)}/{player.max_hunger}'
            if hunger_str != self.cached_hunger_str or self.hunger_tex is None:
                if self.hunger_tex:
                    self.hunger_tex.release()
                self.hunger_tex = self.text_renderer.get_dynamic_texture(hunger_str)
                self.cached_hunger_str = hunger_str

            draw_bar(hunger_ratio, 0.22, y + 0.08, (0.1, 0.1, 0.1, 0.8), (0.8, 0.5, 0.1, 0.9), self.hunger_tex)

            if player.oxygen < player.max_oxygen:
                oxy_ratio: float = max(0.0, float(player.oxygen) / player.max_oxygen)
                oxy_str: str = f'O2: {int(player.oxygen)}/{player.max_oxygen}'
                if oxy_str != self.cached_oxy_str or self.oxy_tex is None:
                    if self.oxy_tex:
                        self.oxy_tex.release()
                    self.oxy_tex = self.text_renderer.get_dynamic_texture(oxy_str)
                    self.cached_oxy_str = oxy_str

                draw_bar(oxy_ratio, 0.22, y + 0.12, (0.1, 0.1, 0.1, 0.8), (0.1, 0.6, 0.9, 0.9), self.oxy_tex)


class HeldBlock:
    """
    Renders the 3D model of the currently equipped item or block in the player's hand.
    Includes procedural view bobbing and swinging animations for mining/placing.

    Args:
        app (Any): The main application context.
    """

    @global_profiler.profile_func('HeldBlock_Init')
    def __init__(self, app: Any) -> None:
        self.app: Any = app
        self.mesh: Any = ItemMesh(app)
        self.stick_mesh: Any = ObjMesh(app, get_path('assets/models/items/stick/stick.obj'), tex_id=5)
        self.pickaxe_mesh: Any = ObjMesh(
            app, get_path('assets/models/items/wooden-pickaxe/wooden_pickaxe.obj'), tex_id=6
        )

    @global_profiler.profile_func('HeldBlock_Render')
    def render(self) -> None:
        """Applies transformation matrices to simulate hand movement and renders the item."""
        player: Any = self.app.player
        voxel_id: int = player.inventory[player.hotbar_index]

        if voxel_id == 0:
            return

        # 1. View bobbing
        bob_offset_y: float = glm.sin(player.step_counter) * HELD_ITEM_BOB_OFFSET_Y_MULT
        bob_offset_x: float = glm.cos(player.step_counter * 0.5) * HELD_ITEM_BOB_OFFSET_X_MULT

        # 2. Swinging animation
        swing_offset_y: float = 0.0
        swing_offset_z: float = 0.0
        swing_rotation_x: float = 0.0

        if player.mining_time > 0.0:
            swing_val: float = max(0.0, float(glm.sin(player.mining_time * 0.03)))
            swing_offset_y = swing_val * HELD_ITEM_SWING_OFFSET_Y
            swing_offset_z = -swing_val * HELD_ITEM_SWING_OFFSET_Z
            swing_rotation_x = swing_val * HELD_ITEM_SWING_ROT_X

        else:
            time_since_place: int = pg.time.get_ticks() - player.interaction_timer

            if time_since_place < player.interaction_delay:
                progress: float = time_since_place / player.interaction_delay
                swing_val = float(glm.sin(progress * glm.pi()))
                swing_offset_y = swing_val * HELD_ITEM_PLACE_SWING_OFFSET_Y
                swing_rotation_x = swing_val * HELD_ITEM_PLACE_SWING_ROTATION_X

        # 3. Position the block in the bottom right (in local camera space)
        pos: Any = HELD_ITEM_POS + glm.vec3(bob_offset_x, bob_offset_y - swing_offset_y, swing_offset_z)

        # Compute Model Matrix in World Space for perfectly accurate lighting
        m_model: Any = glm.inverse(player.m_view)
        m_model = glm.translate(m_model, pos)
        # Render the held block in static Camera Space instead of World Space
        # m_model = glm.translate(glm.mat4(), pos)

        if voxel_id == STICK:
            m_model = glm.translate(m_model, HELD_STICK_POS_OFFSET)
            m_model = glm.rotate(m_model, HELD_STICK_ROT_X - swing_rotation_x, glm.vec3(1, 0, 0))
            m_model = glm.rotate(m_model, HELD_STICK_ROT_Z, glm.vec3(0, 0, 1))
            m_model = glm.scale(m_model, HELD_STICK_SCALE)
            mesh = self.stick_mesh

        elif voxel_id == WOODEN_PICKAXE:
            m_model = glm.translate(m_model, HELD_PICKAXE_POS_OFFSET)
            m_model = glm.rotate(m_model, HELD_PICKAXE_ROT_X - swing_rotation_x, glm.vec3(1, 0, 0))
            m_model = glm.rotate(m_model, HELD_PICKAXE_ROT_Z, glm.vec3(0, 0, 1))
            m_model = glm.scale(m_model, HELD_PICKAXE_SCALE)
            mesh = self.pickaxe_mesh

        else:
            m_model = glm.rotate(m_model, HELD_BLOCK_ROT_X - swing_rotation_x, glm.vec3(1, 0, 0))
            m_model = glm.rotate(m_model, HELD_BLOCK_ROT_Y, glm.vec3(0, 1, 0))
            m_model = glm.scale(m_model, HELD_BLOCK_SCALE)
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

        self.app.ctx.disable(mgl.DEPTH_TEST)  # Draw on top of the world without depth clearing
        self.app.ctx.enable(mgl.CULL_FACE)  # Toggle this to enable/disable backfaces!
        mesh.render()
        self.app.ctx.enable(mgl.DEPTH_TEST)


class InventoryUI:
    """
    Manages the full player inventory and crafting grid interface.
    Handles drag-and-drop item management, stack splitting, and crafting matrix evaluation.

    Args:
        app (Any): The main application context.
    """

    @global_profiler.profile_func('InventoryUI_Init')
    def __init__(self, app: Any) -> None:
        self.app: Any = app
        self.block_mesh: Any = BlockIconMesh(app)
        self.color_mesh: Any = UIColorMesh(app)
        self.text_mesh: Any = UITextMesh(app)
        self.text_renderer: Any = TextRenderer(app)

        self.drag_id: int = 0
        self.drag_count: int = 0
        self.drag_start_pos: Tuple[int, int] = (0, 0)
        self.tooltip_texture: Any = None
        self.last_hover_name: str = ''
        self._cached_aspect: float = ASPECT_RATIO
        self._slot_positions: Dict[int, Tuple[float, float]] = {}
        self.count_textures: Dict[int, Any] = {i: self.text_renderer.get_texture(str(i)) for i in range(1, 65)}

    @global_profiler.profile_func('InventoryUI_UpdateCrafting')
    def update_crafting(self) -> None:
        """Evaluates the 2x2 crafting grid and updates the output slot if a valid recipe matches."""
        player: Any = self.app.player
        grid: Tuple[int, ...] = tuple(player.inventory[36:40])  # Tuple is hashable for dictionary lookup

        recipes: Dict[Tuple[int, ...], Tuple[int, int]] = {
            # Wood -> 4 Planks
            (WOOD, 0, 0, 0): (WOOD_PLANKS, 4),
            (0, WOOD, 0, 0): (WOOD_PLANKS, 4),
            (0, 0, WOOD, 0): (WOOD_PLANKS, 4),
            (0, 0, 0, WOOD): (WOOD_PLANKS, 4),
            # 2 Planks -> 4 Sticks (Vertical)
            (WOOD_PLANKS, 0, WOOD_PLANKS, 0): (STICK, 4),
            (0, WOOD_PLANKS, 0, WOOD_PLANKS): (STICK, 4),
            # Wooden Pickaxe -> Top row planks, Bottom left stick
            (WOOD_PLANKS, WOOD_PLANKS, STICK, 0): (WOODEN_PICKAXE, 1),
            # Glowstone!
            (SAND, SAND, SAND, SAND): (GLOWSTONE, 4),
            # Glass
            (SAND, 0, 0, 0): (GLASS, 1),
            (0, SAND, 0, 0): (GLASS, 1),
            (0, 0, SAND, 0): (GLASS, 1),
            (0, 0, 0, SAND): (GLASS, 1),
            # Stone Bricks
            (STONE, STONE, STONE, STONE): (STONE_BRICKS, 4),
        }

        if grid in recipes:
            player.inventory[40], player.inventory_counts[40] = recipes[grid]

        else:
            player.inventory[40], player.inventory_counts[40] = 0, 0

    @global_profiler.profile_func('InventoryUI_GetSlotPos')
    def get_slot_pos(self, i: int) -> Tuple[float, float]:
        """Calculates and caches the 2D screen coordinate for a specific inventory slot."""
        if self._cached_aspect != ASPECT_RATIO:
            self._slot_positions.clear()
            self._cached_aspect = ASPECT_RATIO

        if i in self._slot_positions:
            return self._slot_positions[i]

        gap: float = 0.01
        x_spacing: float = (SLOT_SCALE * 2 + gap) / ASPECT_RATIO
        y_spacing: float = SLOT_SCALE * 2 + gap

        if i < HOTBAR_SIZE:
            col: int = i % HOTBAR_SIZE
            x = -4 * x_spacing + col * x_spacing
            y = HOTBAR_Y  # Hotbar

        elif i < 36:
            col = i % HOTBAR_SIZE
            row: int = 2 - ((i - HOTBAR_SIZE) // HOTBAR_SIZE)
            y = HOTBAR_Y + (row + 1.5) * y_spacing
            x = -4 * x_spacing + col * x_spacing

        elif i < 40:  # 2x2 Crafting Grid
            grid_idx: int = i - 36
            x = 0.5 * x_spacing + (grid_idx % 2) * x_spacing
            y = HOTBAR_Y + (6.0 - (grid_idx // 2)) * y_spacing

        else:  # Output Slot
            x = 3.0 * x_spacing
            y = HOTBAR_Y + 5.5 * y_spacing

        self._slot_positions[i] = (x, y)
        return x, y

    @global_profiler.profile_func('InventoryUI_GetSlotAtMouse')
    def get_slot_at_mouse(self, mouse_pos: Tuple[int, int]) -> int:
        """Returns the ID of the inventory slot currently hovered by the mouse cursor."""
        mx: float = (mouse_pos[0] / WIN_RES.x) * 2.0 - 1.0
        my: float = 1.0 - (mouse_pos[1] / WIN_RES.y) * 2.0

        slot_w: float = SLOT_SCALE / ASPECT_RATIO
        slot_h: float = SLOT_SCALE

        for i in range(INVENTORY_SIZE):
            slot_pos: Tuple[float, float] = self.get_slot_pos(i)
            sx: float = slot_pos[0]
            sy: float = slot_pos[1]

            if sx - slot_w < mx < sx + slot_w and sy - slot_h < my < sy + slot_h:
                return i

        return -1

    @global_profiler.profile_func('InventoryUI_GetClosestValidSlot')
    def get_closest_valid_slot(self, mouse_pos: Tuple[int, int], drag_id: int, drag_count: int) -> int:
        """Finds the closest valid drop target slot during a drag-and-drop operation."""
        mx: float = (mouse_pos[0] / WIN_RES.x) * 2.0 - 1.0
        my: float = 1.0 - (mouse_pos[1] / WIN_RES.y) * 2.0

        best_i: int = -1
        best_dist_sq: float = float('inf')

        gap: float = 0.01
        y_spacing: float = SLOT_SCALE * 2 + gap
        # Max snap distance based on UI scale
        max_dist_sq: float = (y_spacing * 1.5) ** 2

        player: Any = self.app.player

        for i in range(INVENTORY_SIZE):
            if i == 40:
                continue  # Prevent dropping items into the output slot

            slot_pos: Tuple[float, float] = self.get_slot_pos(i)
            sx: float = slot_pos[0]
            sy: float = slot_pos[1]

            dx: float = (mx - sx) * ASPECT_RATIO
            dy: float = my - sy
            dist_sq: float = dx * dx + dy * dy

            if dist_sq < best_dist_sq and dist_sq < max_dist_sq:
                slot_id: int = player.inventory[i]

                if slot_id == 0 or (slot_id == drag_id and player.inventory_counts[i] < 64):
                    best_i = i
                    best_dist_sq = dist_sq

        return best_i

    @global_profiler.profile_func('InventoryUI_HandleEvent')
    def handle_event(self, event: Any) -> None:
        """Processes left/right mouse clicks for selecting, splitting, and merging item stacks."""
        if event.type == pg.MOUSEBUTTONDOWN:
            i: int = self.get_slot_at_mouse(pg.mouse.get_pos())

            if i != -1:
                player: Any = self.app.player
                slot_id: int = player.inventory[i]
                slot_count: int = player.inventory_counts[i]

                if event.button == 1:  # Left click (Pick up stack / Swap / Place stack)
                    if i == 40:  # Output slot logic
                        if slot_id != 0:
                            can_take: bool = False

                            if self.drag_id == 0:
                                self.drag_id = slot_id
                                self.drag_count = slot_count
                                can_take = True

                            elif self.drag_id == slot_id and self.drag_count + slot_count <= 64:
                                self.drag_count += slot_count
                                can_take = True

                            if can_take:  # Consume 1 from each crafting input!
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
                                space: int = 64 - slot_count

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

                elif event.button == 3:  # Right click (Split half / Place one)
                    if i != 40:
                        if self.drag_id == 0:
                            if slot_id != 0:
                                half: int = slot_count - (slot_count // 2)
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

                                if self.drag_count <= 0:
                                    self.drag_id = 0

                            elif slot_id == self.drag_id and slot_count < 64:
                                player.inventory_counts[i] += 1
                                self.drag_count -= 1

                                if self.drag_count <= 0:
                                    self.drag_id = 0

                    self.update_crafting()

        elif event.type == pg.MOUSEBUTTONUP:
            if event.button == 1 and self.drag_id != 0:
                mouse_pos: Tuple[int, int] = pg.mouse.get_pos()
                dx: int = mouse_pos[0] - self.drag_start_pos[0]
                dy: int = mouse_pos[1] - self.drag_start_pos[1]

                # Check if mouse moved more than 10 pixels (to separate drag from standard click)
                if dx * dx + dy * dy > 100:
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

    @global_profiler.profile_func('InventoryUI_Close')
    def close(self) -> None:
        """Cleans up the inventory screen, ejecting active crafting items back into the world."""
        player: Any = self.app.player

        # Eject crafting items back into inventory (or drop them!)
        for i in range(36, 40):
            if player.inventory[i] != 0:
                for _ in range(player.inventory_counts[i]):
                    if not player.add_item(player.inventory[i]):
                        self.app.scene.item_manager.add_item(player.position, player.inventory[i])

                player.inventory[i], player.inventory_counts[i] = 0, 0

        # Re-inject leftover dragged item or drop it!
        if self.drag_id != 0:
            while self.drag_count > 0:
                if not player.add_item(self.drag_id):
                    # Inventory completely full, drop in the world
                    for _ in range(self.drag_count):
                        self.app.scene.item_manager.add_item(player.position, self.drag_id)

                    break
                self.drag_count -= 1

            self.drag_id = 0
            self.drag_count = 0

        self.update_crafting()

        if self.tooltip_texture:
            self.tooltip_texture.release()
            self.tooltip_texture = None
            self.last_hover_name = ''

    @global_profiler.profile_func('InventoryUI_Render')
    def render(self) -> None:
        """Issues draw calls for the entire inventory UI, background, and floating tooltip items."""
        gap: float = 0.01
        x_spacing: float = (SLOT_SCALE * 2 + gap) / ASPECT_RATIO
        y_spacing: float = SLOT_SCALE * 2 + gap

        # Unified background for the entire inventory and crafting menu
        bg_w: float = 4.5 * x_spacing + 0.02
        bg_h: float = 3.0 * y_spacing + 0.02

        self.color_mesh.program['u_scale'] = (bg_w, bg_h)
        self.color_mesh.program['u_offset'] = (0.0, HOTBAR_Y + 4.0 * y_spacing)
        self.color_mesh.program['u_color'] = UI_BG_COLOR
        self.color_mesh.render()

        player: Any = self.app.player
        hover_idx: int = self.get_slot_at_mouse(pg.mouse.get_pos())

        for i in range(INVENTORY_SIZE):
            slot_pos: Tuple[float, float] = self.get_slot_pos(i)
            x: float = slot_pos[0]
            y: float = slot_pos[1]
            s: float = SLOT_SCALE

            if i == hover_idx:
                self.color_mesh.program['u_scale'] = ((s + 0.005) / ASPECT_RATIO, s + 0.005)
                self.color_mesh.program['u_offset'] = (x, y)
                self.color_mesh.program['u_color'] = UI_SLOT_HOVER_COLOR
                self.color_mesh.render()

            self.color_mesh.program['u_scale'] = (s / ASPECT_RATIO, s)
            self.color_mesh.program['u_offset'] = (x, y)
            self.color_mesh.program['u_color'] = UI_SLOT_BG_COLOR
            self.color_mesh.render()

            voxel_id: int = player.inventory[i]
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

            count: int = player.inventory_counts[i]

            if count > 0:
                tex: Any = self.count_textures.get(count)
                if tex:
                    tex.use(location=4)
                    scale_y: float = 0.025
                    scale_x: float = scale_y * (tex.size[0] / tex.size[1]) / ASPECT_RATIO
                    self.text_mesh.program['u_scale'] = (scale_x, scale_y)
                    self.text_mesh.program['u_offset'] = (x + 0.015, y - 0.025)
                    self.text_mesh.render()

        # Dragged Item Render (Follows Mouse Cursor)
        if self.drag_id != 0:
            mouse_pos: Tuple[int, int] = pg.mouse.get_pos()
            mx: float = (mouse_pos[0] / WIN_RES.x) * 2.0 - 1.0
            my: float = 1.0 - (mouse_pos[1] / WIN_RES.y) * 2.0

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
                drag_tex: Any = self.count_textures.get(self.drag_count)
                if drag_tex:
                    drag_tex.use(location=4)
                    drag_scale_y: float = 0.025
                    drag_scale_x: float = drag_scale_y * (drag_tex.size[0] / drag_tex.size[1]) / ASPECT_RATIO
                    self.text_mesh.program['u_scale'] = (drag_scale_x, drag_scale_y)
                    self.text_mesh.program['u_offset'] = (mx + 0.015, my - 0.025)
                    self.text_mesh.render()

        # Draw Tooltip on Hover
        if hover_idx != -1 and self.drag_id == 0:
            hover_id: int = player.inventory[hover_idx]

            if hover_id != 0:
                # Simple static mapping dictionary, can be expanded!
                item_names: Dict[int, str] = {
                    1: 'Sand',
                    2: 'Grass',
                    3: 'Dirt',
                    4: 'Stone',
                    5: 'Wood',
                    6: 'Leaves',
                    7: 'Wood Planks',
                    9: 'Glass',
                    10: 'Glowstone',
                    20: 'Stick',
                    21: 'Wooden Pickaxe',
                }
                name: str = item_names.get(hover_id, f'Item ID: {hover_id}')

                tt_mouse_pos: Tuple[int, int] = pg.mouse.get_pos()
                tt_mx: float = (tt_mouse_pos[0] / WIN_RES.x) * 2.0 - 1.0
                tt_my: float = 1.0 - (tt_mouse_pos[1] / WIN_RES.y) * 2.0

                if name != self.last_hover_name:
                    if self.tooltip_texture:
                        self.tooltip_texture.release()
                    self.tooltip_texture = self.text_renderer.get_dynamic_texture(name)
                    self.last_hover_name = name

                tt_tex: Any = self.tooltip_texture
                tt_tex.use(location=4)
                tt_scale_y: float = 0.025
                tt_scale_x: float = tt_scale_y * (tt_tex.size[0] / tt_tex.size[1]) / ASPECT_RATIO

                self.color_mesh.program['u_scale'] = (tt_scale_x + 0.01, tt_scale_y + 0.01)
                self.color_mesh.program['u_offset'] = (tt_mx + tt_scale_x + 0.02, tt_my - tt_scale_y - 0.02)
                self.color_mesh.program['u_color'] = (0.05, 0.05, 0.05, 0.95)
                self.color_mesh.render()

                self.text_mesh.program['u_scale'] = (tt_scale_x, tt_scale_y)
                self.text_mesh.program['u_offset'] = (tt_mx + tt_scale_x + 0.02, tt_my - tt_scale_y - 0.02)
                self.text_mesh.render()


class DebugOverlay:
    """
    Displays an on-screen overlay with performance metrics, player coordinates,
    targeted block info, and current game mode (F3 menu).

    Args:
        app (Any): The main application context.
    """

    @global_profiler.profile_func('DebugOverlay_Init')
    def __init__(self, app: Any) -> None:
        self.app: Any = app
        self.font: pg.font.Font = pg.font.SysFont('arial', FONT_SIZE_DEBUG, bold=True)
        self.text_mesh: Any = UITextMesh(app)
        self.dynamic_texture: Any = None
        self.last_update: int = 0

    @global_profiler.profile_func('DebugOverlay_Render')
    def render(self) -> None:
        """Compiles and renders the performance statistics and positional data overlay."""
        current_time: int = pg.time.get_ticks()

        if current_time - self.last_update > 250 or self.dynamic_texture is None:
            self.last_update = current_time

            player: Any = self.app.player
            handler: Any = self.app.scene.world.voxel_handler

            fps: float = self.app.clock.get_fps()
            x: float = float(player.position.x)
            y: float = float(player.position.y)
            z: float = float(player.position.z)
            cx: int = int(x // CHUNK_SIZE)
            cy: int = int(y // CHUNK_SIZE)
            cz: int = int(z // CHUNK_SIZE)
            yaw: float = float(glm.degrees(player.yaw) % 360)
            pitch: float = float(glm.degrees(player.pitch))

            target: str = 'Air'
            if handler.voxel_id:
                target = f'ID: {handler.voxel_id} at {int(handler.voxel_world_pos.x)} {int(handler.voxel_world_pos.y)} {int(handler.voxel_world_pos.z)}'

            lines: List[str] = [
                f'Pyrite (FPS: {fps:.0f})',
                f'XYZ: {x:.3f} / {y:.5f} / {z:.3f}',
                f'Chunk: {cx} {cy} {cz}',
                f'Facing: Yaw {yaw:.1f} Pitch {pitch:.1f}',
                f'Time: {self.app.world_session_time:.2f}',
                f'Target Block: {target}',
                f'Game Mode: {"Survival" if player.game_mode == SURVIVAL else "Creative"}',
            ]

            surfaces: List[pg.Surface] = []
            for line in lines:
                shadow: pg.Surface = self.font.render(line, True, (60, 60, 60))
                text: pg.Surface = self.font.render(line, True, (220, 220, 220))
                merged: pg.Surface = pg.Surface((text.get_width() + 2, text.get_height() + 2), pg.SRCALPHA)
                merged.blit(shadow, (2, 2))
                merged.blit(text, (0, 0))
                surfaces.append(merged)

            max_w: int = max(s.get_width() for s in surfaces)
            total_h: int = sum(s.get_height() for s in surfaces)

            bg_surf: pg.Surface = pg.Surface((max_w + 10, total_h + 10), pg.SRCALPHA)
            bg_surf.fill((0, 0, 0, 120))

            curr_y: int = 5
            for s in surfaces:
                bg_surf.blit(s, (5, curr_y))
                curr_y += s.get_height()

            if self.dynamic_texture:
                self.dynamic_texture.release()  # Prevent VRAM leaks

            self.dynamic_texture = self.app.ctx.texture(bg_surf.get_size(), 4, pg.image.tobytes(bg_surf, 'RGBA', True))
            self.dynamic_texture.filter = (mgl.NEAREST, mgl.NEAREST)

        self.dynamic_texture.use(location=4)

        tex_w: int = self.dynamic_texture.size[0]
        tex_h: int = self.dynamic_texture.size[1]
        scale_y: float = tex_h / WIN_RES.y
        scale_x: float = tex_w / WIN_RES.x

        x_offset: float = -1.0 + scale_x
        y_offset: float = 1.0 - scale_y

        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = (x_offset, y_offset)
        self.text_mesh.render()
