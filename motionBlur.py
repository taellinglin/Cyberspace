from panda3d.core import CardMaker, NodePath, TransparencyAttrib, ColorBlendAttrib
from direct.task import Task


class MotionBlur:
    def __init__(self, fade_rate=0.0001):
        """
        Initialize the MotionBlur effect.
        :param fade_rate: The rate at which the motion blur fades out (0.0 to 1.0).
                         Higher values result in slower fading.
        """
        # Disable clearing the color buffer for blending effect
        base.win.set_clear_color_active(False)

        # Create a full-screen quad for the motion blur effect
        cardmaker = CardMaker("motion_blur_quad")
        cardmaker.set_frame_fullscreen_quad()

        # Attach the quad to a render-to-texture camera, not the main camera
        self.motion_quad = NodePath(cardmaker.generate())
        self.motion_quad.reparent_to(base.render2d)

        # Set transparency and enable additive blending
        self.motion_quad.set_transparency(TransparencyAttrib.M_alpha)
        self.motion_quad.set_attrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))

        # Set initial color and alpha
        self.motion_quad.set_color(0, 0, 0, 0.0)

        # Adjust Z order and depth properties
        self.motion_quad.set_bin("background", 0)
        self.motion_quad.set_depth_test(False)
        self.motion_quad.set_depth_write(False)

        # Fade rate for the motion trails
        self.fade_rate = fade_rate

        # Add a task to manage the fade-out effect
        base.task_mgr.add(self.update_motion_blur, "UpdateMotionBlur")

    def update_motion_blur(self, task):
        """
        Gradually fade out the motion blur effect by reducing the alpha value.
        """
        current_color = self.motion_quad.get_color()
        current_alpha = current_color[3]

        # Gradually reduce alpha
        new_alpha = max(0.0, current_alpha * self.fade_rate)
        self.motion_quad.set_color(current_color[0], current_color[1], current_color[2], new_alpha)

        return Task.cont

    def apply_blur(self, intensity=0.0001):
        """
        Apply motion blur by increasing the alpha value.
        :param intensity: The alpha value to apply for the motion blur (0.0 to 1.0).
        """
        self.motion_quad.set_color(0, 0, 0, intensity)

    def cleanup(self):
        """Clean up the motion blur quad."""
        if self.motion_quad is None or self.motion_quad.is_empty():
            return
        self.motion_quad.removeNode()
        self.motion_quad = None
