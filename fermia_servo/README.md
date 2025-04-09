# Fermia Servo Controller

A Python library for controlling servo motors with Redis persistence.

## Installation

```bash
pip install fermia_servo
```

Or for development:

```bash
git clone https://github.com/yourusername/fermia_servo.git
cd fermia_servo
pip install -e .
```

## Usage

```python
from fermia_servo import ServoController

# Initialize the controller
controller = ServoController()

# Move a servo
controller.move_servo(channel=0, target_angle=90, speed="medium")

# Reset all servos to default positions
controller.reset_all()

# Get information about all servos
servos = controller.get_all_servos()
print(servos)
```

## Features

- Control multiple servo motors
- Redis persistence for servo positions and settings
- Adjustable speed control
- Default position restoration
- Smooth movement interpolation

## Requirements

- Python 3.7 or higher
- Redis server
- Adafruit ServoKit library