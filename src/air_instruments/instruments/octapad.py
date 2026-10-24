"""Octapad instrument definition: 8 electronic percussion drum pads."""
from ..config import OCTAPAD_LEFT_PADS, OCTAPAD_RIGHT_PADS
from ..rendering import draw_octapad


class Octapad:
    key = "octapad"
    display_name = "Octapad"
    sound_kind = "octapad"
    max_hands = 2
    hand_slots = ("left", "right")
    notes_by_slot = {
        "left": OCTAPAD_LEFT_PADS,
        "right": OCTAPAD_RIGHT_PADS,
    }

    @staticmethod
    def draw(frame, raised_by_slot, single_hand_thumb_up: bool = True) -> None:
        draw_octapad(frame, raised_by_slot, single_hand_thumb_up=single_hand_thumb_up)

    @staticmethod
    def status_text(hand_count: int, thumb_up: bool = True) -> str:
        if hand_count >= 2:
            return "OCTAPAD | 2 Hands detected: Left (Pads 1-4) & Right (Pads 5-8)"
        elif hand_count == 1:
            bank = "Bank A (Pads 1-4)" if thumb_up else "Bank B (Pads 5-8)"
            return f"OCTAPAD | 1 Hand detected: {bank} active"
        return "OCTAPAD | Hands detected: 0/2"

    @staticmethod
    def instruction_text() -> str:
        return "Left = Kick/Snare/HiHat · Right = Toms/Crash/Clap · 1 Hand: Thumb switches Bank A/B"
