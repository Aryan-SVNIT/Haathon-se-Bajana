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
        label = "LEFT HAND" if side == "left" else "RIGHT HAND"
        cv2.putText(frame, f"{label} (5 Chords)", (left + 5, top - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

        for index, note_item in enumerate(notes):
            note_name = note_item[0]
            x0 = int(left + index * key_width)
            x1 = int(left + (index + 1) * key_width) - 2
            is_pressed = raised is not None and not raised[index]
            fill = (100, 220, 120) if is_pressed else (245, 245, 245)
            cv2.rectangle(frame, (x0, top), (x1, bottom), fill, -1)
            cv2.rectangle(frame, (x0, top), (x1, bottom), (30, 30, 30), 2)
            label_text = f"{note_name} ({TIP_NAMES[index]})"
            font_scale = 0.38 if width < 900 else 0.46
            text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)[0]
            text_x = x0 + max(2, (x1 - x0 - text_size[0]) // 2)
            text_y = top + (bottom - top + text_size[1]) // 2
            cv2.putText(frame, label_text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX,
                        font_scale, (20, 20, 20), 1, cv2.LINE_AA)


def draw_guitar_neck(frame, notes, raised: list[bool] | None = None, thumb_is_up: bool = True) -> None:
    """Draw a four-string guitar neck with Thumb Major/Minor switch status."""
    height, width = frame.shape[:2]
    left = int(width * 0.05)
    right = int(width * 0.95)
    top = int(height * 0.68)
    bottom = int(height * 0.96)
    label_width = max(115, int(width * 0.22))
    string_start = left + 15
    string_end = right - label_width

    # Guitar fretboard body
    cv2.rectangle(frame, (left, top), (right, bottom), (44, 32, 24), -1)
    cv2.rectangle(frame, (left, top), (right, bottom), (190, 160, 125), 2)

    # Mode switch status badge above the neck
    mode_text = "THUMB UP -> [MAJOR MODE]" if thumb_is_up else "THUMB DOWN -> [MINOR MODE]"
    mode_color = (80, 245, 120) if thumb_is_up else (50, 165, 255)
    cv2.putText(frame, mode_text, (left + 10, top - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, mode_color, 2, cv2.LINE_AA)

    # Guitar nut and fret wires
    cv2.line(frame, (string_start, top + 8), (string_start, bottom - 8), (215, 210, 195), 5)
    for fret in range(1, 5):
        x = string_start + int((string_end - string_start) * fret / 5)
        cv2.line(frame, (x, top + 8), (x, bottom - 8), (135, 112, 92), 2)

    row_gap = (bottom - top - 20) / len(notes)
    for index, note_item in enumerate(notes):
        note_name = note_item[0]
        y = int(top + 10 + (index + 0.5) * row_gap)
        # In 4-string mode, strings 0..3 map to fingers 1..4 (Index, Middle, Ring, Pinky)
        finger_idx = index + 1 if len(notes) == 4 else index
        is_pressed = raised is not None and not raised[finger_idx]
        string_color = (80, 245, 120) if is_pressed else (220, 218, 208)

        # Draw glowing string when plucked
        cv2.line(frame, (string_start, y), (string_end, y), string_color, 4 if is_pressed else 2)
        cv2.circle(frame, (string_start + 22, y), 5, string_color, -1)

        # String label showing note name and finger
        finger_name = FINGER_NAMES[finger_idx]
        label_text = f"{note_name} ({finger_name})"
        cv2.putText(frame, label_text, (string_end + 10, y + 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (245, 245, 245), 1, cv2.LINE_AA)


def draw_octapad(frame, raised_by_slot: dict, single_hand_thumb_up: bool = True) -> None:
    """Draw an authentic 8-pad electronic percussion console (Roland Octapad layout).
    
    Layout: 2 rows of 4 pads.
    Bank A (Left 4 pads):  [1: Kick]   [2: Snare]   |  Bank B (Right 4 pads): [5: Low Tom]  [6: High Tom]
                           [3: Hi-Hat] [4: Open HH] |                         [7: Crash]    [8: Clap]
    """
    height, width = frame.shape[:2]
    console_left = int(width * 0.04)
    console_right = int(width * 0.96)
    console_top = int(height * 0.63)
    console_bottom = int(height * 0.97)

    # Dark chassis with neon purple/blue rim
    cv2.rectangle(frame, (console_left, console_top), (console_right, console_bottom), (24, 20, 32), -1)
    cv2.rectangle(frame, (console_left, console_top), (console_right, console_bottom), (160, 90, 240), 2)

    # Determine which hands are active
    left_raised = raised_by_slot.get("left")
    right_raised = raised_by_slot.get("right")
    octapad_raised = raised_by_slot.get("octapad")

    two_hands_mode = left_raised is not None and right_raised is not None
    single_hand = octapad_raised if octapad_raised is not None else (left_raised or right_raised)

    # Status header
    if two_hands_mode:
        badge_text = "OCTAPAD | 2 HANDS [LEFT: PADS 1-4 · RIGHT: PADS 5-8]"
        badge_color = (80, 245, 120)
    elif single_hand is not None:
        bank_name = "BANK A (PADS 1-4)" if single_hand_thumb_up else "BANK B (PADS 5-8)"
        thumb_desc = "Thumb UP" if single_hand_thumb_up else "Thumb DOWN"
        badge_text = f"OCTAPAD | 1 HAND [{bank_name} active via {thumb_desc}]"
        badge_color = (80, 245, 120) if single_hand_thumb_up else (50, 165, 255)
    else:
        badge_text = "OCTAPAD | READY (Show 1 or 2 hands to trigger pads)"
        badge_color = (200, 200, 220)

    cv2.putText(frame, badge_text, (console_left + 12, console_top - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, badge_color, 2, cv2.LINE_AA)

    # 8 Pads definitions: (pad_num, name, row, col, bank, finger_idx)
    # col: 0, 1, 2, 3 ; row: 0 (top), 1 (bottom)
    pads = [
        (1, "KICK", 0, 0, "A", 1, "IDX"),
        (2, "SNARE", 0, 1, "A", 2, "MID"),
        (3, "HI-HAT", 1, 0, "A", 3, "RNG"),
        (4, "OPEN HH", 1, 1, "A", 4, "PNK"),
        (5, "LOW TOM", 0, 2, "B", 1, "IDX"),
        (6, "HIGH TOM", 0, 3, "B", 2, "MID"),
        (7, "CRASH", 1, 2, "B", 3, "RNG"),
        (8, "CLAP", 1, 3, "B", 4, "PNK"),
    ]

    pad_margin = 6
    inner_w = console_right - console_left - 16
    inner_h = console_bottom - console_top - 16
    col_w = inner_w / 4.0
    row_h = inner_h / 2.0

    # Draw center divider between Bank A and Bank B
    center_x = int(console_left + 8 + 2 * col_w)
    cv2.line(frame, (center_x, console_top + 6), (center_x, console_bottom - 6), (110, 80, 140), 2)

    for pad_num, pad_name, row, col, bank, finger_idx, finger_label in pads:
        x0 = int(console_left + 8 + col * col_w + pad_margin)
        x1 = int(console_left + 8 + (col + 1) * col_w - pad_margin)
        y0 = int(console_top + 8 + row * row_h + pad_margin)
        y1 = int(console_top + 8 + (row + 1) * row_h - pad_margin)

        # Check if pad is pressed / triggered
        is_hit = False
        if two_hands_mode:
            target_raised = left_raised if bank == "A" else right_raised
            if target_raised and not target_raised[finger_idx]:
                is_hit = True
        elif single_hand is not None:
            # In single hand mode, thumb UP = Bank A, thumb DOWN = Bank B
            hand_in_this_bank = (bank == "A" and single_hand_thumb_up) or (bank == "B" and not single_hand_thumb_up)
            if hand_in_this_bank and not single_hand[finger_idx]:
                is_hit = True

        # Pad styling: glowing neon when hit, sleek rubber pad when idle
        if is_hit:
            pad_bg = (80, 245, 120) if bank == "A" else (255, 130, 210)
            pad_border = (255, 255, 255)
            text_color = (15, 15, 15)
        else:
            pad_bg = (48, 42, 60) if bank == "A" else (40, 48, 62)
            pad_border = (130, 100, 175) if bank == "A" else (100, 130, 185)
            text_color = (240, 240, 250)

        cv2.rectangle(frame, (x0, y0), (x1, y1), pad_bg, -1)
        cv2.rectangle(frame, (x0, y0), (x1, y1), pad_border, 2)

        # Pad header: e.g. "PAD 1 [L-IDX]"
        hand_prefix = "L" if bank == "A" else "R"
        corner_label = f"P{pad_num} [{hand_prefix}-{finger_label}]"
        cv2.putText(frame, corner_label, (x0 + 6, y0 + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, text_color, 1, cv2.LINE_AA)

        # Pad instrument name: e.g. "KICK"
        font_scale = 0.52 if width >= 640 else 0.42
        text_size = cv2.getTextSize(pad_name, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0]
        text_x = x0 + max(2, (x1 - x0 - text_size[0]) // 2)
        text_y = y0 + (y1 - y0 + text_size[1]) // 2 + 6
        cv2.putText(frame, pad_name, (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 2, cv2.LINE_AA)

