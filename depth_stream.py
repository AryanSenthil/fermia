import cv2
import fermia_camera
import threading
import time
import datetime
import os
import numpy as np
from flask import Flask, Response, render_template, jsonify

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

# Create a HTML template
with open('templates/depth_stream_index.html', 'w') as f:
    f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Fermia Depth Stream</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            height: 100vh;
            background-color: #000;
            position: relative;
            overflow: hidden;
        }
        
        .main-container {
            display: flex;
            flex: 1;
            position: relative;
            overflow: hidden;
        }
        
        .container {
            flex: 1;
            position: relative;
            overflow: hidden;
            cursor: move;
        }
        
        .video-container {
            width: 100%;
            height: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }
        
        #camera-feed {
            width: 100%;
            height: 100%;
            object-fit: contain;
            transform-origin: center;
            transition: transform 0.1s ease;
        }
        
        .colormap-container {
            width: 40px;
            margin-right: 10px;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        
        .colormap {
            width: 40px;
            height: 80%;
            background: linear-gradient(to bottom, 
                #ff0000, #ff8000, #ffff00, 
                #80ff00, #00ff00, #00ff80, 
                #00ffff, #0080ff, #0000ff);
            border-radius: 5px;
        }
        
        .colormap-label {
            color: white;
            font-family: Arial, sans-serif;
            font-size: 12px;
            margin: 5px 0;
            writing-mode: vertical-rl;
            transform: rotate(180deg);
            text-align: center;
        }
        
        .controls {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background-color: rgba(0, 0, 0, 0.7);
            padding: 10px;
            display: flex;
            justify-content: center;
            gap: 20px;
            z-index: 100;
        }
        
        .btn {
            background-color: #333;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            transition: background-color 0.3s;
        }
        
        .btn:hover {
            background-color: #555;
        }
        
        .btn.active {
            background-color: #f00;
        }
        
        .status-message {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            opacity: 0;
            transition: opacity 0.3s;
            z-index: 100;
        }
        
        .instructions {
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-size: 14px;
            z-index: 100;
            opacity: 0.7;
        }
        
        .instructions:hover {
            opacity: 1;
        }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="container" id="drag-container">
            <div class="video-container">
                <img id="camera-feed" src="{{ url_for('video_feed') }}">
            </div>
        </div>
        
        <div class="colormap-container">
            <div class="colormap-label">6.0 m</div>
            <div class="colormap"></div>
            <div class="colormap-label">0.0 m</div>
        </div>
    </div>
    
    <div class="controls">
        <button class="btn" id="reset-view">Reset View</button>
        <button class="btn" id="take-photo">Take Photo</button>
        <button class="btn" id="record-video">Record Video</button>
    </div>
    
    <div class="instructions">
        <p>Mouse wheel: Zoom in/out</p>
        <p>Click and drag: Pan around</p>
        <p>Double-click: Reset zoom</p>
    </div>
    
    <div class="status-message" id="status-message"></div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const container = document.getElementById('drag-container');
            const cameraFeed = document.getElementById('camera-feed');
            const resetView = document.getElementById('reset-view');
            const takePhoto = document.getElementById('take-photo');
            const recordVideo = document.getElementById('record-video');
            const statusMessage = document.getElementById('status-message');
            
            let zoomLevel = 1;
            let posX = 0;
            let posY = 0;
            let startPosX = 0;
            let startPosY = 0;
            let mouseX = 0;
            let mouseY = 0;
            let isDragging = false;
            let isRecording = false;
            
            // Initialize transform
            updateTransform();
            
            // Mouse wheel zoom
            container.addEventListener('wheel', function(e) {
                e.preventDefault();
                
                // Calculate zoom center point (position of mouse)
                const rect = container.getBoundingClientRect();
                mouseX = e.clientX - rect.left;
                mouseY = e.clientY - rect.top;
                
                // Adjust zoom level based on wheel direction
                if (e.deltaY < 0) {
                    // Zoom in
                    zoomLevel *= 1.1;
                    if (zoomLevel > 5) zoomLevel = 5; // Max zoom limit
                } else {
                    // Zoom out
                    zoomLevel /= 1.1;
                    if (zoomLevel < 1) {
                        zoomLevel = 1;
                        posX = 0;
                        posY = 0;
                    }
                }
                
                updateTransform();
            });
            
            // Mouse drag to pan
            container.addEventListener('mousedown', function(e) {
                if (zoomLevel > 1) {
                    isDragging = true;
                    startPosX = e.clientX - posX;
                    startPosY = e.clientY - posY;
                    container.style.cursor = 'grabbing';
                }
            });
            
            container.addEventListener('mousemove', function(e) {
                if (isDragging) {
                    posX = e.clientX - startPosX;
                    posY = e.clientY - startPosY;
                    
                    // Limit panning to not go too far outside
                    const maxPan = (zoomLevel - 1) * 100;
                    posX = Math.max(-maxPan, Math.min(maxPan, posX));
                    posY = Math.max(-maxPan, Math.min(maxPan, posY));
                    
                    updateTransform();
                }
            });
            
            container.addEventListener('mouseup', function() {
                isDragging = false;
                container.style.cursor = 'move';
            });
            
            container.addEventListener('mouseleave', function() {
                isDragging = false;
                container.style.cursor = 'move';
            });
            
            // Double-click to reset zoom
            container.addEventListener('dblclick', function() {
                resetViewFunction();
            });
            
            // Reset view button
            resetView.addEventListener('click', resetViewFunction);
            
            function resetViewFunction() {
                zoomLevel = 1;
                posX = 0;
                posY = 0;
                updateTransform();
                showStatus('View reset');
            }
            
            function updateTransform() {
                cameraFeed.style.transform = `translate(${posX}px, ${posY}px) scale(${zoomLevel})`;
            }
            
            // Take photo functionality
            takePhoto.addEventListener('click', function() {
                fetch('/take_photo')
                    .then(response => response.json())
                    .then(data => {
                        showStatus(data.message);
                    })
                    .catch(error => {
                        console.error('Error taking photo:', error);
                        showStatus('Error taking photo');
                    });
            });
            
            // Record video functionality
            recordVideo.addEventListener('click', function() {
                isRecording = !isRecording;
                
                if (isRecording) {
                    recordVideo.classList.add('active');
                    recordVideo.textContent = 'Stop Recording';
                    
                    fetch('/start_recording')
                        .then(response => response.json())
                        .then(data => {
                            showStatus(data.message);
                        })
                        .catch(error => {
                            console.error('Error starting recording:', error);
                            showStatus('Error starting recording');
                            isRecording = false;
                            recordVideo.classList.remove('active');
                            recordVideo.textContent = 'Record Video';
                        });
                } else {
                    recordVideo.classList.remove('active');
                    recordVideo.textContent = 'Record Video';
                    
                    fetch('/stop_recording')
                        .then(response => response.json())
                        .then(data => {
                            showStatus(data.message);
                        })
                        .catch(error => {
                            console.error('Error stopping recording:', error);
                            showStatus('Error stopping recording');
                        });
                }
            });
            
            function showStatus(message) {
                statusMessage.textContent = message;
                statusMessage.style.opacity = 1;
                
                setTimeout(() => {
                    statusMessage.style.opacity = 0;
                }, 3000);
            }
        });
    </script>
</body>
</html>
    ''')

def capture_frames():
    global frame
    while True:
        try:
            color_img = fermia_camera.get_depth_image()
            if color_img is not None:
                # Resize if needed
                color_img = cv2.resize(color_img, (1280, 720))
                
                # Update the global frame with thread safety
                with frame_lock:
                    frame = color_img
            else:
                print("Waiting for depth image...")
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
    return render_template('depth_stream_index.html')

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
    filename = f"depth_photo_{timestamp}.jpg"
    filepath = os.path.join("photos", filename)
    
    # Save the image
    cv2.imwrite(filepath, current_frame)
    
    return jsonify({
        "success": True,
        "message": f"Depth photo saved as {filename}",
        "filename": filename
    })

@app.route('/start_recording')
def start_recording():
    global is_recording, recording_thread, record_stop_event, video_writer, video_path, frame
    
    if is_recording:
        return jsonify({"success": False, "message": "Already recording"})
    
    with frame_lock:
        if frame is None:
            return jsonify({"success": False, "message": "No camera frame available"})
        
        # Get frame dimensions
        height, width = frame.shape[:2]
    
    # Generate a unique filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"depth_video_{timestamp}.avi"
    video_path = os.path.join("videos", filename)
    frame_rate = 6.0
    
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
    global is_recording, recording_thread, record_stop_event, video_writer, video_path
    
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

if __name__ == "__main__":
    # Start the camera capture thread
    capture_thread = threading.Thread(target=capture_frames)
    capture_thread.daemon = True
    capture_thread.start()
    
    # Start the Flask server
    print("Starting depth stream web server. Access the stream at:")
    print("- Local:   http://localhost:5000")
    print("- Network: http://<your-ip-address>:5000")
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)