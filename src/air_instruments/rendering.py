"""OpenCV drawing helpers for landmarks and the virtual instruments."""
import cv2

from .config import FINGER_NAMES, PIANO_LEFT_NOTES, PIANO_RIGHT_NOTES, TIP_IDS, TIP_NAMES


def draw_hand_landmarks(frame, points, raised, connections, status_text: str) -> None:
    """Draw the hand skeleton and colour fingertips by UP/DOWN state."""
    for connection in connections:
        cv2.line(frame, points[connection.start], points[connection.end], (0, 200, 0), 2)

    for landmark_id, (x, y) in enumerate(points):
        if landmark_id in TIP_IDS:
            finger_index = TIP_IDS.index(landmark_id)
            color = (60, 230, 60) if raised[finger_index] else (0, 165, 255)
            cv2.circle(frame, (x, y), 9, color, -1)
            cv2.putText(frame, TIP_NAMES[finger_index], (x + 7, y - 7),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
        else:
            cv2.circle(frame, (x, y), 4, (0, 0, 255), -1)

    wrist_x, wrist_y = points[0]
    label_x = max(10, min(wrist_x - 100, frame.shape[1] - 500))
    cv2.putText(frame, status_text, (label_x, max(55, wrist_y - 18)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2, cv2.LINE_AA)


def draw_piano_keyboard(frame, raised_by_side: dict[str, list[bool] | None]) -> None:
    """Draw low and high piano rows; green keys represent a bent finger."""
    height, width = frame.shape[:2]
    left = int(width * 0.05)
    right = int(width * 0.95)
    key_width = (right - left) / 5
    row_top = {"left": int(height * 0.70), "right": int(height * 0.82)}
    row_bottom = {"left": int(height * 0.81), "right": int(height * 0.93)}
    note_sets = {"left": PIANO_LEFT_NOTES, "right": PIANO_RIGHT_NOTES}

    for side in ("left", "right"):
        notes = note_sets[side]
        raised = raised_by_side.get(side)
        top, bottom = row_top[side], row_bottom[side]
        label = "LOW" if side == "left" else "HIGH"
        cv2.putText(frame, f"{label} notes", (left + 5, top - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

        for index, (note_name, _frequency) in enumerate(notes):
            x0 = int(left + index * key_width)
            x1 = int(left + (index + 1) * key_width) - 2
            is_pressed = raised is not None and not raised[index]
            fill = (100, 220, 120) if is_pressed else (245, 245, 245)
            cv2.rectangle(frame, (x0, top), (x1, bottom), fill, -1)
            cv2.rectangle(frame, (x0, top), (x1, bottom), (30, 30, 30), 2)
            label_text = f"{note_name} {FINGER_NAMES[index]}"
            font_scale = 0.45 if width < 900 else 0.55
            text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)[0]
            text_x = x0 + max(3, (x1 - x0 - text_size[0]) // 2)
            text_y = top + (bottom - top + text_size[1]) // 2
            cv2.putText(frame, label_text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX,
                        font_scale, (20, 20, 20), 1, cv2.LINE_AA)


def draw_guitar_neck(frame, notes, raised: list[bool] | None = None) -> None:
    """Draw a simple five-string guitar-style panel."""
    height, width = frame.shape[:2]
    left = int(width * 0.05)
    right = int(width * 0.95)
    top = int(height * 0.69)
    bottom = int(height * 0.95)
    label_width = max(105, int(width * 0.19))
    string_start = left + 15
    string_end = right - label_width

    cv2.rectangle(frame, (left, top), (right, bottom), (48, 34, 26), -1)
    cv2.rectangle(frame, (left, top), (right, bottom), (190, 160, 125), 2)
    cv2.line(frame, (string_start, top + 8), (string_start, bottom - 8), (215, 210, 195), 5)
    for fret in range(1, 5):
        x = string_start + int((string_end - string_start) * fret / 5)
        cv2.line(frame, (x, top + 8), (x, bottom - 8), (135, 112, 92), 2)

    row_gap = (bottom - top - 22) / len(notes)
    for index, (note_name, _frequency) in enumerate(notes):
        y = int(top + 11 + (index + 0.5) * row_gap)
        is_pressed = raised is not None and not raised[index]
        string_color = (80, 245, 120) if is_pressed else (220, 218, 208)
        cv2.line(frame, (string_start, y), (string_end, y), string_color, 4 if is_pressed else 2)
        cv2.circle(frame, (string_start + 23, y), 5, string_color, -1)
        cv2.putText(frame, f"{note_name} {FINGER_NAMES[index]}", (string_end + 12, y + 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (245, 245, 245), 1, cv2.LINE_AA)
