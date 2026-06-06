from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .topics import InterestingTopic


VIDEO_SIZE = (1080, 1920)


def render_video(
    topics: list[InterestingTopic],
    *,
    output_path: Path,
    slides_dir: Path,
    voice_path: Path | None,
    music_path: Path,
    duration_seconds: int,
) -> Path:
    if not topics:
        raise ValueError("Cannot render a video without topics.")

    try:
        from moviepy import AudioFileClip, CompositeAudioClip, ImageClip, concatenate_videoclips
    except ImportError:  # pragma: no cover - supports MoviePy 1.x.
        from moviepy.editor import AudioFileClip, CompositeAudioClip, ImageClip, concatenate_videoclips

    slides_dir.mkdir(parents=True, exist_ok=True)
    slide_paths = [_create_slide(topic, slides_dir / f"slide_{topic.rank:02d}.png") for topic in topics]

    base_duration = duration_seconds / len(slide_paths)
    clips = [_with_duration(ImageClip(str(path)), base_duration) for path in slide_paths]
    video = _with_duration(concatenate_videoclips(clips, method="compose"), duration_seconds)

    audio_tracks = [_volume(_subclip(AudioFileClip(str(music_path)), 0, duration_seconds), 0.18)]
    if voice_path:
        audio_tracks.insert(0, _subclip(AudioFileClip(str(voice_path)), 0, duration_seconds))

    audio = _with_duration(CompositeAudioClip(audio_tracks), duration_seconds)
    video = _with_audio(video, audio)
    video = _with_fps(video, 30)
    video.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        fps=30,
        logger=None,
    )

    video.close()
    audio.close()
    for track in audio_tracks:
        track.close()

    return output_path


def _create_slide(topic: InterestingTopic, output_path: Path) -> Path:
    image = Image.new("RGB", VIDEO_SIZE, color=(13, 17, 38))
    draw = ImageDraw.Draw(image)
    title_font = _font(94)
    rank_font = _font(130)
    body_font = _font(56)
    footer_font = _font(36)

    gradient_color = (45, 110, 255)
    draw.rounded_rectangle((80, 120, 1000, 430), radius=48, fill=gradient_color)
    draw.text((130, 145), f"#{topic.rank}", font=rank_font, fill=(255, 255, 255))
    draw.text((130, 320), "TOP 10 INTERESTING TOPICS", font=footer_font, fill=(230, 240, 255))

    draw.multiline_text(
        (90, 600),
        "\n".join(textwrap.wrap(topic.title, width=16)),
        font=title_font,
        fill=(255, 255, 255),
        spacing=18,
    )

    body = "\n".join(textwrap.wrap(topic.summary, width=27))
    draw.multiline_text((90, 980), body, font=body_font, fill=(219, 227, 255), spacing=16)
    draw.text((90, 1760), "Daily Interesting Top 10", font=footer_font, fill=(153, 171, 218))

    image.save(output_path)
    return output_path


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _with_duration(clip, duration: float):
    return clip.with_duration(duration) if hasattr(clip, "with_duration") else clip.set_duration(duration)


def _with_audio(clip, audio):
    return clip.with_audio(audio) if hasattr(clip, "with_audio") else clip.set_audio(audio)


def _with_fps(clip, fps: int):
    return clip.with_fps(fps) if hasattr(clip, "with_fps") else clip.set_fps(fps)


def _subclip(clip, start: float, end: float):
    if hasattr(clip, "subclipped"):
        return clip.subclipped(start, end)
    return clip.subclip(start, end)


def _volume(clip, factor: float):
    if hasattr(clip, "with_volume_scaled"):
        return clip.with_volume_scaled(factor)
    return clip.volumex(factor)
