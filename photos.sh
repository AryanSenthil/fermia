#!/bin/bash
# start_photos_app.sh - Start the photos application with Uvicorn on port 5003

# Get current directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

# Check if Uvicorn is installed; if not, install it.
if ! command -v uvicorn &> /dev/null; then
    echo "Uvicorn is not installed. Installing now..."
    pip install uvicorn
fi

# Start the server with Uvicorn on port 5003
echo "Starting the photos app on port 5003..."
gunicorn --bind 0.0.0.0:5003 --worker-class=gthread --threads=4 --workers=1 photos_app:app