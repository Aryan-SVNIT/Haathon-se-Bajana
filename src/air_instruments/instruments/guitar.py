"""Guitar instrument definition: one hand, five plucked-string-like notes."""
from ..config import GUITAR_NOTES
from ..rendering import draw_guitar_neck


class Guitar:
    key = "guitar"
    display_name = "Guitar"
    sound_kind = "guitar"
    max_hands = 1
    hand_slots = ("guitar",)
    notes_by_slot = {"guitar": GUITAR_NOTES}

    @staticmethod
    def draw(frame, raised_by_slot) -> None:
        draw_guitar_neck(frame, GUITAR_NOTES, raised_by_slot.get("guitar"))

    @staticmethod
    def status_text(hand_count: int) -> str:
        return f"GUITAR | Hand detected: {min(hand_count, 1)}/1"

    @staticmethod
    def instruction_text() -> str:
        return "Use one hand. Bend a finger to pluck its mapped note."
