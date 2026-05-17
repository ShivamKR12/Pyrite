.. _ui:

User Interface Systems and Components
======================================

This document details Pyrite's UI architecture, component hierarchy, event handling, and rendering pipeline. The UI spans from in-game HUD (hotbar, health bar) to menus (main menu, inventory, options).

UI Architecture Overview
------------------------

**Rendering Pipeline:**

.. code-block:: text

    Main Loop
        ↓
    [Update Phase]
        → Player input events
        → UI component updates (hover states, animations)
        → Inventory logic
        ↓
    [Render Phase]
        → Disable depth test
        → Render world (if in-game)
        → Render UI layer (depth disabled)
        → Render text overlay (if applicable)
        → Re-enable depth test

**Screen Coordinate System:**

- **Normalized Device Coordinates (NDC):** -1 to 1 in both X and Y axes
- **Calculate screen pos:** `screen_x = (pixel_x / WIN_WIDTH) * 2 - 1`
- **UI shaders use:** `gl_Position = vec4(screen_x, screen_y, 0, 1)` (orthographic projection)

Core UI Component Base Class
-----------------------------

**UIComponent (Abstract Base)**

.. code-block:: text

    class UIComponent:
        def __init__(self, pos, size):
            self.position: (float, float) = pos       # Top-left in NDC
            self.size: (float, float) = size          # Width, height
            self.visible: bool = True
            self.mouse_over: bool = False
            self.clicked: bool = False
        
        def update(self, delta_time):
            # Update animations, hover states, etc.
            pass
        
        def render(self, ctx, program):
            # Draw to screen (or skip if not visible)
            pass
        
        def handle_event(self, event):
            # Respond to mouse/keyboard
            pass
        
        def contains_point(self, x, y) -> bool:
            # Check if (x, y) is within component bounds
            return (self.position[0] <= x <= self.position[0] + self.size[0] and
                    self.position[1] <= y <= self.position[1] + self.size[1])

In-Game HUD Components
----------------------

**1. Crosshair**

Simple '+' rendered at screen center. Always visible in-game.

.. code-block:: python

    class Crosshair(UIComponent):
        def __init__(self):
            super().__init__((0, 0), (0.02, 0.02))  # Small quad at center
            self.color = (1, 1, 1, 0.5)  # White, semi-transparent
        
        def render(self, ctx, program):
            # Draw 2 quads: horizontal and vertical lines forming '+'
            # Use ui_color shader to render simple geometry

**2. Hotbar**

9 slots at bottom of screen, showing held items with selection highlight.

.. code-block:: python

    class Hotbar(UIComponent):
        def __init__(self, player):
            super().__init__((-0.45, -0.95), (0.9, 0.08))  # Bottom center
            self.player = player
            self.slots = []  # Array of slot quads
            self.selected_index = 0
        
        def update(self, delta_time):
            # Update selection when player changes hotbar_index
            self.selected_index = player.hotbar_index
        
        def render(self, ctx, program):
            # Render 9 slot backgrounds
            for i in range(9):
                slot_pos = (-0.4 + i * 0.1, -0.95)
                slot_size = (0.08, 0.08)
                
                # Render background quad (gray for unselected, bright for selected)
                color = (1, 1, 1, 0.8) if i == selected_index else (0.5, 0.5, 0.5, 0.8)
                render_quad(slot_pos, slot_size, color)
                
                # Render held item icon
                voxel_id, count = player.inventory[i], player.inventory_counts[i]
                if voxel_id > 0:
                    render_item_icon(slot_pos, voxel_id)
                    render_count_text(slot_pos, count)

**3. Health/Hunger/Oxygen Bars**

Status indicators above hotbar.

.. code-block:: python

    class HealthBar(UIComponent):
        def __init__(self, player):
            super().__init__((-0.45, -1.05), (0.09, 0.04))  # Per-heart display
            self.player = player
        
        def render(self, ctx, program):
            # Render 10 hearts (2 per full health point)
            for i in range(10):
                heart_pos = (-0.45 + i * 0.045, -1.05)
                health_fill = player.health / 20.0
                
                # Full heart, half heart, or empty heart based on fill
                render_heart(heart_pos, health_fill)

**4. Debug Overlay (F3)**

Shows FPS, coords, chunk, facing direction, time, target block.

.. code-block:: python

    class DebugOverlay(UIComponent):
        def __init__(self, app, player):
            super().__init__((-0.95, -0.95), (0.4, 0.3))
            self.app = app
            self.player = player
            self.update_interval = 0.25  # ms
            self.last_update = 0
        
        def update(self, delta_time):
            self.last_update += delta_time
            if self.last_update >= self.update_interval:
                # Gather data
                fps = self.app.clock.get_fps()
                pos = player.feet_pos
                chunk = (int(pos.x // 48), int(pos.z // 48))
                facing = compute_facing_direction(player.yaw)
                time = world.session_time
                
                self.debug_text = f"""
                FPS: {fps:.1f}
                XYZ: {pos.x:.1f} {pos.y:.1f} {pos.z:.1f}
                Chunk: {chunk}
                Facing: {facing}
                Time: {time:.0f}
                """
                
                self.last_update = 0
        
        def render(self, ctx, program):
            render_text(self.position, self.debug_text, font_size=12)

Menu System
-----------

**Finite State Machine (UI States)**

.. code-block:: text

    Possible UI States:
    - MAIN_MENU:      Title screen, Play/Options/Quit buttons
    - SELECT_WORLD:   List of worlds, New World button
    - CREATE_WORLD:   Name/Seed input, Game mode select, Create/Back
    - IN_GAME:        HUD visible (hotbar, health, crosshair)
    - INVENTORY:      Full inventory grid with crafting and drag/drop
    - PAUSED:         In-game pause menu (Resume/Options/Quit)
    - OPTIONS:        Settings sliders and toggles

**MainMenu Component**

.. code-block:: python

    class MainMenu(UIComponent):
        def __init__(self, app):
            super().__init__((-0.2, 0), (0.4, 0.6))
            self.app = app
            
            # Buttons as child components
            self.buttons = [
                Button((-0.1, 0.1), (0.2, 0.08), "Play", self.on_play),
                Button((-0.1, 0.2), (0.2, 0.08), "Options", self.on_options),
                Button((-0.1, 0.3), (0.2, 0.08), "Quit", self.on_quit),
            ]
        
        def update(self, delta_time):
            for button in self.buttons:
                button.update(delta_time)
        
        def render(self, ctx, program):
            # Render title
            render_text((-0.15, -0.5), "PYRITE", font_size=48, color=(1, 0.5, 0))
            
            # Render buttons
            for button in self.buttons:
                button.render(ctx, program)
        
        def handle_event(self, event):
            for button in self.buttons:
                if button.contains_point(event.x, event.y):
                    button.handle_event(event)

**Inventory Grid and Crafting**

.. code-block:: python

    class InventoryUI(UIComponent):
        def __init__(self, player):
            super().__init__((-0.35, -0.45), (0.7, 0.9))
            self.player = player
            self.slots = [SlotWidget(i) for i in range(41)]
            self.dragging_from = None
            self.crafting_output = 0  # Current crafting output voxel ID
        
        def update_crafting(self):
            # Check crafting recipes
            recipe_map = {
                (WOOD, 0, 0, 0): (WOOD_PLANKS, 4),
                (WOOD_PLANKS, 0, WOOD_PLANKS, 0): (STICK, 4),
                (WOOD_PLANKS, WOOD_PLANKS, STICK, 0): (WOODEN_PICKAXE, 1),
                # ... more recipes
            }
            
            inputs = (
                player.inventory[36], player.inventory[37],
                player.inventory[38], player.inventory[39]
            )
            
            if inputs in recipe_map:
                output, count = recipe_map[inputs]
                player.inventory[40] = output
                player.inventory_counts[40] = count
            else:
                player.inventory[40] = 0
                player.inventory_counts[40] = 0
        
        def render(self, ctx, program):
            # Render grid background
            render_quad(self.position, self.size, (0.2, 0.2, 0.2, 0.9))
            
            # Render 41 slot quads
            slot_positions = self.compute_slot_grid()
            for i, (pos, size) in enumerate(slot_positions):
                voxel_id = player.inventory[i]
                count = player.inventory_counts[i]
                
                # Draw slot background
                render_quad(pos, size, (0.3, 0.3, 0.3, 0.8))
                
                # Draw item if present
                if voxel_id > 0:
                    render_item_icon(pos, voxel_id, size)
                    if count > 1:
                        render_text(pos, str(count), font_size=10)
        
        def handle_event(self, event):
            if event.type == MOUSEBUTTONDOWN and event.button == 1:  # LClick
                # Find slot at click position
                slot_index = self.get_slot_at(event.x, event.y)
                if slot_index is not None:
                    if self.dragging_from is None:
                        # Start drag
                        self.dragging_from = slot_index
                    else:
                        # Drop on target
                        self.swap_or_merge(self.dragging_from, slot_index)
                        self.dragging_from = None

Layout Metrics (Slot Grid)
---------------------------

**Inventory Grid (36 main slots + 9 hotbar):**

.. code-block:: text

    Hotbar (Bottom, 9 slots)
    [0] [1] [2] [3] [4] [5] [6] [7] [8]
    
    Main (3 rows, 9 slots each)
    [9 ] [10] [11] [12] [13] [14] [15] [16] [17]
    [18] [19] [20] [21] [22] [23] [24] [25] [26]
    [27] [28] [29] [30] [31] [32] [33] [34] [35]
    
    Crafting (2x2 grid + output)
    [36] [37]     [40]  (output)
    [38] [39]

**3x3 Slot Size:** Typically 0.08 x 0.08 in NDC

**Slot Position Formula:**

.. code-block:: python

    def compute_slot_positions():
        slot_size = 0.08
        spacing = 0.02
        
        positions = {}
        
        # Hotbar (bottom, centered)
        for i in range(9):
            x = -0.35 + i * (slot_size + spacing)
            y = -0.05
            positions[i] = ((x, y), (slot_size, slot_size))
        
        # Main inventory (above hotbar)
        for row in range(3):
            for col in range(9):
                i = 9 + row * 9 + col
                x = -0.35 + col * (slot_size + spacing)
                y = 0.15 + row * (slot_size + spacing)
                positions[i] = ((x, y), (slot_size, slot_size))
        
        # Crafting grid
        craft_positions = [36, 37, 38, 39, 40]
        craft_x = 0.30
        craft_y = 0.25
        craft_slot_size = 0.06
        
        # 2x2 grid
        positions[36] = ((craft_x, craft_y), (craft_slot_size, craft_slot_size))
        positions[37] = ((craft_x + 0.08, craft_y), (craft_slot_size, craft_slot_size))
        positions[38] = ((craft_x, craft_y + 0.08), (craft_slot_size, craft_slot_size))
        positions[39] = ((craft_x + 0.08, craft_y + 0.08), (craft_slot_size, craft_slot_size))
        
        # Output (larger, to the right)
        positions[40] = ((craft_x + 0.20, craft_y + 0.04), (0.08, 0.08))
        
        return positions

Button and Component Library
-----------------------------

**Button Component**

.. code-block:: python

    class Button(UIComponent):
        def __init__(self, pos, size, label, callback):
            super().__init__(pos, size)
            self.label = label
            self.callback = callback
            self.hover = False
            self.pressed = False
        
        def update(self, delta_time):
            # Track hover via mouse position (from pygame)
            mouse_pos = pygame.mouse.get_pos()
            ndc_pos = self.screen_to_ndc(mouse_pos)
            self.hover = self.contains_point(ndc_pos[0], ndc_pos[1])
        
        def render(self, ctx, program):
            # Draw background (brighter if hovering)
            color = (0.6, 0.6, 0.6, 1.0) if self.hover else (0.4, 0.4, 0.4, 1.0)
            render_quad(self.position, self.size, color)
            
            # Draw label text
            render_text(self.position, self.label, color=(1, 1, 1, 1))
        
        def handle_event(self, event):
            if event.type == MOUSEBUTTONDOWN and self.hover:
                self.callback()

**TextInput Component**

.. code-block:: python

    class TextInput(UIComponent):
        def __init__(self, pos, size, placeholder=""):
            super().__init__(pos, size)
            self.text = ""
            self.placeholder = placeholder
            self.active = False
            self.cursor_blink = 0
        
        def update(self, delta_time):
            self.cursor_blink += delta_time
            if self.cursor_blink > 1.0:
                self.cursor_blink = 0
        
        def render(self, ctx, program):
            # Draw input box
            render_quad(self.position, self.size, (0.2, 0.2, 0.2, 1.0))
            
            # Draw text
            display_text = self.text if self.text else self.placeholder
            render_text(self.position, display_text, color=(1, 1, 1, 1) if self.text else (0.5, 0.5, 0.5, 0.5))
            
            # Draw cursor if active and blinking
            if self.active and self.cursor_blink < 0.5:
                cursor_x = self.position[0] + len(self.text) * 0.01
                render_text((cursor_x, self.position[1]), "|", color=(1, 1, 1, 1))
        
        def handle_event(self, event):
            if event.type == MOUSEBUTTONDOWN:
                self.active = self.contains_point(event.x, event.y)
            
            if self.active and event.type == KEYDOWN:
                if event.key == K_BACKSPACE:
                    self.text = self.text[:-1]
                elif event.unicode.isprintable():
                    self.text += event.unicode

**Slider Component**

.. code-block:: python

    class Slider(UIComponent):
        def __init__(self, pos, size, min_val, max_val, initial, on_change):
            super().__init__(pos, size)
            self.min_val = min_val
            self.max_val = max_val
            self.value = initial
            self.on_change = on_change
            self.dragging = False
        
        def render(self, ctx, program):
            # Draw background bar
            render_quad(self.position, self.size, (0.3, 0.3, 0.3, 1.0))
            
            # Draw filled portion (based on value)
            fill_width = self.size[0] * ((self.value - self.min_val) / (self.max_val - self.min_val))
            render_quad(self.position, (fill_width, self.size[1]), (0.5, 0.8, 0.5, 1.0))
            
            # Draw value text
            value_text = f"{self.value:.2f}"
            render_text((self.position[0] + self.size[0] + 0.02, self.position[1]), value_text)
        
        def handle_event(self, event):
            if event.type == MOUSEBUTTONDOWN:
                if self.contains_point(event.x, event.y):
                    self.dragging = True
            elif event.type == MOUSEBUTTONUP:
                self.dragging = False
            elif event.type == MOUSEMOTION and self.dragging:
                # Calculate new value from mouse position
                relative_x = event.x - self.position[0]
                new_value = self.min_val + (relative_x / self.size[0]) * (self.max_val - self.min_val)
                self.value = clamp(new_value, self.min_val, self.max_val)
                self.on_change(self.value)

Transition Animations
---------------------

**Menu Slide-In/Out (cubic easing):**

.. code-block:: python

    class MenuTransition:
        def __init__(self, duration=0.3):
            self.duration = duration
            self.elapsed = 0
            self.complete = False
        
        def update(self, delta_time):
            self.elapsed += delta_time
            if self.elapsed >= self.duration:
                self.complete = True
                self.elapsed = self.duration
        
        def get_progress(self):
            # Cubic easing-in
            t = self.elapsed / self.duration
            return t * t * t
        
        def get_offset(self, full_offset):
            # Use progress for smooth slide
            return full_offset * (1.0 - self.get_progress())

Integration with Main Loop
---------------------------

**Order of Operations (per frame):**

1. **Event Handling:**
   - Poll pygame events (mouse, keyboard)
   - Dispatch to active UI state handler
   
2. **Update:**
   - Update all visible UI components
   - Update crafting logic if inventory open
   
3. **Render:**
   - Disable depth test
   - Render UI components in order (background → middle → foreground)
   - Render text overlay
   - Re-enable depth test

**pseudocode:**

.. code-block:: python

    def main_loop():
        while running:
            for event in pygame.event.get():
                if ui_state == 'IN_GAME':
                    player.handle_event(event)
                    if event.type == KEYDOWN and event.key == K_e:
                        ui_state = 'INVENTORY'
                elif ui_state == 'INVENTORY':
                    inventory_ui.handle_event(event)
                    if event.type == KEYDOWN and event.key == K_e:
                        ui_state = 'IN_GAME'
                elif ui_state == 'MAIN_MENU':
                    main_menu.handle_event(event)
            
            # Update
            if ui_state == 'IN_GAME':
                player.update(delta_time)
                hud.update(delta_time)
            elif ui_state == 'INVENTORY':
                inventory_ui.update_crafting()
                inventory_ui.update(delta_time)
            
            # Render
            glDisable(GL_DEPTH_TEST)
            if ui_state == 'IN_GAME':
                crosshair.render()
                hotbar.render()
                health_bar.render()
            elif ui_state == 'INVENTORY':
                inventory_ui.render()
            glEnable(GL_DEPTH_TEST)

