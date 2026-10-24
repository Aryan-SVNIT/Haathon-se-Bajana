"""Guitar instrument definition: thumb switch for Major / Minor, four playable fingers."""
from ..config import GUITAR_MAJOR_NOTES, GUITAR_MINOR_NOTES
from ..rendering import draw_guitar_neck


class Guitar:
    key = "guitar"
    display_name = "Guitar"
    sound_kind = "guitar"
    max_hands = 1
    hand_slots = ("guitar",)
    notes_major = GUITAR_MAJOR_NOTES
    notes_minor = GUITAR_MINOR_NOTES
    notes_by_slot = {
        "guitar_major": GUITAR_MAJOR_NOTES,
        "guitar_minor": GUITAR_MINOR_NOTES,
    }

    @staticmethod
    def draw(frame, raised_by_slot) -> None:
        raised = raised_by_slot.get("guitar")
        thumb_is_up = True if raised is None else bool(raised[0])
        notes = GUITAR_MAJOR_NOTES if thumb_is_up else GUITAR_MINOR_NOTES
        draw_guitar_neck(frame, notes, raised, thumb_is_up=thumb_is_up)

    @staticmethod
    def status_text(hand_count: int, thumb_is_up: bool = True) -> str:
        mode = "MAJOR" if thumb_is_up else "MINOR"
        return f"GUITAR [{mode} MODE] | Hand detected: {min(hand_count, 1)}/1"

    @staticmethod
    def instruction_text() -> str:
        return "Thumb UP = Major notes | Thumb DOWN = Minor notes | Bend Index/Mid/Ring/Pinky to play"
