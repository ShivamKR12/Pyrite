"""
Reusable UI component classes for building complex, hierarchical game menus.

This module provides a node-based scene graph system (`UINode`, `VBox`) and a
suite of interactive widgets (`Button`, `Slider`, `TextInput`, `Toggle`). It also
includes a lazy-loading resource manager (`get_shared_resource`) to efficiently
share and reuse heavy objects like fonts and meshes, preventing VRAM bloat.
"""

import os
from typing import Any, Callable, Dict, List, Optional, Tuple

import moderngl as mgl
import pygame as pg

from profiler import global_profiler
from settings import ASPECT_RATIO, FONT_SIZE_BUTTONS, FONT_SIZE_SLIDERS, UI_BUTTON_COLOR, UI_HOVER_COLOR, WIN_RES

from .meshes import UIColorMesh, UITextMesh
from .text import TextRenderer

_shared_ui_resources: Dict[str, Any] = {}


@global_profiler.profile_func('GetSharedResource')
def get_shared_resource(app: Any, res_type: str, **kwargs: Any) -> Any:
    """
    Lazily loads and shares UI meshes, fonts, and textures to prevent VRAM and CPU bloat.

    This function acts as a singleton factory, ensuring that expensive resources like
    text renderers or button mask textures are only created once and then reused
    across all UI components that request them.
    """
    if res_type == 'color_mesh':
        if 'color_mesh' not in _shared_ui_resources:
            _shared_ui_resources['color_mesh'] = UIColorMesh(app)

        return _shared_ui_resources['color_mesh']

    elif res_type == 'text_mesh':
        if 'text_mesh' not in _shared_ui_resources:
            _shared_ui_resources['text_mesh'] = UITextMesh(app)

        return _shared_ui_resources['text_mesh']

    elif res_type == 'text_renderer':
        font_size: int = kwargs.get('size', 24)
        bold: bool = kwargs.get('bold', True)
        key: str = f'text_renderer_{font_size}_{bold}'

        if key not in _shared_ui_resources:
            tr: Any = TextRenderer(app)
            tr.font = pg.font.SysFont('arial', font_size, bold=bold)
            _shared_ui_resources[key] = tr

        return _shared_ui_resources[key]

    elif res_type == 'button_mask':
        radius: int = kwargs.get('radius', 12)
        size_tuple: Tuple[float, float] = kwargs.get('size', (0.2, 0.05))
        w: float = size_tuple[0]
        h: float = size_tuple[1]
        key = f'mask_{w}_{h}_{radius}'

        if key not in _shared_ui_resources:
            px_w: int = max(1, int(w * WIN_RES.x))
            px_h: int = max(1, int(h * WIN_RES.y))
            surf: pg.Surface = pg.Surface((px_w, px_h), pg.SRCALPHA)
            pg.draw.rect(surf, (255, 255, 255, 255), surf.get_rect(), border_radius=radius)
            tex: Any = app.ctx.texture(surf.get_size(), 4, pg.image.tobytes(surf, 'RGBA', True))
            tex.filter = (mgl.LINEAR, mgl.LINEAR)
            _shared_ui_resources[key] = tex

        return _shared_ui_resources[key]


class UINode:
    """
    Base class for all UI elements in the hierarchical layout system.

    This class forms the foundation of the scene graph, allowing UI elements
    to be nested within each other. It handles the recursive calculation of
    global positions and the propagation of update, event, and render calls.

    Args:
        size (Tuple[float, float]): The normalized width and height of the node.
    """

    @global_profiler.profile_func('UINode_Init')
    def __init__(self, size: Tuple[float, float] = (0, 0)) -> None:
        """
        Initialize a `UINode` container.

        Sets up basic parent/children relationships and default local position/size.
        """
        self.parent: Optional['UINode'] = None
        self.children: List['UINode'] = []
        self.local_pos: List[float] = [0.0, 0.0]  # Position relative to parent
        self.size: Tuple[float, float] = size

    @global_profiler.profile_func('UINode_AddChild')
    def add_child(self, child: 'UINode') -> 'UINode':
        """
        Adds a child node to this node's list of children and sets its parent.
        """
        child.parent = self
        self.children.append(child)

        return child

    @global_profiler.profile_func('UINode_GetGlobalPos')
    def get_global_pos(self) -> Tuple[float, float]:
        """Recursively computes absolute screen position by climbing the scene graph."""
        if self.parent:
            parent_pos: Tuple[float, float] = self.parent.get_global_pos()
            ppx: float = parent_pos[0]
            ppy: float = parent_pos[1]

            return (ppx + self.local_pos[0], ppy + self.local_pos[1])

        return (self.local_pos[0], self.local_pos[1])

    @global_profiler.profile_func('UINode_UpdateLayout')
    def update_layout(self) -> None:
        """
        Recursively calls `update_layout` on all children.
        """
        for child in self.children:
            child.update_layout()

    @global_profiler.profile_func('UINode_Update')
    def update(self, mouse_pos: Optional[Tuple[int, int]] = None) -> None:
        """
        Recursively calls `update` on all children, passing down the mouse position.
        """
        for child in self.children:
            child.update(mouse_pos)

    @global_profiler.profile_func('UINode_HandleEvent')
    def handle_event(self, event: Any) -> None:
        """
        Recursively calls `handle_event` on all children, passing down the Pygame event.
        """
        for child in self.children:
            child.handle_event(event)

    @global_profiler.profile_func('UINode_Render')
    def render(self, offset: Tuple[float, float] = (0, 0), alpha: float = 1.0) -> None:
        """
        Recursively calls `render` on all children, passing down animation offsets and alpha.
        """
        for child in self.children:
            child.render(offset, alpha)


class VBox(UINode):
    """
    Vertical stacking container that automatically arranges its children.

    This layout group simplifies menu creation by positioning child nodes one
    after another in a vertical column, with a configurable spacing between them.

    Args:
        pos (Tuple[float, float]): The normalized screen position of the container's origin.
        spacing (float): The normalized vertical gap to place between each child element.
    """

    @global_profiler.profile_func('VBox_Init')
    def __init__(self, pos: Tuple[float, float] = (0, 0), spacing: float = 0.05) -> None:
        """
        Initialize a `VBox` layout container.

        `pos` defines the local origin; `spacing` is the vertical gap between children.
        """
        super().__init__()
        self.local_pos: List[float] = list(pos)
        self.spacing: float = spacing

    @global_profiler.profile_func('VBox_UpdateLayout')
    def update_layout(self) -> None:
        """
        Layout children vertically and update this container's size.

        Arranges children with the configured spacing and computes the total
        height for correct nesting in parent containers.
        """
        current_y: float = 0.0

        for child in self.children:
            child.update_layout()  # Compute child's layout and size first!
            child.local_pos[1] = current_y
            # We leave local_pos[0] untouched so you can still add custom horizontal indentations!
            current_y -= child.size[1] + self.spacing

        # Update this VBox's total size so it can be safely nested!
        total_height: float = abs(current_y) - self.spacing if self.children else 0.0
        self.size = (self.size[0], max(0.0, total_height))


class Button(UINode):
    """
    Represents a clickable UI button with text, hover effects, and an assigned action.

    Features a pseudo-3D elevation effect that visually depresses when clicked.
    It lazily loads shared resources to minimize VRAM usage.

    Args:
        app (Any): The main application instance.
        text (str): The text label to display on the button.
        pos (Tuple[float, float]): The local normalized position.
        size (Tuple[float, float]): The normalized width and height.
        action (Callable[[], None]): The function to call when the button is clicked.
        border_radius (int): The pixel radius for the rounded corners.
        elevation (int): The pixel height of the 3D elevation effect.
    """

    @global_profiler.profile_func('Button_Init')
    def __init__(
        self,
        app: Any,
        text: str,
        pos: Tuple[float, float],
        size: Tuple[float, float],
        action: Optional[Callable[[], None]] = None,
        border_radius: int = 12,
        elevation: int = 5,
    ) -> None:
        """
        Construct a clickable `Button` widget.

        The constructor configures visual properties, shared resources and the
        click `action` callback.
        """
        super().__init__(size)
        self.app: Any = app
        self.text: str = text
        self.local_pos: List[float] = list(pos)
        self.action: Optional[Callable[[], None]] = action
        self.border_radius: int = border_radius
        self.elevation: int = elevation
        self.dynamic_elevation: int = elevation

        self.color_mesh: Any = get_shared_resource(app, 'color_mesh')
        self.text_mesh: Any = get_shared_resource(app, 'text_mesh')
        self.text_renderer: Any = get_shared_resource(app, 'text_renderer', size=FONT_SIZE_BUTTONS, bold=True)

        self.is_hovered: bool = False
        self.is_pressed: bool = False
        self.base_color: Tuple[float, float, float, float] = UI_BUTTON_COLOR
        self.hover_color: Tuple[float, float, float, float] = UI_HOVER_COLOR
        self.text_tex: Any = self.text_renderer.get_texture(self.text)

    @global_profiler.profile_func('Button_CheckHover')
    def check_hover(self, mouse_pos: Tuple[int, int]) -> bool:
        """
        Check whether the mouse cursor is inside the button's bounding box.

        Args:
            mouse_pos: Mouse position in pixel coordinates as (x, y).

        Returns:
            True if the mouse is hovering the button, False otherwise.
        """
        global_pos: Tuple[float, float] = self.get_global_pos()
        x: float = global_pos[0]
        y: float = global_pos[1]
        y_dynamic: float = y + (self.dynamic_elevation / WIN_RES.y)
        w: float = self.size[0]
        h: float = self.size[1]

        # Convert normalized screen coords to pixel coords
        mouse_x: int = mouse_pos[0]
        mouse_y: int = mouse_pos[1]
        win_w: int = int(WIN_RES.x)
        win_h: int = int(WIN_RES.y)

        # Convert button normalized pos/size to pixel coords
        btn_x: float = (x + 1) * 0.5 * win_w
        btn_y: float = (-y_dynamic + 1) * 0.5 * win_h
        btn_w: float = w * 0.5 * win_w
        btn_h: float = h * 0.5 * win_h

        self.is_hovered = btn_x - btn_w < mouse_x < btn_x + btn_w and btn_y - btn_h < mouse_y < btn_y + btn_h

        if not self.is_hovered and self.is_pressed:
            self.is_pressed = False
            self.dynamic_elevation = self.elevation

        return self.is_hovered

    @global_profiler.profile_func('Button_Update')
    def update(self, mouse_pos: Optional[Tuple[int, int]] = None) -> None:
        """
        Update visual/interaction state for this button.

        Args:
            mouse_pos: Optional mouse position in pixels; when None the current
                system mouse position is used.
        """
        if mouse_pos is None:
            mouse_pos = pg.mouse.get_pos()

        self.check_hover(mouse_pos)

    @global_profiler.profile_func('Button_HandleEvent')
    def handle_event(self, event: Any) -> None:
        """
        Handle Pygame mouse button events and trigger the button's action.

        Args:
            event: Pygame event object to handle (mouse down/up).
        """
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.is_pressed = True
                self.dynamic_elevation = 0

        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed:
                self.is_pressed = False
                self.dynamic_elevation = self.elevation

                if self.is_hovered and self.action:
                    self.action()

    @global_profiler.profile_func('Button_Render')
    def render(self, offset: Tuple[float, float] = (0, 0), alpha: float = 1.0) -> None:
        """
        Render the button visuals including elevation, mask, and text.

        Args:
            offset: Render offset applied to the button position.
            alpha: Opacity multiplier for rendering.
        """
        global_pos: Tuple[float, float] = self.get_global_pos()
        px: float = global_pos[0]
        py: float = global_pos[1]
        w: float = self.size[0]
        h: float = self.size[1]

        # Render Bottom (Elevation) Quad
        mask: Any = get_shared_resource(self.app, 'button_mask', radius=self.border_radius, size=(w, h))
        mask.use(location=4)

        b_c: Tuple[float, float, float, float] = self.base_color
        self.text_mesh.program['u_scale'] = (w, h)
        self.text_mesh.program['u_offset'] = (px + offset[0], py + offset[1])

        if 'u_color' in self.text_mesh.program:
            self.text_mesh.program['u_color'] = (b_c[0] * 0.5, b_c[1] * 0.5, b_c[2] * 0.5, b_c[3])

        if 'u_alpha' in self.text_mesh.program:
            self.text_mesh.program['u_alpha'] = alpha

        self.text_mesh.render()

        # Render Top (Main) Quad
        py_dynamic: float = py + (self.dynamic_elevation / WIN_RES.y)
        c: Tuple[float, float, float, float] = self.hover_color if self.is_hovered else self.base_color
        self.text_mesh.program['u_scale'] = (w, h)
        self.text_mesh.program['u_offset'] = (px + offset[0], py_dynamic + offset[1])

        if 'u_color' in self.text_mesh.program:
            self.text_mesh.program['u_color'] = c

        self.text_mesh.render()

        # Render Text
        tex: Any = self.text_tex
        tex.use(location=4)
        tex_w: int = tex.size[0]
        tex_h: int = tex.size[1]
        scale_y: float = h * 0.5
        scale_x: float = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = (px + offset[0], py_dynamic + offset[1])

        if 'u_color' in self.text_mesh.program:
            self.text_mesh.program['u_color'] = (1.0, 1.0, 1.0, 1.0)

        self.text_mesh.render()

        if 'u_alpha' in self.text_mesh.program:
            self.text_mesh.program['u_alpha'] = 1.0


class WorldButton(UINode):
    """
    A specialized button used in the World Selection menu to display rich information
    about a saved game world, including its thumbnail, seed, and playtime data.

    Args:
        app (Any): The main application instance.
        save_name (str): The raw filename of the save.
        display_name (str): The user-friendly world name.
        seed (int): The world's procedural generation seed.
        game_mode (int): The game mode (Survival/Creative).
        creation_date (str): ISO format creation timestamp.
        last_played (str): ISO format last played timestamp.
        pos (Tuple[float, float]): The local normalized position.
        size (Tuple[float, float]): The normalized width and height.
        action (Callable[[], None]): The function to call when clicked.
        border_radius (int): The pixel radius for the rounded corners.
        elevation (int): The pixel height of the 3D elevation effect.
    """

    @global_profiler.profile_func('WorldButton_Init')
    def __init__(
        self,
        app: Any,
        save_name: str,
        display_name: str,
        seed: int,
        game_mode: int,
        creation_date: str,
        last_played: str,
        pos: Tuple[float, float],
        size: Tuple[float, float],
        action: Optional[Callable[[], None]] = None,
        border_radius: int = 12,
        elevation: int = 5,
    ) -> None:
        """
        Construct a `WorldButton` showing a world thumbnail and metadata.

        This is used in the world-selection view to represent a saved world.
        """
        super().__init__(size)
        self.app: Any = app
        self.save_name: str = save_name
        self.display_name: str = display_name
        self.seed: int = seed
        self.game_mode: str = 'Survival' if game_mode == 1 else 'Creative'
        self.creation_date: str = creation_date
        self.last_played: str = last_played
        self.local_pos: List[float] = list(pos)
        self.action: Optional[Callable[[], None]] = action
        self.border_radius: int = border_radius
        self.elevation: int = elevation
        self.dynamic_elevation: int = elevation

        self.color_mesh: Any = get_shared_resource(app, 'color_mesh')
        self.text_mesh: Any = get_shared_resource(app, 'text_mesh')
        self.text_renderer: Any = get_shared_resource(app, 'text_renderer', size=FONT_SIZE_BUTTONS, bold=True)

        self.is_hovered: bool = False
        self.is_pressed: bool = False
        self.base_color: Tuple[float, float, float, float] = UI_BUTTON_COLOR
        self.hover_color: Tuple[float, float, float, float] = UI_HOVER_COLOR

        thumb_path: str = f'saves/{save_name}_thumb.png'
        img: pg.Surface
        if os.path.exists(thumb_path):
            img = pg.image.load(thumb_path).convert_alpha()
        else:
            img = pg.Surface((320, 180), pg.SRCALPHA)
            img.fill((80, 80, 80, 255))

        self.thumb_tex: Any = self.app.ctx.texture(img.get_size(), 4, pg.image.tobytes(img, 'RGBA', True))
        self.thumb_tex.filter = (mgl.LINEAR, mgl.LINEAR)

        self.tex_title: Any = self.text_renderer.get_dynamic_texture(self.display_name)
        self.tex_details: Any = self.text_renderer.get_dynamic_texture(f'{self.game_mode} Mode  |  Seed: {self.seed}')
        self.tex_dates: Any = self.text_renderer.get_dynamic_texture(
            f'Created: {self.creation_date}  |  Last Played: {self.last_played}'
        )

    @global_profiler.profile_func('WorldButton_CheckHover')
    def check_hover(self, mouse_pos: Tuple[int, int]) -> bool:
        """
        Check whether the mouse cursor is inside the world button's bounding box.

        Args:
            mouse_pos: Mouse position in pixel coordinates as (x, y).

        Returns:
            True if the mouse is hovering this world button, False otherwise.
        """
        global_pos: Tuple[float, float] = self.get_global_pos()
        x: float = global_pos[0]
        y: float = global_pos[1]

        y_dynamic: float = y + (self.dynamic_elevation / WIN_RES.y)
        w: float = self.size[0]
        h: float = self.size[1]
        win_w: int = int(WIN_RES.x)
        win_h: int = int(WIN_RES.y)

        btn_x: float = (x + 1) * 0.5 * win_w
        btn_y: float = (-y_dynamic + 1) * 0.5 * win_h
        btn_w: float = w * 0.5 * win_w
        btn_h: float = h * 0.5 * win_h

        self.is_hovered = btn_x - btn_w < mouse_pos[0] < btn_x + btn_w and btn_y - btn_h < mouse_pos[1] < btn_y + btn_h

        if not self.is_hovered and self.is_pressed:
            self.is_pressed = False
            self.dynamic_elevation = self.elevation

        return self.is_hovered

    @global_profiler.profile_func('WorldButton_Update')
    def update(self, mouse_pos: Optional[Tuple[int, int]] = None) -> None:
        """
        Update hover state for the world button.

        Args:
            mouse_pos: Optional mouse position; current mouse position is used when None.
        """
        if mouse_pos is None:
            mouse_pos = pg.mouse.get_pos()

        self.check_hover(mouse_pos)

    @global_profiler.profile_func('WorldButton_HandleEvent')
    def handle_event(self, event: Any) -> None:
        """
        Handle mouse events for clicking/pressing the world button.

        Args:
            event: Pygame event instance.
        """
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.is_pressed = True
                self.dynamic_elevation = 0

        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed:
                self.is_pressed = False
                self.dynamic_elevation = self.elevation
                if self.is_hovered and self.action:
                    self.action()

    @global_profiler.profile_func('WorldButton_Render')
    def render(self, offset: Tuple[float, float] = (0, 0), alpha: float = 1.0) -> None:
        """
        Render the world button including thumbnail, title and details.

        Args:
            offset: Render offset applied to the button.
            alpha: Opacity multiplier.
        """
        global_pos: Tuple[float, float] = self.get_global_pos()
        px: float = global_pos[0]
        py: float = global_pos[1]
        w: float = self.size[0]
        h: float = self.size[1]

        mask: Any = get_shared_resource(self.app, 'button_mask', radius=self.border_radius, size=(w, h))
        mask.use(location=4)

        b_c: Tuple[float, float, float, float] = self.base_color
        render_pos_bottom: Tuple[float, float] = (px + offset[0], py + offset[1])
        self.text_mesh.program['u_scale'] = (w, h)
        self.text_mesh.program['u_offset'] = render_pos_bottom

        if 'u_color' in self.text_mesh.program:
            self.text_mesh.program['u_color'] = (b_c[0] * 0.5, b_c[1] * 0.5, b_c[2] * 0.5, b_c[3])

        if 'u_alpha' in self.text_mesh.program:
            self.text_mesh.program['u_alpha'] = alpha

        self.text_mesh.render()

        py_dynamic: float = py + (self.dynamic_elevation / WIN_RES.y)
        render_pos_top: Tuple[float, float] = (px + offset[0], py_dynamic + offset[1])
        c: Tuple[float, float, float, float] = self.hover_color if self.is_hovered else self.base_color
        self.text_mesh.program['u_scale'] = (w, h)
        self.text_mesh.program['u_offset'] = render_pos_top

        if 'u_color' in self.text_mesh.program:
            self.text_mesh.program['u_color'] = c

        self.text_mesh.render()

        if 'u_color' in self.text_mesh.program:
            self.text_mesh.program['u_color'] = (1.0, 1.0, 1.0, 1.0)

        self.thumb_tex.use(location=4)
        thumb_h: float = h * 0.8
        thumb_w: float = thumb_h * (self.thumb_tex.width / self.thumb_tex.height) / ASPECT_RATIO
        thumb_x: float = render_pos_top[0] - w + 0.02 + thumb_w
        self.text_mesh.program['u_scale'] = (thumb_w, thumb_h)
        self.text_mesh.program['u_offset'] = (thumb_x, render_pos_top[1])
        self.text_mesh.render()

        text_x: float = thumb_x + thumb_w + 0.02

        def render_cached_text(tex: Any, offset_y: float, scale_h: float) -> None:
            tex.use(location=4)
            scale_y: float = h * scale_h
            scale_x: float = scale_y * (tex.width / tex.height) / ASPECT_RATIO
            self.text_mesh.program['u_scale'] = (scale_x, scale_y)
            self.text_mesh.program['u_offset'] = (text_x + scale_x, render_pos_top[1] + h * offset_y)
            self.text_mesh.render()

        render_cached_text(self.tex_title, 0.4, 0.25)
        render_cached_text(self.tex_details, -0.05, 0.15)
        render_cached_text(self.tex_dates, -0.4, 0.12)

        if 'u_alpha' in self.text_mesh.program:
            self.text_mesh.program['u_alpha'] = 1.0


class TextInput(UINode):
    """
    Provides a simple interactive text entry field for the UI.

    Captures keyboard input, renders a blinking cursor when active, and
    displays a placeholder label when empty.

    Args:
        app (Any): The main application instance.
        pos (Tuple[float, float]): The local normalized position.
        size (Tuple[float, float]): The normalized width and height.
        label (str): The placeholder text to show when the input is empty.
    """

    @global_profiler.profile_func('TextInput_Init')
    def __init__(self, app: Any, pos: Tuple[float, float], size: Tuple[float, float], label: str = '') -> None:
        """
        Initialize a `TextInput` control for short text entry.

        `label` is a placeholder string shown when the field is empty.
        """
        super().__init__(size)
        self.app: Any = app
        self.local_pos: List[float] = list(pos)
        self.label: str = label
        self.text: str = ''
        self.is_active: bool = False

        self.color_mesh: Any = get_shared_resource(app, 'color_mesh')
        self.text_mesh: Any = get_shared_resource(app, 'text_mesh')
        self.text_renderer: Any = get_shared_resource(app, 'text_renderer', size=FONT_SIZE_BUTTONS, bold=False)
        self.cached_text: Optional[str] = None
        self.text_tex: Any = None

    @global_profiler.profile_func('TextInput_HandleEvent')
    def handle_event(self, event: Any) -> None:
        """
        Handle mouse and keyboard events for the text input control.

        Args:
            event: Pygame event instance to process.
        """
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos: Tuple[int, int] = pg.mouse.get_pos()
            global_pos: Tuple[float, float] = self.get_global_pos()
            x: float = global_pos[0]
            y: float = global_pos[1]

            w: float = self.size[0]
            h: float = self.size[1]
            win_w: int = int(WIN_RES.x)
            win_h: int = int(WIN_RES.y)

            btn_x: float = (x + 1) * 0.5 * win_w
            btn_y: float = (-y + 1) * 0.5 * win_h
            btn_w: float = w * 0.5 * win_w
            btn_h: float = h * 0.5 * win_h

            self.is_active = (
                btn_x - btn_w < mouse_pos[0] < btn_x + btn_w and btn_y - btn_h < mouse_pos[1] < btn_y + btn_h
            )

        if self.is_active and event.type == pg.KEYDOWN:
            if event.key == pg.K_BACKSPACE:
                self.text = self.text[:-1]

            elif event.key == pg.K_RETURN or event.key == pg.K_ESCAPE:
                self.is_active = False

            else:
                if len(self.text) < 20 and event.unicode.isprintable():
                    self.text += event.unicode

    @global_profiler.profile_func('TextInput_Render')
    def render(self, offset: Tuple[float, float] = (0, 0), alpha: float = 1.0) -> None:
        """
        Render the input box, current text and blinking cursor.

        Args:
            offset: Render offset applied to the control position.
            alpha: Opacity multiplier for rendering.
        """
        w: float = self.size[0]
        h: float = self.size[1]

        c_val: Tuple[float, float, float, float] = (0.2, 0.25, 0.3, 0.9) if self.is_active else (0.1, 0.12, 0.15, 0.7)
        color: Tuple[float, float, float, float] = (c_val[0], c_val[1], c_val[2], c_val[3] * alpha)

        global_pos: Tuple[float, float] = self.get_global_pos()
        gx: float = global_pos[0]
        gy: float = global_pos[1]
        render_pos: Tuple[float, float] = (gx + offset[0], gy + offset[1])

        mask: Any = get_shared_resource(self.app, 'button_mask', radius=8, size=(w, h))
        mask.use(location=4)

        self.text_mesh.program['u_scale'] = (w, h)
        self.text_mesh.program['u_offset'] = render_pos

        if 'u_color' in self.text_mesh.program:
            self.text_mesh.program['u_color'] = color

        if 'u_alpha' in self.text_mesh.program:
            self.text_mesh.program['u_alpha'] = 1.0

        self.text_mesh.render()

        display_text: str = self.text + ('_' if self.is_active and (pg.time.get_ticks() // 500) % 2 == 0 else '')
        if not display_text and not self.is_active:
            display_text = self.label

        if 'u_color' in self.text_mesh.program:
            self.text_mesh.program['u_color'] = (1.0, 1.0, 1.0, 1.0)

        if 'u_alpha' in self.text_mesh.program:
            self.text_mesh.program['u_alpha'] = alpha

        # The rest of your text rendering logic remains the same
        if self.cached_text != display_text or self.text_tex is None:
            if self.text_tex:
                self.text_tex.release()
            self.text_tex = self.text_renderer.get_dynamic_texture(display_text)
            self.cached_text = display_text

        tex: Any = self.text_tex
        tex.use(location=4)
        tex_w: int = tex.size[0]
        tex_h: int = tex.size[1]

        scale_y: float = h * 0.6
        scale_x: float = scale_y * (tex_w / tex_h) / ASPECT_RATIO

        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = render_pos
        self.text_mesh.render()


class Slider(UINode):
    """
    An interactive UI slider component used to adjust numerical settings
    between a minimum and maximum value.

    Args:
        app (Any): The main application instance.
        text (str): The text label to display next to the slider.
        pos (Tuple[float, float]): The local normalized position.
        size (Tuple[float, float]): The normalized width and height.
        min_val (float): The minimum value of the slider.
        max_val (float): The maximum value of the slider.
        config_key (str): The key in `app.config` this slider controls.
        action (Optional[Callable[[Any], None]]): An optional callback to run on value change.
        is_int (bool): If True, the slider value will be rounded to the nearest integer.
    """

    @global_profiler.profile_func('Slider_Init')
    def __init__(
        self,
        app: Any,
        text: str,
        pos: Tuple[float, float],
        size: Tuple[float, float],
        min_val: float,
        max_val: float,
        config_key: str,
        action: Optional[Callable[[Any], None]] = None,
        is_int: bool = False,
    ) -> None:
        """
        Create a `Slider` used to adjust numerical settings.

        Supports integer rounding and optional callback `action` on change.
        """
        super().__init__(size)
        self.app: Any = app
        self.text: str = text
        self.local_pos: List[float] = list(pos)
        self.size: Tuple[float, float] = size
        self.min_val: float = min_val
        self.max_val: float = max_val
        self.config_key: str = config_key
        self.action: Optional[Callable[[Any], None]] = action
        self.is_int: bool = is_int

        self.color_mesh: Any = get_shared_resource(app, 'color_mesh')
        self.text_mesh: Any = get_shared_resource(app, 'text_mesh')
        self.text_renderer: Any = get_shared_resource(app, 'text_renderer', size=FONT_SIZE_SLIDERS, bold=True)

        self.is_hovered: bool = False
        self.is_dragging: bool = False
        self.cached_text: Optional[str] = None
        self.text_tex: Any = None

    @global_profiler.profile_func('Slider_Update')
    def update(self, mouse_pos: Optional[Tuple[int, int]] = None) -> None:
        """
        Update the slider's hover/drag state and apply value changes.

        Args:
            mouse_pos: Optional mouse position in pixels; current mouse position used when None.
        """
        if mouse_pos is None:
            mouse_pos = pg.mouse.get_pos()

        global_pos: Tuple[float, float] = self.get_global_pos()
        x: float = global_pos[0]
        y: float = global_pos[1]
        w: float = self.size[0]
        h: float = self.size[1]
        win_w: int = int(WIN_RES.x)
        win_h: int = int(WIN_RES.y)

        btn_x: float = (x + 1) * 0.5 * win_w
        btn_y: float = (-y + 1) * 0.5 * win_h
        btn_w: float = w * 0.5 * win_w
        btn_h: float = h * 0.5 * win_h

        self.is_hovered = btn_x - btn_w < mouse_pos[0] < btn_x + btn_w and btn_y - btn_h < mouse_pos[1] < btn_y + btn_h

        if self.is_dragging:
            if not pg.mouse.get_pressed()[0]:
                self.is_dragging = False
                self.app.save_config()

            else:
                progress: float = (mouse_pos[0] - (btn_x - btn_w)) / (btn_w * 2)
                progress = max(0.0, min(1.0, progress))
                val: Any = self.min_val + progress * (self.max_val - self.min_val)

                if self.is_int:
                    val = int(round(val))
                elif self.config_key == 'sensitivity':
                    val = round(val, 4)

                self.app.config[self.config_key] = val
                if self.action:
                    self.action(val)

    @global_profiler.profile_func('Slider_HandleEvent')
    def handle_event(self, event: Any) -> None:
        """
        Handle mouse events to begin dragging the slider.

        Args:
            event: Pygame event object.
        """
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.is_dragging = True

    @global_profiler.profile_func('Slider_Render')
    def render(self, offset: Tuple[float, float] = (0, 0), alpha: float = 1.0) -> None:
        """
        Render the slider track, fill and value text.

        Args:
            offset: Render offset applied to the slider position.
            alpha: Opacity multiplier for rendering.
        """
        w: float = self.size[0]
        h: float = self.size[1]
        global_pos: Tuple[float, float] = self.get_global_pos()
        gx: float = global_pos[0]
        gy: float = global_pos[1]
        render_pos: Tuple[float, float] = (gx + offset[0], gy + offset[1])

        mask: Any = get_shared_resource(self.app, 'button_mask', radius=8, size=(w, h))
        mask.use(location=4)
        self.text_mesh.program['u_scale'] = (w, h)
        self.text_mesh.program['u_offset'] = render_pos

        if 'u_color' in self.text_mesh.program:
            self.text_mesh.program['u_color'] = (0.1, 0.1, 0.1, 0.8 * alpha)

        if 'u_alpha' in self.text_mesh.program:
            self.text_mesh.program['u_alpha'] = 1.0

        self.text_mesh.render()

        val: Any = self.app.config[self.config_key]
        progress: float = (val - self.min_val) / (self.max_val - self.min_val)

        if progress > 0:
            # Clip the fill bar to the correct progress width
            clip_x_max: float = render_pos[0] - w + (w * 2 * progress)

            if 'u_clip' in self.app.shader_program.ui_text:
                self.app.shader_program.ui_text['u_clip'] = (-2.0, -2.0, clip_x_max, 2.0)

            fill_color: Tuple[float, float, float, float] = (
                UI_HOVER_COLOR[0],
                UI_HOVER_COLOR[1],
                UI_HOVER_COLOR[2],
                UI_HOVER_COLOR[3] * alpha,
            )

            if 'u_color' in self.text_mesh.program:
                self.text_mesh.program['u_color'] = fill_color

            self.text_mesh.render()

            # Reset clipping area
            if 'u_clip' in self.app.shader_program.ui_text:
                self.app.shader_program.ui_text['u_clip'] = (-2.0, -2.0, 2.0, 2.0)

        display_val: Any
        if self.is_int or self.config_key == 'fov':
            display_val = int(val)
        else:
            display_val = f'{val:.4f}'

        display_str: str = f'{self.text}: {display_val}'

        if self.cached_text != display_str or self.text_tex is None:
            if self.text_tex:
                self.text_tex.release()
            self.text_tex = self.text_renderer.get_dynamic_texture(display_str)
            self.cached_text = display_str

        tex: Any = self.text_tex
        tex.use(location=4)
        tex_w: int = tex.size[0]
        tex_h: int = tex.size[1]
        scale_y: float = h * 0.6
        scale_x: float = scale_y * (tex_w / tex_h) / ASPECT_RATIO

        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = render_pos

        if 'u_color' in self.text_mesh.program:
            self.text_mesh.program['u_color'] = (1.0, 1.0, 1.0, 1.0)

        if 'u_alpha' in self.text_mesh.program:
            self.text_mesh.program['u_alpha'] = alpha

        self.text_mesh.render()

        if 'u_alpha' in self.text_mesh.program:
            self.text_mesh.program['u_alpha'] = 1.0


class Toggle(UINode):
    """
    A binary toggle switch component for the UI (e.g., for On/Off settings).

    Args:
        app (Any): The main application instance.
        text (str): The text label to display next to the toggle.
        pos (Tuple[float, float]): The local normalized position.
        size (Tuple[float, float]): The normalized width and height of the switch track.
        config_key (str): The key in `app.config` this toggle controls.
        action (Optional[Callable[[bool], None]]): An optional callback to run on value change.
    """

    @global_profiler.profile_func('Toggle_Init')
    def __init__(
        self,
        app: Any,
        text: str,
        pos: Tuple[float, float],
        size: Tuple[float, float],
        config_key: str,
        action: Optional[Callable[[bool], None]] = None,
    ) -> None:
        """
        Initialize a binary `Toggle` control bound to a config key.

        Toggling updates `app.config` and calls `action` if provided.
        """
        super().__init__(size)
        self.app: Any = app
        self.text: str = text
        self.local_pos: List[float] = list(pos)
        self.config_key: str = config_key
        self.action: Optional[Callable[[bool], None]] = action

        self.color_mesh: Any = get_shared_resource(app, 'color_mesh')
        self.text_mesh: Any = get_shared_resource(app, 'text_mesh')
        self.text_renderer: Any = get_shared_resource(app, 'text_renderer', size=FONT_SIZE_SLIDERS, bold=True)

        self.is_hovered: bool = False
        self.cached_val: Optional[bool] = None
        self.text_tex: Any = None

    @global_profiler.profile_func('Toggle_Update')
    def update(self, mouse_pos: Optional[Tuple[int, int]] = None) -> None:
        """
        Update hover state for the toggle control.

        Args:
            mouse_pos: Optional mouse position in pixels; current mouse position used when None.
        """
        if mouse_pos is None:
            mouse_pos = pg.mouse.get_pos()

        global_pos: Tuple[float, float] = self.get_global_pos()
        x: float = global_pos[0]
        y: float = global_pos[1]
        w: float = self.size[0]
        h: float = self.size[1]

        win_w: int = int(WIN_RES.x)
        win_h: int = int(WIN_RES.y)

        btn_x: float = (x + 1) * 0.5 * win_w
        btn_y: float = (-y + 1) * 0.5 * win_h
        btn_w: float = w * 0.5 * win_w
        btn_h: float = h * 0.5 * win_h

        self.is_hovered = btn_x - btn_w < mouse_pos[0] < btn_x + btn_w and btn_y - btn_h < mouse_pos[1] < btn_y + btn_h

    @global_profiler.profile_func('Toggle_HandleEvent')
    def handle_event(self, event: Any) -> None:
        """
        Handle mouse clicks to flip the toggle and persist to config.

        Args:
            event: Pygame event object.
        """
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                val: bool = self.app.config.get(self.config_key, False)
                self.app.config[self.config_key] = not val
                self.app.save_config()

                if self.action:
                    self.action(not val)

    @global_profiler.profile_func('Toggle_Render')
    def render(self, offset: Tuple[float, float] = (0, 0), alpha: float = 1.0) -> None:
        """
        Render the toggle control including track and thumb.

        Args:
            offset: Render offset applied to the toggle position.
            alpha: Opacity multiplier for rendering.
        """
        w: float = self.size[0]
        h: float = self.size[1]
        global_pos: Tuple[float, float] = self.get_global_pos()
        gx: float = global_pos[0]
        gy: float = global_pos[1]
        render_pos: Tuple[float, float] = (gx + offset[0], gy + offset[1])

        val: bool = self.app.config.get(self.config_key, False)

        # Render text aligned to the left of the toggle switch
        if self.cached_val != val or self.text_tex is None:
            if self.text_tex:
                self.text_tex.release()
            display_val: str = 'ON' if val else 'OFF'
            self.text_tex = self.text_renderer.get_dynamic_texture(f'{self.text}: {display_val}')
            self.cached_val = val

        tex: Any = self.text_tex
        tex.use(location=4)
        tex_w: int = tex.size[0]
        tex_h: int = tex.size[1]
        scale_y: float = h * 0.8
        scale_x: float = scale_y * (tex_w / tex_h) / ASPECT_RATIO

        text_x: float = render_pos[0] - w - scale_x - 0.02

        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = (text_x, render_pos[1])

        if 'u_color' in self.text_mesh.program:
            self.text_mesh.program['u_color'] = (1.0, 1.0, 1.0, 1.0)

        if 'u_alpha' in self.text_mesh.program:
            self.text_mesh.program['u_alpha'] = alpha

        self.text_mesh.render()

        # Render track (pill shape)
        track_mask: Any = get_shared_resource(self.app, 'button_mask', radius=int(h * WIN_RES.y), size=(w, h))
        track_mask.use(location=4)
        self.text_mesh.program['u_scale'] = (w, h)
        self.text_mesh.program['u_offset'] = render_pos

        if 'u_color' in self.text_mesh.program:
            self.text_mesh.program['u_color'] = (0.1, 0.1, 0.1, 0.8 * alpha)

        if 'u_alpha' in self.text_mesh.program:
            self.text_mesh.program['u_alpha'] = 1.0

        self.text_mesh.render()

        thumb_w: float = h / ASPECT_RATIO
        thumb_h: float = h
        travel_dist: float = w - thumb_w
        thumb_x: float = render_pos[0] + travel_dist if val else render_pos[0] - travel_dist

        thumb_mask: Any = get_shared_resource(
            self.app, 'button_mask', radius=int(h * WIN_RES.y), size=(thumb_w, thumb_h)
        )
        thumb_mask.use(location=4)
        self.text_mesh.program['u_scale'] = (thumb_w, thumb_h)
        self.text_mesh.program['u_offset'] = (thumb_x, render_pos[1])

        base_c: Tuple[float, float, float, float] = (0.2, 0.7, 0.3, alpha) if val else (0.7, 0.2, 0.2, alpha)

        if self.is_hovered:
            base_c = (base_c[0] + 0.1, base_c[1] + 0.1, base_c[2] + 0.1, alpha)

        if 'u_color' in self.text_mesh.program:
            self.text_mesh.program['u_color'] = base_c

        self.text_mesh.render()

        if 'u_alpha' in self.text_mesh.program:
            self.text_mesh.program['u_alpha'] = 1.0
