import redis
import subprocess
import os
import time
import base64
import cv2
import numpy as np

# Initialize Redis client (must match the one used by the publisher)
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def ensure_publisher():
    """
    Checks if the publisher is running (via a Redis key). If not, spawns it.
    """
    publisher_running = redis_client.get("fermia_publisher_running")
    if not publisher_running:
        # Attempt to acquire a lock to avoid simultaneous spawns
        lock_acquired = redis_client.set("fermia_publisher_lock", str(os.getpid()), nx=True, ex=10)
        if lock_acquired:
            print("No publisher running. Starting publisher automatically.")
            # Spawn the publisher process in the background
            subprocess.Popen(["python", "-m", "fermia_camera.publisher"])
            # Allow a moment for the publisher to initialize
            time.sleep(2)

# Ensure the publisher is running when the package is imported.
ensure_publisher()

def get_image():
    """
    Retrieves the latest image from Redis.
    Returns:
    The decoded OpenCV image (numpy array) or None if unavailable.
    """
    b64_img = redis_client.get("camera_feed")
    if b64_img is None:
        return None
    try:
        img_bytes = base64.b64decode(b64_img)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None

def get_base64_image():
    """
    Retrieves the latest image from Redis.
    Returns:
    The a base64 image or None if unavailable.
    """
    b64_img = redis_client.get("camera_feed")
    if b64_img is None:
        return None
    try:
        return b64_img.decode('utf-8')
    except Exception:
        return None

def get_depth_data():
    """
    Retrieves the latest depth array from Redis
    Returns:
    The depth array as a numpy array or None if unavailable.
    """
    b64_depth = redis_client.get("depth_feed")
    if b64_depth is None:
        return None
    try:
        depth_bytes = base64.b64decode(b64_depth)
        # Convert the raw bytes back into numpy array
        depth_array = np.frombuffer(depth_bytes, dtype=np.uint16)
        depth_array = depth_array.reshape((720, 1280))
        return depth_array
    except Exception:
        return None

def get_depth_image():
    """
    Retrives the latest depth image from Redis
    Returns:
    The depth image or None if unavailable.
    """
    b64_depth = redis_client.get("depth_feed")
    if b64_depth is None:
        return None
    try:
        depth_bytes = base64.b64decode(b64_depth)
        # Convert the raw bytes back into numpy array
        depth_array = np.frombuffer(depth_bytes, dtype=np.uint16)
        depth_array = depth_array.reshape((720, 1280))
        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_array, alpha=0.06), cv2.COLORMAP_JET)
        return depth_colormap
    except Exception:
        return None