import time
import redis
import cv2
import base64
import numpy as np
import pyrealsense2 as rs

# Initialize Redis client (make sure this matches the consumer)
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def publish_placeholder():
    """Publish a default placeholder (black image) to Redis."""
    placeholder_img = np.zeros((720, 1280, 3), dtype=np.uint8)
    ret, encoded_img = cv2.imencode('.jpg', placeholder_img)
    if ret:
        b64_img = base64.b64encode(encoded_img.tobytes()).decode('utf-8')
        redis_client.set("camera_feed", b64_img)
        
        # depth image
        depth_placeholder = np.zeros((720, 1280), dtype=np.uint16)
        b64_depth = base64.b64encode(depth_placeholder.tobytes()).decode('utf-8')
        redis_client.set("depth_feed", b64_depth)

def run_publisher():
    while True:
        try:
            # Check for connected RealSense devices
            ctx = rs.context()
            devices = ctx.devices
            if len(devices) == 0:
                print("No camera detected. Publishing placeholder image.")
                publish_placeholder()
                time.sleep(2)
                continue
            
            print("Camera detected. Starting pipeline.")
            pipeline = rs.pipeline()
            config = rs.config()
            
            # color image stream
            config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 15)
            # depth image stream
            config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 6)
            
            pipeline.start(config)
            
            # frame_skip = 5 # Skip initial unstable frames
            # frame_count = 0
            
            while True:
                # Refresh running key so consumers know the publisher is alive
                redis_client.set("fermia_publisher_running", "true", ex=5)
                
                try:
                    frames = pipeline.wait_for_frames(timeout_ms=5000)
                except Exception:
                    print("Camera stopped sending frames. Stopping pipeline.")
                    break
                
                color_frame = frames.get_color_frame()
                depth_frame = frames.get_depth_frame()
                
                if not color_frame:
                    continue
                
                # frame_count += 1
                # if frame_count <= frame_skip:
                #     continue # Skip early frames
                
                img = np.asanyarray(color_frame.get_data())
                ret, img_encoded = cv2.imencode('.jpg', img)
                if ret:
                    b64_img = base64.b64encode(img_encoded.tobytes()).decode('utf-8')
                    redis_client.set("camera_feed", b64_img)
                
                # Process and publish the depth frame
                depth_img = np.asanyarray(depth_frame.get_data())
                b64_depth = base64.b64encode(depth_img.tobytes()).decode('utf-8')
                redis_client.set("depth_feed", b64_depth)
                
        except Exception as e:
            print("Exception in publisher:", e)
        finally:
            try:
                pipeline.stop()
            except Exception:
                pass
            time.sleep(1)

if __name__ == "__main__":
    run_publisher()