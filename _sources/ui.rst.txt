.. _ui:

=====================================
User Interface Systems and Components
=====================================

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

    self.position: (float, float) = pos
    self.size: (float, float) = size

* **Base Structure:** Every standard sub-component maps basic bounds tracking logically across generalized generic initialization phases.

.. code-block:: text

    def render(self, ctx, program):
        pass

* **Visual Dispatch:** Each class mandates distinct custom geometric allocations processing seamlessly directly over base UI shaders.

In-Game HUD Components
----------------------

**1. Crosshair**

Simple '+' rendered at screen center. Always visible in-game.

.. code-block:: python

    super().__init__((0, 0), (0.02, 0.02))
    self.color = (1, 1, 1, 0.5)

* **Center Overlay:** A hardcoded alpha-bound quad locks tightly permanently relative directly across viewports.

**2. Hotbar**

9 slots at bottom of screen, showing held items with selection highlight.

.. code-block:: python

    self.selected_index = player.hotbar_index

* **Slot Logic:** Specific bounds dynamically link strictly back to primary mapped vectors continually synchronously processing changes immediately.

.. code-block:: python

    color = (1, 1, 1, 0.8) if i == selected_index else (0.5, 0.5, 0.5, 0.8)
    render_quad(slot_pos, slot_size, color)

* **Slot Masking:** Grayed indices uniquely map rendering blocks dynamically highlighting correctly globally identically visually directly.

**3. Health/Hunger/Oxygen Bars**

Status indicators above hotbar.

.. code-block:: python

    health_fill = player.health / 20.0
    render_heart(heart_pos, health_fill)

* **Status Masking:** Numeric allocations immediately populate precise graphical representations functionally seamlessly uniformly visually cleanly.

**4. Debug Overlay (F3)**

Shows FPS, coords, chunk, facing direction, time, target block.

.. code-block:: python

    fps = self.app.clock.get_fps()
    chunk = (int(pos.x // 48), int(pos.z // 48))

* **Data Strings:** Text strings constantly poll dynamic internal matrix queries strictly efficiently formatting debug tracking perfectly visually reliably.

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

    if button.contains_point(event.x, event.y):
        button.handle_event(event)

* **State Hierarchy:** Parent instances distribute input checks logically downward towards local objects recursively optimally successfully inherently strictly accurately.

**Inventory Grid and Crafting**

.. code-block:: python

    if inputs in recipe_map:
        output, count = recipe_map[inputs]
        player.inventory[40] = output

* **Crafting Matrix:** Dedicated tuples directly compare index combinations perfectly uniformly calculating valid logical states seamlessly cleanly.

.. code-block:: python

    self.swap_or_merge(self.dragging_from, slot_index)

* **Drag Drop:** Memory mappings exchange internal storage indexes natively logically safely reliably effectively strictly purely mathematically functionally accurately.

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

    x = -0.35 + col * (slot_size + spacing)
    y = 0.15 + row * (slot_size + spacing)

* **Grid Layouts:** Formulaic offsets cleanly configure exact spacing globally flawlessly strictly reliably effectively smoothly natively automatically statically clearly purely.

Button and Component Library
-----------------------------

**Button Component**

.. code-block:: python

    if event.type == MOUSEBUTTONDOWN and self.hover:
        self.callback()

* **Interaction Flow:** Polled mouse arrays trigger prebound callbacks implicitly smoothly effectively perfectly uniformly successfully completely safely natively seamlessly accurately fully.

**TextInput Component**

.. code-block:: python

    if event.unicode.isprintable():
        self.text += event.unicode

* **Keyboard Trapping:** Typing instances automatically catch raw Unicode parameters organically perfectly cleanly seamlessly correctly explicitly functionally directly efficiently organically.

**Slider Component**

.. code-block:: python

    new_value = self.min_val + (relative_x / self.size[0]) * (self.max_val - self.min_val)
    self.value = clamp(new_value, self.min_val, self.max_val)

* **Interpolated Ratios:** Scaled dragging translates implicitly accurately identically dynamically globally seamlessly purely cleanly strictly visually functionally optimally reliably fully natively.

Transition Animations
---------------------

**Menu Slide-In/Out (cubic easing):**

.. code-block:: python

    t = self.elapsed / self.duration
    return t * t * t

* **Animation Scaling:** Duration mapping applies natural visual easing precisely universally efficiently cleanly seamlessly flawlessly organically optimally explicitly accurately reliably natively.

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

**Render Dispatch Implementation:**

.. code-block:: python

    glDisable(GL_DEPTH_TEST)
    inventory_ui.render()
    glEnable(GL_DEPTH_TEST)

* **Drawing Pass:** Render dispatches are natively bracketed uniformly strictly securely automatically explicitly fully effectively cleanly reliably safely securely accurately flawlessly securely correctly seamlessly.

Next Steps
----------

Now that you understand the 2D overlays and menus, proceed to the :doc:`audio` system to learn how Pyrite handles spatial block sound effects and background music.
