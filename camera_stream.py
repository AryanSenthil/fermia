import cv2
import fermia_camera
import threading
import time
import datetime
import os
from flask import Flask, Response, render_template, jsonify
import numpy as np

app = Flask(__name__)

# Create directories if they don't exist
os.makedirs('templates', exist_ok=True)
os.makedirs('photos', exist_ok=True)
os.makedirs('videos', exist_ok=True)

# Global variables
frame = None
frame_lock = threading.Lock()
is_recording = False
recording_thread = None
record_stop_event = threading.Event()
video_writer = None
video_path = None

# Global variables for thread safety
frame = None
frame_lock = threading.Lock()
recording = False
video_writer = None
video_path = None

def capture_frames():
    global frame
    while True:
        try:
            color_img = fermia_camera.get_image()
            if color_img is not None:
                # Resize if needed
                color_img = cv2.resize(color_img, (1280, 720))
                
                # Update the global frame with thread safety
                with frame_lock:
                    frame = color_img
            else:
                print("Waiting for color image...")
                time.sleep(0.5)
        except Exception as e:
            print(f"Error capturing frame: {e}")
            time.sleep(1)

def generate_frames():
    global frame
    while True:
        # Get the current frame with thread safety
        with frame_lock:
            current_frame = frame
        
        if current_frame is not None:
            # Encode the frame as JPEG
            ret, buffer = cv2.imencode('.jpg', current_frame)
            if not ret:
                continue
                
            # Convert to bytes and yield for the HTTP response
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        # Add a small delay to control frame rate
        time.sleep(0.033)  # ~30 FPS

@app.route('/')
def index():
    return render_template('camera_stream_index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/take_photo')
def take_photo():
    global frame
    
    with frame_lock:
        if frame is None:
            return jsonify({"success": False, "message": "No camera frame available"})
        
        # Create a copy of the current frame
        current_frame = frame.copy()
    
    # Generate a unique filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"photo_{timestamp}.jpg"
    filepath = os.path.join("photos", filename)
    
    # Save the image
    cv2.imwrite(filepath, current_frame)
    
    return jsonify({
        "success": True,
        "message": f"Photo saved as {filename}",
        "filename": filename
    })

@app.route('/start_recording')
def start_recording():
    global is_recording, recording_thread, record_stop_event, video_writer, frame
    
    if is_recording:
        return jsonify({"success": False, "message": "Already recording"})
    
    with frame_lock:
        if frame is None:
            return jsonify({"success": False, "message": "No camera frame available"})
        
        # Get frame dimensions
        height, width = frame.shape[:2]
    
    # Generate a unique filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"video_{timestamp}.avi"
    video_path = os.path.join("videos", filename)
    frame_rate = 15.0
    
    # Define the codec and create VideoWriter object
    # Using XVID codec which is widely supported
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    video_writer = cv2.VideoWriter(video_path, fourcc, frame_rate, (width, height))
    
    # Clear the stop event
    record_stop_event.clear()
    
    # Create and start recording thread
    def record_video():
        global frame
        try:
            while not record_stop_event.is_set():
                current_frame = None
                with frame_lock:
                    if frame is not None:
                        current_frame = frame.copy()
                
                if current_frame is not None:
                    video_writer.write(current_frame)
                
                # Control frame rate
                time.sleep(1/15.0)
        except Exception as e:
            print(f"Error in recording thread: {e}")
        finally:
            if video_writer is not None:
                video_writer.release()
                print(f"Video saved to {video_path}")
    
    recording_thread = threading.Thread(target=record_video)
    recording_thread.daemon = True
    recording_thread.start()
    
    is_recording = True
    
    return jsonify({
        "success": True,
        "message": "Recording started",
        "filename": filename
    })

@app.route('/stop_recording')
def stop_recording():
    global is_recording, recording_thread, record_stop_event, video_writer
    
    if not is_recording:
        return jsonify({"success": False, "message": "Not recording"})
    
    # Signal the recording thread to stop
    record_stop_event.set()
    
    # Wait for the thread to complete (with timeout)
    if recording_thread and recording_thread.is_alive():
        recording_thread.join(timeout=2.0)
    
    is_recording = False
    
    return jsonify({
        "success": True,
        "message": "Recording saved successfully",
        "filename": os.path.basename(video_path) if video_path else "unknown"
    })

# Start the camera capture thread
capture_thread = threading.Thread(target=capture_frames)
capture_thread.daemon = True
capture_thread.start()


if __name__ == "__main__":
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)