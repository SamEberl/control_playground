import numpy as np


class Controller:
    def __init__(self):
        self.k_p = 5.0
        self.k_i = 2.0
        self.k_d = 3.0

        self.x_err_i = 0.0
        self.prev_t = 0.0

    def reset(self) -> None:
        """
        Optional: reset any internal state (e.g., when the simulation is reset).
        """
        self.x_err_i = 0.0
        self.prev_t = 0.0

    def __call__(self, state: np.ndarray, t: float, ref_x: float, ref_theta: float) -> float:
        """
        Compute the control input given the current state and references.
        """
        
        x = state[0]
        x_dot = state[1]
        theta = state[2]
        theta_dot = state[3]

        dt = t - self.prev_t
        self.prev_t = t

        x_err = ref_x - x
        self.x_err_i += x_err * dt
        # x_err_pred = ref_x - (x + x_dot)

        u_p = self.k_p * x_err
        u_i = self.k_i * self.x_err_i
        u_d = self.k_d * x_dot * -1.0

        u = u_p + u_i + u_d

        return u


# Single shared controller instance used by the simulation
_controller = Controller()


def controller(state: np.ndarray, t: float, ref_x: float, ref_theta: float) -> float:
    """
    Function-style entry point used by the main simulation.
    Delegates to the shared Controller instance.
    """
    return _controller(state, t, ref_x, ref_theta)


def reset_controller() -> None:
    """
    Reset the controller's internal state.
    Called when the simulation is reset.
    """
    _controller.reset()


def get_controller() -> Controller:
    """
    Get the shared controller instance for direct parameter access.
    """
    return _controller

