"""
GUI widgets for controller parameter adjustment.
"""
import pygame
from dataclasses import dataclass
from typing import Callable


@dataclass
class SliderConfig:
    """Configuration for a single slider."""
    name: str           # Display label
    attr: str           # Attribute name on the controller
    min_val: float
    max_val: float
    color: tuple[int, int, int] = (70, 140, 200)


class ParameterPanel:
    """
    A floating panel with sliders and text inputs for adjusting controller parameters.
    """

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        sliders: list[SliderConfig],
        controller_getter: Callable,
        title: str = "Controller",
    ):
        self.x = x
        self.y = y
        self.width = width
        self.sliders = sliders
        self.get_controller = controller_getter
        self.title = title

        # Styling
        self.padding = 12
        self.slider_height = 6
        self.slider_spacing = 28
        self.handle_radius = 8
        self.title_height = 26
        self.label_width = 28
        self.input_width = 55
        self.input_height = 18

        # Computed height
        self.height = self.title_height + self.padding + len(sliders) * self.slider_spacing + self.padding - 4

        # Fonts (initialized on first draw)
        self._fonts_initialized = False
        self.title_font = None
        self.label_font = None
        self.value_font = None
        self.input_font = None

        # Drag state
        self.dragging_index: int | None = None

        # Text input state
        self.editing_index: int | None = None
        self.edit_text: str = ""
        self.cursor_blink_timer: int = 0

    def _init_fonts(self):
        if not self._fonts_initialized:
            self.title_font = pygame.font.SysFont("segoeui", 13, bold=True)
            self.label_font = pygame.font.SysFont("consolas", 12)
            self.value_font = pygame.font.SysFont("consolas", 12)
            self.input_font = pygame.font.SysFont("consolas", 12)
            self._fonts_initialized = True

    def _get_slider_rect(self, index: int) -> tuple[int, int, int, int]:
        """Return (x, y, width, height) for the slider track."""
        # Label is on the left, then slider, then input box
        sx = self.x + self.padding + self.label_width + 6
        sy = self.y + self.title_height + self.padding + index * self.slider_spacing + 6
        # Leave room for the input box on the right
        sw = self.width - self.padding - self.label_width - 6 - self.input_width - 8 - self.padding
        sh = self.slider_height
        return sx, sy, sw, sh

    def _get_input_rect(self, index: int) -> pygame.Rect:
        """Return the rect for the text input box."""
        sx, sy, sw, sh = self._get_slider_rect(index)
        ix = sx + sw + 6
        iy = sy - (self.input_height - sh) // 2
        return pygame.Rect(ix, iy, self.input_width, self.input_height)

    def _get_handle_pos(self, index: int, value: float) -> tuple[int, int]:
        """Return (x, y) for the handle center."""
        sx, sy, sw, sh = self._get_slider_rect(index)
        slider = self.sliders[index]
        norm = (value - slider.min_val) / (slider.max_val - slider.min_val) if slider.max_val > slider.min_val else 0.0
        norm = max(0.0, min(1.0, norm))
        hx = sx + int(norm * sw)
        hy = sy + sh // 2
        return hx, hy

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle mouse and keyboard events. Returns True if the event was consumed by the panel.
        """
        # Handle text input when editing
        if self.editing_index is not None:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    self._commit_edit()
                    return True
                elif event.key == pygame.K_ESCAPE:
                    self._cancel_edit()
                    return True
                elif event.key == pygame.K_BACKSPACE:
                    self.edit_text = self.edit_text[:-1]
                    return True
                elif event.key == pygame.K_TAB:
                    # Move to next/previous input
                    self._commit_edit()
                    shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
                    if shift:
                        next_idx = (self.editing_index - 1) % len(self.sliders)
                    else:
                        next_idx = (self.editing_index + 1) % len(self.sliders)
                    self._start_edit(next_idx)
                    return True
                elif event.unicode and (event.unicode.isdigit() or event.unicode in '.-'):
                    self.edit_text += event.unicode
                    return True
                return True

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # Check if clicking on a different input or outside
                clicked_input = False
                for i in range(len(self.sliders)):
                    input_rect = self._get_input_rect(i)
                    if input_rect.collidepoint(mx, my):
                        if i != self.editing_index:
                            self._commit_edit()
                            self._start_edit(i)
                        clicked_input = True
                        return True

                if not clicked_input:
                    # Clicked outside inputs, commit and check other panel interactions
                    self._commit_edit()
                    # Fall through to check slider clicks

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Check if click is within panel
            if self.x <= mx <= self.x + self.width and self.y <= my <= self.y + self.height:
                # Check each input box first
                for i in range(len(self.sliders)):
                    input_rect = self._get_input_rect(i)
                    if input_rect.collidepoint(mx, my):
                        self._start_edit(i)
                        return True

                # Check each slider
                ctrl = self.get_controller()
                for i, slider in enumerate(self.sliders):
                    sx, sy, sw, sh = self._get_slider_rect(i)

                    # Check if near handle or on track
                    track_top = sy - 12
                    track_bottom = sy + sh + 12
                    if sx - 5 <= mx <= sx + sw + 5 and track_top <= my <= track_bottom:
                        self.dragging_index = i
                        # Update value immediately on click
                        self._update_value_from_mouse(mx)
                        return True
                return True  # Consumed click even if not on slider

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging_index is not None:
                self.dragging_index = None
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_index is not None:
                mx, my = event.pos
                self._update_value_from_mouse(mx)
                return True

        return False

    def _start_edit(self, index: int):
        """Start editing a text input."""
        ctrl = self.get_controller()
        slider = self.sliders[index]
        value = getattr(ctrl, slider.attr, 0.0)
        self.editing_index = index
        # Use more precision for small values
        if abs(value) < 0.01 and value != 0:
            self.edit_text = f"{value:.4f}".rstrip('0').rstrip('.')
        else:
            self.edit_text = f"{value:.2f}".rstrip('0').rstrip('.')
        self.cursor_blink_timer = 0

    def _commit_edit(self):
        """Commit the current text edit."""
        if self.editing_index is None:
            return

        try:
            value = float(self.edit_text)
            ctrl = self.get_controller()
            slider = self.sliders[self.editing_index]
            setattr(ctrl, slider.attr, value)
        except ValueError:
            pass  # Invalid input, ignore

        self.editing_index = None
        self.edit_text = ""

    def _cancel_edit(self):
        """Cancel the current text edit."""
        self.editing_index = None
        self.edit_text = ""

    def _update_value_from_mouse(self, mx: int):
        """Update the currently dragged slider's value based on mouse x."""
        if self.dragging_index is None:
            return

        slider = self.sliders[self.dragging_index]
        sx, sy, sw, sh = self._get_slider_rect(self.dragging_index)

        # Compute normalized position
        norm = (mx - sx) / sw if sw > 0 else 0.0
        norm = max(0.0, min(1.0, norm))

        # Map to value range
        value = slider.min_val + norm * (slider.max_val - slider.min_val)

        # Set on controller
        ctrl = self.get_controller()
        setattr(ctrl, slider.attr, value)

    def is_dragging(self) -> bool:
        """Return True if currently dragging a slider."""
        return self.dragging_index is not None

    def is_editing(self) -> bool:
        """Return True if currently editing a text input."""
        return self.editing_index is not None

    def draw(self, surface: pygame.Surface):
        """Draw the parameter panel."""
        self._init_fonts()
        ctrl = self.get_controller()
        self.cursor_blink_timer += 1

        # Panel background with subtle shadow
        shadow_offset = 3
        shadow_rect = pygame.Rect(self.x + shadow_offset, self.y + shadow_offset, self.width, self.height)
        pygame.draw.rect(surface, (180, 180, 180), shadow_rect, border_radius=12)

        panel_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, (255, 255, 255), panel_rect, border_radius=12)
        pygame.draw.rect(surface, (100, 100, 100), panel_rect, 2, border_radius=12)

        # Title bar
        title_rect = pygame.Rect(self.x, self.y, self.width, self.title_height)
        pygame.draw.rect(surface, (50, 55, 65), title_rect, border_top_left_radius=12, border_top_right_radius=12)

        title_img = self.title_font.render(self.title, True, (240, 240, 240))
        title_x = self.x + (self.width - title_img.get_width()) // 2
        title_y = self.y + (self.title_height - title_img.get_height()) // 2
        surface.blit(title_img, (title_x, title_y))

        # Draw each slider
        mx, my = pygame.mouse.get_pos()

        for i, slider in enumerate(self.sliders):
            sx, sy, sw, sh = self._get_slider_rect(i)
            value = getattr(ctrl, slider.attr, 0.0)
            hx, hy = self._get_handle_pos(i, value)

            # Label on the left
            label_img = self.label_font.render(slider.name, True, (50, 50, 50))
            label_x = self.x + self.padding
            label_y = sy + (sh - label_img.get_height()) // 2
            surface.blit(label_img, (label_x, label_y))

            # Track background
            track_rect = pygame.Rect(sx, sy, sw, sh)
            pygame.draw.rect(surface, (220, 220, 220), track_rect, border_radius=4)

            # Filled portion (clamp norm for display)
            norm = (value - slider.min_val) / (slider.max_val - slider.min_val) if slider.max_val > slider.min_val else 0.0
            norm_clamped = max(0.0, min(1.0, norm))
            if norm_clamped > 0:
                fill_w = int(norm_clamped * sw)
                fill_rect = pygame.Rect(sx, sy, fill_w, sh)
                pygame.draw.rect(surface, slider.color, fill_rect, border_radius=4)

            # Track border
            pygame.draw.rect(surface, (160, 160, 160), track_rect, 1, border_radius=4)

            # Handle (only show if value is within slider range)
            if 0.0 <= norm <= 1.0:
                is_dragging_this = self.dragging_index == i
                is_hover = abs(mx - hx) < self.handle_radius + 4 and abs(my - hy) < self.handle_radius + 4

                if is_dragging_this:
                    handle_color = tuple(min(255, c + 40) for c in slider.color)
                elif is_hover:
                    handle_color = tuple(min(255, c + 20) for c in slider.color)
                else:
                    handle_color = slider.color

                pygame.draw.circle(surface, handle_color, (hx, hy), self.handle_radius)
                pygame.draw.circle(surface, (60, 60, 60), (hx, hy), self.handle_radius, 2)

                # Inner highlight on handle
                highlight_pos = (hx - 3, hy - 3)
                pygame.draw.circle(surface, (255, 255, 255), highlight_pos, 3)

            # Text input box
            input_rect = self._get_input_rect(i)
            is_editing_this = self.editing_index == i

            if is_editing_this:
                # Active input style
                pygame.draw.rect(surface, (255, 255, 255), input_rect, border_radius=4)
                pygame.draw.rect(surface, slider.color, input_rect, 2, border_radius=4)

                # Render edit text with cursor
                text_to_render = self.edit_text
                text_img = self.input_font.render(text_to_render, True, (30, 30, 30))
                text_x = input_rect.x + 4
                text_y = input_rect.y + (input_rect.height - text_img.get_height()) // 2
                surface.blit(text_img, (text_x, text_y))

                # Blinking cursor
                if (self.cursor_blink_timer // 30) % 2 == 0:
                    cursor_x = text_x + text_img.get_width() + 1
                    cursor_y1 = input_rect.y + 3
                    cursor_y2 = input_rect.bottom - 3
                    pygame.draw.line(surface, (30, 30, 30), (cursor_x, cursor_y1), (cursor_x, cursor_y2), 2)
            else:
                # Inactive input style
                input_hover = input_rect.collidepoint(mx, my)
                bg_color = (245, 245, 245) if not input_hover else (250, 250, 250)
                border_color = (180, 180, 180) if not input_hover else (140, 140, 140)

                pygame.draw.rect(surface, bg_color, input_rect, border_radius=4)
                pygame.draw.rect(surface, border_color, input_rect, 1, border_radius=4)

                # Display current value (use more precision for small values)
                if abs(value) < 0.01 and value != 0:
                    value_str = f"{value:.4f}".rstrip('0').rstrip('.')
                else:
                    value_str = f"{value:.2f}".rstrip('0').rstrip('.')
                text_img = self.input_font.render(value_str, True, (60, 60, 60))
                text_x = input_rect.x + 4
                text_y = input_rect.y + (input_rect.height - text_img.get_height()) // 2
                surface.blit(text_img, (text_x, text_y))
