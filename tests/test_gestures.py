"""Dependency-free tests for the image-space thumb settings copied from hand_detection.py."""
import math
import unittest

from air_instruments.gestures import ThumbStateTracker, distance, joint_angle


def thumb_pose(ip_angle: float, spread_ratio: float):
    """Make landmarks with a specified thumb IP angle and thumb-tip spread."""
    points = [(0.0, 0.0) for _ in range(21)]

    # 2-3 is the thumb middle segment; make it 60 pixels long and horizontal.
    points[2] = (100.0, 100.0)
    points[3] = (160.0, 100.0)
    direction = math.radians(180.0 - ip_angle)
    points[4] = (
        points[3][0] + 60.0 * math.cos(direction),
        points[3][1] + 60.0 * math.sin(direction),
    )

    # Define a 100 px palm width and independent normalized tip spread.
    points[5] = (points[4][0] - spread_ratio * 100.0, points[4][1])
    points[17] = (points[5][0] - 100.0, points[5][1])
    # Other fingertips are placed above their PIP joints for completeness.
    for tip_id, pip_id, x in ((8, 6, 220), (12, 10, 240), (16, 14, 260), (20, 18, 280)):
        points[pip_id] = (x, 150.0)
        points[tip_id] = (x, 120.0)
    return points


class GestureGeometryTests(unittest.TestCase):
    def test_distance(self):
        self.assertAlmostEqual(distance((0, 0), (3, 4)), 5.0)

    def test_straight_angle(self):
        self.assertAlmostEqual(joint_angle((0, 0), (1, 0), (2, 0)), 180.0)

    def test_right_angle(self):
        self.assertAlmostEqual(joint_angle((1, 0), (0, 0), (0, 1)), 90.0)

    def test_thumb_starts_down_then_enters_up(self):
        tracker = ThumbStateTracker()
        straight = thumb_pose(160, 0.50)
        for _ in range(5):
            tracker.update(straight)
        self.assertTrue(tracker.is_up)

    def test_mild_bend_does_not_immediately_release_thumb(self):
        tracker = ThumbStateTracker()
        straight = thumb_pose(160, 0.50)
        for _ in range(5):
            tracker.update(straight)
        self.assertTrue(tracker.is_up)

        mildly_bent = thumb_pose(115, 0.25)
        for _ in range(4):
            tracker.update(mildly_bent)
        self.assertTrue(tracker.is_up)

    def test_deep_fold_moves_thumb_down(self):
        tracker = ThumbStateTracker()
        straight = thumb_pose(160, 0.50)
        folded = thumb_pose(85, 0.10)
        for _ in range(5):
            tracker.update(straight)
        self.assertTrue(tracker.is_up)
        for _ in range(5):
            tracker.update(folded)
        self.assertFalse(tracker.is_up)

    def test_thumb_can_be_straightened_again(self):
        tracker = ThumbStateTracker()
        straight = thumb_pose(160, 0.50)
        folded = thumb_pose(85, 0.10)
        for _ in range(5):
            tracker.update(straight)
        for _ in range(5):
            tracker.update(folded)
        self.assertFalse(tracker.is_up)
        for _ in range(5):
            tracker.update(straight)
        self.assertTrue(tracker.is_up)



if __name__ == "__main__":
    unittest.main()
