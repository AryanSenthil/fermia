from control import Program
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
import time 
from langchain_core.tools import tool
import os
import subprocess
import signal
import socket
from typing import Literal, Optional
from prompt import fermia_prompt

from servo.servo import ServoController

servo = ServoController()

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
        stop_process_on_port(5000)
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
    return f"[Click here](http://{device_ip}:5000)"


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
    return f"[Click here](http://{device_ip}:5001)"



@tool
def photos_feed() -> str:
    """
    Provides access to the robot's photo storage and management interface is not already running.
    Returns the URL of the web app where captured photos can be viewed, managed, or downloaded. 
    """

    result = subprocess.run(["lsof", "-t", "-i:5003"], 
                            capture_output=True, text=True)

    if not result.stdout:
        # Stream is not running, start it 
        script_dir = os.path.dirname(os.path.abspath(__file__))
        photos_app_script = os.path.join(script_dir, "photos.sh")

        # Make sure the script is executable 
        subprocess.run(["chmod", "+x", photos_app_script], check=False)

        # Start the depth stream in the background 
        subprocess.Popen([photos_app_script],
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE)
        
        # Give it a moment to start 
        time.sleep(2) 
    return f"[Click here](http://{device_ip}:5003)"

@tool
def motor_control_interface_app() -> str:
    """
    provies the motor control interface is not already running.
    Returns the URL of the web app where captured photos can be viewed, managed, or downloaded. 
    """

    result = subprocess.run(["lsof", "-t", "-i:8081"], 
                            capture_output=True, text=True)

    # Check if something is already running on port 8081
    result = subprocess.run(["lsof", "-t", "-i:8081"], capture_output=True, text=True)

    if not result.stdout:
        # Application is not running, so launch it using streamlir
        script_dir = os.path.dirname(os.path.abspath(__file__))
        motor_control_interface_script = os.path.join(script_dir, "servo_app.py")

        # Launch using the streamlir command with the specified server port
        subprocess.Popen([
            "python3",
            "-m",
            "streamlit",
            "run",
            motor_control_interface_script,
            "--server.port", "8081",
            "--server.headless", "True"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Allow some time for the service to start up
        time.sleep(2)
    return f"[Click here](http://{device_ip}:8081)"

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


@tool
def move_servo(motor: int, target_angle: float, speed: Optional[Literal["low", "medium", "high"]] = None) -> str:
    """
    Moves a servo to the specified angle.
    
    Args:
        motor (int): servo ID.
        target_angle (float): Target angle in degrees.
        speed (str, optional): "low", "medium", or "high". Defaults to preset speed if omitted.
    
    Returns:
        str: Confirmation message.
    """
    channel = motor - 1
    servo.move_servo(channel=channel, target_angle=target_angle, speed=speed)
    return f"Motor {motor} was moved to {target_angle}"


@tool
def set_default_angle(motor: int, angle: float) -> str:
    """
    Sets the default angle for a servo.
    
    Args:
        motor (int): servo ID.
        angle (float): Default angle in degrees.
    
    Returns:
        str: Confirmation message.
    """
    channel = motor - 1
    servo.set_default_angle(channel=channel, angle=angle)
    return f"Changed default angle of Motor {motor} to {angle} degrees. It will now initialize to {angle} degrees."


@tool
def set_default_speed(motor: int, speed: Literal["low", "medium", "high"]) -> str:
    """
    Updates the default speed for a servo.
    
    Args:
        motor (int): servo ID.
        speed (str): "low", "medium", or "high".
    
    Returns:
        str: Confirmation message.
    """
    channel = motor - 1
    servo.set_default_speed(channel=channel, speed=speed)
    return f"Changed speed of Motor {motor} to {speed}."


@tool
def initialize_all_servos() -> str:
    """
    Resets all servos to their default positions.
    
    Returns:
        str: Confirmation message.
    """
    servo.reset_all()
    return "All servo motors have been reset to their default positions."


@tool
def initialize_servo_to_default(motor: int) -> str:
    """
    Resets one servo to its default settings.
    
    Args:
        motor (int): 1-indexed servo ID.
    
    Returns:
        str: Confirmation message.
    """
    channel = motor - 1
    servo.reset_channel(channel)
    return f"Motor {motor} has been reset to its default position."


@tool
def get_motor_info(query: str) -> str:
    """
    Retrieves servo motor info from the RAG system.
    Args:
        query (str): Query string about servo based on the user's query
    Returns:
        str: Information from the knowledge base.
    """
    import subprocess
    
    try:
        # Run the servo_rag.py script as a subprocess with the query as an argument

        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, "servo/servo_rag.py")

        result = subprocess.run(
            ["python3", script_path, query], 
            capture_output=True, 
            text=True,
            check=True
        )
        
        # Get the output from the subprocess
        output = result.stdout.strip()
        
        # If there's no output, return a message
        if not output:
            return "No information found for your query."
        
        return output
    
    except subprocess.CalledProcessError as e:
        # Handle any errors from the subprocess
        error_message = f"Error executing query: {e}"
        if e.stderr:
            error_message += f"\nDetails: {e.stderr}"
        return error_message
    except Exception as e:
        # Handle any other exceptions
        return f"An error occurred while processing your query: {str(e)}"



llm = ChatOllama(
    model = "qwen2.5:7b",
    temperature = 0,
)

graph = create_react_agent(
    llm,
    tools=[camera_feed, depth_feed, vision_model, photos_feed, motor_control_interface_app, move_servo, set_default_angle, set_default_speed, 
           initialize_all_servos, initialize_servo_to_default, get_motor_info],

    prompt=fermia_prompt
)


def invoke_our_graph(st_messages):
    return graph.invoke({"messages": st_messages})

