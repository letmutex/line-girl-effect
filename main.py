import tkinter as tk
from tkinter import colorchooser, filedialog

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Button
from PIL import Image
from scipy.ndimage import gaussian_filter1d

# Initialize global Tk instance to prevent crashes
# We keep it hidden since we only need it for dialogs
root = tk.Tk()
root.withdraw()

# ==========================================
#           Parameter Configuration
# ==========================================

# --- Canvas Basic Settings ---
CANVAS_SIZE = 512
# Initial colors (can be modified via UI)
INITIAL_BG_COLOR = "#3A4F68"
INITIAL_DOT_COLOR = "#e1ebf5"

# --- Core Animation Physics Parameters (keep values unchanged) ---

LINES_PER_FRAME = 1
# Meaning: Number of lines generated per frame.
# Increase: Lines become denser, gaps shrink, overall brighter, like a solid body.
# Decrease: Lines become sparser, stronger scanline effect, darker overall.

FRAME_INTERVAL = 15
# Meaning: Time interval (in frames) for generating new lines.
# Increase: New lines generate slowly, horizontal spacing increases, stretched appearance.
# Decrease: New lines generate quickly, horizontal spacing decreases, compressed appearance.

BASE_SPEED = 3.0
# Meaning: Base particle movement speed on pure black background.
# Increase: Stronger flow sensation, but may cause line breaks.
# Decrease: Slower flow, more coherent appearance.

FRICTION_FACTOR = 0.9
# Meaning: Degree of brightness-based speed impedance (0.0 - 1.0).
# Increase (closer to 1.0): Bright area particles almost stop, forming extreme 3D relief (peaks).
# Decrease: Bright area particles decelerate less obviously, flatter appearance.

ACCELERATION = 0.0001
# Meaning: Acceleration in X-axis direction.
# Increase: Lines accelerate during movement, creating stretching effect.
# Decrease: Uniform motion.

LINE_TENSION = 0.3
# Meaning: Line smoothness (Gaussian blur Sigma value).
# Increase: Very smooth lines, loss of detail, liquid-like appearance.
# Decrease: Lines retain more noise and jaggedness, sharper.

# --- Image Processing Parameters (Adjustable) ---
PROCESS_PARAMS = {
    "contrast_steepness": 9,
    "contrast_midpoint": 0.3,
    "blur_sigma": 2.0,
}

# Track current image path for re-processing
current_image_path = "input.jpg"
# Cache for raw normalized data (before effects) to optimize slider performance
raw_normalized_data = None

# ==========================================
#          Image Processing Logic
# ==========================================


def crop_center_square(img):
    """
    Crop image to a center square to avoid distortion.
    """
    width, height = img.size
    min_dim = min(width, height)

    left = (width - min_dim) / 2
    top = (height - min_dim) / 2
    right = (width + min_dim) / 2
    bottom = (height + min_dim) / 2

    img = img.crop((left, top, right, bottom))
    return img


def load_image_data(image_path: str):
    """
    Load, crop, resize, and normalize image.
    Returns raw normalized float array (0-1).
    """
    try:
        if image_path:
            input_img = Image.open(image_path)
        else:
            raise FileNotFoundError
    except (FileNotFoundError, AttributeError):
        print("Image not found, generating default test texture...")
        x = np.linspace(0, 1, CANVAS_SIZE)
        y = np.linspace(0, 1, CANVAS_SIZE)
        xv, yv = np.meshgrid(x, y)
        input_img = Image.fromarray(
            (np.sin(xv * 10) * np.cos(yv * 5) * 127 + 128).astype("uint8")
        )

    # 1. Crop and scale
    input_img = crop_center_square(input_img)
    input_img = input_img.convert("L")
    input_img = input_img.resize((CANVAS_SIZE, CANVAS_SIZE), Image.Resampling.LANCZOS)

    # 2. Normalize
    data = np.array(input_img) / 255.0

    # --- Image Enhancement (Static) ---

    # Histogram stretching: Expand darkest and brightest ranges to ensure sufficient dynamic range
    p_min, p_max = np.percentile(data, (2, 98))
    if p_max - p_min > 0:
        data = (data - p_min) / (p_max - p_min)
    data = np.clip(data, 0, 1)

    return data


def apply_image_effects(data):
    """
    Apply real-time effects (contrast, blur) to normalized data.
    """
    # S-curve: Nonlinear contrast adjustment
    # Purpose is to darken background noise while enhancing midtone layers (clothing/facial features)
    steepness = PROCESS_PARAMS["contrast_steepness"]
    midpoint = PROCESS_PARAMS["contrast_midpoint"]
    data = 1 / (1 + np.exp(-(data - midpoint) * steepness))

    # Re-normalize to 0-1
    data = (data - data.min()) / (data.max() - data.min())

    # 3. Preprocessing blur
    sigma = PROCESS_PARAMS["blur_sigma"]
    data = gaussian_filter1d(data, sigma=sigma, axis=0)
    data = gaussian_filter1d(data, sigma=sigma, axis=1)

    return np.flipud(data * 255.0)


# Initialize data
raw_normalized_data = load_image_data(current_image_path)
pixels = apply_image_effects(raw_normalized_data)

# ==========================================
#          UI and Drawing Logic
# ==========================================

fig, ax = plt.subplots(figsize=(9, 9), dpi=100)
# Leave more space at bottom for buttons
plt.subplots_adjust(bottom=0.15, left=0.05, right=0.95, top=0.95)

# Set initial colors
current_bg_color = INITIAL_BG_COLOR
current_dot_color = INITIAL_DOT_COLOR

ax.set_facecolor(current_bg_color)
fig.patch.set_facecolor(current_bg_color)
ax.set_xlim(0, CANVAS_SIZE)
ax.set_ylim(0, CANVAS_SIZE)
ax.axis("off")

# Debug background image
img_obj = ax.imshow(
    pixels,
    cmap="gray",
    origin="lower",
    extent=(0, CANVAS_SIZE, 0, CANVAS_SIZE),
    alpha=0.0,  # Hidden by default
    visible=False,
)

# Particle object
scat = ax.scatter([], [], s=0.2, c=current_dot_color, alpha=0.9, marker="o")

# Global variables
particles_x = []
frame_count = 0
is_generating = True


# --- Interaction Callback Functions ---


def toggle_view(event):
    """Toggle between original image/lines display"""
    current_state = img_obj.get_visible()
    # If currently invisible (False), set to visible with alpha=0.8, otherwise set to 0
    img_obj.set_visible(not current_state)
    img_obj.set_alpha(0.8 if not current_state else 0.0)
    scat.set_visible(current_state)  # Reverse
    plt.draw()


def select_image(event):
    """Select image file"""
    global pixels, particles_x, frame_count, current_image_path, raw_normalized_data

    # Remove local root creation/destruction
    # We still rely on the hidden global root for these dialogs
    file_path = filedialog.askopenfilename(
        title="Select Image",
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.webp")],
    )

    if file_path:
        current_image_path = file_path
        # Load and cache input data
        raw_normalized_data = load_image_data(file_path)
        # Apply effects
        pixels = apply_image_effects(raw_normalized_data)

        img_obj.set_data(pixels)
        particles_x = []  # Clear current lines
        frame_count = 0
        plt.draw()


def set_bg_color(event):
    """Set background color"""
    global current_bg_color
    # Remove local root creation/destruction
    color = colorchooser.askcolor(
        title="Select Background Color", initialcolor=current_bg_color
    )[1]

    if color:
        current_bg_color = color
        ax.set_facecolor(current_bg_color)
        fig.patch.set_facecolor(current_bg_color)
        plt.draw()


def set_dot_color(event):
    """Set particle color"""
    global current_dot_color
    # Remove local root creation/destruction
    color = colorchooser.askcolor(
        title="Select Particle Color", initialcolor=current_dot_color
    )[1]

    if color:
        current_dot_color = color
        scat.set_color(current_dot_color)
        plt.draw()

    if raw_normalized_data is not None:
        pixels = apply_image_effects(raw_normalized_data)
        img_obj.set_data(pixels)
        plt.draw()


def toggle_generation(event):
    """Toggle line generation"""
    global is_generating
    is_generating = not is_generating
    # Update button label
    new_label = "Start" if not is_generating else "Stop"
    btn_stop.label.set_text(new_label)
    plt.draw()


# --- Button Layout ---
# Styling
BUTTON_COLOR = "#2c3e50"
BUTTON_HOVER_COLOR = "#34495e"
TEXT_COLOR = "#ecf0f1"


def create_styled_button(axes, label, callback):
    """Helper to create a consistently styled button."""
    btn = Button(axes, label, color=BUTTON_COLOR, hovercolor=BUTTON_HOVER_COLOR)
    btn.label.set_color(TEXT_COLOR)
    btn.on_clicked(callback)
    return btn


# Single row of buttons at the bottom
# Spacing calculation: 5 buttons, equal width
button_y = 0.02
button_width = 0.15
button_height = 0.06
spacing = 0.03
start_x = (1.0 - (5 * button_width + 4 * spacing)) / 2

# 1. Toggle View
ax_btn_toggle = plt.axes((start_x, button_y, button_width, button_height))
btn_toggle = create_styled_button(ax_btn_toggle, "Toggle", toggle_view)

# 2. Select Image
ax_btn_select = plt.axes(
    (start_x + button_width + spacing, button_y, button_width, button_height)
)
btn_select = create_styled_button(ax_btn_select, "Image", select_image)

# 3. BG Color
ax_btn_bg = plt.axes(
    (start_x + 2 * (button_width + spacing), button_y, button_width, button_height)
)
btn_bg = create_styled_button(ax_btn_bg, "BG Color", set_bg_color)

# 4. Dot Color
ax_btn_dot = plt.axes(
    (start_x + 3 * (button_width + spacing), button_y, button_width, button_height)
)
btn_dot = create_styled_button(ax_btn_dot, "Dot Color", set_dot_color)

# 5. Stop/Start
ax_btn_stop = plt.axes(
    (start_x + 4 * (button_width + spacing), button_y, button_width, button_height)
)
btn_stop = create_styled_button(ax_btn_stop, "Stop", toggle_generation)


# ==========================================
#          Core Animation Loop
# ==========================================


def animate(frame):
    global frame_count, particles_x

    frame_count += 1

    # Generate new lines
    if is_generating and frame_count % FRAME_INTERVAL == 0:
        new_column = np.zeros(CANVAS_SIZE)
        particles_x.append(new_column)

    active_particles = []
    y_indices = np.arange(CANVAS_SIZE)

    for col_x in particles_x:
        # Get brightness
        current_x_int = np.clip(col_x, 0, CANVAS_SIZE - 1).astype(int)
        brightness = pixels[y_indices, current_x_int]
        norm_b = brightness / 255.0

        # Calculate speed
        current_speed = BASE_SPEED * (1.0 - (norm_b * FRICTION_FACTOR))
        x_accel = col_x * ACCELERATION
        final_speed = current_speed + x_accel

        # Move
        col_x += final_speed

        # Smooth
        col_x[:] = gaussian_filter1d(col_x, sigma=LINE_TENSION)

        # Keep points within canvas
        if np.min(col_x) < CANVAS_SIZE:
            active_particles.append(col_x)

    particles_x = active_particles

    # Update scatter data
    if particles_x:
        all_x = np.array(particles_x).flatten()
        all_y = np.tile(y_indices, len(particles_x))
        mask = all_x < CANVAS_SIZE
        if np.any(mask):
            data = np.stack([all_x[mask], all_y[mask]], axis=1)
            scat.set_offsets(data)
        else:
            scat.set_offsets(np.zeros((0, 2)))
    else:
        scat.set_offsets(np.zeros((0, 2)))

    return [scat, img_obj]


ani = animation.FuncAnimation(
    fig, animate, frames=None, interval=20, blit=False, cache_frame_data=False
)
plt.show()
