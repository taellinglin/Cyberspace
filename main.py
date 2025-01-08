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

class AdditiveSynthesizerApp(ShowBase):
    def __init__(self, scene_path="01.bam", motion_blur_factor=0.9):
        super().__init__(self)
        self.accept("escape", self.quit)
        self.setup_fullscreen()
        self.ling_factor = 1*random.choice([8])
        # Set background color to black
        self.setBackgroundColor(0, 0, 0, 0.0)
                # Get the current working directory
        cwd = os.getcwd()
        
        # Define valid scene file extensions
        valid_extensions = (".bam", ".egg", ".gltf", ".glb")
        
        # Collect all valid scene files in the CWD
        scene_files = [
            file
            for file in os.listdir(cwd)
            if file.endswith(valid_extensions)
        ]
        
        if not scene_files:
            print("No valid scene files found in the current working directory.")
            return
        
        # Choose a random scene file
        random_scene = random.choice(scene_files)
        print(f"Loading random scene: {random_scene}")
        
        # Load the chosen scene by its file name
        self.scene = self.loader.loadModel(random_scene)
        if not self.scene:
            raise FileNotFoundError(f"Scene file '{scene_path}' could not be loaded.")
        self.scene.reparentTo(self.render)

        # Get all objects in the scene
        self.objects = self.scene.findAllMatches("**/*")

        # Compute the center of mass for the objects in the scene
        self.center_of_mass = self.compute_center_of_mass(self.objects)

        # Create pentatonic scale frequencies (in Hz)
        self.pentatonic_scale = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88]

        # Initialize camera path and emission color updates
        self.t = 0
        self.taskMgr.add(self.update_camera_path, "UpdateCameraPath")
        self.taskMgr.add(self.update_emissive_colors, "UpdateEmissiveColors")
        if random_scene == "00.bam" or random_scene == "02.bam" or random_scene == "04.bam":
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
        self.taskMgr.add(self.arpeggio_synthesizer, "ArpeggioSynthesizer")
        self.taskMgr.add(self.arpeggio_synthesizer, "AdditiveSynthesizer")
        
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
            sound = self.audio3darray[obj].playSfx(sfx="o", obj=obj, loop=True, playspeed=idx*self.ling_factor*math.sin(idx), volume=((idx/(distance))*0.001)) # Replace "o" with your actual sound source
            
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


    def additive_synthesizer(self, task):
        """Implement additive synthesis by combining multiple sine waves for each object, with frequency modulation based on camera distance and color cycle speed."""
    
        for idx, obj in enumerate(self.objects):
            
            # Get the base frequency from the pentatonic scale
            base_freq = self.pentatonic_scale[idx % len(self.pentatonic_scale)]
            
            # Number of harmonics to combine for additive synthesis
            harmonic_count = 5 
            
            # Get the speed from the color cycle for this object (using color_cursors)
            color_cycle_speed = self.color_cursors[obj]  # The color cursor value is in [0, 1]
            
            # Calculate the distance from the camera to the object
            obj_position = obj.getPos(self.render)
            camera_position = self.camera.getPos(self.render)
            distance = (obj_position - camera_position).length()
            
            # Scale the color cycle speed and the distance to control the arpeggio speed
            # The closer the object is to the camera, the faster the arpeggio
            distance_factor = max(1, distance / 10.0)  # Scale distance (larger distances result in slower speed)
            arpeggio_speed = (0.1 + color_cycle_speed * 1.9) / distance_factor  # Adjust arpeggio speed based on distance
            
            # Sum up multiple sine waves (fundamental and harmonics) with modulation based on color cycle speed and distance
            signal = 0
            for harmonic in range(1, harmonic_count + 1):
                # Calculate the frequency for each harmonic (multiples of the base frequency)
                frequency = base_freq * harmonic
                # The speed of oscillation is now modulated by the color cycle speed and distance
                modulated_frequency = frequency + arpeggio_speed * harmonic  # Modulate frequency with speed
                
                # Amplitude decreases for higher harmonics
                amplitude = 1.0 / harmonic
                
                # Sine wave formula (using modulated frequency)
                signal += amplitude * np.sin(2 * np.pi * modulated_frequency * task.time)
            
            # Normalize the signal to the range [-1, 1]
            signal = np.clip(signal, -1, 1)
            
            # Map the signal to a sound volume
            sound_volume = (signal + 1) / 2  # Convert signal range [-1, 1] to [0, 1]
            
            # Debugging: Print out the signal to check if it's modulating correctly
            print(f"Object {obj.getName()} Arpeggio Speed: {arpeggio_speed}, Signal Volume: {sound_volume}")
            
            # Compute the direction of the sound relative to the listener (camera)
            direction = obj_position - camera_position
            direction.normalize()
            
            # Apply distance attenuation based on the object's distance to the listener
            distance_attenuation = max(0, 1 - distance / 100)
            
            # Calculate stereo panning (left-right based on x-axis direction)
            pan = direction.x  # Use x-axis for stereo pan (left-right)
            pan_left = max(0, min(1, (1 - pan) / 2))
            pan_right = max(0, min(1, (1 + pan) / 2))
            
            # Get the object's color (assuming it has a material with color)
            if obj.hasMaterials():
                mat = obj.getMaterials()[0]  # Get the first material
                color = mat.getDiffuse()  # Get the diffuse color (RGBA)
                # Calculate the average color intensity (using RGB)
                color_intensity = (color[0] + color[1] + color[2]) / 3  # Average of RGB values
                
                # Use color intensity to scale the sound volume
                scaled_sound_volume = sound_volume * color_intensity
            else:
                scaled_sound_volume = sound_volume  # Default to normal volume if no color is set
            
            # Play the sound with the computed volume and pan for each object
            sound_name = "o"  # Adjust this to the appropriate sound
            sound = self.audio3darray[obj].playSfx(sfx="o", obj=obj, loop=True, playspeed=color_intensity*self.ling_factor)  
            self.audio3darray[obj].setVolume(scaled_sound_volume)
            
            if sound:
                # Apply 3D volume based on synthesized signal, distance, and color-based scaling
                sound.setVolume(scaled_sound_volume * distance_attenuation)
                
                # Apply the calculated pan (left-right positioning)
                sound.setPan(pan_left, pan_right)
        
        return Task.cont





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

    def update_camera_path(self, task):
        """Move the camera along a path targeting the center of mass."""
        t = self.t
        self.t += 0.001
        x = np.sin(t) * 20 + np.sin(t * 2) * 5
        y = np.cos(t) * 30 + np.sin(t * 0.5) * 10
        z = np.sin(t * 3) * 5 + np.cos(t * 0.7) * 15

        self.camera.setPos(x + self.center_of_mass[0], y + self.center_of_mass[1], z + self.center_of_mass[2] + 20)
        self.camera.lookAt(self.center_of_mass)
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
            sound = self.audio3darray[obj].playSfx(sfx=sound_name, obj=obj, loop=True, playspeed=32*color_cycle_speed + pitch_flux, volume=1/(idx+1))
            #self.audio3darray[obj].setLoopSpeed(2/color_cycle_speed*self.ling_factor)     
            self.audio3darray[obj].setVolume(1/color_cycle_speed)      
            

            
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
            self.audio3darray[obj].setVolume(opacity)      
            

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

app = AdditiveSynthesizerApp("02.bam", motion_blur_factor=0.9)
app.setup_fullscreen()
#app.mb = MotionBlur()
app.run()
