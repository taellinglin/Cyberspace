from panda3d.core import Vec4, AudioManager, AudioSound
from panda3d.core import NodePath, Material
from panda3d.core import AudioSound
from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties, PerspectiveLens
import random
from direct.task import Task
import numpy as np
from panda3d.core import LQuaternionf, LVector3f
from math import sin, pi, cos
from audio3d import audio3d
import math
from motionBlur import MotionBlur
import os
from panda3d.core import loadPrcFileData
from screeninfo import get_monitors
import argparse
from panda3d.core import Vec3
from panda3d.core import KeyboardButton, InputDevice
import sys
import time

class AdditiveSynthesizerApp(ShowBase):
    def __init__(self, scene_path=None, motion_blur_factor=0.9):
        super().__init__(self)
        self.accept("escape", sys.exit)
        self.disableMouse()

        # Initialize variables
        self.camera_speed = 10
        self.rotation_speed = 120
        self.smoothing_factor = 0.2
        self.camera_velocity = Vec3(0, 0, 0)
        self.camera_rotation_velocity = Vec3(0, 0, 0)

        # Time tracking for gamepad activity
        self.last_gamepad_activity = time.time()
        self.idle_threshold = 5.0  # Seconds before considering the gamepad idle

        # Initialize camera path variables
        self.t = 0
        self.center_of_mass = Vec3(0, 0, 0)

        # Add task for updating the camera
        self.taskMgr.add(self.update_camera, "UpdateCamera")

        # Check for gamepad support
        if not self.devices.getDevices(InputDevice.DeviceClass.gamepad):
            print("No gamepad detected. Defaulting to camera path.")
            self.use_camera_path = True
        else:
            self.gamepad = self.devices.getDevices(InputDevice.DeviceClass.gamepad)[0]
            self.attachInputDevice(self.gamepad)
            self.use_camera_path = False

        self.setup_fullscreen()
        self.ling_factor = 1*random.choice([1/48000])
        # Set background color to black
        self.setBackgroundColor(0, 0, 0, 0.0)
                # Get the current working directory
        random_scene = scene_path
        
        # Load the chosen scene by its file name
        self.scene = self.loader.loadModel(scene_path)
        if not self.scene:
            raise FileNotFoundError(f"Scene file '{scene_path}' could not be loaded.")
        self.scene.reparentTo(self.render)

        # Get all objects in the scene
        self.objects = self.scene.findAllMatches("**/*")

        # Compute the center of mass for the objects in the scene
        self.center_of_mass = self.compute_center_of_mass(self.objects)

        # Create pentatonic scale frequencies (in Hz)
        self.pentatonic_scale = [65.41, 73.42, 81.76, 98.21, 108.35, 130.82, 146.83, 163.52, 196.43, 216.71, 261.63, 293.66, 327.04, 392.86, 433.42, 523.25, 587.33, 654.08, 785.71, 866.84, 1047.50, 1174.67, 1305.25, 1471.42, 1741.68, 2083.00, 2349.34, 2610.50, 2942.84, 3483.36, 4177.99, 4698.68, 5221.00, 5945.67, 8375.37, 9397.36, 10442.00, 11891.34, 13312.00, 14751.36, 17614.73, 18892.36, 20884.00, 23677.64, 25187.04, 29524.00, 33766.72, 37591.90, 41746.56, 47167.36, 51095.52, 58661.72, 62576.88]



        # Initialize camera path and emission color updates
        self.t = 0
        #self.taskMgr.add(self.update_camera_path, "UpdateCameraPath")
        self.taskMgr.add(self.update_emissive_colors, "UpdateEmissiveColors")
        if random_scene == "00.bam" or random_scene == "02.bam" or random_scene == "04.bam" or random_scene == "11.bam" or random_scene == "10.bamn":
            self.taskMgr.add(self.oscillate_scale_and_rotation, "OscillateScaleAndRotation")
        self.taskMgr.add(self.twinkle_effect, "TwinkleEffect")
        
        self.color_cursors = {}
        for obj in self.objects:
            self.color_cursors[obj] = random.random()
        self.material = Material()
        
        # Initialize scale speeds for each object in the scene
        self.scale_speeds = {}
        for obj in self.objects:
            self.scale_speeds[obj] = random.uniform(0.1, 1.0)  # Assign a random speed value between 0.1 and 1.0

        # Initialize audio3d array to hold unique audio3d instances for each object
        self.audio3darray = {}
        for idx, obj in enumerate(self.objects):
            self.audio3darray[obj] = audio3d()  # Assign a unique audio3d instance to each object
        
        # Additive synthesis sounds (combining multiple sine waves for each object)
        #self.taskMgr.add(self.arpeggio_synthesizer, "ArpeggioSynthesizer")
        #\self.taskMgr.add(self.arpeggio_synthesizer, "AdditiveSynthesizer")
        
        #self.taskMgr.add(self.rotate_objects, "Rotate")
        #self.mb = MotionBlur()
    
    def quit(self):
        """Gracefully quit the application"""
        print("Exiting the application...")
        self.userExit() 
    def setup_fullscreen(self):
        """Set up fullscreen at native resolution"""
        props = WindowProperties()
        props.setFullscreen(True)

        # Get the native resolution of the primary monitor
        monitor = get_monitors()[0]  # Assumes primary monitor is the first
        width = monitor.width
        height = monitor.height

        # Set the window size to match the display
        props.setSize(width, height)

        # Request the properties
        self.win.requestProperties(props)

        print(f"Setting fullscreen resolution to {width}x{height}")

    def get_gamepad_axes(self):
        """Get gamepad axes for movement, rotation, and roll."""
        # Left stick for movement
        move_x = self.gamepad.findAxis(InputDevice.Axis.left_x).value
        move_y = -self.gamepad.findAxis(InputDevice.Axis.left_y).value

        # Right stick for rotation
        look_x = self.gamepad.findAxis(InputDevice.Axis.right_x).value
        look_y = -self.gamepad.findAxis(InputDevice.Axis.right_y).value

        # Triggers for roll
        left_trigger = self.gamepad.findAxis(InputDevice.Axis.left_trigger).value
        right_trigger = self.gamepad.findAxis(InputDevice.Axis.right_trigger).value

        return move_x, move_y, look_x, look_y, left_trigger, right_trigger


    def is_gamepad_active(self, move_x, move_y, look_x, look_y):
        """Check if the gamepad is active (any axis is not at rest)."""
        return any(abs(value) > 0.1 for value in (move_x, move_y, look_x, look_y))

    def update_camera(self, task):
        """Update the camera based on gamepad input or follow a path."""
        # Get gamepad axes
        move_x, move_y, look_x, look_y, left_trigger, right_trigger = self.get_gamepad_axes()

        # Check for gamepad activity
        if self.is_gamepad_active(move_x, move_y, look_x, look_y):
            self.last_gamepad_activity = time.time()  # Update last activity time
            self.update_camera_gamepad(move_x, move_y, look_x, look_y, left_trigger, right_trigger)
        else:
            # If idle for longer than the threshold, switch to the camera path
            if time.time() - self.last_gamepad_activity > self.idle_threshold:
                self.update_camera_path()

        return Task.cont


    def update_camera_gamepad(self, move_x, move_y, look_x, look_y, left_trigger, right_trigger):
        """Update camera movement, rotation, pitch, roll based on gamepad input, similar to Starfox."""
        
        # Get the camera's current orientation (forward, right, and up vectors)
        forward = self.camera.getQuat().getForward()  # Camera's forward direction
        right = self.camera.getQuat().getRight()      # Camera's right direction
        up = self.camera.getQuat().getUp()            # Camera's up direction

        # **Left Analog Stick (Thrust/Move Forward/Backward and Left/Right)**
        forward_velocity = forward * -move_y * self.camera_speed  # Move forward/backward relative to camera
        right_velocity = right * move_x * self.camera_speed      # Move left/right relative to camera
        
        # Combine the thrust velocities for final movement
        target_velocity = forward_velocity + right_velocity
        self.camera_velocity += (target_velocity - self.camera_velocity) * self.smoothing_factor

        # Apply the velocity to move the camera
        self.camera.setPos(self.camera.getPos() + self.camera_velocity * globalClock.getDt())

        # **Right Analog Stick (Rotation/Look Around)**

        # Pitch (up/down movement on the right analog stick - X-axis rotation)
        pitch_input = -look_y * self.rotation_speed  # Negative because up tilts down
        self.camera.setP(self.camera.getP() + pitch_input * globalClock.getDt())  # Update camera pitch

        # Roll (left/right movement on the right analog stick - Z-axis rotation)
        roll_input = look_x * self.rotation_speed  # Positive for right tilt, negative for left tilt
        self.camera.setR(self.camera.getR() + roll_input * globalClock.getDt())  # Update camera roll

        # **Triggers (Inverted Spin Control) - Yaw Rotation relative to camera**
        spin_speed = self.rotation_speed  # Speed multiplier for spinning

        # Invert the triggers and make the rotation relative to the camera
        # The right trigger (RT) should rotate the camera left (negative rotation)
        # The left trigger (LT) should rotate the camera right (positive rotation)
        spin_input = (left_trigger - right_trigger) * spin_speed  # Inverted calculation for triggers

        # Adjust the camera's yaw (horizontal spin) based on the trigger input and make it relative to the camera's current facing direction
        self.camera.setH(self.camera.getH() + spin_input * globalClock.getDt())







    def update_camera_path(self):
        """Move the camera along a path targeting the center of mass."""
        t = self.t
        self.t += 0.001
        x = np.sin(t) * 20 + np.sin(t * 2) * 5
        y = np.cos(t) * 30 + np.sin(t * 0.5) * 10
        z = np.sin(t * 3) * 5 + np.cos(t * 0.7) * 15

        self.camera.setPos(
            x + self.center_of_mass[0],
            y + self.center_of_mass[1],
            z + self.center_of_mass[2] + 20,
        )
        self.camera.lookAt(self.center_of_mass)

    def arpeggio_synthesizer(self, task):
        """Create arpeggios for each object that move up and down a scale, with position-based pitch adjustments."""
    
        # Define a simple scale (e.g., a pentatonic scale, can be modified as needed)
        scale = [440.0, 466.16, 493.88, 523.25, 554.37, 587.33, 622.25, 659.25, 698.46, 739.99]  # A major scale
        
        for idx, obj in enumerate(self.objects):
            
            # Define the note index in the scale for each object
            note_index = idx % len(scale)
            base_freq = scale[note_index]  # Base frequency from the scale
            
            # Calculate the direction of the arpeggio (up or down)
            # Using time to determine the movement direction
            arpeggio_direction = 1 if int(task.time * 2) % 2 == 0 else -1  # Toggle direction every half second
            
            # Calculate the number of steps in the arpeggio
            steps = len(scale)
            
            # Calculate the current note index based on time and direction
            note_idx = (note_index + int(task.time * 2) * arpeggio_direction) % steps
            
            # Get the note frequency for the current position in the arpeggio
            note_freq = scale[note_idx]
            
            # Calculate the distance from the camera to the object for volume adjustment
            obj_position = obj.getPos(self.render)
            camera_position = self.camera.getPos(self.render)
            distance = (obj_position - camera_position).length()
            
            # Volume based on distance (attenuation)
            volume = max(0, 1 - distance / 100)  # Basic volume attenuation based on distance
            
            # Panning based on object's position (left-right)
            pan = (obj_position.x - camera_position.x) / 10.0  # Scale pan for stereo
            pan_left = max(0, min(1, (1 - pan) / 2))
            pan_right = max(0, min(1, (1 + pan) / 2))
            
            # Create a synthetic signal for the note frequency
            signal = np.sin(2 * np.pi * note_freq * task.time)  # Basic sine wave signal at the note frequency
            
            # Normalize the signal to [-1, 1]
            signal = np.clip(signal, -1, 1)
            distance = self.get_distance_from_camera(obj)
            # Apply the volume and pan based on distance and position
            #sound = self.audio3darray[obj].playSfx(sfx="o", obj=obj, loop=True, playspeed=, volume=1/distance) # Replace "o" with your actual sound source
            
            if sound:
                # Apply calculated volume and panning
                sound.setVolume(signal * volume)
                sound.setPan(pan_left, pan_right)
        
        return Task.cont
    def get_distance_from_camera(self, obj):
        """Calculate the distance between the object and the camera."""
        obj_position = obj.getPos(self.render)
        camera_position = self.camera.getPos(self.render)
        distance = (obj_position - camera_position).length()
        return distance








    def rotate_objects(self, task):
        """Rotate all objects at different speeds on three axes."""
        if not hasattr(self, 'rotation_speeds'):
            self.rotation_speeds = {}
            for obj in self.objects:
                self.rotation_speeds[obj] = {
                    'x': random.uniform(5, 20),
                    'y': random.uniform(5, 20),
                    'z': random.uniform(5, 20),
                }

        for obj in self.objects:
            speed_x = self.rotation_speeds[obj]['x']
            speed_y = self.rotation_speeds[obj]['y']
            speed_z = self.rotation_speeds[obj]['z']
            
            obj.setH(obj.getH() + speed_y * task.dt)
            obj.setP(obj.getP() + speed_x * task.dt)
            obj.setR(obj.getR() + speed_z * task.dt)
        
        return Task.cont



    def update_emissive_colors(self, task):
        """Rapidly cycle colors of each object in the scene, modulate binaural beat frequency with color cycling speed."""
        
        roygbiv_colors = [
            Vec4(1, 0, 0, 0.25),  # Red
            Vec4(1, 0.5, 0, 0.25),  # Orange
            Vec4(1, 1, 0, 0.25),  # Yellow
            Vec4(0, 1, 0, 0.25),  # Green
            Vec4(0, 0, 1, 0.25),  # Blue
            Vec4(0.29, 0, 0.51, 0.25),  # Indigo
            Vec4(0.56, 0, 1, 0.25),  # Violet
        ]

        # Define base binaural beat frequencies (in Hz)
        base_freq_left = 300  # Left ear base frequency (Hz)
        base_freq_right = 305  # Right ear base frequency (Hz)

        for idx, obj in enumerate(self.objects):
            # Update color cursor based on time (cycling through the colors)
            color_cursor = self.color_cursors[obj] + task.time * 0.1
            self.color_cursors[obj] = color_cursor % 1
            
            # Calculate color index and apply color to object
            color_index = int(self.color_cursors[obj] * len(roygbiv_colors))
            color = roygbiv_colors[color_index % len(roygbiv_colors)]
            self.material.setEmission(color)
            obj.setMaterial(self.material)
            obj.setColor(color)
            obj.setTwoSided(True)
            obj.setTransparency(True)
            
            # Calculate the speed of the color cycling for binaural beat modulation
            color_cycle_speed = self.color_cursors[obj] * 2 * math.pi  # Convert [0, 1] range to oscillating speed
            
            # Oscillate the difference frequency of the binaural beat based on the color cycle speed
            diff_frequency = 5 + (color_cycle_speed * 10)  # Adjust the difference frequency range (5 Hz to ~60 Hz)

            # Create binaural beats by modulating the difference between the left and right frequencies
            freq_left = base_freq_left
            freq_right = base_freq_right + diff_frequency
            
            # Generate the binaural beat signal (in this case, a sine wave with the difference frequency)
            time = task.time
            left_signal = np.sin(2 * np.pi * freq_left * time)  # Left ear signal
            right_signal = np.sin(2 * np.pi * freq_right * time)  # Right ear signal
            
            # Binaural beat is the perceived difference between the two signals
            binaural_beat = left_signal - right_signal
            
            # Now you can use this binaural beat signal to modulate an audio source, for example:
            sound_name = "o"
            pitch_flux = (sin(task.time/16) + 1)/2
            pitch_flux2 = (cos(task.time/8)+1)/2
            print(f"Color Cycle Speed: {color_cycle_speed}")
            distance = self.get_distance_from_camera(obj)
            if(distance > 0):
                sound = self.audio3darray[obj].playSfx(sfx="o", obj=obj, loop=True, playspeed=(self.get_distance_from_camera(obj))*random.choice(self.pentatonic_scale)*(1/color_cycle_speed)/32, volume=binaural_beat)
                #self.audio3darray[obj].setLoopSpeed(2/color_cycle_speed*self.ling_factor)     
                self.audio3darray[obj].setVolume(1/self.get_distance_from_camera(obj))
                

                
                if sound:
                    # Apply the binaural beat signal's volume (this can be mapped to the signal's strength)
                    sound.setVolume(np.clip(abs(binaural_beat), 0, 1))  # Normalize the binaural beat volume (0 to 1)
            
        return Task.cont

    def oscillate_scale_and_rotation(self, task):
        """Oscillate scale and rotation of each object."""
        for obj in self.objects:
            scale_factor = 0.5 + 0.5 * np.sin(task.time * self.scale_speeds[obj] + random.random())
            obj.setScale(scale_factor)

            rotation_speed = random.uniform(.1, .05)
            obj.setH(obj.getH() + rotation_speed * task.time)
            #obj.setP(obj.getP() + scale_factor * task.time)
        return Task.cont

    def twinkle_effect(self, task):
        """Apply a twinkling effect by oscillating the opacity (alpha value)."""
        for index, obj in enumerate(self.objects):
            opacity = 0.5 + 0.5 * np.sin(task.time * 5 + index)
            color = obj.getColor()
            color.setW(opacity)
            obj.setColor(color)
            #self.audio3darray[obj].setVolume(opacity)      
            

        return Task.cont

    def compute_center_of_mass(self, objects):
        """Compute the center of mass for all objects in the scene."""
        total_position = LVector3f(0, 0, 0)
        total_weight = 0
        for obj in objects:
            if obj.getBounds():
                total_position += obj.getBounds().getCenter()
                total_weight += 1
        return total_position / total_weight if total_weight > 0 else LVector3f(0, 0, 0)

# Main script
def main():
    parser = argparse.ArgumentParser(description="Run the AdditiveSynthesizerApp with a specified level.")
    parser.add_argument(
        "--level", 
        type=str, 
        help="The level file to load (e.g., '02.bam'). If not specified, a random level will be selected."
    )
    parser.add_argument(
        "--motion_blur_factor", 
        type=float, 
        default=0.9, 
        help="The motion blur factor to apply (default: 0.9)."
    )

    args = parser.parse_args()
    cwd = os.getcwd()
    level = None
    
    # Define valid scene file extensions
    valid_extensions = (".bam", ".egg", ".gltf", ".glb")
    
    # Collect all valid scene files in the CWD
    scene_files = [
        file
        for file in os.listdir(cwd)
        if file.endswith(valid_extensions)
    ]
    
    if args.level is None:
        # Load a random level if --level is not provided
        level = random.choice(scene_files)
        if not scene_files:
            print("No valid scene files found in the current working directory.")
            
            print(f"No level specified. Loading random level: {level}")
            return
            
    else:
        level = args.level

    app = AdditiveSynthesizerApp(scene_path=level, motion_blur_factor=args.motion_blur_factor)
    app.setup_fullscreen()
    # app.mb = MotionBlur()
    app.run()

if __name__ == "__main__":
    main()
