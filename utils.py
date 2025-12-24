import math
from typing import Sequence

import numpy as np

from params import P


def wrap_angle(theta: float) -> float:
    return (theta + math.pi) % (2 * math.pi) - math.pi


def clamp(v: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, v)))


def mechanical_energy(state: np.ndarray) -> float:
    x, x_dot, theta, theta_dot = state
    s = math.sin(theta)
    c = math.cos(theta)

    x_com_dot = x_dot + P.l * theta_dot * c
    y_com_dot = -P.l * theta_dot * s
    v_com2 = x_com_dot**2 + y_com_dot**2

    T_cart = 0.5 * P.M * x_dot**2
    T_com = 0.5 * P.m * v_com2

    I_com = (1.0 / 3.0) * P.m * (P.l**2)
    T_rot = 0.5 * I_com * theta_dot**2

    V = P.m * P.g * P.l * (1.0 - c)  # 0 at upright

    return T_cart + T_com + T_rot + V


def mouse_force(cart_x_px: float, mouse_x_px: float, left_down: bool, right_down: bool) -> float:
    if not (left_down or right_down):
        return 0.0

    dx_px = mouse_x_px - cart_x_px

    if left_down:
        k = 0.16  # N per pixel
        f = k * dx_px
    else:
        f = 26.0 * math.tanh(dx_px / 75.0)

    return clamp(f, -P.max_mouse_force, P.max_mouse_force)


