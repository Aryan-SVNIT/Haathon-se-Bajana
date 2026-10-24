"""Download and validate the MediaPipe hand-landmarker model on first run."""
from pathlib import Path
from shutil import copyfileobj
from urllib.error import URLError
from urllib.request import urlopen

from .config import MODEL_DIR, MODEL_PATH, MODEL_URL


def ensure_model() -> Path:
    """Return the local model path, downloading the model if it is missing."""
    if MODEL_PATH.is_file() and MODEL_PATH.stat().st_size > 0:
        return MODEL_PATH

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    temporary_path = MODEL_PATH.with_suffix(MODEL_PATH.suffix + ".part")
    print("Downloading the MediaPipe hand model (first run only)...")
    try:
        with urlopen(MODEL_URL, timeout=30) as response, temporary_path.open("wb") as output:
            copyfileobj(response, output)
        if temporary_path.stat().st_size < 100_000:
            raise RuntimeError("The downloaded model file is unexpectedly small.")
        temporary_path.replace(MODEL_PATH)
        print(f"Model downloaded successfully: {MODEL_PATH}")
        return MODEL_PATH
    except (OSError, URLError, RuntimeError) as exc:
        temporary_path.unlink(missing_ok=True)
        raise RuntimeError(
            "Could not download the MediaPipe hand model. Check your internet connection "
            f"and try again. Model URL: {MODEL_URL}"
        ) from exc
