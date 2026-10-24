"""Optional camera/landmark test, using the same shared tracking components."""
import cv2

from .gestures import ThumbStateTracker, count_raised_fingers
from .rendering import draw_hand_landmarks
from .tracking import HandTrackingEngine, open_camera


def run_tracking_test() -> None:
    """Open the webcam and show tracked hands/fingertips without playing sound."""
    camera = None
    trackers = {}
    try:
        with HandTrackingEngine(max_hands=2) as tracker:
            camera = open_camera()
            print("Hand-tracking test started. Show one or two hands. Press Q to quit.")
            while True:
                ok, frame = camera.read()
                if not ok:
                    print("Could not read a webcam frame.")
                    break
                frame = cv2.flip(frame, 1)
                height, width = frame.shape[:2]
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = tracker.detect(frame_rgb)
                seen = set()

                for hand_index, landmarks in enumerate(result.hand_landmarks):
                    points = [(int(p.x * width), int(p.y * height)) for p in landmarks]
                    slot = "left" if points[0][0] < width / 2 else "right"
                    if slot in seen:
                        slot = f"hand-{hand_index}"
                    seen.add(slot)
                    trackers.setdefault(slot, ThumbStateTracker())
                    raised = count_raised_fingers(points, trackers[slot])
                    label = (
                        f"{slot}: {sum(raised)}/5 | {trackers[slot].debug_label}"
                    )
                    draw_hand_landmarks(frame, points, raised, tracker.connections, label)

                for slot in list(trackers):
                    if slot not in seen:
                        trackers.pop(slot, None)

                cv2.putText(frame, f"Hands detected: {len(result.hand_landmarks)}/2 | Q = quit",
                            (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, "Tip labels: T=Thumb I=Index M=Middle R=Ring P=Pinky",
                            (15, height - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                            (255, 255, 255), 1, cv2.LINE_AA)
                cv2.imshow("Air Instruments | Tracking Test", frame)
                if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
                    break
    finally:
        if camera is not None:
            camera.release()
        cv2.destroyAllWindows()
