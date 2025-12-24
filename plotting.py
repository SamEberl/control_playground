import numpy as np
import pygame

from utils import clamp


def draw_plot(surface, rect: pygame.Rect, data, ymin, ymax, label: str, ref_value=None):
    pygame.draw.rect(surface, (255, 255, 255), rect, border_radius=8)
    pygame.draw.rect(surface, (40, 40, 40), rect, 1, border_radius=8)

    if len(data) < 2:
        return

    midy = rect.y + rect.height // 2
    pygame.draw.line(surface, (220, 220, 220), (rect.x + 6, midy), (rect.right - 6, midy), 1)

    if ref_value is not None and ymax > ymin:
        ry = rect.bottom - 6 - int((ref_value - ymin) / (ymax - ymin) * (rect.height - 12))
        ry = clamp(ry, rect.y + 6, rect.bottom - 6)
        pygame.draw.line(surface, (170, 170, 170), (rect.x + 6, int(ry)), (rect.right - 6, int(ry)), 1)

    xs = np.linspace(rect.x + 6, rect.right - 6, num=len(data))
    ys = []
    for v in data:
        if ymax <= ymin:
            y = midy
        else:
            y = rect.bottom - 6 - (v - ymin) / (ymax - ymin) * (rect.height - 12)
        ys.append(y)

    pts = list(zip(xs.astype(int), np.array(ys).astype(int)))
    pygame.draw.lines(surface, (0, 0, 0), False, pts, 2)

    font = pygame.font.SysFont("consolas", 14)
    txt = font.render(label, True, (20, 20, 20))
    surface.blit(txt, (rect.x + 8, rect.y + 6))


def draw_phase_plot(
    surface,
    rect: pygame.Rect,
    x_data,
    y_data,
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    x_label: str,
    y_label: str,
    color: tuple[int, int, int] = (50, 100, 180),
    current_x: float | None = None,
    current_y: float | None = None,
):
    """
    Draw a phase diagram (x vs y) with axes through the origin.
    x_data and y_data should be sequences of the same length.
    """
    pygame.draw.rect(surface, (255, 255, 255), rect, border_radius=8)
    pygame.draw.rect(surface, (40, 40, 40), rect, 1, border_radius=8)

    pad = 6
    plot_x = rect.x + pad
    plot_y = rect.y + pad
    plot_w = rect.width - 2 * pad
    plot_h = rect.height - 2 * pad

    font = pygame.font.SysFont("consolas", 11)
    value_font = pygame.font.SysFont("consolas", 10)

    def to_px(xv, yv):
        if xmax <= xmin or ymax <= ymin:
            return plot_x + plot_w // 2, plot_y + plot_h // 2
        px = plot_x + (xv - xmin) / (xmax - xmin) * plot_w
        py = plot_y + plot_h - (yv - ymin) / (ymax - ymin) * plot_h
        return int(clamp(px, plot_x, plot_x + plot_w)), int(clamp(py, plot_y, plot_y + plot_h))

    # Draw axes through origin
    origin_px, origin_py = to_px(0, 0)
    # Vertical axis (y)
    if plot_x <= origin_px <= plot_x + plot_w:
        pygame.draw.line(surface, (180, 180, 180), (origin_px, plot_y), (origin_px, plot_y + plot_h), 1)
    # Horizontal axis (x)
    if plot_y <= origin_py <= plot_y + plot_h:
        pygame.draw.line(surface, (180, 180, 180), (plot_x, origin_py), (plot_x + plot_w, origin_py), 1)

    # Axis labels at axis ends
    # X-axis label: at right end of horizontal axis
    x_txt = font.render(x_label, True, (100, 100, 100))
    x_label_y = clamp(origin_py + 2, plot_y, plot_y + plot_h - x_txt.get_height())
    surface.blit(x_txt, (plot_x + plot_w - x_txt.get_width(), int(x_label_y)))

    # Y-axis label: at top end of vertical axis
    y_txt = font.render(y_label, True, (100, 100, 100))
    y_label_x = clamp(origin_px + 2, plot_x, plot_x + plot_w - y_txt.get_width())
    surface.blit(y_txt, (int(y_label_x), plot_y))

    # Current values display (bottom-left corner)
    if current_x is not None and current_y is not None:
        val_str = f"{current_x:+.2f}, {current_y:+.2f}"
        val_txt = value_font.render(val_str, True, (60, 60, 60))
        surface.blit(val_txt, (rect.x + 6, rect.bottom - val_txt.get_height() - 4))

    if len(x_data) < 2 or len(y_data) < 2:
        return

    # Build points
    pts = []
    for xv, yv in zip(x_data, y_data):
        pts.append(to_px(xv, yv))

    # Draw trajectory
    if len(pts) >= 2:
        # Draw with fading effect (older points lighter)
        n = len(pts)
        for i in range(n - 1):
            alpha = 0.3 + 0.7 * (i / n)
            c = tuple(int(255 - alpha * (255 - cc)) for cc in color)
            pygame.draw.line(surface, c, pts[i], pts[i + 1], 2)

    # Highlight current point
    if pts:
        pygame.draw.circle(surface, color, pts[-1], 5)
        pygame.draw.circle(surface, (30, 30, 30), pts[-1], 5, 1)


