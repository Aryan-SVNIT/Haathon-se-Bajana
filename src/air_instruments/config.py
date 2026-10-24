"""Central configuration for notes, model assets, and hand landmarks."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)
MODEL_DIR = PROJECT_ROOT / "assets" / "models"
MODEL_PATH = MODEL_DIR / "hand_landmarker.task"

SAMPLE_RATE = 44_100
CAMERA_INDEX = 0

# MediaPipe's 21-landmark hand model: fingertips, in thumb-to-pinky order.
TIP_IDS = (4, 8, 12, 16, 20)
TIP_NAMES = ("T", "I", "M", "R", "P")
FINGER_NAMES = ("Thumb", "Index", "Middle", "Ring", "Pinky")
FINGER_TIP_IDS = (8, 12, 16, 20)
FINGER_PIP_IDS = (6, 10, 14, 18)

# Thumb detection tuning, based on image-space landmarks.
# To enter UP, the thumb IP joint must be straighter and tip spread wider.
# Once UP, more forgiving thresholds keep small bends from causing flicker.
THUMB_UP_ANGLE_DEG = 125.0
THUMB_UP_SPREAD_RATIO = 0.30
THUMB_DOWN_ANGLE_DEG = 105.0
THUMB_DOWN_SPREAD_RATIO = 0.20
THUMB_STABLE_FRAMES = 5
THUMB_UP_VOTES_REQUIRED = 3
THUMB_RELEASE_MAX_UP_VOTES = 1

# For piano, the hand on the LEFT side of the mirrored webcam image plays low notes;
# the hand on the RIGHT side plays higher notes. Five gestures per hand = 10 notes.
PIANO_LEFT_NOTES = (
    ("C3", 130.81),
    ("D3", 146.83),
    ("E3", 164.81),
    ("F3", 174.61),
    ("G3", 196.00),
)
PIANO_RIGHT_NOTES = (
    ("C4", 261.63),
    ("D4", 293.66),
    ("E4", 329.63),
    ("F4", 349.23),
    ("G4", 392.00),
)

# The first guitar prototype maps the five fingers to five plucked-string-like notes.
GUITAR_NOTES = (
    ("E3", 164.81),
    ("A3", 220.00),
    ("D4", 293.66),
    ("G4", 392.00),
    ("B4", 493.88),
)
