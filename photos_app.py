from flask import Flask, render_template, send_from_directory, request, jsonify
import os
import socket
import mimetypes
from datetime import datetime

app = Flask(__name__)

# Configure directories
PHOTOS_DIR = "/home/arisenthil/fermia/photos"
VIDEOS_DIR = "/home/arisenthil/fermia/videos"

# Ensure correct MIME types are registered
mimetypes.add_type('video/mp4', '.mp4')
mimetypes.add_type('video/x-msvideo', '.avi')  # Correct MIME type for AVI
mimetypes.add_type('video/avi', '.avi')  # Fallback MIME type for AVI
mimetypes.add_type('image/jpeg', '.jpg')

def get_file_info(file_path):
    """Get file information including creation time and size."""
    stats = os.stat(file_path)
    creation_time = datetime.fromtimestamp(stats.st_mtime)
    size_mb = stats.st_size / (1024 * 1024)  # Convert to MB
    
    return {
        'name': os.path.basename(file_path),
        'date': creation_time.strftime('%Y-%m-%d %H:%M:%S'),
        'size': f"{size_mb:.2f} MB",
        'path': file_path
    }

def get_media_files(directory):
    """Get all media files from directory with their info."""
    files = []
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                files.append(get_file_info(file_path))
    
    # Sort by date (newest first)
    files.sort(key=lambda x: x['date'], reverse=True)
    return files

@app.route('/')
def index():  
    """Main page showing photos and videos."""
    photos = get_media_files(PHOTOS_DIR)
    videos = get_media_files(VIDEOS_DIR)
    
    return render_template('media_index.html', 
                          photos=photos, 
                          videos=videos,
                          title="Fermia Media Gallery")

@app.route('/photos/<path:filename>')
def serve_photo(filename):
    """Serve photo files."""
    return send_from_directory(PHOTOS_DIR, filename)

@app.route('/videos/<path:filename>')
def serve_video(filename):
    """Serve video files with the correct MIME type."""
    file_path = os.path.join(VIDEOS_DIR, filename)
    
    # Determine MIME type based on file extension
    extension = os.path.splitext(filename)[1].lower()
    if extension == '.mp4':
        mimetype = 'video/mp4'
    elif extension == '.avi':
        mimetype = 'video/x-msvideo'
    else:
        # Let Flask guess the MIME type as a fallback
        mimetype = None
        
    return send_from_directory(VIDEOS_DIR, filename, mimetype=mimetype)

@app.route('/api/media')
def get_all_media():
    """API endpoint to get all media files."""
    media_type = request.args.get('type', 'all')
    
    if media_type == 'photos':
        return jsonify(get_media_files(PHOTOS_DIR))
    elif media_type == 'videos':
        return jsonify(get_media_files(VIDEOS_DIR))
    else:
        # Return both photos and videos
        return jsonify({
            'photos': get_media_files(PHOTOS_DIR),
            'videos': get_media_files(VIDEOS_DIR)
        })

def get_ip_address():
    """Get the local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

if __name__ == '__main__':
    ip_address = get_ip_address()
    
    # Create templates directory if it doesn't exist
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
        
    # Create the template file if it doesn't exist
    template_path = os.path.join(templates_dir, 'media_index.html')
    if not os.path.exists(template_path):
        with open(template_path, 'w') as f:
            f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .media-section {
            margin-bottom: 30px;
        }
        .media-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
        }
        .media-item {
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .media-item:hover {
            transform: translateY(-5px);
        }
        .media-item img, .media-item video {
            width: 100%;
            height: 200px;
            object-fit: cover;
        }
        .media-info {
            padding: 10px;
        }
        .media-name {
            font-weight: bold;
            margin-bottom: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .media-date, .media-size {
            font-size: 0.8em;
            color: #666;
        }
        .tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 1px solid #ddd;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            background: #eee;
            margin-right: 5px;
            border-radius: 5px 5px 0 0;
        }
        .tab.active {
            background: #007bff;
            color: white;
        }
        .media-content {
            display: none;
        }
        .media-content.active {
            display: block;
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 100;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.9);
        }
        .modal-content {
            margin: auto;
            display: block;
            max-width: 90%;
            max-height: 90%;
        }
        .close {
            position: absolute;
            top: 15px;
            right: 35px;
            color: #f1f1f1;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ title }}</h1>
        
        <div class="tabs">
            <div class="tab active" data-tab="all">All</div>
            <div class="tab" data-tab="photos">Photos</div>
            <div class="tab" data-tab="videos">Videos</div>
        </div>
        
        <div id="all-content" class="media-content active">
            {% if photos or videos %}
                {% if photos %}
                <div class="media-section">
                    <h2>Photos ({{ photos|length }})</h2>
                    <div class="media-grid">
                        {% for photo in photos %}
                            <div class="media-item photo-item" data-src="/photos/{{ photo.name }}">
                                <img src="/photos/{{ photo.name }}" alt="{{ photo.name }}">
                                <div class="media-info">
                                    <div class="media-name">{{ photo.name }}</div>
                                    <div class="media-date">{{ photo.date }}</div>
                                    <div class="media-size">{{ photo.size }}</div>
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}
                
                {% if videos %}
                <div class="media-section">
                    <h2>Videos ({{ videos|length }})</h2>
                    <div class="media-grid">
                        {% for video in videos %}
                            <div class="media-item video-item" data-src="/videos/{{ video.name }}">
                                <video src="/videos/{{ video.name }}" preload="metadata" type="{% if video.name.endswith('.mp4') %}video/mp4{% elif video.name.endswith('.avi') %}video/x-msvideo{% endif %}"></video>
                                <div class="media-info">
                                    <div class="media-name">{{ video.name }}</div>
                                    <div class="media-date">{{ video.date }}</div>
                                    <div class="media-size">{{ video.size }}</div>
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}
            {% else %}
                <p>No media files found.</p>
            {% endif %}
        </div>
        
        <div id="photos-content" class="media-content">
            {% if photos %}
                <div class="media-section">
                    <h2>Photos ({{ photos|length }})</h2>
                    <div class="media-grid">
                        {% for photo in photos %}
                            <div class="media-item photo-item" data-src="/photos/{{ photo.name }}">
                                <img src="/photos/{{ photo.name }}" alt="{{ photo.name }}">
                                <div class="media-info">
                                    <div class="media-name">{{ photo.name }}</div>
                                    <div class="media-date">{{ photo.date }}</div>
                                    <div class="media-size">{{ photo.size }}</div>
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                </div>
            {% else %}
                <p>No photos found.</p>
            {% endif %}
        </div>
        
        <div id="videos-content" class="media-content">
            {% if videos %}
                <div class="media-section">
                    <h2>Videos ({{ videos|length }})</h2>
                    <div class="media-grid">
                        {% for video in videos %}
                            <div class="media-item video-item" data-src="/videos/{{ video.name }}">
                                <video src="/videos/{{ video.name }}" preload="metadata"></video>
                                <div class="media-info">
                                    <div class="media-name">{{ video.name }}</div>
                                    <div class="media-date">{{ video.date }}</div>
                                    <div class="media-size">{{ video.size }}</div>
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                </div>
            {% else %}
                <p>No videos found.</p>
            {% endif %}
        </div>
    </div>
    
    <!-- Modal for viewing media -->
    <div id="mediaModal" class="modal">
        <span class="close">&times;</span>
        <img id="modalImage" class="modal-content">
        <video id="modalVideo" class="modal-content" controls></video>
    </div>
    
    <script>
        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                // Update active tab
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                // Show corresponding content
                document.querySelectorAll('.media-content').forEach(content => {
                    content.classList.remove('active');
                });
                
                const tabName = tab.getAttribute('data-tab');
                if (tabName === 'all') {
                    document.getElementById('all-content').classList.add('active');
                } else if (tabName === 'photos') {
                    document.getElementById('photos-content').classList.add('active');
                } else if (tabName === 'videos') {
                    document.getElementById('videos-content').classList.add('active');
                }
            });
        });
        
        // Modal for viewing photos
        const modal = document.getElementById('mediaModal');
        const modalImg = document.getElementById('modalImage');
        const modalVideo = document.getElementById('modalVideo');
        const closeBtn = document.getElementsByClassName('close')[0];
        
        // Load and display video thumbnails
        document.querySelectorAll('.video-item video').forEach(video => {
            video.addEventListener('loadedmetadata', function() {
                this.currentTime = 1; // Seek to 1 second to get a thumbnail
            });
        });
        
        // Handle photo clicks
        document.querySelectorAll('.photo-item').forEach(item => {
            item.addEventListener('click', function() {
                modal.style.display = 'flex';
                modalImg.style.display = 'block';
                modalVideo.style.display = 'none';
                modalImg.src = this.getAttribute('data-src');
            });
        });
        
        // Handle video clicks
        document.querySelectorAll('.video-item').forEach(item => {
            item.addEventListener('click', function() {
                const videoSrc = this.getAttribute('data-src');
                const videoType = videoSrc.endsWith('.mp4') ? 'video/mp4' : 
                                 videoSrc.endsWith('.avi') ? 'video/x-msvideo' : '';
                
                modal.style.display = 'flex';
                modalImg.style.display = 'none';
                modalVideo.style.display = 'block';
                
                // Clear previous source elements
                while (modalVideo.firstChild) {
                    modalVideo.removeChild(modalVideo.firstChild);
                }
                
                // Create a source element with appropriate type
                const source = document.createElement('source');
                source.src = videoSrc;
                source.type = videoType;
                modalVideo.appendChild(source);
                
                // Try to load and play the video
                modalVideo.load();
                modalVideo.play().catch(error => {
                    console.error('Error playing video:', error);
                    alert('This video format may not be supported by your browser. Try using VLC or another media player to view this file.');
                });
            });
        });
        
        // Close modal
        closeBtn.addEventListener('click', function() {
            modal.style.display = 'none';
            modalVideo.pause();
        });
        
        // Also close when clicking outside the modal content
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                modal.style.display = 'none';
                modalVideo.pause();
            }
        });
    </script>
</body>
</html>
            ''')
    
    # Run the app
    app.run(host='0.0.0.0', port=5003, debug=True)