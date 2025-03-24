#!/bin/bash
# start_depth_stream.sh - Start the depth stream with Gunicorn

# Get current directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

# Check if Gunicorn is installed
if ! command -v gunicorn &> /dev/null; then
    echo "Gunicorn is not installed. Installing now..."
    pip install gunicorn
fi

# Start the server with Gunicorn using thread workers instead
echo "Starting depth stream on port 5000..."
gunicorn --bind 0.0.0.0:5000 --worker-class=gthread --threads=4 --workers=1 camera_stream:app