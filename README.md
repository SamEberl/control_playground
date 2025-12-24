# Cart-Pole Playground

An interactive cart-pole simulation with real-time visualization and a customizable controller.

## Overview

This project provides a physics simulation of the classic cart-pole (inverted pendulum) control problem. The cart moves along a 1D track while balancing a pole attached via a pivot. The goal is to design a controller that keeps the pole balanced while moving the cart to a target position.

## Features

- **Real-time physics simulation** using RK4 integration
- **Interactive controls**: push the cart with mouse or keyboard
- **Adjustable controller gains** via GUI sliders (k_p, k_i, k_d)
- **Time-series plots**: position, angle, and force over time
- **Phase diagrams**: x vs x_dot and θ vs θ_dot
- **Performance metrics**: settling time, max error, energy usage
- **Toggleable friction** for testing robustness

## Installation

Requires Python 3.10+ with the following packages:

```bash
pip install numpy pygame
```

## Usage

Run the simulation:

```bash
python main.py
```

### Controls

| Key/Mouse | Action |
|-----------|--------|
| ← / → | Apply force to cart |
| Left Mouse Button | Drag cart with spring force |
| Right Mouse Button | Shove cart |
| Q / A | Decrease / increase reference x position |
| W / S | Increase / decrease reference angle |
| C | Center references (reset to 0) |
| F | Toggle friction on/off |
| R | Reset simulation |
| Space | Pause/resume |
| H | Toggle history plots |
| Esc | Quit |

### Controller

Edit `controller.py` to implement your own control law. The `Controller` class provides:

- `k_p`, `k_i`, `k_d`: gain parameters (adjustable via GUI)
- `__call__(state, t, ref_x, ref_theta)`: called each timestep, returns force
- `reset()`: called when simulation resets

The state vector is `[x, x_dot, theta, theta_dot]` where:
- `x`: cart position (m)
- `x_dot`: cart velocity (m/s)
- `theta`: pole angle from vertical (rad, 0 = upright)
- `theta_dot`: pole angular velocity (rad/s)

## Project Structure

```
├── main.py        # Main loop, rendering, event handling
├── controller.py  # User-defined controller (edit this!)
├── dynamics.py    # Physics equations and RK4 integrator
├── params.py      # Simulation parameters (masses, limits, etc.)
├── metrics.py     # Performance tracking (settling time, etc.)
├── plotting.py    # Time-series and phase diagram rendering
├── gui.py         # Parameter panel with sliders
└── utils.py       # Helper functions (clamp, wrap_angle, etc.)
```

## Parameters

Key parameters in `params.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| M | 1.0 kg | Cart mass |
| m | 0.2 kg | Pole mass |
| l | 0.5 m | Pole length (pivot to COM) |
| max_force | 50.0 N | Maximum controller force |
| dt | 1/240 s | Integration timestep |

## License

MIT

