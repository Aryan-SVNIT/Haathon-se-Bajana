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


if __name__ == "__main__":
    unittest.main()
