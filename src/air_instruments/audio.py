"""Offline sound synthesis for the prototype piano and guitar notes."""
from array import array
import math

import pygame

from .config import SAMPLE_RATE


def initialize_audio() -> None:
    """Initialize the audio mixer and allow several notes to overlap."""
    try:
        pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
        pygame.mixer.set_num_channels(24)
    except pygame.error as exc:
        raise RuntimeError(
            "Could not initialize audio. Check that Windows has an active sound output device."
        ) from exc


def make_tone(frequency: float, instrument: str, duration: float | None = None) -> pygame.mixer.Sound:
    """Synthesize one note without external audio files.

    Piano is a simple harmonic/decay approximation. Guitar is a plucked-string-like
    approximation; it is not a sample recording of an acoustic/electric guitar.
    """
    if duration is None:
        duration = 0.90 if instrument == "piano" else 1.10
    sample_count = int(SAMPLE_RATE * duration)
    samples = array("h")

    for sample_index in range(sample_count):
        t = sample_index / SAMPLE_RATE
        if instrument == "piano":
            attack = min(1.0, sample_index / (SAMPLE_RATE * 0.010))
            release = min(1.0, (sample_count - sample_index) / (SAMPLE_RATE * 0.10))
            envelope = attack * release * math.exp(-3.2 * t)
            wave = (
                0.68 * math.sin(2 * math.pi * frequency * t)
                + 0.23 * math.sin(2 * math.pi * frequency * 2 * t)
                + 0.09 * math.sin(2 * math.pi * frequency * 3 * t)
            )
        elif instrument == "guitar":
            attack = 1.0 - math.exp(-t / 0.0025)
            envelope = attack * math.exp(-2.25 * t)
            wave = (
                0.54 * math.sin(2 * math.pi * frequency * t)
                + 0.26 * math.sin(2 * math.pi * frequency * 2 * t)
                + 0.13 * math.sin(2 * math.pi * frequency * 3 * t)
                + 0.07 * math.sin(2 * math.pi * frequency * 4 * t)
            )
        else:
            raise ValueError(f"Unsupported sound type: {instrument}")

        value = max(-32767, min(32767, int(13_500 * envelope * wave)))
        samples.append(value)

    sound = pygame.mixer.Sound(buffer=samples.tobytes())
    sound.set_volume(0.85)
    return sound


def create_note_sounds(notes_by_slot: dict[str, tuple[tuple[str, float], ...]], instrument: str):
    """Pre-create note sounds so a gesture doesn't need to synthesize audio live."""
    return {
        slot: [make_tone(frequency, instrument) for _note_name, frequency in notes]
        for slot, notes in notes_by_slot.items()
    }
