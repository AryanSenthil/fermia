from control import Program
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
import time 
from langchain_core.tools import tool
import os
import subprocess
import signal
import socket


# Function used by tools - is_realsense_connected()
def is_realsense_connected():
    """
    Check if a RealSense camera is connected to the system.
    This function attempts to import the `pyrealsense2` library and create a context object
    to discover connected RealSense devices. It returns `True` if any devices are found,
    otherwise it returns `False`. If there is an error importing the library or querying
    the devices, it prints an error message and returns `False`.
    Returns:
        bool: `True` if a RealSense camera is connected, `False` otherwise.
    """
    try:
        import pyrealsense2 as rs 

        # Create a context object to discover RealSense devices 
        ctx = rs.context() 
        devices = ctx.query_devices() 

        # Check if any devices are connected 
        if devices.size() > 0:
            return True 
        
        else: 
            return False 
        
    except (ImportError, Exception) as e:
        print(f"Error checking Realsense Camera: {e}")
        return False 

# Function used by tools - stop
def stop_process_on_port(port):
    """
    Stops any process using the specified port.
    
    Args:
        port (int or str): The port number to check and terminate process on.
    
    Returns:
        bool: True if the operation succeeded, False otherwise.
    """
    try:
        # Check if a process is using the given port
        result = subprocess.run(["lsof", "-t", f"-i:{port}"], 
                                capture_output=True, text=True)
        if result.stdout:
            # Get process IDs
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                print(f"Stopping process on port {port} (PID: {pid})")
                subprocess.run(["kill", "-TERM", pid])
        else:
            print(f"No process found on port {port}")
        return True
    except Exception as e:
        print(f"Error stopping process on port {port}: {e}")
        return False


# Get the hostname
hostname = socket.gethostname()

# Get the IP address
device_ip = socket.gethostbyname(hostname)

@tool
def camera_feed() -> str:
    """
    starts a camera stream if it is not already running.
    Returns:
        str: the link to the camera feed.
    """

    # Check if the RealSense camera is connected 
    if not is_realsense_connected():
        stop_process_on_port(5001)
        return "No Camera Detected."
    
    # Camera is detected, check if stream is already running 
    result = subprocess.run(["lsof", "-t", "-i:5000"], 
                            capture_output=True, text=True)
    
    if not result.stdout:
        # Stream is not running, start it 
        script_dir = os.path.dirname(os.path.abspath(__file__))
        camera_stream_script = os.path.join(script_dir, "camera_stream.sh")

        # Make sure the script is executable 
        subprocess.run(["chmod", "+x", camera_stream_script], check=False)

        # Start the depth stream in the background 
        subprocess.Popen([camera_stream_script],
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE)
        
        # Give it a moment to start 
        time.sleep(2) 
    return f"http://{device_ip}:5000"


@tool
def depth_feed() -> str:
    """
    starts a depth stream if it is not already running.
    Returns:
        str: link to the depth feed.
    """
    
    # Check if the RealSense camera is connected 
    if not is_realsense_connected():
        stop_process_on_port(5001)
        return "No Camera Detected."
    
    # Camera is detected, check if stream is already running 
    result = subprocess.run(["lsof", "-t", "-i:5001"], 
                            capture_output=True, text=True)
    
    if not result.stdout:
        # Stream is not running, start it 
        script_dir = os.path.dirname(os.path.abspath(__file__))
        depth_stream_script = os.path.join(script_dir, "depth_stream.sh")

        # Make sure the script is executable 
        subprocess.run(["chmod", "+x", depth_stream_script], check=False)

        # Start the depth stream in the background 
        subprocess.Popen([depth_stream_script],
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE)
        
        # Give it a moment to start 
        time.sleep(2) 
    return f"http://{device_ip}:5000"



# @tool
# def photos_feed() -> str:
#     """
#     Provides access to the robot's photo storage and management interface.
#     Returns the URL of the web app where captured photos can be viewed, managed, or downloaded.
#     """
#     return f"http://{device_ip}:5002"

@tool
def vision_model(prompt: str) -> str:
    """
    Performs visual analysis based on a descriptive prompt using the robot's vision model.

    Args:
        prompt (str): A natural language prompt describing what to analyze or look for.

    Returns:
        str: The interpreted output or results from the vision model.
    """
    # Check if the RealSense camera is connected 
    if not is_realsense_connected():
        stop_process_on_port(5001)
        return "No Camera Detected."
    
    from bakllava_vision import camera_vision
    response = camera_vision(prompt)
    return response

llm = ChatOllama(
    model = "qwen2.5:14b",
    temperature = 0,
)

graph = create_react_agent(
    llm,
    tools=[camera_feed, depth_feed, vision_model],
    prompt="""
You are to act as assistant acting as a robot. Use the following tools based on the user's intent:

- Use the `vision_model` tool to interpret anything the user asks about what they 'see', 'observe', or what is 'visible'. This includes identifying objects, describing scenes, or analyzing visual input. Pass the user’s prompt directly to the tool.

- If the user asks to view the live camera feed, use `camera_feed` and return the link.

- If the user asks to view the depth feed (spatial awareness), use `depth_feed` and return the link.

Always respond clearly and return the relevant tool output. Do not make assumptions; rely on the tools to answer queries."""
)


def invoke_our_graph(st_messages):
    return graph.invoke({"messages": st_messages})

