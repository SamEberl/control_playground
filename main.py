import math
import sys
from collections import deque

import numpy as np
import pygame

from controller import controller, reset_controller, get_controller
from dynamics import rk4_step
from gui import ParameterPanel, SliderConfig
from metrics import Metrics
from params import P
from plotting import draw_plot, draw_phase_plot
from utils import clamp, mechanical_energy, mouse_force, wrap_angle


# -----------------------------
# Main
# -----------------------------
def main():
    pygame.init()
    pygame.display.set_caption("Cart-Pole Playground (constraints + refs + metrics + history)")

    # Bigger window
    W, H = 1600, 800
    screen = pygame.display.set_mode((W, H))
    clock = pygame.time.Clock()
    hud_font = pygame.font.SysFont("consolas", 16)

    ppm = P.pixels_per_meter
    track_y = int(H * 0.72)

    cart_w = int(P.cart_width_m * ppm)
    cart_h = int(P.cart_height_m * ppm)
    wheel_r = int(P.wheel_radius_m * ppm)
    pole_len_px = int(2.0 * P.l * ppm)

    x_min_px = cart_w // 2 + 12
    x_max_px = W - cart_w // 2 - 12
    x_min_m = (x_min_px - W / 2) / ppm
    x_max_m = (x_max_px - W / 2) / ppm

    ref_x = 0.0
    ref_theta = 0.0

    def reset_state():
        return np.array([0.0, 0.0, 0.15, 0.0], dtype=float)

    state = reset_state()
    t = 0.0
    paused = False
    show_history = P.plot_enabled_default

    # Toggleable friction
    friction_on = True

    key_force = 0.0
    key_force_mag = 18.0

    metrics = Metrics()
    metrics.reset()

    # Controller parameter panel
    param_panel = ParameterPanel(
        x=12,
        y=H - 140,
        width=400,
        sliders=[
            SliderConfig(name="k_p", attr="k_p", min_val=0.0, max_val=10.0, color=(70, 140, 200)),
            SliderConfig(name="k_i", attr="k_i", min_val=0.0, max_val=10.0, color=(200, 120, 70)),
            SliderConfig(name="k_d", attr="k_d", min_val=0.0, max_val=10.0, color=(120, 180, 90)),
        ],
        controller_getter=get_controller,
        title="Controller Gains",
    )

    hist_t = deque(maxlen=P.history_len)
    hist_x = deque(maxlen=P.history_len)
    hist_x_dot = deque(maxlen=P.history_len)
    hist_theta = deque(maxlen=P.history_len)
    hist_theta_dot = deque(maxlen=P.history_len)
    hist_force = deque(maxlen=P.history_len)

    def push_history(tt, st, force):
        hist_t.append(tt)
        hist_x.append(float(st[0]))
        hist_x_dot.append(float(st[1]))
        hist_theta.append(float(wrap_angle(st[2])))
        hist_theta_dot.append(float(st[3]))
        hist_force.append(float(force))

    def cart_px_from_x(x_m: float) -> float:
        return W / 2 + x_m * ppm

    def draw_text_lines(x, y, lines):
        yy = y
        for line in lines:
            img = hud_font.render(line, True, (20, 20, 20))
            screen.blit(img, (x, yy))
            yy += img.get_height() + 2

    def constraint_flag(st: np.ndarray, force_total: float) -> bool:
        eps = 1e-6
        x = float(st[0])

        at_left = x <= x_min_m + eps
        at_right = x >= x_max_m - eps

        pushing_left = force_total < 0.0
        pushing_right = force_total > 0.0

        return (at_left and pushing_left) or (at_right and pushing_right)

    running = True
    while running:
        # --- events ---
        for event in pygame.event.get():
            # Let parameter panel handle events first
            if param_panel.handle_event(event):
                continue

            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    state = reset_state()
                    t = 0.0
                    metrics.reset()
                    reset_controller()
                    hist_t.clear(); hist_x.clear(); hist_x_dot.clear(); hist_theta.clear(); hist_theta_dot.clear(); hist_force.clear()
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_h:
                    show_history = not show_history
                elif event.key == pygame.K_c:
                    ref_x = 0.0
                    ref_theta = 0.0
                elif event.key == pygame.K_f:
                    friction_on = not friction_on

        keys = pygame.key.get_pressed()

        # Disable keyboard controls while editing text input
        if not param_panel.is_editing():
            # Keyboard force
            if keys[pygame.K_LEFT] and not keys[pygame.K_RIGHT]:
                key_force = -key_force_mag
            elif keys[pygame.K_RIGHT] and not keys[pygame.K_LEFT]:
                key_force = key_force_mag
            else:
                key_force = 0.0

            # Reference adjustments
            if keys[pygame.K_q]:
                ref_x -= 0.01
            if keys[pygame.K_a]:
                ref_x += 0.01
            ref_x = clamp(ref_x, x_min_m, x_max_m)

            if keys[pygame.K_w]:
                ref_theta += math.radians(0.5)
            if keys[pygame.K_s]:
                ref_theta -= math.radians(0.5)
            ref_theta = wrap_angle(ref_theta)
        else:
            key_force = 0.0

        # Mouse
        mx, my = pygame.mouse.get_pos()
        left_down, _, right_down = pygame.mouse.get_pressed()

        # Don't apply mouse force if interacting with parameter panel
        if param_panel.is_dragging() or param_panel.is_editing():
            left_down = False
            right_down = False

        # Effective damping based on friction toggle
        cart_damp = P.cart_damping if friction_on else 0.0
        pole_damp = P.pole_damping if friction_on else 0.0

        # Forces
        u_raw = controller(state.copy(), t, ref_x, ref_theta)
        u = clamp(u_raw, -P.max_force, P.max_force)
        is_saturated = abs(u_raw) > P.max_force

        cart_x_px = cart_px_from_x(state[0])
        f_mouse = mouse_force(cart_x_px, mx, left_down, right_down)
        f_total = float(u + f_mouse + key_force)

        # Integrate
        if not paused:
            for _ in range(P.substeps):
                constrained = constraint_flag(state, f_total)

                if constrained:
                    if state[0] <= x_min_m:
                        state[0] = x_min_m
                    if state[0] >= x_max_m:
                        state[0] = x_max_m
                    state[1] = 0.0

                state = rk4_step(state, f_total, P.dt, constrained, cart_damp, pole_damp)

                # Safety clamp
                if state[0] < x_min_m:
                    state[0] = x_min_m
                    if state[1] < 0:
                        state[1] = 0.0
                elif state[0] > x_max_m:
                    state[0] = x_max_m
                    if state[1] > 0:
                        state[1] = 0.0

                t += P.dt
                metrics.update(state, t, f_total, ref_x, ref_theta, P.dt)

            push_history(t, state, f_total)

        # Draw
        screen.fill((245, 245, 245))
        pygame.draw.line(screen, (60, 60, 60), (0, track_y), (W, track_y), 3)

        # Reference x line
        ref_x_px = int(cart_px_from_x(ref_x))
        pygame.draw.line(screen, (120, 120, 120), (ref_x_px, track_y - 90), (ref_x_px, track_y + 30), 2)

        # Cart
        cart_x_px = int(cart_px_from_x(state[0]))
        cart_y_px = track_y - cart_h // 2
        cart_rect = pygame.Rect(cart_x_px - cart_w // 2, cart_y_px - cart_h // 2, cart_w, cart_h)

        # Change cart color when saturated
        if is_saturated:
            cart_color = (200, 80, 50)  # Orange-red when saturated
            cart_border = (180, 40, 20)
        else:
            cart_color = (30, 120, 200)  # Normal blue
            cart_border = (20, 20, 20)

        pygame.draw.rect(screen, cart_color, cart_rect, border_radius=10)
        pygame.draw.rect(screen, cart_border, cart_rect, 2, border_radius=10)

        # Saturation indicator bar below cart
        if is_saturated:
            sat_bar_w = 40
            sat_bar_h = 4
            sat_bar_x = cart_x_px - sat_bar_w // 2
            sat_bar_y = cart_y_px + cart_h // 2 + 4
            pygame.draw.rect(screen, (220, 60, 30), (sat_bar_x, sat_bar_y, sat_bar_w, sat_bar_h), border_radius=2)

        # Wheels
        pygame.draw.circle(screen, (40, 40, 40), (cart_x_px - cart_w // 4, track_y + wheel_r), wheel_r)
        pygame.draw.circle(screen, (40, 40, 40), (cart_x_px + cart_w // 4, track_y + wheel_r), wheel_r)

        # Pivot
        pivot_x = cart_x_px
        pivot_y = cart_y_px - cart_h // 2 + int(0.04 * ppm)

        theta = float(state[2])
        end_x = int(pivot_x + pole_len_px * math.sin(theta))
        end_y = int(pivot_y - pole_len_px * math.cos(theta))
        pygame.draw.line(screen, (200, 50, 50), (pivot_x, pivot_y), (end_x, end_y), P.pole_thickness_px)
        pygame.draw.circle(screen, (120, 0, 0), (end_x, end_y), max(10, int(0.06 * ppm)))
        pygame.draw.circle(screen, (20, 20, 20), (pivot_x, pivot_y), 6)

        # Reference theta dashed line
        ref_end_x = int(pivot_x + pole_len_px * math.sin(ref_theta))
        ref_end_y = int(pivot_y - pole_len_px * math.cos(ref_theta))
        dash_n = 18
        for i in range(dash_n):
            a = i / dash_n
            b = (i + 0.5) / dash_n
            x1 = int(pivot_x + a * (ref_end_x - pivot_x))
            y1 = int(pivot_y + a * (ref_end_y - pivot_y))
            x2 = int(pivot_x + b * (ref_end_x - pivot_x))
            y2 = int(pivot_y + b * (ref_end_y - pivot_y))
            pygame.draw.line(screen, (140, 140, 140), (x1, y1), (x2, y2), 2)

        # Force indicators - common scale for all forces
        force_to_px_scale = 4.0  # pixels per Newton

        # Controller force indicator (muted grey bar)
        if abs(u) > 0.1:
            force_bar_len = int(u * force_to_px_scale)
            force_bar_y = track_y - 105
            pygame.draw.line(screen, (140, 140, 140), (cart_x_px, force_bar_y), (cart_x_px + force_bar_len, force_bar_y), 3)

        # Mouse force indicator
        if abs(f_mouse) > 0.1:
            mouse_bar_len = int(f_mouse * force_to_px_scale)
            mouse_bar_y = track_y - 95
            pygame.draw.line(screen, (0, 0, 0), (cart_x_px, mouse_bar_y), (cart_x_px + mouse_bar_len, mouse_bar_y), 2)
            pygame.draw.circle(screen, (0, 0, 0), (cart_x_px + mouse_bar_len, mouse_bar_y), 5)

        # Parameter panel
        param_panel.draw(screen)

        # HUD
        E = mechanical_energy(state)
        theta_err = wrap_angle(theta - ref_theta)
        x_err = float(state[0] - ref_x)

        settle_str = "—" if metrics.settle_time is None else f"{metrics.settle_time: .2f}s"

        hud_lines = [
            f"t={t:7.3f}s  paused={paused}  history(H)={show_history}  friction(F)={'ON' if friction_on else 'OFF'}",
            f"x={state[0]: .3f}m  x_dot={state[1]: .3f}m/s  (err {x_err:+.3f}m, ref {ref_x:+.3f}m)",
            f"theta={theta: .3f}rad  theta_dot={state[3]: .3f}rad/s  (err {theta_err:+.3f}rad, ref {ref_theta:+.3f}rad)",
            f"u={u:+.2f}N  mouse={f_mouse:+.2f}N  keys={key_force:+.2f}N  total={f_total:+.2f}N",
            f"Max |theta_err|={metrics.max_abs_theta: .3f}rad   Max |x_err|={metrics.max_abs_x_dev: .3f}m",
            f"Settling time={settle_str}  (band: |x|<={P.settle_x_thresh}m, |theta|<={math.degrees(P.settle_theta_thresh):.1f}deg for {P.settle_hold_time}s)",
            f"∫|F|dt={metrics.energy_abs_impulse: .2f} N·s   E_mech~={E: .3f}",
            "Controls: ←/→ force | LMB drag spring | RMB shove | Q/A ref x | W/S ref theta | C center refs",
            "          F friction | R reset | Space pause | H plots | Esc quit",
        ]
        draw_text_lines(12, 12, hud_lines)

        # Plots
        if show_history:
            pad = 12
            plot_w = 320
            plot_h = 94
            phase_size = 145

            # Time series plots on the left column of the right panel area
            x0 = W - plot_w - phase_size - pad - 8
            y0 = pad

            hx = list(hist_x)
            hxd = list(hist_x_dot)
            ht = list(hist_theta)
            htd = list(hist_theta_dot)
            hf = list(hist_force)

            draw_plot(screen, pygame.Rect(x0, y0, plot_w, plot_h), hx, ymin=x_min_m, ymax=x_max_m, label="x (m)", ref_value=ref_x)
            draw_plot(screen, pygame.Rect(x0, y0 + plot_h + 8, plot_w, plot_h), ht, ymin=-math.pi, ymax=math.pi, label="theta (rad)", ref_value=ref_theta)
            draw_plot(
                screen,
                pygame.Rect(x0, y0 + 2 * (plot_h + 8), plot_w, plot_h),
                hf,
                ymin=-(P.max_force + P.max_mouse_force + key_force_mag),
                ymax=(P.max_force + P.max_mouse_force + key_force_mag),
                label="force (N)",
                ref_value=0.0
            )

            # Phase diagrams on the right column
            phase_x0 = x0 + plot_w + 8
            phase_y0 = y0

            # Velocity ranges (approximate)
            x_dot_max = 3.0
            theta_dot_max = 8.0

            draw_phase_plot(
                screen,
                pygame.Rect(phase_x0, phase_y0, phase_size, phase_size),
                hx, hxd,
                xmin=x_min_m, xmax=x_max_m,
                ymin=-x_dot_max, ymax=x_dot_max,
                x_label="x",
                y_label="x_dot",
                color=(70, 140, 200),
                current_x=state[0],
                current_y=state[1],
            )
            draw_phase_plot(
                screen,
                pygame.Rect(phase_x0, phase_y0 + phase_size + 8, phase_size, phase_size),
                ht, htd,
                xmin=-math.pi, xmax=math.pi,
                ymin=-theta_dot_max, ymax=theta_dot_max,
                x_label="θ",
                y_label="θ_dot",
                color=(200, 80, 80),
                current_x=state[2],
                current_y=state[3],
            )

        pygame.display.flip()
        clock.tick(120)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
