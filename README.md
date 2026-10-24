# Air Instruments — Hand-Gesture Piano & Guitar

A Windows-friendly Python project that uses a webcam to track hand gestures and play virtual instrument notes. At launch, choose **PIANO** or **GUITAR**. The selected instrument alone starts.

## Features

- **Piano mode:** tracks up to **two hands** simultaneously. The hand on the left side of the mirrored webcam view plays lower notes (C3–G3); the hand on the right side plays higher notes (C4–G4). This provides 10 gesture-mapped notes.
- **Guitar mode:** tracks **one hand** and maps five fingers to five guitar-register notes.
- MediaPipe's 21 hand landmarks identify fingertips and joints.
- Thumb detection now uses the same image-space IP angle + normalized thumb-tip spread rule as the provided working `hand_detection.py`. The MCP/world-angle experiment has been removed from the active classification path. Different UP/DOWN thresholds and five-frame voting reduce flicker; the webcam overlay shows IP angle, spread ratio, candidate state and vote count.
- A note plays on the transition from a finger being UP to being BENT. Straighten it to re-arm that note; holding a bent finger does not retrigger the sound every frame.
- Notes are synthesized locally. The guitar tone is a plucked-string-style approximation, not a recorded guitar sample.
- A separate tracking test helps debug the webcam without starting instrument audio.

## Project structure

```text
Air_Instruments_Project/
├── run.py                         # One entry point for the whole project
├── requirements.txt               # Python dependencies
├── README.md                      # Setup and usage documentation
├── .gitignore
├── assets/
│   └── models/                    # MediaPipe model downloads here automatically
├── src/
│   └── air_instruments/
│       ├── app.py                 # Main application flow
│       ├── audio.py               # Sound synthesis and audio setup
│       ├── config.py              # Notes, finger IDs, and paths
│       ├── diagnostics.py         # Optional tracking-only test mode
│       ├── gestures.py            # Raised-finger and thumb logic
│       ├── menu.py                # Piano/Guitar selection GUI
│       ├── model.py               # First-run model download
│       ├── rendering.py           # Webcam overlays and virtual instruments
│       ├── tracking.py            # Shared MediaPipe and webcam interface
│       └── instruments/
│           ├── piano.py           # Two-hand piano settings
│           └── guitar.py          # One-hand guitar settings
└── tests/
    └── test_gestures.py           # Small geometry tests
```

The source is separated by responsibility. Do not make another copy of the tracker for each instrument: Piano and Guitar both use the shared `tracking.py` and `gestures.py` modules.

## Requirements

- Windows 10/11, 64-bit
- Recommended: Python 3.11 (64-bit)
- A working webcam and audio output device
- Internet for the first run only, to download `hand_landmarker.task`

## Setup on Windows / PowerShell

Open this project folder in VS Code. In the terminal, run:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, run this for the current terminal only, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

If `py -3.11` is unavailable, use `py -0p` to list installed Python versions and choose a supported 64-bit Python interpreter.

## Run the app

```powershell
python run.py
```

Click **PIANO** or **GUITAR** in the startup window. Keyboard shortcuts in the chooser: `P` selects Piano, `G` selects Guitar, and `Q` or `Esc` closes it. After the webcam opens, press `Q` to exit.

### Piano controls

1. Show both hands, palms facing the camera, with fingers visible.
2. Spread the hands apart in the mirrored camera view.
3. The screen-left hand maps to C3, D3, E3, F3, G3; the screen-right hand maps to C4, D4, E4, F4, G4.
4. Bend a finger to trigger its note. Straighten the finger to arm it for the next press.

The mapping uses screen position, so if only one hand is visible it controls the row nearest its side of the frame. For most reliable two-hand playing, keep one hand on each side of the image. Thumb detection follows the working `hand_detection.py` prototype: image-space IP joint angle, normalized thumb-tip spread, asymmetric UP/DOWN thresholds, and five-frame voting. The thumb starts DOWN; hold it clearly straight for several frames to arm it. A slight bend should not switch it off; a strong bend sustained for several frames triggers its note.

### Guitar controls

Guitar mode intentionally limits detection to one hand. Thumb, index, middle, ring, and pinky map to E3, A3, D4, G4, and B4 respectively. Bend a finger to pluck its mapped note.

## Test hand tracking without sound

```powershell
python run.py --test-tracking
```

This test shows landmarks for up to two hands and does not launch the instrument selector or play notes.

## Thumb detection tuning

Thumb thresholds live near the top of `src/air_instruments/config.py`:

- `THUMB_UP_ANGLE_DEG = 125` and `THUMB_UP_SPREAD_RATIO = 0.30`: both must pass to enter UP.
- `THUMB_DOWN_ANGLE_DEG = 105` and `THUMB_DOWN_SPREAD_RATIO = 0.20`: while already UP, small bends are tolerated; the thumb is a DOWN candidate only when either signal falls below its release threshold.
- `THUMB_STABLE_FRAMES = 5`, `THUMB_UP_VOTES_REQUIRED = 3`, and `THUMB_RELEASE_MAX_UP_VOTES = 1` smooth noisy frames.

During use, the hand label shows `IP`, normalized spread (`SP`), the raw candidate (`C`), and vote count (`V`). Open `python run.py --test-tracking` to tune tracking without sound. These are initial thresholds; hand orientation and camera angle still affect image-space measurements.

## Troubleshooting

- **Model download fails:** check internet access and rerun `python run.py`. The model downloads into `assets/models/`.
- **Camera cannot open:** close apps that may be using the webcam and allow camera access in Windows Settings → Privacy & security → Camera.
- **No camera permission prompt:** press **Join room** (permission is intentionally requested only after this click). If the status stays at “Ready to connect”, hard-refresh with Ctrl+F5. If permission was blocked earlier, click the site/info icon beside `http://localhost:8080`, open Site settings, set Camera to Allow, and reload.
- **No sound:** check Windows output volume and that an audio output device is connected; rerun after selecting an instrument.
- **Fingers are misclassified:** keep your palm facing the camera, fingers inside the frame, and your hand reasonably upright. Finger pose detection is geometric, so extreme angles can reduce accuracy.
- **Install errors:** use the project's `.venv` and do not mix it with unrelated system/Conda environments. The requirements intentionally avoid OpenCV 5 and NumPy 2 to stay within a broadly compatible setup.

## Tests

With the dependencies installed and this project folder open:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```

The tests cover image-space geometry and thumb-state transitions with synthetic poses based on the same algorithm as `hand_detection.py`. A successful unit test run does not replace testing with your actual webcam and hand pose.


## Two-player multiplayer webcam mode (new)

This adds a browser-based multiplayer mode without changing the existing desktop Piano/Guitar modes. Each player opens the same room code in a browser. The video streams are shared over WebRTC. For hand tracking, each browser sends small compressed webcam frames to the Python WebSocket server; the server runs the existing MediaPipe Python tracker and forwards detected finger states, hand slots, and each player's selected instrument to the other player. The browser synthesizes notes locally with the Web Audio API, so no microphone audio is sent. This avoids requiring a browser-accessible third-party CDN for the tracker.

### Start the server

Install the updated dependencies in the project's Python 3.11 environment:

```powershell
python -m pip install -r requirements.txt
python run.py --multiplayer --host 0.0.0.0 --port 8080
```

The command-line flags above are passed to the multiplayer server. Open `http://localhost:8080` on the host laptop. On a second laptop, use a **secure HTTPS URL** for the browser camera (browsers generally block `getUserMedia()` on another machine over plain HTTP). For same-machine smoke testing, `http://localhost:8080` is allowed. For two laptops, deploy behind HTTPS or configure TLS for the server, then both players open the same HTTPS URL, allow camera access, and enter the same room code. If Windows Firewall prompts, allow Python on the private network.

### Notes / limitations

- The multiplayer browser mode now maps UP → BENT finger transitions to the same piano/guitar note layout as the desktop app. Each browser synthesizes incoming local and remote gesture notes, so both players hear the same gestures. This is synthesized browser audio, not the desktop Pygame audio engine and not a recording of a real instrument.
- Piano: the hand on the left side of the camera frame plays C3–G3, and the hand on the right plays C4–G4. Guitar uses one visible hand and maps thumb/index/middle/ring/pinky to E3/A3/D4/G4/B4.
- There is not yet a shared song timeline, scoring, or recording feature. Notes are triggered from tracked gesture state updates, so timing depends on the webcam frame rate, server latency, and network.
- The signaling server pairs up to two clients per room. WebRTC uses a public STUN server; some restrictive networks require a TURN server.
- Browser webcam access is allowed on `localhost` or HTTPS. For a second laptop on plain HTTP over a LAN, some browsers may block camera access because it is not a secure context. If that happens, use HTTPS (recommended for cross-device use) or test locally on each device with a secure deployment.
- The Python server uses the bundled `assets/models/hand_landmarker.task` model. Once Python dependencies and the model are installed, no browser MediaPipe CDN is needed.
- The browser's thumb display uses a per-frame threshold for responsive feedback; the original desktop app retains the existing stable five-frame voting and hysteresis algorithm.


### Multiplayer hand tracking troubleshooting

The multiplayer browser no longer downloads `@mediapipe/tasks-vision` from a CDN. Instead, it sends a compressed low-resolution frame over the room WebSocket and the Python server processes it with the same `HandTrackingEngine` used by the desktop app. The Python environment running `python run.py --multiplayer` must have the dependencies from `requirements.txt` installed and the local `assets/models/hand_landmarker.task` file present. If tracking fails, the local video panel shows the Python exception; the server terminal also logs its traceback.
