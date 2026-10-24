"""WebSocket signaling server for the browser-based two-player mode."""
import argparse
import asyncio
import base64
import json
import logging
import secrets
from pathlib import Path
from aiohttp import web, WSMsgType

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOMS = {}
PEER_ROOMS = {}
PEER_TRACKERS = {}
PEER_TRACKER_ERRORS = {}


def order_hands_for_instrument(hand_landmarks, instrument):
    """Return (landmark_index, slot) pairs for the selected browser instrument.

    Piano assigns the two hands by wrist x-position, while one visible hand is
    assigned to the side it occupies. Guitar intentionally consumes one hand.
    This helper is pure so its slot rules can be unit-tested without a camera.
    """
    if not hand_landmarks:
        return []
    if instrument == "guitar":
        return [(0, "guitar")]

    ordered = sorted(
        enumerate(hand_landmarks),
        key=lambda item: float(item[1][0].x),
    )
    if len(ordered) >= 2:
        return [(ordered[0][0], "left"), (ordered[-1][0], "right")]
    index, hand = ordered[0]
    slot = "left" if float(hand[0].x) < 0.5 else "right"
    return [(index, slot)]

def process_tracking_frame(peer_id, frame_data, instrument="piano"):
    """Run the project's Python MediaPipe hand tracker on one JPEG camera frame.

    MediaPipe is loaded lazily so a missing optional dependency doesn't prevent
    the video room itself from working. Tracker/model failures are reported to
    the originating browser by the websocket handler.
    """
    if not isinstance(frame_data, str) or ',' not in frame_data:
        return None
    header, encoded = frame_data.split(',', 1)
    if not header.startswith('data:image/') or len(encoded) > 900_000:
        return None

    import cv2
    import numpy as np

    raw = base64.b64decode(encoded, validate=False)
    frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return None
    frame_h, frame_w = frame.shape[:2]

    state = PEER_TRACKERS.get(peer_id)
    if state is None:
        from air_instruments.tracking import HandTrackingEngine
        from air_instruments.gestures import ThumbStateTracker, count_raised_fingers

        state = {
            'engine': HandTrackingEngine(max_hands=2),
            'thumb_trackers': {
                'left': ThumbStateTracker(),
                'right': ThumbStateTracker(),
                'guitar': ThumbStateTracker(),
            },
            'count_raised_fingers': count_raised_fingers,
        }
        PEER_TRACKERS[peer_id] = state

    if instrument not in ("guitar", "octapad"):
        instrument = "piano"
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = state['engine'].detect(rgb)
    detections = list(result.hand_landmarks or [])
    ordered = order_hands_for_instrument(detections, instrument)
    all_landmarks = []
    hands = []
    slots = []
    for tracker_index, (landmark_index, slot) in enumerate(ordered):
        hand = detections[landmark_index]
        normalized = [{'x': float(point.x), 'y': float(point.y)} for point in hand]
        pixel_points = [(float(point.x) * frame_w, float(point.y) * frame_h) for point in hand]
        all_landmarks.append(normalized)
        hands.append(state['count_raised_fingers'](pixel_points, state['thumb_trackers'][slot]))
        slots.append(slot)
    return {'hands': hands, 'landmarks': all_landmarks, 'handCount': len(hands), 'slots': slots, 'instrument': instrument}


def close_peer_tracker(peer_id):
    state = PEER_TRACKERS.pop(peer_id, None)
    PEER_TRACKER_ERRORS.pop(peer_id, None)
    if state:
        try:
            state['engine'].close()
        except Exception:
            logging.exception('Failed to close tracker for peer %s', peer_id)

async def index(request):
    return web.FileResponse(PROJECT_ROOT / "web" / "index.html")

async def static_file(request):
    name = request.match_info["name"]
    allowed = {"client.js", "style.css"}
    if name not in allowed:
        raise web.HTTPNotFound()
    return web.FileResponse(PROJECT_ROOT / "web" / name)

async def model_file(request):
    path = PROJECT_ROOT / "assets" / "models" / "hand_landmarker.task"
    if not path.exists():
        raise web.HTTPNotFound(text="MediaPipe model missing. Run the desktop app once or download the model.")
    return web.FileResponse(path)

async def websocket_handler(request):
    ws = web.WebSocketResponse(heartbeat=25, max_msg_size=1_000_000)
    await ws.prepare(request)
    peer_id = secrets.token_hex(6)
    room_code = None
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                if msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                    break
                continue
            try:
                data = json.loads(msg.data)
            except json.JSONDecodeError:
                continue
            kind = data.get("type")
            if kind == "join":
                room_code = str(data.get("room", "")).strip().upper()[:32]
                if not room_code or len(room_code) < 3:
                    await ws.send_json({"type": "error", "message": "Room code must be at least 3 characters."})
                    room_code = None
                    continue
                peers = ROOMS.setdefault(room_code, {})
                if len(peers) >= 2:
                    await ws.send_json({"type": "error", "message": "This room already has two players."})
                    room_code = None
                    continue
                existing = list(peers.items())
                peers[peer_id] = ws
                PEER_ROOMS[peer_id] = room_code
                await ws.send_json({"type": "joined", "peer_id": peer_id, "room": room_code, "players": len(peers)})
                if existing:
                    other_id, other_ws = existing[0]
                    await ws.send_json({"type": "peer-available", "peer_id": other_id, "initiator": True})
                    await other_ws.send_json({"type": "peer-available", "peer_id": peer_id, "initiator": False})
                continue
            if room_code and kind == "frame":
                if peer_id in PEER_TRACKER_ERRORS:
                    continue
                try:
                    instrument = "guitar" if data.get("instrument") == "guitar" else "piano"
                    tracking_result = await asyncio.to_thread(process_tracking_frame, peer_id, data.get("frame"), instrument)
                    if tracking_result is None:
                        continue
                    await ws.send_json({"type": "tracked-result", **tracking_result})
                    for other_id, other_ws in list(ROOMS.get(room_code, {}).items()):
                        if other_id != peer_id and not other_ws.closed:
                            await other_ws.send_json({
                                "type": "gesture",
                                "from": peer_id,
                                "hands": tracking_result["hands"],
                                "handCount": tracking_result["handCount"],
                                "slots": tracking_result["slots"],
                                "instrument": tracking_result["instrument"],
                            })
                except Exception as exc:
                    message = f"{type(exc).__name__}: {exc}"
                    PEER_TRACKER_ERRORS[peer_id] = message
                    logging.exception("Python hand tracker failed for peer %s", peer_id)
                    await ws.send_json({"type": "tracker-error", "message": message})
                continue
            if room_code and kind in {"offer", "answer", "ice", "gesture", "peer-state"}:
                for other_id, other_ws in list(ROOMS.get(room_code, {}).items()):
                    if other_id != peer_id and not other_ws.closed:
                        forwarded = dict(data)
                        forwarded["from"] = peer_id
                        await other_ws.send_json(forwarded)
    finally:
        close_peer_tracker(peer_id)
        if room_code:
            peers = ROOMS.get(room_code, {})
            peers.pop(peer_id, None)
            if not peers:
                ROOMS.pop(room_code, None)
            else:
                for other_ws in peers.values():
                    if not other_ws.closed:
                        await other_ws.send_json({"type": "peer-left"})
        PEER_ROOMS.pop(peer_id, None)
    return ws

def create_app():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/ws", websocket_handler)
    app.router.add_get("/static/{name}", static_file)
    app.router.add_get("/assets/models/hand_landmarker.task", model_file)
    return app

def main():
    parser = argparse.ArgumentParser(description="Air Instruments multiplayer signaling server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    print(f"Air Instruments multiplayer server: http://localhost:{args.port}")
    print("Same Wi-Fi: players can open http://<host-LAN-IP>:%d on their laptops." % args.port)
    web.run_app(create_app(), host=args.host, port=args.port)

if __name__ == "__main__":
    main()
