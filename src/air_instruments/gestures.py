"""Convert MediaPipe image-space landmarks into stable per-finger UP/DOWN states.

The thumb rules intentionally match the working standalone ``hand_detection.py``:
- calculate the 2-D image-space angle at the thumb IP joint (landmarks 2, 3, 4)
- normalize tip-to-index-MCP distance by palm width
- use separate UP-entry and DOWN-release thresholds (hysteresis)
- vote over recent frames to suppress one-frame landmark jitter

No MediaPipe 3-D world landmarks are used for thumb classification.
"""
from collections import deque
import math
from typing import Sequence

from .config import (
    FINGER_PIP_IDS,
    FINGER_TIP_IDS,
    THUMB_DOWN_ANGLE_DEG,
    THUMB_DOWN_SPREAD_RATIO,
    THUMB_STABLE_FRAMES,
    THUMB_UP_ANGLE_DEG,
    THUMB_UP_SPREAD_RATIO,
    THUMB_UP_VOTES_REQUIRED,
    THUMB_RELEASE_MAX_UP_VOTES,
)

Point = Sequence[float]


def distance(a: Point, b: Point) -> float:
    """Return Euclidean distance between two 2-D image points."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def joint_angle(a: Point, b: Point, c: Point) -> float:
    """Return angle ABC in degrees, safely handling near-zero vectors."""
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    denominator = math.hypot(*ba) * math.hypot(*bc)
    if denominator < 1e-6:
        return 0.0
    cosine = (ba[0] * bc[0] + ba[1] * bc[1]) / denominator
    cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(cosine))


class ThumbStateTracker:
    """Use image-space IP angle, spread, hysteresis and frame voting.

    This deliberately mirrors the thumb algorithm from the user's working
    standalone script instead of the experimental MCP/world-angle version.
    """

    def __init__(self) -> None:
        self.is_up = False
        self.votes: deque[bool] = deque(maxlen=THUMB_STABLE_FRAMES)
        self.last_ip_angle = 0.0
        self.last_spread_ratio = 0.0
        self.last_extension_ratio = 0.0
        self.last_candidate_up = False

    def update(self, points: Sequence[Point]) -> bool:
        """Update the thumb state from 21 pixel-space hand landmarks."""
        if len(points) < 21:
            self.last_candidate_up = False
            return self.is_up

        # Thumb IP angle: 180 degrees means the joint is straight.
        ip_angle = joint_angle(points[2], points[3], points[4])

        # Normalize thumb-tip-to-index-MCP distance by palm width.
        palm_width = max(distance(points[5], points[17]), 1.0)
        spread_ratio = distance(points[4], points[5]) / palm_width

        # Thumb segment extension ratio: distance(tip, MCP) / (segment1 + segment2).
        # When straight this is ~0.95-1.0; when bent it drops below 0.80.
        seg1 = distance(points[3], points[2])
        seg2 = distance(points[4], points[3])
        total_len = max(seg1 + seg2, 1.0)
        extension_ratio = distance(points[4], points[2]) / total_len

        self.last_ip_angle = ip_angle
        self.last_spread_ratio = spread_ratio
        self.last_extension_ratio = extension_ratio

        if self.is_up:
            # While UP, tolerate minor adjustments; release when clearly bent or tucked.
            candidate_up = (
                (ip_angle >= THUMB_DOWN_ANGLE_DEG or extension_ratio >= 0.82)
                and spread_ratio >= THUMB_DOWN_SPREAD_RATIO
            )
        else:
            # To enter UP, thumb must be straight and extended from the palm.
            candidate_up = (
                (ip_angle >= THUMB_UP_ANGLE_DEG or extension_ratio >= 0.90)
                and spread_ratio >= THUMB_UP_SPREAD_RATIO
            )

        self.last_candidate_up = candidate_up
        self.votes.append(candidate_up)

        # Decide after 2 frames for fast, natural response time.
        if len(self.votes) >= 2:
            up_votes = sum(self.votes)
            if not self.is_up and up_votes >= THUMB_UP_VOTES_REQUIRED:
                self.is_up = True
            elif self.is_up and up_votes <= THUMB_RELEASE_MAX_UP_VOTES:
                self.is_up = False

        return self.is_up

    @property
    def debug_label(self) -> str:
        """Measurements shown in the webcam overlay for practical tuning."""
        state = "UP" if self.is_up else "DOWN"
        candidate = "UP" if self.last_candidate_up else "DOWN"
        up_votes = sum(self.votes)
        return (
            f"T:{state} IP:{self.last_ip_angle:.0f}° "
            f"SP:{self.last_spread_ratio:.2f} EXT:{self.last_extension_ratio:.2f} "
            f"V:{up_votes}/{len(self.votes)}"
        )


def count_raised_fingers(
    points: Sequence[Point], thumb_tracker: ThumbStateTracker
) -> list[bool]:
    """Return [thumb, index, middle, ring, pinky]; True means UP/straight."""
    raised = [thumb_tracker.update(points)]
    # Other four fingers match the standalone reference's 2-D y-coordinate rule.
    for tip_id, pip_id in zip(FINGER_TIP_IDS, FINGER_PIP_IDS):
        raised.append(points[tip_id][1] < points[pip_id][1])
    return raised
