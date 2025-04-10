# servo.py
# to delete all the redis servo keys use the commond below 
# redis-cli KEYS "servo:*" | xargs redis-cli DEL

import time
import json
import redis
from adafruit_servokit import ServoKit

class ServoController:
    def __init__(self, channels=16, redis_host='localhost', redis_port=6379, redis_db=0, redis_key_prefix='servo:'):
        """
        Initialize a servo controller with Redis storage
        
        Args:
            channels (int): Number of servo channels (default: 16)
            redis_host (str): Redis server host
            redis_port (int): Redis server port
            redis_db (int): Redis database number
            redis_key_prefix (str): Prefix for Redis keys
        """
        self.kit = ServoKit(channels=channels)
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
        self.redis_key_prefix = redis_key_prefix
        
        # Set pulse width range for all servos
        for i in range(channels):
            self.kit.servo[i].set_pulse_width_range(750, 2250)
            # Auto-register all servos with default values if not already in Redis
            if not self._get_servo_data(i):
                self.register_servo(i)
            else:
                # Initialize the servo with the stored angle
                self._initialize_servo(i)
    
    def _get_servo_key(self, channel):
        """Generate the Redis key for a servo"""
        return f"{self.redis_key_prefix}{channel}"
    
    def _get_servo_data(self, channel):
        """Get servo data from Redis"""
        key = self._get_servo_key(channel)
        data = self.redis_client.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    def _save_servo_data(self, channel, data):
        """Save servo data to Redis"""
        key = self._get_servo_key(channel)
        self.redis_client.set(key, json.dumps(data))
    
    def _initialize_servo(self, channel):
        """Initialize a specific servo to its current or default angle"""
        servo_data = self._get_servo_data(channel)
        if not servo_data:
            return
        
        # If angle is not set, use default angle
        angle = servo_data.get("angle")
        if angle is None:
            angle = servo_data["default_angle"]
            servo_data["angle"] = angle
            self._save_servo_data(channel, servo_data)
        
        # Ensure speed is set to a valid value
        if servo_data.get("speed") is None:
            servo_data["speed"] = servo_data.get("default_speed", "medium")  # Use default_speed or medium as fallback
            self._save_servo_data(channel, servo_data)
        
        # Move servo to position without animation
        self.kit.servo[channel].angle = angle
            
    def register_servo(self, channel, default_angle=90, default_speed="medium"):
        """
        Register a servo with default values in Redis
        
        Args:
            channel (int): Servo channel number (0-15)
            default_angle (int): Default angle for initialization (0-180)
            default_speed (str): Default speed for servo movement ("low", "medium", "high")
        """
        channel = min(16, max(0, channel))
        motor_name = f"motor {channel+1}"  # motor_1 to motor_16
        
        servo_data = {
            "channel": channel,  # Store the channel number
            "name": motor_name,
            "angle": default_angle,  # Initialize with default angle
            "speed": default_speed,  # Initialize with default speed
            "default_angle": default_angle,
            "default_speed": default_speed
        }
        
        self._save_servo_data(channel, servo_data)
        
        # Initialize this servo
        self.kit.servo[channel].angle = default_angle
        
        return motor_name
    
    def initialize(self, channel=None):
        """
        Initialize servo(s) to their current or default angle
        
        Args:
            channel (int): Specific channel to initialize, or None for all
        """
        if channel is not None:
            # Initialize a specific servo
            self._initialize_servo(channel)
        else:
            # Initialize all servos
            for i in range(16):  # Assuming max 16 channels
                self._initialize_servo(i)
    
    def move_servo(self, channel, target_angle, speed=None):
        """
        Move a servo to the specified angle
        
        Args:
            channel (int): Servo channel number (0-15)
            target_angle (int): Target angle (0-180)
            speed (str): Speed setting ("low", "medium", "high")
                     If None, uses the servo's current speed
        """
        # Validate target angle
        target_angle = min(180, max(0, target_angle))
        
        # Get servo data from Redis
        servo_data = self._get_servo_data(channel)
        if not servo_data:
            # Register servo if not found
            self.register_servo(channel)
            servo_data = self._get_servo_data(channel)
        
        # Use current speed if not specified
        if speed is None:
            speed = servo_data["default_speed"]
        
        # Define step and delay based on speed
        if speed == "low":  # Slow
            step = 1
            delay = 0.03
        elif speed == "high":  # Fast
            step = 1
            delay = 0.005
        else:  # Medium (default)
            step = 1
            delay = 0.02
        
        # Get current angle
        current_angle = servo_data.get("angle")
        
        # If no current angle is stored, use default angle
        if current_angle is None:
            current_angle = servo_data["default_angle"]
            servo_data["angle"] = current_angle
            self._save_servo_data(channel, servo_data)
            self.kit.servo[channel].angle = current_angle
        
        # Move the servo
        if current_angle < target_angle:
            for angle in range(int(current_angle), int(target_angle) + 1, step):
                self.kit.servo[channel].angle = angle
                time.sleep(delay)
        else:
            for angle in range(int(current_angle), int(target_angle) - 1, -step):
                self.kit.servo[channel].angle = angle
                time.sleep(delay)
        
        # Update stored angle and speed in Redis
        servo_data["angle"] = target_angle
        servo_data["speed"] = speed  # Update the current speed
        self._save_servo_data(channel, servo_data)
        
        # Return actual motor name for reference
        return servo_data["name"]
    
    def set_default_angle(self, channel, angle):
        """
        Set the default angle for a servo
        
        Args:
            channel (int): Servo channel number (0-15)
            angle (int): Default angle (0-180)
        """
        angle = min(180, max(0, angle))
        
        servo_data = self._get_servo_data(channel)
        if not servo_data:
            self.register_servo(channel, default_angle=angle)
        else:
            servo_data["default_angle"] = angle
            self._save_servo_data(channel, servo_data)
    
    def set_default_speed(self, channel, speed):
        """
        Set the default speed for a servo
        
        Args:
            channel (int): Servo channel number (0-15)
            speed (str): Default speed ("low", "medium", "high")
        """
        if speed not in ["low", "medium", "high"]:
            speed = "medium"  # Default to medium if invalid
        
        servo_data = self._get_servo_data(channel)
        if not servo_data:
            self.register_servo(channel, default_speed=speed)
        else:
            servo_data["default_speed"] = speed
            self._save_servo_data(channel, servo_data)
    
    def set_speed(self, channel, speed):
        """
        Set the current speed for a servo ("low", "medium", "high")
        
        Args:
            channel (int): Servo channel number (0-15)
            speed (str): Speed setting ("low", "medium", "high")
        """
        if speed not in ["low", "medium", "high"]:
            speed = "medium"  # Default to medium if invalid
        
        servo_data = self._get_servo_data(channel)
        if not servo_data:
            self.register_servo(channel)
            servo_data = self._get_servo_data(channel)
            
        servo_data["speed"] = speed
        self._save_servo_data(channel, servo_data)
    
    def reset_all(self):
        """Reset all servos to their default angles"""
        for i in range(16):  # Assuming max 16 channels
            servo_data = self._get_servo_data(i)
            if servo_data:
                default_angle = servo_data["default_angle"]
                self.move_servo(i, default_angle)
    
    def reset_channel(self, channel):
        """Reset the specified servo channel to its default angle."""
        servo_data = self._get_servo_data(channel)
        if servo_data:
            default_angle = servo_data["default_angle"]
            self.move_servo(channel, default_angle)
    
    def get_all_servos(self):
        """Get information about all registered servos"""
        servos = {}
        
        # Use Redis pattern matching to get all servo keys
        pattern = f"{self.redis_key_prefix}*"
        for key in self.redis_client.keys(pattern):
            # Extract channel number from key
            channel = int(key.split(':')[-1])
            servo_data = self._get_servo_data(channel)
            if servo_data:
                servos[channel] = servo_data
                
        return servos