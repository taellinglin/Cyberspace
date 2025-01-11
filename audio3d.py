from direct.showbase import Audio3DManager
from random import choice, shuffle
from panda3d.core import AudioSound

class audio3d:
    def __init__(self):
        self.audio3d = Audio3DManager.Audio3DManager(base.sfxManagerList[0], camera)

        # Initializing sound effects for 'o'
        self.sfx3d = {
            "o": [
                self.audio3d.loadSfx("o.wav")
            ]
        }

        # Set global audio settings
        self.audio3d.setDistanceFactor(0.01)
        self.audio3d.setDopplerFactor(30)

        # List of looping sounds
        self.playing_loops = []

    def enter(self):
        """ Start the update task for the audio manager. """
        base.task_mgr.add(self.update, "update")

    def playSfx(self, sfx=None, obj=None, loop=False, playspeed=1.0, volume=1.0):
        """ Play the requested sound effect (non-blocking) with optional speed adjustment. """
        if sfx is None:
            print("No sfx provided...")
            return

        if obj is None:
            print("No object provided to attach sound to.")
            return

        # Check if sound exists in the dictionary
        if self.sfx3d.get(sfx):
            list_copy = self.sfx3d.get(sfx)
            shuffle(list_copy)  # Shuffle to pick a random sound if there are multiple options

            sfx3d = list_copy.pop()  # Take the sound effect object
            sfx3d.setLoop(loop)  # Set loop status
            sfx3d.setVolume(volume)  # Set the volume

            # Apply the playspeed
            sfx3d.setPlayRate(playspeed)  # Adjust the play rate based on the playspeed

            # Attach sound to the object and adjust distance factors
            self.audio3d.attachSoundToObject(sfx3d, obj)
            self.audio3d.setSoundMinDistance(sfx3d, 100)
            self.audio3d.setSoundMaxDistance(sfx3d, 200)
            self.audio3d.setDropOffFactor(0.01)
            self.audio3d.setDopplerFactor(30)
            # Play sound immediately (non-blocking)
            sfx3d.play()

            # Keep track of the looping sounds if looping is enabled
            if loop:
                self.playing_loops.append(sfx3d)

            print(f"Attached and played sound: {sfx} to object: {str(obj)} at speed: {playspeed}")

    def update(self, task):
        """ Update the audio system (called every frame). """
        self.audio3d.update()

        return task.cont

    def stopLoopingAudio(self):
        """ Stop all looping audio effects. """
        for sound in self.playing_loops:
            sound.stop()

        # Clear the list of looping sounds after stopping
        self.playing_loops.clear()
        
    def setLoopSpeed(self, playspeed=1.0):
        """ Adjust the playback speed of all currently playing looping sounds. """
        if not self.playing_loops:
            print("No looping sounds are currently playing.")
            return

        for sound in self.playing_loops:
            sound.setPlayRate(playspeed)
            print(f"Adjusted looping sound speed to: {playspeed}")

    def setVolume(self, volume=1.0):
        """ Adjust the volume of all currently playing looping sounds. """
        if not self.playing_loops:
            print("No looping sounds are currently playing.")
            return

        # Clamp the volume between 0.0 and 1.0
        volume = max(0.0, min(volume, 1.0))

        for sound in self.playing_loops:
            sound.setVolume(volume)
            print(f"Adjusted looping sound volume to: {volume}")

    def status(self, obj):
        """ Get the status of the sound attached to an object. """
        if obj not in self.sfx3d:
            print("No sound attached to this object.")
            return None

        for sound in self.sfx3d.values():
            if sound.status() == AudioSound.PLAYING:
                print(f"Sound is playing for object: {str(obj)}.")
                return "Playing"
            else:
                print(f"Sound is not playing for object: {str(obj)}.")
                return "Stopped"
            
    def getPos(self, obj):
        """ Get the position of the object to which the sound is attached. """
        if obj is None:
            print("No object provided.")
            return None

        # Get the position of the object (assuming it's a Panda3D node)
        position = obj.getPos()
        
        print(f"Object position: {position}")
        return position
