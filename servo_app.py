# servo_app.py
import streamlit as st
import time
import threading
import json
import redis

from fermia_servo import ServoController

# Initialize the servo controller
@st.cache_resource
def get_servo_controller():
    try:
        # Modify these parameters as needed for your setup
        controller = ServoController(
            channels=16,
            redis_host='localhost',
            redis_port=6379,
            redis_db=0,
            redis_key_prefix='servo:'
        )
        return controller, None
    except Exception as e:
        return None, str(e)
    
st.set_page_config(page_title = "Fermia Motor Control", layout="wide")


# Initialize controller 
controller, error = get_servo_controller()

if error:
    st.error(f"Failed to initialize servo controller: {error}")
    st.stop()

# Function to get all servos 
def get_all_servos():
    try:
        return controller.get_all_servos(), None 
    except Exception as e:
        return None, str(e)
    
# Get all servos 
servos, servo_error = get_all_servos() 

if servo_error:
    st.error(f"Failed to get servo data: {servo_error}")
    st.stop() 

# Reset all servos button
if st.button("Reset All Motors", type="primary"):
    try:
        controller.reset_all()
        st.success("All motors reset to default.")
        # Force a rerun to update all sliders
        st.rerun()
    except Exception as e:
        st.error(f"Failed to reset motors: {str(e)}")

# Create two columns for the servo controls
col1, col2 = st.columns(2)

# Sort servos by channel number
sorted_servos = sorted([s for s in servos.values()], key=lambda x: x['channel'])

# Split servos into two equal groups 
servos_col1 = sorted_servos[::2]  # Even indices
servos_col2 = sorted_servos[1::2]  # Odd indices


# Function to render a servo control in a given column 
def render_servo_control(col, servo):
    with col: 
        st.subheader(f"{servo['name']}")

        # Current angle display
        current_angle = servo['angle'] if servo['angle'] is not None else servo['default_angle']

        # Speed selection 
        speed_col1, speed_col2, speed_col3 = st.columns([1,1,1])
        
        # Always read speed directly from Redis to ensure fresh data
        servo_data = controller._get_servo_data(servo['channel'])
        current_speed = servo_data.get('speed', "medium")  # Default to medium if not set

        with speed_col1:
            low_selected = current_speed == "low"
            if st.button("Low", key=f"low_{servo['channel']}", 
                        type="primary" if low_selected else "secondary",
                        use_container_width=True):
                controller.set_speed(servo['channel'], "low")
                st.rerun()
        
        with speed_col2:
            medium_selected = current_speed == "medium"
            if st.button("Medium", key=f"medium_{servo['channel']}", 
                        type="primary" if medium_selected else "secondary",
                        use_container_width=True):
                controller.set_speed(servo['channel'], "medium")
                st.rerun()
        
        with speed_col3:
            high_selected = current_speed == "high"
            if st.button("High", key=f"high_{servo['channel']}", 
                        type="primary" if high_selected else "secondary",
                        use_container_width=True):
                controller.set_speed(servo['channel'], "high")
                st.rerun()

        # Angle slider 
        new_angle = st.slider(
            f"Angle: {int(current_angle)}°",
            min_value=0,
            max_value=180,
            value=int(current_angle),
            key=f"slider_{servo['channel']}"
        )

        if new_angle != current_angle:
            try:
                controller.move_servo(
                    channel=servo['channel'],
                    target_angle=new_angle,
                    speed=current_speed
                )
                # Force an immediate refresh to update the display of the angle 
                st.rerun() 
            except Exception as e:
                st.error(f"Failed to move servo: {str(e)}")

# Render servos in both columns
for servo in servos_col1:
    render_servo_control(col1, servo)

for servo in servos_col2:
    render_servo_control(col2, servo)
