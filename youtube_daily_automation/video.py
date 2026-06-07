from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .documentary import DocumentaryPlan, DocumentaryScene


VIDEO_SIZE = (1920, 1080)
ARTWORK_SIZE = (2304, 1296)
SUBTITLE_SIZE = (1500, 150)


def render_documentary_video(
    plan: DocumentaryPlan,
    *,
    output_path: Path,
    assets_dir: Path,
    voice_path: Path | None,
    music_path: Path,
    duration_seconds: int,
    subtitles_path: Path,
    scene_image_paths: list[Path] | None = None,
    music_volume: float = 0.18,
    transition_seconds: float = 1.0,
    transition_style: str = "crossfade",
) -> Path:
    if not plan.scenes:
        raise ValueError("Cannot render a documentary without scenes.")

    try:
        from moviepy import AudioFileClip, CompositeAudioClip, CompositeVideoClip, ImageClip, concatenate_videoclips
        from moviepy.video.fx import FadeIn, FadeOut
    except ImportError:  # pragma: no cover - supports MoviePy 1.x.
        from moviepy.editor import AudioFileClip, CompositeAudioClip, CompositeVideoClip, ImageClip, concatenate_videoclips
        from moviepy.video.fx import FadeIn, FadeOut

    assets_dir.mkdir(parents=True, exist_ok=True)
    scene_paths = scene_image_paths or [_create_scene_art(scene, assets_dir / f"scene_{scene.number:02d}.png") for scene in plan.scenes]
    if len(scene_paths) != len(plan.scenes):
        raise ValueError("scene_image_paths must contain one image per scene.")
    subtitle_paths = [_create_subtitle_card(scene, assets_dir / f"subtitle_{scene.number:02d}.png") for scene in plan.scenes]

    clips = []
    for index, (scene, scene_path, subtitle_path) in enumerate(zip(plan.scenes, scene_paths, subtitle_paths)):
        duration = scene.duration_seconds
        artwork = _animate_artwork(ImageClip(str(scene_path)), duration=duration, index=index)
        subtitle = _with_position(_with_duration(ImageClip(str(subtitle_path)), duration), ("center", 900))
        clip = CompositeVideoClip([artwork, subtitle], size=VIDEO_SIZE)
        clip = _with_duration(_with_fps(clip, 30), duration)
        fade_seconds = min(transition_seconds, max(duration / 4, 0.1))
        clip = _apply_scene_transition(clip, style=transition_style, fade_seconds=fade_seconds, index=index)
        clips.append(clip)

    padding = -transition_seconds if transition_style == "crossfade" and len(clips) > 1 else 0
    video = concatenate_videoclips(clips, method="compose", padding=padding)
    video = _with_duration(video, duration_seconds)

    audio_tracks = [_volume(_fit_audio_duration(AudioFileClip(str(music_path)), duration_seconds), music_volume)]
    if voice_path:
        audio_tracks.insert(0, _fit_audio_duration(AudioFileClip(str(voice_path)), duration_seconds))

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


def _apply_scene_transition(clip, *, style: str, fade_seconds: float, index: int):
    try:
        from moviepy.video.fx import FadeIn, FadeOut
    except ImportError:  # pragma: no cover - supports MoviePy 1.x.
        from moviepy.video.fx import FadeIn, FadeOut

    if style == "crossfade":
        return clip.with_effects([FadeIn(fade_seconds), FadeOut(fade_seconds)])
    if style == "slide":
        return _slide_clip(clip, fade_seconds=fade_seconds, index=index).with_effects([FadeIn(fade_seconds / 2), FadeOut(fade_seconds / 2)])
    return clip.with_effects([FadeIn(fade_seconds), FadeOut(fade_seconds)])


def render_video(*args, **kwargs) -> Path:
    return render_documentary_video(*args, **kwargs)


def _create_scene_art(scene: DocumentaryScene, output_path: Path) -> Path:
    image = Image.new("RGB", ARTWORK_SIZE, color=(8, 10, 14))
    draw = ImageDraw.Draw(image)
    title_font = _font(78)
    label_font = _font(42)
    body_font = _font(38)
    small_font = _font(30)

    for y in range(ARTWORK_SIZE[1]):
        shade = int(16 + 42 * (y / ARTWORK_SIZE[1]))
        draw.line((0, y, ARTWORK_SIZE[0], y), fill=(shade // 2, shade, shade + 16))

    draw.rectangle((0, 0, ARTWORK_SIZE[0], ARTWORK_SIZE[1]), outline=(218, 184, 99), width=10)
    draw.line((170, 0, 170, ARTWORK_SIZE[1]), fill=(218, 184, 99), width=3)
    draw.line((ARTWORK_SIZE[0] - 170, 0, ARTWORK_SIZE[0] - 170, ARTWORK_SIZE[1]), fill=(218, 184, 99), width=3)
    draw.ellipse((1500, 110, 2240, 850), outline=(92, 128, 180), width=8)
    draw.rounded_rectangle((130, 115, 690, 205), radius=24, fill=(218, 184, 99))
    draw.text((165, 138), f"SCENE {scene.number:02d}", font=label_font, fill=(8, 10, 14))

    draw.multiline_text(
        (130, 300),
        "\n".join(textwrap.wrap(scene.title.upper(), width=30)),
        font=title_font,
        fill=(244, 240, 229),
        spacing=14,
    )

    prompt_excerpt = scene.image_prompt.replace("Cinematic documentary still, ", "")
    draw.multiline_text(
        (130, 680),
        "\n".join(textwrap.wrap(prompt_excerpt, width=72)[:8]),
        font=body_font,
        fill=(209, 222, 238),
        spacing=12,
    )
    draw.text((130, 1190), "CINEMATIC DOCUMENTARY", font=small_font, fill=(218, 184, 99))

    image.save(output_path)
    return output_path


def _create_subtitle_card(scene: DocumentaryScene, output_path: Path) -> Path:
    image = Image.new("RGBA", SUBTITLE_SIZE, color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = _font(44)
    draw.rounded_rectangle((0, 0, SUBTITLE_SIZE[0], SUBTITLE_SIZE[1]), radius=28, fill=(0, 0, 0, 168))
    draw.multiline_text(
        (44, 28),
        "\n".join(textwrap.wrap(scene.subtitle, width=52)[:2]),
        font=font,
        fill=(255, 255, 255, 255),
        spacing=8,
    )
    image.save(output_path)
    return output_path


def _animate_artwork(clip, *, duration: float, index: int):
    duration = max(duration, 0.1)
    base_width = getattr(clip, "w", ARTWORK_SIZE[0])
    base_height = getattr(clip, "h", ARTWORK_SIZE[1])

    def scale(t):
        return 1.0 + 0.08 * (t / duration)

    def position(t):
        progress = t / duration
        scaled_width = base_width * scale(t)
        scaled_height = base_height * scale(t)
        max_x = VIDEO_SIZE[0] - scaled_width
        max_y = VIDEO_SIZE[1] - scaled_height
        if index % 2:
            x = max_x * progress
            y = max_y * (1.0 - progress)
        else:
            x = max_x * (1.0 - progress)
            y = max_y * progress
        return (x, y)

    return _with_position(_with_duration(clip.resized(scale), duration), position)


def _slide_clip(clip, *, fade_seconds: float, index: int):
    duration = max(getattr(clip, "duration", 0) or 0, 0.1)
    slide_time = min(fade_seconds, duration / 3)
    direction = -1 if index % 2 else 1

    def position(t):
        if t < slide_time:
            progress = t / slide_time
            return (direction * VIDEO_SIZE[0] * (1 - progress), 0)
        if t > duration - slide_time:
            progress = (t - (duration - slide_time)) / slide_time
            return (-direction * VIDEO_SIZE[0] * progress, 0)
        return (0, 0)

    return _with_position(clip, position)


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


def _with_position(clip, position):
    return clip.with_position(position) if hasattr(clip, "with_position") else clip.set_position(position)


def _with_fps(clip, fps: int):
    return clip.with_fps(fps) if hasattr(clip, "with_fps") else clip.set_fps(fps)


def _subclip(clip, start: float, end: float):
    if hasattr(clip, "subclipped"):
        return clip.subclipped(start, end)
    return clip.subclip(start, end)


def _fit_audio_duration(clip, duration: float):
    clip_duration = getattr(clip, "duration", None)
    if clip_duration and clip_duration >= duration:
        return _subclip(clip, 0, duration)
    return _with_duration(clip, duration)


def _volume(clip, factor: float):
    if hasattr(clip, "with_volume_scaled"):
        return clip.with_volume_scaled(factor)
    return clip.volumex(factor)
