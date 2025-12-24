from dataclasses import dataclass

import numpy as np

from params import P
from utils import wrap_angle


@dataclass
class Metrics:
    max_abs_theta: float = 0.0
    max_abs_x_dev: float = 0.0
    energy_abs_impulse: float = 0.0
    settle_time: float | None = None
    _in_band_since: float | None = None

    def reset(self):
        self.max_abs_theta = 0.0
        self.max_abs_x_dev = 0.0
        self.energy_abs_impulse = 0.0
        self.settle_time = None
        self._in_band_since = None

    def update(self, state: np.ndarray, t: float, force: float, ref_x: float, ref_theta: float, dt: float):
        x, _, theta, _ = state

        theta_err = wrap_angle(theta - ref_theta)
        x_err = x - ref_x

        self.max_abs_theta = max(self.max_abs_theta, abs(theta_err))
        self.max_abs_x_dev = max(self.max_abs_x_dev, abs(x_err))
        self.energy_abs_impulse += abs(force) * dt

        in_band = (abs(x_err) <= P.settle_x_thresh) and (abs(theta_err) <= P.settle_theta_thresh)

        if self.settle_time is None:
            if in_band:
                if self._in_band_since is None:
                    self._in_band_since = t
                elif (t - self._in_band_since) >= P.settle_hold_time:
                    self.settle_time = self._in_band_since
            else:
                self._in_band_since = None


