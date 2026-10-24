"""Tests for assigning tracked hands to browser instruments without a camera."""
from types import SimpleNamespace
import unittest

from air_instruments.multiplayer.server import order_hands_for_instrument


def hand_at(wrist_x: float):
    """Return the minimal landmark structure used by the slot assigner."""
    return [SimpleNamespace(x=wrist_x, y=0.5)] + [SimpleNamespace(x=0.5, y=0.5) for _ in range(20)]


class InstrumentSlotTests(unittest.TestCase):
    def test_two_piano_hands_are_sorted_left_to_right(self):
        right = hand_at(0.8)
        left = hand_at(0.2)
        self.assertEqual(order_hands_for_instrument([right, left], "piano"), [(1, "left"), (0, "right")])

    def test_single_piano_hand_uses_its_side(self):
        self.assertEqual(order_hands_for_instrument([hand_at(0.25)], "piano"), [(0, "left")])
        self.assertEqual(order_hands_for_instrument([hand_at(0.75)], "piano"), [(0, "right")])

    def test_guitar_uses_only_one_hand(self):
        self.assertEqual(order_hands_for_instrument([hand_at(0.2), hand_at(0.8)], "guitar"), [(0, "guitar")])

    def test_no_detected_hands(self):
        self.assertEqual(order_hands_for_instrument([], "piano"), [])

    def test_guitar_major_and_minor_note_counts(self):
        from air_instruments.config import GUITAR_MAJOR_NOTES, GUITAR_MINOR_NOTES, GUITAR_PLAYING_FINGERS, PIANO_LEFT_NOTES, PIANO_RIGHT_NOTES
        self.assertEqual(len(GUITAR_MAJOR_NOTES), 4)
        self.assertEqual(len(GUITAR_MINOR_NOTES), 4)
        self.assertEqual(len(GUITAR_PLAYING_FINGERS), 4)
        self.assertEqual(len(PIANO_LEFT_NOTES), 5)
        self.assertEqual(len(PIANO_RIGHT_NOTES), 5)
        # Verify 4 guitar roots: C, G, D, A
        self.assertTrue(GUITAR_MAJOR_NOTES[0][0].startswith("C"))
        self.assertTrue(GUITAR_MAJOR_NOTES[1][0].startswith("G"))
        self.assertTrue(GUITAR_MAJOR_NOTES[2][0].startswith("D"))
        self.assertTrue(GUITAR_MAJOR_NOTES[3][0].startswith("A"))

    def test_octapad_hands_and_pads(self):
        from air_instruments.config import OCTAPAD_LEFT_PADS, OCTAPAD_RIGHT_PADS, OCTAPAD_CORE_PADS
        from air_instruments.instruments.octapad import Octapad

        right = hand_at(0.75)
        left = hand_at(0.25)
        self.assertEqual(order_hands_for_instrument([right, left], "octapad"), [(1, "left"), (0, "right")])
        self.assertEqual(order_hands_for_instrument([hand_at(0.3)], "octapad"), [(0, "left")])

        # Verify pads count and instrument properties
        self.assertEqual(len(OCTAPAD_LEFT_PADS), 5)
        self.assertEqual(len(OCTAPAD_RIGHT_PADS), 5)
        self.assertEqual(len(OCTAPAD_CORE_PADS), 8)
        self.assertEqual(Octapad.key, "octapad")
        self.assertEqual(Octapad.sound_kind, "octapad")


if __name__ == "__main__":
    unittest.main()

