import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider


class ControlPanelMSG:
    def __init__(self, params, on_process_change, on_toggle_gen):
        self.params = params
        self.on_process_change = on_process_change
        self.on_toggle_gen = on_toggle_gen
        self.sliders = []
        self.checks = []

        # Create a new figure for controls
        # Hide toolbar to keep it clean
        with matplotlib.rc_context({"toolbar": "None"}):
            self.fig = plt.figure(figsize=(4.5, 9), facecolor="#f0f0f0")

        self.fig.canvas.manager.set_window_title("Control Panel")

        # Adjust layout
        # We'll use manual positioning, so subplots_adjust isn't critical
        # but keeps default areas clean.
        self.fig.subplots_adjust(left=0.05, bottom=0.05, right=0.95, top=0.95)

        self._add_title(0.96, "Generation Parameters")
        
        y = 0.92
        pitch = 0.0656

        self._add_slider(
            "Lines/Frame",
            "LINES_PER_FRAME",
            1,
            10,
            valstep=1,
            start_y=y,
            desc="Particles born per frame. Higher = Denser.",
        )
        y -= pitch
        self._add_slider(
            "Interval",
            "FRAME_INTERVAL",
            1,
            60,
            valstep=1,
            start_y=y,
            desc="Frames between births. Higher = Slower/Stretched.",
        )
        y -= pitch
        self._add_slider(
            "Base Speed",
            "BASE_SPEED",
            0.1,
            10.0,
            start_y=y,
            desc="Particle flow speed in dark areas.",
        )
        y -= pitch
        self._add_slider(
            "Friction",
            "FRICTION_FACTOR",
            0.0,
            1.0,
            start_y=y,
            desc="Slowdown in bright areas. 1.0 = Stop.",
        )
        y -= pitch
        self._add_slider(
            "Accel",
            "ACCELERATION",
            0.0,
            0.002,
            start_y=y,
            desc="Horizontal acceleration.",
        )
        y -= pitch
        self._add_slider(
            "Tension",
            "LINE_TENSION",
            0.1,
            2.0,
            start_y=y,
            desc="Smoothness (Sigma). Higher = Smoother.",
        )

        y -= 0.10  # Extra gap for section title
        self._add_title(y, "Image Processing")
        y -= 0.06

        self._add_slider(
            "Contrast Str",
            "contrast_steepness",
            1.0,
            20.0,
            start_y=y,
            is_process=True,
            desc="S-Curve steepness.",
        )
        y -= pitch
        self._add_slider(
            "Contrast Mid",
            "contrast_midpoint",
            0.0,
            1.0,
            start_y=y,
            is_process=True,
            desc="S-Curve midpoint balance.",
        )
        y -= pitch
        self._add_slider(
            "Blur",
            "blur_sigma",
            0.0,
            10.0,
            start_y=y,
            is_process=True,
            desc="Pre-blur amount.",
        )

    def _add_title(self, y, text):
        self.fig.text(
            0.5, y, text, ha="center", va="center", fontweight="bold", fontsize=12
        )

    def _add_slider(
        self,
        label,
        key,
        vmin,
        vmax,
        valstep=None,
        start_y=0.9,
        is_process=False,
        desc="",
    ):
        # Layout:
        # [Label] [Slider -----------------] [Value]
        #         [Description string      ]

        # Slider Axes
        # [left, bottom, width, height]
        ax_slider = self.fig.add_axes([0.30, start_y, 0.50, 0.03])

        slider = Slider(
            ax=ax_slider,
            label=label,
            valmin=vmin,
            valmax=vmax,
            valinit=self.params[key],
            valstep=valstep,
            color="#3498db",
        )
        slider.label.set_size(10)

        # Add description text below the slider
        if desc:
            self.fig.text(0.30, start_y - 0.025, desc, fontsize=8, color="#555555")

        # Callback
        def update(val):
            self.params[key] = val
            if is_process:
                self.on_process_change()

        slider.on_changed(update)
        self.sliders.append(slider)
