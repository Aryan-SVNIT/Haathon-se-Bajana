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
# Calibrated for natural hand poses, fast response time, and jitter resistance.
THUMB_UP_ANGLE_DEG = 118.0
THUMB_UP_SPREAD_RATIO = 0.22
THUMB_DOWN_ANGLE_DEG = 102.0
THUMB_DOWN_SPREAD_RATIO = 0.15
THUMB_STABLE_FRAMES = 3
THUMB_UP_VOTES_REQUIRED = 2
THUMB_RELEASE_MAX_UP_VOTES = 1

# Ten requested chord progressions:
# Left hand (5 chords): C Major, G Major, A Minor, F Major, D Major
# Right hand (5 chords): E Minor, A Major, B Minor, E Major, F# Minor
PIANO_LEFT_NOTES = (
    ("C Major", 130.81, 164.81, 196.00),   # C - E - G
    ("G Major", 196.00, 246.94, 293.66),   # G - B - D
    ("A Minor", 220.00, 261.63, 329.63),   # A - C - E
    ("F Major", 174.61, 220.00, 261.63),   # F - A - C
    ("D Major", 146.83, 185.00, 220.00),   # D - F# - A
)
PIANO_RIGHT_NOTES = (
    ("E Minor", 164.81, 196.00, 246.94),   # E - G - B
    ("A Major", 220.00, 277.18, 329.63),   # A - C# - E
    ("B Minor", 246.94, 293.66, 369.99),   # B - D - F#
    ("E Major", 164.81, 207.65, 246.94),   # E - G# - B
    ("F# Minor", 185.00, 220.00, 277.18),  # F# - A - C#
)

# Guitar mappings: The thumb acts as a Major / Minor mode switch.
# Thumb UP = Major; Thumb DOWN = Minor.
# The 4 playable fingers (Index, Middle, Ring, Pinky) map to 4 guitar chords from this list.
GUITAR_PLAYING_FINGERS = ("Index", "Middle", "Ring", "Pinky")

GUITAR_MAJOR_NOTES = (
    ("C Major", 130.81, 164.81, 196.00),  # Index: C Major
    ("G Major", 196.00, 246.94, 293.66),  # Middle: G Major
    ("D Major", 146.83, 185.00, 220.00),  # Ring: D Major
    ("A Major", 220.00, 277.18, 329.63),  # Pinky: A Major
)

GUITAR_MINOR_NOTES = (
    ("A Minor", 220.00, 261.63, 329.63),  # Index: A Minor (relative minor of C Major)
    ("E Minor", 164.81, 196.00, 246.94),  # Middle: E Minor (relative minor of G Major)
    ("B Minor", 246.94, 293.66, 369.99),  # Ring: B Minor (relative minor of D Major)
    ("F# Minor", 185.00, 220.00, 277.18), # Pinky: F# Minor (relative minor of A Major)
)

# Retain for backward compatibility
GUITAR_NOTES = GUITAR_MAJOR_NOTES

# Octapad Electronic Percussion Pad mappings:
# 8 iconic electronic percussion drum pads (plus Thumb extras: Cowbell / Ride):
# Left Hand (Bank A / Rhythm):
#   Thumb (0): Cowbell
#   Index (1): Kick (Bass Drum)
#   Middle (2): Snare Drum
#   Ring (3): Hi-Hat Closed
#   Pinky (4): Hi-Hat Open
# Right Hand (Bank B / Accents & Fills):
#   Thumb (0): Ride Cymbal
#   Index (1): Low Tom
#   Middle (2): High Tom
#   Ring (3): Crash Cymbal
#   Pinky (4): Hand Clap
OCTAPAD_LEFT_PADS = (
    ("Cowbell", "cowbell", 820.0),
    ("Kick", "kick", 55.0),
    ("Snare", "snare", 190.0),
    ("Hi-Hat Closed", "hihat_closed", 8000.0),
    ("Hi-Hat Open", "hihat_open", 7500.0),
)

OCTAPAD_RIGHT_PADS = (
    ("Ride Cymbal", "ride", 4200.0),
    ("Low Tom", "low_tom", 95.0),
    ("High Tom", "high_tom", 165.0),
    ("Crash Cymbal", "crash", 5000.0),
    ("Hand Clap", "clap", 1200.0),
)

# 8 Core Octapad pads in standard 1..8 display order
OCTAPAD_CORE_PADS = (
    ("Pad 1: Kick", "kick", 55.0),
    ("Pad 2: Snare", "snare", 190.0),
    ("Pad 3: Hi-Hat Closed", "hihat_closed", 8000.0),
    ("Pad 4: Hi-Hat Open", "hihat_open", 7500.0),
    ("Pad 5: Low Tom", "low_tom", 95.0),
    ("Pad 6: High Tom", "high_tom", 165.0),
    ("Pad 7: Crash Cymbal", "crash", 5000.0),
    ("Pad 8: Hand Clap", "clap", 1200.0),
)

