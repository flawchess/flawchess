"""Synthesize the blunder-check pot sound (CC0, self-authored, "Walnut" style).

Writes one clip to `frontend/public/sound/`:

- `PotBust.mp3`: a falling, detuned tumble onto a low thud, the pot being lost.

(Banking the pot plays the coin clip three times instead of a clip of its own.)

Pure standard library (`wave`, `math`, `random`) plus `ffmpeg` for the mp3 encode, so it
needs no project dependency. The noise is seeded: a re-run renders the same samples.

Usage:
    uv run python scripts/synth_pot_sounds.py
"""

import math
import random
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

SAMPLE_RATE: int = 44_100
SAMPLE_WIDTH_BYTES: int = 2
INT16_MAX: int = 32_767
MP3_BITRATE: str = "128k"
NOISE_SEED: int = 249
OUTPUT_DIR: Path = Path(__file__).resolve().parent.parent / "frontend" / "public" / "sound"

# A marimba bar: the fundamental, the bar's tuned 4th partial and a short bright 10th.
# (frequency ratio, level, decay seconds)
MARIMBA_PARTIALS: tuple[tuple[float, float, float], ...] = (
    (1.0, 1.0, 0.16),
    (4.0, 0.30, 0.05),
    (10.0, 0.10, 0.015),
)
# The mallet's wood click: filtered noise that is gone within a few milliseconds.
CLICK_LEVEL: float = 0.35
CLICK_DECAY_S: float = 0.004
# Ramp at each note's start, so a note never opens on a discontinuity (an audible tick).
ATTACK_S: float = 0.002
# Fade at the clip's end, so the decay tail never cuts off mid-swing.
TAIL_FADE_S: float = 0.03

C4_HZ: float = 261.63


def _semitones(base_hz: float, steps: float) -> float:
    return base_hz * 2 ** (steps / 12)


@dataclass(frozen=True)
class Note:
    start_s: float
    freq_hz: float
    level: float
    # Scales every partial's decay: above 1 rings longer, below 1 is a duller knock.
    ring: float = 1.0
    partials: tuple[tuple[float, float, float], ...] = MARIMBA_PARTIALS


@dataclass(frozen=True)
class Clip:
    name: str
    duration_s: float
    peak: float
    notes: tuple[Note, ...]


CLIPS: tuple[Clip, ...] = (
    Clip(
        name="PotBust",
        duration_s=0.85,
        peak=0.55,
        notes=(
            # A falling diminished tumble, slightly off the grid and off pitch.
            Note(0.00, _semitones(C4_HZ, 9.15), 0.85, ring=0.7),
            Note(0.065, _semitones(C4_HZ, 5.9), 0.80, ring=0.7),
            Note(0.145, _semitones(C4_HZ, 3.1), 0.80, ring=0.7),
            Note(0.215, _semitones(C4_HZ, -0.2), 0.85, ring=0.8),
            Note(0.33, _semitones(C4_HZ, -11), 1.00, ring=1.6),  # the low thud
            Note(0.33, _semitones(C4_HZ, -10), 0.55, ring=1.2),  # a semitone rub on it
        ),
    ),
)


def _render_note(samples: list[float], note: Note, noise: random.Random) -> None:
    start = round(note.start_s * SAMPLE_RATE)
    previous_noise = 0.0
    for index in range(start, len(samples)):
        t = (index - start) / SAMPLE_RATE
        tone = 0.0
        for ratio, level, decay_s in note.partials:
            tone += (
                level
                * math.exp(-t / (decay_s * note.ring))
                * math.sin(2 * math.pi * note.freq_hz * ratio * t)
            )
        # One-pole low-pass on the noise: wood, not hiss.
        previous_noise = 0.6 * previous_noise + 0.4 * noise.uniform(-1.0, 1.0)
        click = CLICK_LEVEL * math.exp(-t / CLICK_DECAY_S) * previous_noise
        attack = min(1.0, t / ATTACK_S)
        samples[index] += note.level * attack * (tone + click)


def _render(clip: Clip) -> list[float]:
    samples = [0.0] * round(clip.duration_s * SAMPLE_RATE)
    noise = random.Random(NOISE_SEED)
    for note in clip.notes:
        _render_note(samples, note, noise)
    fade_samples = round(TAIL_FADE_S * SAMPLE_RATE)
    for offset in range(fade_samples):
        samples[len(samples) - 1 - offset] *= offset / fade_samples
    loudest = max(abs(sample) for sample in samples)
    return [sample * clip.peak / loudest for sample in samples]


def _write_mp3(clip: Clip, samples: list[float]) -> Path:
    target = OUTPUT_DIR / f"{clip.name}.mp3"
    frames = b"".join(
        round(sample * INT16_MAX).to_bytes(SAMPLE_WIDTH_BYTES, "little", signed=True)
        for sample in samples
    )
    with tempfile.TemporaryDirectory() as workdir:
        wav_path = Path(workdir) / f"{clip.name}.wav"
        with wave.open(str(wav_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(SAMPLE_WIDTH_BYTES)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(frames)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(wav_path),
                "-codec:a",
                "libmp3lame",
                "-b:a",
                MP3_BITRATE,
                # No ID3/Xing metadata: byte-stable output across ffmpeg runs.
                "-map_metadata",
                "-1",
                "-write_xing",
                "0",
                "-id3v2_version",
                "0",
                str(target),
            ],
            check=True,
        )
    return target


def main() -> None:
    for clip in CLIPS:
        target = _write_mp3(clip, _render(clip))
        print(f"wrote {target.relative_to(OUTPUT_DIR.parent.parent.parent)}")


if __name__ == "__main__":
    main()
