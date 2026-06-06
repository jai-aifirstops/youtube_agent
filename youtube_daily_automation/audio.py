from __future__ import annotations

import asyncio
import math
import wave
from pathlib import Path


async def synthesize_voice_async(
    text: str,
    output_path: Path,
    *,
    voice: str,
    rate: str,
    pitch: str,
) -> Path:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(output_path))
    return output_path


def synthesize_voice(text: str, output_path: Path, *, voice: str, rate: str, pitch: str) -> Path:
    return asyncio.run(
        synthesize_voice_async(
            text,
            output_path,
            voice=voice,
            rate=rate,
            pitch=pitch,
        )
    )


def generate_background_music(output_path: Path, *, duration_seconds: int, volume: float = 0.14) -> Path:
    """Generate a simple royalty-free ambient backing track."""
    sample_rate = 44_100
    frame_count = duration_seconds * sample_rate
    chord_hz = (220.0, 277.18, 329.63, 440.0)

    with wave.open(str(output_path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        frames = bytearray()
        for index in range(frame_count):
            t = index / sample_rate
            envelope = min(1.0, t / 3.0, (duration_seconds - t) / 3.0)
            pulse = 0.6 + 0.4 * math.sin(2 * math.pi * 0.18 * t)
            sample = sum(math.sin(2 * math.pi * hz * t) for hz in chord_hz) / len(chord_hz)
            value = int(32767 * volume * envelope * pulse * sample)
            frames.extend(value.to_bytes(2, byteorder="little", signed=True))

        wav.writeframes(bytes(frames))

    return output_path
