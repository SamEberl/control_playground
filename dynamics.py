import math

import numpy as np

from params import P
from utils import wrap_angle


def dynamics_free(state: np.ndarray, force: float, cart_damp: float, pole_damp: float) -> np.ndarray:
    x, x_dot, theta, theta_dot = state

    force_eff = force - cart_damp * x_dot

    s = math.sin(theta)
    c = math.cos(theta)

    tau_damp = -pole_damp * theta_dot
    theta_dd_extra = tau_damp / (P.m * (P.l**2) + 1e-9)

    temp = (force_eff + P.m * P.l * (theta_dot ** 2) * s) / (P.M + P.m)
    denom = P.l * (4.0 / 3.0 - (P.m * (c ** 2)) / (P.M + P.m))
    theta_dd = (P.g * s - c * temp) / (denom + 1e-9)
    x_dd = temp - (P.m * P.l * theta_dd * c) / (P.M + P.m)

    theta_dd += theta_dd_extra

    return np.array([x_dot, x_dd, theta_dot, theta_dd], dtype=float)


def dynamics_constrained(state: np.ndarray, pole_damp: float) -> np.ndarray:
    # Cart held at wall: x_dot = 0, x_dd = 0; pole is a fixed-pivot rod
    x, x_dot, theta, theta_dot = state

    s = math.sin(theta)

    tau_damp = -pole_damp * theta_dot
    theta_dd_extra = tau_damp / (P.m * (P.l**2) + 1e-9)

    denom_fixed = P.l * (4.0 / 3.0)
    theta_dd = (P.g * s) / (denom_fixed + 1e-9) + theta_dd_extra

    return np.array([0.0, 0.0, theta_dot, theta_dd], dtype=float)


def rk4_step(state: np.ndarray, force: float, dt: float, constrained: bool, cart_damp: float, pole_damp: float) -> np.ndarray:
    if constrained:
        f = lambda st: dynamics_constrained(st, pole_damp)
    else:
        f = lambda st: dynamics_free(st, force, cart_damp, pole_damp)

    k1 = f(state)
    k2 = f(state + 0.5 * dt * k1)
    k3 = f(state + 0.5 * dt * k2)
    k4 = f(state + dt * k3)

    nxt = state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
    nxt[2] = wrap_angle(float(nxt[2]))
    return nxt


