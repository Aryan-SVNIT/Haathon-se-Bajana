import numpy as np
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
    """Synthesize rich, lingering acoustic instrument notes using numpy.

    Piano features percussive hammer attack with warm dual-decay soundboard resonance.
    Guitar features acoustic pluck transient with prolonged fundamental sustain.
    """
    if duration is None:
        duration = 2.40 if instrument == "piano" else 2.10

    sample_count = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, sample_count, endpoint=False, dtype=np.float32)

    if instrument == "piano":
        # Hammer strike attack (12 ms)
        attack = np.minimum(1.0, t / 0.012)
        # Resonant acoustic body decay with prolonged lingering tail
        envelope = attack * (0.65 * np.exp(-1.05 * t) + 0.35 * np.exp(-2.5 * t))
        # Rich harmonic spectrum with warm unison detune
        wave = (
            0.52 * np.sin(2 * np.pi * frequency * t)
            + 0.28 * np.sin(2 * np.pi * (2 * frequency) * t)
            + 0.12 * np.sin(2 * np.pi * (3 * frequency) * t)
            + 0.05 * np.sin(2 * np.pi * (4 * frequency) * t)
            + 0.03 * np.sin(2 * np.pi * (frequency + 0.45) * t)  # Acoustic unison chorus
        )
        signal = envelope * wave
    elif instrument == "guitar":
        # Sharp string pluck attack (3 ms)
        attack = 1.0 - np.exp(-t / 0.003)
        # Higher harmonics decay quickly; warm fundamental and 2nd harmonic linger
        h1 = 0.58 * np.sin(2 * np.pi * frequency * t) * np.exp(-1.1 * t)
        h2 = 0.26 * np.sin(2 * np.pi * (2 * frequency) * t) * np.exp(-2.0 * t)
        h3 = 0.11 * np.sin(2 * np.pi * (3 * frequency) * t) * np.exp(-3.6 * t)
        h4 = 0.05 * np.sin(2 * np.pi * (4 * frequency) * t) * np.exp(-5.2 * t)
        signal = attack * (h1 + h2 + h3 + h4)
    else:
        raise ValueError(f"Unsupported sound type: {instrument}")

    # Smooth 30ms fade-out at the very end to prevent any clicks
    fade_len = int(SAMPLE_RATE * 0.030)
    if fade_len > 0 and len(signal) >= fade_len:
        signal[-fade_len:] *= np.linspace(1.0, 0.0, fade_len, dtype=np.float32)

    samples = np.clip(signal * 14_500, -32767, 32767).astype(np.int16)
    sound = pygame.mixer.Sound(buffer=samples.tobytes())
    sound.set_volume(0.88)
    return sound


def make_guitar_chord(root_freq: float, third_freq: float, duration: float = 2.20) -> pygame.mixer.Sound:
    """Synthesize a plucked acoustic guitar chord (root + third).

    A tiny 2ms strum offset between root and third replicates a natural guitar pick strum.
    """
    sample_count = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, sample_count, endpoint=False, dtype=np.float32)

    # 2ms strum offset between root and 3rd string
    dt_strum = 0.002
    attack_root = 1.0 - np.exp(-t / 0.003)
    t_third = np.maximum(0.0, t - dt_strum)
    attack_third = np.where(t >= dt_strum, 1.0 - np.exp(-t_third / 0.003), 0.0)

    # Root string harmonics (deep acoustic linger)
    r1 = 0.50 * np.sin(2 * np.pi * root_freq * t) * np.exp(-1.05 * t)
    r2 = 0.22 * np.sin(2 * np.pi * (2 * root_freq) * t) * np.exp(-1.9 * t)
    r3 = 0.08 * np.sin(2 * np.pi * (3 * root_freq) * t) * np.exp(-3.2 * t)
    root_signal = attack_root * (r1 + r2 + r3)

    # Third string harmonics (characterizes Major vs Minor)
    th1 = 0.45 * np.sin(2 * np.pi * third_freq * t_third) * np.exp(-1.15 * t_third)
    th2 = 0.18 * np.sin(2 * np.pi * (2 * third_freq) * t_third) * np.exp(-2.1 * t_third)
    th3 = 0.06 * np.sin(2 * np.pi * (3 * third_freq) * t_third) * np.exp(-3.5 * t_third)
    third_signal = attack_third * (th1 + th2 + th3)

    signal = root_signal + third_signal

    fade_len = int(SAMPLE_RATE * 0.030)
    if fade_len > 0 and len(signal) >= fade_len:
        signal[-fade_len:] *= np.linspace(1.0, 0.0, fade_len, dtype=np.float32)

    samples = np.clip(signal * 13_500, -32767, 32767).astype(np.int16)
    sound = pygame.mixer.Sound(buffer=samples.tobytes())
    sound.set_volume(0.88)
    return sound


def make_piano_chord(frequencies: tuple[float, ...], duration: float = 2.40) -> pygame.mixer.Sound:
    """Synthesize a rich acoustic piano chord triad (root + 3rd + 5th)."""
    sample_count = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, sample_count, endpoint=False, dtype=np.float32)

    # Hammer strike attack (12 ms)
    attack = np.minimum(1.0, t / 0.012)
    # Resonant soundboard decay with lingering tail
    envelope = attack * (0.65 * np.exp(-1.05 * t) + 0.35 * np.exp(-2.5 * t))

    combined = np.zeros_like(t)
    weights = (0.42, 0.32, 0.26) if len(frequencies) >= 3 else (0.55, 0.45)

    for i, freq in enumerate(frequencies[:3]):
        w = weights[i] if i < len(weights) else (1.0 / len(frequencies))
        note_wave = (
            0.55 * np.sin(2 * np.pi * freq * t)
            + 0.26 * np.sin(2 * np.pi * 2 * freq * t)
            + 0.12 * np.sin(2 * np.pi * 3 * freq * t)
            + 0.07 * np.sin(2 * np.pi * (freq + 0.35) * t)  # Unison chorus
        )
        combined += w * note_wave

    signal = envelope * combined

    # Smooth 30ms fade-out
    fade_len = int(SAMPLE_RATE * 0.030)
    if fade_len > 0 and len(signal) >= fade_len:
        signal[-fade_len:] *= np.linspace(1.0, 0.0, fade_len, dtype=np.float32)

    samples = np.clip(signal * 14_500, -32767, 32767).astype(np.int16)
    sound = pygame.mixer.Sound(buffer=samples.tobytes())
    sound.set_volume(0.88)
    return sound


def make_percussion(sound_kind: str) -> pygame.mixer.Sound:
    """Synthesize punchy electronic drum kit pads for the Octapad."""
    sr = SAMPLE_RATE
    sound_kind = sound_kind.lower()

    if sound_kind == "kick":
        dur = 0.35
        t = np.linspace(0, dur, int(sr * dur), endpoint=False, dtype=np.float32)
        f = 45.0 + 120.0 * np.exp(-t / 0.032)
        phase = 2 * np.pi * np.cumsum(f) / sr
        click = 0.22 * np.sin(4 * np.pi * np.cumsum(f) / sr) * np.exp(-t / 0.015)
        sig = (np.sin(phase) + click) * np.exp(-t / 0.080)
    elif sound_kind == "snare":
        dur = 0.28
        t = np.linspace(0, dur, int(sr * dur), endpoint=False, dtype=np.float32)
        body = np.sin(2 * np.pi * 185.0 * t) * np.exp(-t / 0.055)
        noise = np.random.uniform(-1.0, 1.0, len(t)).astype(np.float32) * np.exp(-t / 0.095)
        sig = 0.44 * body + 0.56 * noise
    elif sound_kind == "hihat_closed":
        dur = 0.065
        t = np.linspace(0, dur, int(sr * dur), endpoint=False, dtype=np.float32)
        noise = np.random.uniform(-1.0, 1.0, len(t)).astype(np.float32)
        metal = (np.sin(2 * np.pi * 5800 * t) + np.sin(2 * np.pi * 7400 * t)) * 0.25
        sig = (0.75 * noise + 0.25 * metal) * np.exp(-t / 0.018)
    elif sound_kind == "hihat_open":
        dur = 0.45
        t = np.linspace(0, dur, int(sr * dur), endpoint=False, dtype=np.float32)
        noise = np.random.uniform(-1.0, 1.0, len(t)).astype(np.float32)
        metal = (np.sin(2 * np.pi * 5800 * t) + np.sin(2 * np.pi * 7400 * t)) * 0.20
        sig = (0.80 * noise + 0.20 * metal) * np.exp(-t / 0.12)
    elif sound_kind in ("low_tom", "high_tom"):
        dur = 0.42
        f0 = 95.0 if sound_kind == "low_tom" else 165.0
        t = np.linspace(0, dur, int(sr * dur), endpoint=False, dtype=np.float32)
        f = f0 * (1.0 + 0.40 * np.exp(-t / 0.035))
        phase = 2 * np.pi * np.cumsum(f) / sr
        sig = (np.sin(phase) + 0.28 * np.sin(2 * phase)) * np.exp(-t / 0.125)
    elif sound_kind == "crash":
        dur = 1.35
        t = np.linspace(0, dur, int(sr * dur), endpoint=False, dtype=np.float32)
        noise = np.random.uniform(-1.0, 1.0, len(t)).astype(np.float32)
        metal = (np.sin(2 * np.pi * 440 * t) + np.sin(2 * np.pi * 630 * t) + np.sin(2 * np.pi * 890 * t)) * 0.22
        sig = (0.70 * noise + 0.30 * metal) * np.exp(-t / 0.35)
    elif sound_kind == "clap":
        dur = 0.30
        t = np.linspace(0, dur, int(sr * dur), endpoint=False, dtype=np.float32)
        noise = np.random.uniform(-1.0, 1.0, len(t)).astype(np.float32)
        env = (
            np.exp(-np.maximum(0, t) / 0.010)
            + np.exp(-np.maximum(0, t - 0.011) / 0.010)
            + np.exp(-np.maximum(0, t - 0.022) / 0.010)
            + np.exp(-np.maximum(0, t - 0.033) / 0.065)
        )
        sig = noise * env * 0.45
    elif sound_kind == "cowbell":
        dur = 0.35
        t = np.linspace(0, dur, int(sr * dur), endpoint=False, dtype=np.float32)
        sig = (np.sin(2 * np.pi * 540 * t) + 0.65 * np.sin(2 * np.pi * 800 * t)) * np.exp(-t / 0.075)
    elif sound_kind == "ride":
        dur = 1.15
        t = np.linspace(0, dur, int(sr * dur), endpoint=False, dtype=np.float32)
        noise = np.random.uniform(-1.0, 1.0, len(t)).astype(np.float32)
        ping = np.sin(2 * np.pi * 2100 * t) * np.exp(-t / 0.16)
        sig = (0.50 * ping + 0.50 * noise) * np.exp(-t / 0.28)
    else:
        # Fallback tone
        return make_tone(220.0, "piano", 0.3)

    fade_len = int(sr * 0.020)
    if fade_len > 0 and len(sig) >= fade_len:
        sig[-fade_len:] *= np.linspace(1.0, 0.0, fade_len, dtype=np.float32)

    peak = np.max(np.abs(sig))
    if peak > 0.001:
        sig = (sig / peak) * 0.92

    samples = np.clip(sig * 28_000, -32767, 32767).astype(np.int16)
    sound = pygame.mixer.Sound(buffer=samples.tobytes())
    sound.set_volume(0.92)
    return sound


def create_note_sounds(notes_by_slot: dict, instrument: str):
    """Pre-create note sounds so a gesture doesn't need to synthesize audio live."""
    sounds = {}
    for slot, notes in notes_by_slot.items():
        sounds[slot] = []
        for note_item in notes:
            if instrument == "octapad":
                # note_item format: (display_name, sound_id, freq)
                sound_kind = note_item[1] if len(note_item) > 1 and isinstance(note_item[1], str) else "kick"
                sounds[slot].append(make_percussion(sound_kind))
                continue

            freqs = note_item[1:]
            if len(freqs) == 1:
                sounds[slot].append(make_tone(freqs[0], instrument))
            elif instrument == "piano":
                sounds[slot].append(make_piano_chord(freqs))
            else:
                sounds[slot].append(make_guitar_chord(freqs[0], freqs[1]))
    return sounds

