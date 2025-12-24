import math
from dataclasses import dataclass


@dataclass
class Params:
    # Physics
    M: float = 1.0       # cart mass (kg)
    m: float = 0.2       # pole mass (kg)
    l: float = 0.5       # pivot to COM distance (m)  (rod length ~ 2l)
    g: float = 9.81

    # Damping (these are the "friction ON" values)
    cart_damping: float = 0.05      # N per (m/s)  (slightly increased)
    pole_damping: float = 0.02      # N*m per (rad/s) (slightly increased)

    # Force limits
    max_force: float = 50.0
    max_mouse_force: float = 50.0

    # Integration
    dt: float = 1.0 / 240.0
    substeps: int = 2

    # Display scaling
    pixels_per_meter: float = 170.0

    # Visual sizes in meters (converted to px)
    cart_width_m: float = 0.55
    cart_height_m: float = 0.25
    wheel_radius_m: float = 0.05
    pole_thickness_px: int = 6

    # History/plots
    history_len: int = 900
    plot_enabled_default: bool = True

    # Settling thresholds
    settle_x_thresh: float = 0.05
    settle_theta_thresh: float = math.radians(3.0)
    settle_hold_time: float = 1.0


P = Params()


