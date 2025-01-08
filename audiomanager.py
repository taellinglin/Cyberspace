from panda3d.core import AudioManager as BaseAudioManager, AudioSound

class SimpleAudioManager(BaseAudioManager):
    def __init__(self):
        super().__init__()

    def play_sound(self, sound_path, volume=1.0, pitch=1.0):
        sound = self.loader.loadSfx(sound_path)
        sound.setVolume(volume)
        sound.setPitch(pitch)
        sound.play()

    def stop_all_sounds(self):
        self.stopAll()
