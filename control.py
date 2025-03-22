import subprocess
import time
import os
import shlex

class Program:
    def __init__(self):
        # No need for SSH credentials in local implementation
        self.shell = None
    
    def connect(self):
        """ No connection needed for local operations. """
        # This is a placeholder to maintain API compatibility
        self.shell = True
    
    def retrieve(self, u_dir, local_dir):
        """ Copies files from one local directory to another. """
        os.system(f'cp -r {local_dir} {u_dir}')
    
    def run_command(self, command):
        """ Runs a command locally and returns the output. """
        result = subprocess.run(command.split(), capture_output=True, text=True)
        return result.stdout
    
    def run_program(self, command):
        """ Runs a command with an input variable locally and returns the output."""
        result = subprocess.run(shlex.split(command), capture_output=True, text=True)
        return result.stdout
    
    def spawn_command(self, command):
        """ Spawns a long-running process locally. """
        # Check if command is already a list
        if isinstance(command, list):
            process = subprocess.Popen(command)
        else:
            # If it's a string, split it
            process = subprocess.Popen(shlex.split(command))
        time.sleep(1)  
        return process