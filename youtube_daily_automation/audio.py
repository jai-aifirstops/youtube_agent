from __future__ import annotations

import asyncio
import math
import os
import time
import wave
from pathlib import Path


DEFAULT_TTS_ATTEMPTS = 3
OPENAI_SPEECH_URL = "https://api.openai.com/v1/audio/speech"


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


def synthesize_documentary_voice(
    text: str,
    output_path: Path,
    *,
    provider: str,
    fallback_path: Path | None = None,
    fallback_duration_seconds: int = 480,
    attempts: int = DEFAULT_TTS_ATTEMPTS,
    retry_delay_seconds: float = 1.0,
    openai_model: str = "gpt-4o-mini-tts",
    openai_voice: str = "onyx",
    edge_voice: str = "en-US-GuyNeural",
    edge_rate: str = "+0%",
    edge_pitch: str = "+0Hz",
) -> Path:
    if attempts < 1:
        raise ValueError("TTS attempts must be at least 1.")
    if provider == "silent":
        placeholder_path = fallback_path or output_path.with_name("silent_voice.wav")
        return generate_silent_audio(placeholder_path, duration_seconds=fallback_duration_seconds)

    chunks = _split_text_for_tts(text)
    errors: list[str] = []
    provider_chain = ["openai", "edge"] if provider == "openai" else [provider]
    if provider not in {"openai", "edge"}:
        errors.append("TTS_PROVIDER must be openai, edge, or silent.")
        provider_chain = []

    for active_provider in provider_chain:
        try:
            _synthesize_chunks(
                chunks,
                output_path,
                provider=active_provider,
                attempts=attempts,
                retry_delay_seconds=retry_delay_seconds,
                openai_model=openai_model,
                openai_voice=openai_voice,
                edge_voice=edge_voice,
                edge_rate=edge_rate,
                edge_pitch=edge_pitch,
            )
            return output_path
        except Exception as error:
            errors.append(f"{active_provider}: {error}")
            if output_path.exists():
                output_path.unlink()

    placeholder_path = fallback_path or output_path.with_name("silent_voice.wav")
    generate_silent_audio(placeholder_path, duration_seconds=fallback_duration_seconds)
    print(
        f"{provider} TTS failed; using silent placeholder audio at {placeholder_path}. "
        f"Last error: {errors[-1]}"
    )
    return placeholder_path


def _synthesize_chunks(
    chunks: list[str],
    output_path: Path,
    *,
    provider: str,
    attempts: int,
    retry_delay_seconds: float,
    openai_model: str,
    openai_voice: str,
    edge_voice: str,
    edge_rate: str,
    edge_pitch: str,
) -> Path:
    try:
        if len(chunks) == 1:
            _synthesize_provider_chunk(
                chunks[0],
                output_path,
                provider=provider,
                attempts=attempts,
                retry_delay_seconds=retry_delay_seconds,
                openai_model=openai_model,
                openai_voice=openai_voice,
                edge_voice=edge_voice,
                edge_rate=edge_rate,
                edge_pitch=edge_pitch,
            )
            return output_path

        segment_paths = []
        for index, chunk in enumerate(chunks, start=1):
            segment_path = output_path.with_name(f"{output_path.stem}_part_{index:02d}{output_path.suffix}")
            _synthesize_provider_chunk(
                chunk,
                segment_path,
                provider=provider,
                attempts=attempts,
                retry_delay_seconds=retry_delay_seconds,
                openai_model=openai_model,
                openai_voice=openai_voice,
                edge_voice=edge_voice,
                edge_rate=edge_rate,
                edge_pitch=edge_pitch,
            )
            segment_paths.append(segment_path)
        _concatenate_audio_files(segment_paths, output_path)
        return output_path
    except Exception:
        if output_path.exists():
            output_path.unlink()
        raise


def _synthesize_provider_chunk(
    text: str,
    output_path: Path,
    *,
    provider: str,
    attempts: int,
    retry_delay_seconds: float,
    openai_model: str,
    openai_voice: str,
    edge_voice: str,
    edge_rate: str,
    edge_pitch: str,
) -> Path:
    errors: list[str] = []
    for attempt in range(1, attempts + 1):
        try:
            if provider == "openai":
                return _openai_tts(text, output_path, model=openai_model, voice=openai_voice)
            if provider == "edge":
                asyncio.run(
                    synthesize_voice_async(
                        text,
                        output_path,
                        voice=edge_voice,
                        rate=edge_rate,
                        pitch=edge_pitch,
                    )
                )
                return output_path
            raise ValueError("TTS_PROVIDER must be openai, edge, or silent.")
        except Exception as error:
            errors.append(f"attempt {attempt}: {error}")
            if output_path.exists():
                output_path.unlink()
            if attempt < attempts:
                time.sleep(retry_delay_seconds * attempt)
    raise RuntimeError("; ".join(errors))


def _split_text_for_tts(text: str, *, max_chars: int = 3000) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs or [text.strip()]:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = paragraph
    if current:
        chunks.append(current)
    return chunks or [text]


def _concatenate_audio_files(segment_paths: list[Path], output_path: Path) -> Path:
    try:
        from moviepy import AudioFileClip, concatenate_audioclips
    except ImportError:  # pragma: no cover - supports MoviePy 1.x.
        from moviepy.editor import AudioFileClip, concatenate_audioclips

    clips = [AudioFileClip(str(path)) for path in segment_paths]
    audio = concatenate_audioclips(clips)
    audio.write_audiofile(str(output_path), logger=None)
    audio.close()
    for clip in clips:
        clip.close()
    return output_path


def _openai_tts(text: str, output_path: Path, *, model: str, voice: str) -> Path:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for OpenAI TTS.")

    import requests

    response = requests.post(
        OPENAI_SPEECH_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "voice": voice, "input": text, "response_format": "mp3"},
        timeout=180,
    )
    response.raise_for_status()
    output_path.write_bytes(response.content)
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
    return synthesize_documentary_voice(
        text,
        output_path,
        provider="edge",
        fallback_path=fallback_path,
        fallback_duration_seconds=fallback_duration_seconds,
        attempts=attempts,
        retry_delay_seconds=retry_delay_seconds,
        edge_voice=voice,
        edge_rate=rate,
        edge_pitch=pitch,
    )


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
