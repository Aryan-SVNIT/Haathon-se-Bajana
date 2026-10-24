"""Piano instrument definition: two hands, ten notes."""
from ..config import PIANO_LEFT_NOTES, PIANO_RIGHT_NOTES
from ..rendering import draw_piano_keyboard


class Piano:
    key = "piano"
    display_name = "Piano"
    sound_kind = "piano"
    max_hands = 2
    hand_slots = ("left", "right")
    notes_by_slot = {"left": PIANO_LEFT_NOTES, "right": PIANO_RIGHT_NOTES}

    @staticmethod
    def draw(frame, raised_by_slot) -> None:
        draw_piano_keyboard(frame, raised_by_slot)

    @staticmethod
    def status_text(hand_count: int) -> str:
        return f"PIANO | Hands detected: {min(hand_count, 2)}/2"

    @staticmethod
    def instruction_text() -> str:
        return "Use both hands: screen-left = low notes, screen-right = high notes"
