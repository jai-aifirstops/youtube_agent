from __future__ import annotations

import asyncio
import math
import time
import wave
from pathlib import Path


DEFAULT_TTS_ATTEMPTS = 3


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


def synthesize_voice(
    text: str,
    output_path: Path,
    *,
    voice: str,
    rate: str,
    pitch: str,
    fallback_path: Path | None = None,
    fallback_duration_seconds: int = 60,
    attempts: int = DEFAULT_TTS_ATTEMPTS,
    retry_delay_seconds: float = 1.0,
) -> Path:
    if attempts < 1:
        raise ValueError("TTS attempts must be at least 1.")

    errors: list[str] = []
    for attempt in range(1, attempts + 1):
        try:
            return asyncio.run(
                synthesize_voice_async(
                    text,
                    output_path,
                    voice=voice,
                    rate=rate,
                    pitch=pitch,
                )
            )
        except Exception as error:
            errors.append(f"attempt {attempt}: {error}")
            if output_path.exists():
                output_path.unlink()
            if attempt < attempts:
                time.sleep(retry_delay_seconds * attempt)

    placeholder_path = fallback_path or output_path.with_name("silent_voice.wav")
    generate_silent_audio(placeholder_path, duration_seconds=fallback_duration_seconds)
    print(
        "Edge TTS failed after "
        f"{attempts} attempts; using silent placeholder audio at {placeholder_path}. "
        f"Last error: {errors[-1]}"
    )
    return placeholder_path


def generate_silent_audio(output_path: Path, *, duration_seconds: int) -> Path:
    sample_rate = 44_100
    frame_count = duration_seconds * sample_rate

    with wave.open(str(output_path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * frame_count)

    return output_path


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
