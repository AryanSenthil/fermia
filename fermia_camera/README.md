# FERMIA Camera

FERMIA Camera is a Python package that provides a Redis-based system for streaming and accessing camera feed data, including both color and depth images. It is designed for use with Intel RealSense cameras but includes a fallback mechanism using placeholder images when no camera is detected.

# The Problem it solves 
One of the key challenges in robotics is seamless sensor integration. For instance, when using a camera, you typically need to start a pipeline to continuously capture frames. However, once a pipeline is initiated within a program, it cannot be accessed simultaneously by other programs, making multi-access difficult. Additionally, sensor integration varies across different tasks, adding further complexity. If you're building a ROS-based robot and later realize you need a camera feed, you often have to modify low-level code to accommodate it.  

Our package, **fermia_camera**, solves this problem by providing a flexible and accessible solution for camera integration. With **fermia_camera**, you can retrieve camera feeds from anywhere, at any time, and from multiple programs simultaneously—without the need to restart or modify the underlying pipeline. This simplifies sensor integration and enhances adaptability for various robotics applications. 

## Features
- Captures and streams RGB and depth images from an Intel RealSense camera.
- Stores the latest images in Redis for easy access.
- Provides functions to retrieve images and depth data as NumPy arrays.
- Includes a publisher process that automatically starts when needed.
- Supports placeholder images when no camera is available.

### Accessing Camera Feed
You can retrieve the latest images using the `fermia_camera` package:

```python
import fermia_camera

# Fetch the latest color image
image = fermia_camera.get_image()

# Fetch the base64 image 
base64_image = fermia_camera.get_base64_image()

# Fetch the latest depth data
depth_array = fermia_camera.get_depth_data()

# Fetch the depth image with colormap
depth_colormap = fermia_camera.get_depth_image()
```

### Function Overview

#### `fermia_camera.get_image()`
Retrieves the latest RGB image as a NumPy array (`720x1280`). Returns `None` if no image is available.

#### `fermia_camera.get_base64_image()`
Retrieves the latest RGB image in Base64 format. Returns `None` if no image is available.

#### `fermia_camera.get_depth_data()`
Retrieves the latest depth data as a NumPy array (`720x1280`). Returns `None` if no data is available.

#### `fermia_camera.get_depth_image()`
Retrieves the latest depth image with a color map applied for visualization. Returns `None` if no data is available.

## How It Works
1. **Publisher (`publisher.py`)**
   - Captures images from the Intel RealSense camera.
   - Encodes and stores the images in Redis.
   - Uses a placeholder image when no camera is detected.
   - Runs in a loop, ensuring images are continuously published.

2. **Client Functions (`__init__.py`)**
   - Provides functions for retrieving images and depth data from Redis.
   - Ensures that the publisher is running when needed.

## Dependencies
- `numpy`
- `opencv-python`
- `redis`
- `pyrealsense2`

## Notes
- Ensure that a Redis server is running before starting the publisher.
- This package is designed for systems using Intel RealSense cameras but includes a fallback mechanism for missing cameras.

## License
This project is licensed under the MIT License.

## Author
Your Name - [aryanyaminisenthil@gmail.com]
