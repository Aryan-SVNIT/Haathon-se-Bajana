"""Main application loop that connects the menu, tracker, gestures, audio, and UI."""
import cv2
import pygame

from .audio import create_note_sounds, initialize_audio
from .gestures import ThumbStateTracker, count_raised_fingers
from .instruments.guitar import Guitar
from .instruments.octapad import Octapad
from .instruments.piano import Piano
from .menu import choose_instrument
from .rendering import draw_hand_landmarks
from .tracking import HandTrackingEngine, open_camera


def _points_from_landmarks(landmarks, width: int, height: int):
    """Convert normalized MediaPipe image landmarks into pixel coordinates."""
    return [(int(point.x * width), int(point.y * height)) for point in landmarks]


def _assign_hands(result, width: int, height: int, instrument):
    """Return (slot, image landmarks, pixel points) for the selected instrument."""
    detections = []
    for landmarks in result.hand_landmarks:
        points = _points_from_landmarks(landmarks, width, height)
        detections.append((landmarks, points))

    if instrument.key == "guitar":
        if not detections:
            return []
        landmarks, points = detections[0]
        return [("guitar", landmarks, points)]

    if len(detections) >= 2:
        detections.sort(key=lambda item: item[1][0][0])  # wrist x-coordinate
        left_hand = detections[0]
        right_hand = detections[-1]
        return [
            ("left", left_hand[0], left_hand[1]),
            ("right", right_hand[0], right_hand[1]),
        ]

    if len(detections) == 1:
        landmarks, points = detections[0]
        side = "left" if points[0][0] < width / 2 else "right"
        return [(side, landmarks, points)]

    return []


def _run_selected_instrument(instrument) -> None:
    """Start the selected instrument and run its webcam interaction loop."""
    initialize_audio()
    note_sounds = create_note_sounds(instrument.notes_by_slot, instrument.sound_kind)
    thumb_trackers = {slot: ThumbStateTracker() for slot in instrument.hand_slots}
    previous_raised = {slot: None for slot in instrument.hand_slots}
    window_title = f"Air {instrument.display_name} | Hand Gesture Instrument"

    camera = None
    try:
        with HandTrackingEngine(max_hands=instrument.max_hands) as tracker:
            camera = open_camera()
            print(f"Selected instrument: {instrument.display_name}")
            print(instrument.instruction_text())
            print("Bend a finger to play its note; straighten it to re-arm. Press Q to quit.")

            while True:
                ok, frame = camera.read()
                if not ok:
                    print("Could not read a webcam frame. Check that the camera is connected.")
                    break

                # Mirror the video to behave like a selfie view.
                frame = cv2.flip(frame, 1)
                height, width = frame.shape[:2]
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = tracker.detect(frame_rgb)

                hands_to_process = _assign_hands(result, width, height, instrument)
                raised_by_slot = {slot: None for slot in instrument.hand_slots}
                seen_slots = set()

                for slot, _landmarks, points in hands_to_process:
                    seen_slots.add(slot)
                    raised = count_raised_fingers(points, thumb_trackers[slot])
                    raised_by_slot[slot] = raised

                    # Play only on a fresh UP -> BENT transition. This avoids replaying
                    # a note every video frame while a finger remains bent.
                    old_state = previous_raised[slot]
                    if old_state is not None:
                        if instrument.key == "guitar":
                            thumb_is_up = bool(raised[0])
                            # In guitar mode, thumb is the Major/Minor mode switch.
                            # The 4 playable fingers are Index (1), Middle (2), Ring (3), Pinky (4).
                            sound_group = "guitar_major" if thumb_is_up else "guitar_minor"
                            for finger_index in range(1, 5):
                                note_index = finger_index - 1
                                if old_state[finger_index] and not raised[finger_index]:
                                    note_sounds[sound_group][note_index].play()
                        elif instrument.key == "octapad":
                            is_single_hand = len(hands_to_process) == 1
                            thumb_is_up = bool(raised[0])
                            # In 1-hand mode: thumb UP = Bank A (left), thumb DOWN = Bank B (right)
                            target_slot = ("left" if thumb_is_up else "right") if is_single_hand else slot
                            for finger_index in range(1, 5):
                                if old_state[finger_index] and not raised[finger_index]:
                                    note_sounds[target_slot][finger_index].play()
                            # In 2-hand mode: thumb 0 triggers Cowbell (left) or Ride (right)
                            if not is_single_hand and old_state[0] and not raised[0]:
                                note_sounds[slot][0].play()
                        else:
                            for finger_index, is_up in enumerate(raised):
                                if old_state[finger_index] and not is_up:
                                    note_sounds[slot][finger_index].play()
                    previous_raised[slot] = raised.copy()

                    if instrument.key == "octapad":
                        is_single = len(hands_to_process) == 1
                        if is_single:
                            bank_str = "BANK A (Kick/Snare/HH)" if raised[0] else "BANK B (Toms/Crash/Clap)"
                            hand_label = f"OCTAPAD [{bank_str}]: {sum(raised[1:])}/4 pads | {thumb_trackers[slot].debug_label}"
                        else:
                            bank_str = "BANK A (Rhythm)" if slot == "left" else "BANK B (Fills)"
                            hand_label = f"OCTAPAD [{bank_str}]: {sum(raised)}/5 pads | {thumb_trackers[slot].debug_label}"
                    elif slot == "left":
                        hand_label = f"LOW / LEFT: {sum(raised)}/5 | {thumb_trackers[slot].debug_label}"
                    elif slot == "right":
                        hand_label = f"HIGH / RIGHT: {sum(raised)}/5 | {thumb_trackers[slot].debug_label}"
                    else:
                        mode_str = "MAJOR" if raised[0] else "MINOR"
                        hand_label = f"GUITAR [{mode_str}]: {sum(raised[1:])}/4 strings | {thumb_trackers[slot].debug_label}"
                    draw_hand_landmarks(frame, points, raised, tracker.connections, hand_label)

                # If a hand disappears, reset its edge-detection state.
                for slot in instrument.hand_slots:
                    if slot not in seen_slots:
                        previous_raised[slot] = None
                        thumb_trackers[slot] = ThumbStateTracker()

                if instrument.key == "guitar":
                    thumb_up = True if raised_by_slot.get("guitar") is None else bool(raised_by_slot["guitar"][0])
                    status_text = instrument.status_text(len(result.hand_landmarks), thumb_up)
                    instrument.draw(frame, raised_by_slot)
                elif instrument.key == "octapad":
                    active_raised = raised_by_slot.get("left") or raised_by_slot.get("right")
                    thumb_up = True if active_raised is None else bool(active_raised[0])
                    status_text = instrument.status_text(len(result.hand_landmarks), thumb_up)
                    instrument.draw(frame, raised_by_slot, single_hand_thumb_up=thumb_up)
                else:
                    status_text = instrument.status_text(len(result.hand_landmarks))
                    instrument.draw(frame, raised_by_slot)

                cv2.putText(frame, status_text,
                            (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.68,
                            (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, instrument.instruction_text(),
                            (15, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.47,
                            (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(frame, "Bend finger = play | Straighten = ready again | Q = quit",
                            (15, height - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                            (255, 255, 255), 1, cv2.LINE_AA)
                cv2.imshow(window_title, frame)
                if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
                    break
    finally:
        if camera is not None:
            camera.release()
        cv2.destroyAllWindows()


def main() -> None:
    """Show the instrument chooser, then launch exactly the selected instrument."""
    try:
        selected = choose_instrument()
        if selected is None:
            print("No instrument selected. Exiting.")
            return
        if selected == "piano":
            instrument = Piano()
        elif selected == "guitar":
            instrument = Guitar()
        else:
            instrument = Octapad()
        _run_selected_instrument(instrument)
    finally:
        pygame.quit()

