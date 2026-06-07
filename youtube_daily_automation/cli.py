from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from dataclasses import replace
from pathlib import Path

from .audio import generate_background_music, synthesize_documentary_voice
from .config import AutomationConfig
from .documentary import build_documentary_plan
from .subtitles import write_srt
from .topics import fetch_daily_topics
from .visuals import prepare_scene_visual_assets


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return run(args)
    if args.command == "auth":
        return auth(args)

    parser.print_help()
    return 2


def auth(args: argparse.Namespace) -> int:
    from .upload import create_token_file

    token_file = create_token_file(
        client_secret_file=Path(args.client_secret_file),
        token_file=Path(args.token_file),
    )
    print(f"Wrote YouTube token to {token_file}")
    return 0


def run(args: argparse.Namespace) -> int:
    day = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(dt.UTC).date()
    config = AutomationConfig.from_env(output_dir=args.output_dir)
    if args.duration_seconds:
        config = replace(config, video_length_seconds=args.duration_seconds)
    if args.scene_count:
        config = replace(config, scene_count=args.scene_count)
    if args.tts_provider:
        config = replace(config, tts_provider=args.tts_provider)
    if args.image_provider:
        config = replace(config, image_provider=args.image_provider)
    if not args.allow_short_render:
        config.validate_for_documentary()

    output_dir = config.ensure_output_dir()

    topics = fetch_daily_topics(day, count=config.topic_count, offline=args.offline)
    topic = args.topic or os.getenv("DOCUMENTARY_TOPIC") or (topics[0].title if topics else config.documentary_topic)
    plan = build_documentary_plan(
        topic=topic,
        day=day,
        source_topics=topics,
        scene_count=config.scene_count,
        duration_seconds=config.video_length_seconds,
        channel_name=config.channel_name,
    )
    narration_path = output_dir / "narration.txt"
    description_path = output_dir / "description.txt"
    plan_path = output_dir / "documentary_plan.json"
    prompts_path = output_dir / "image_prompts.json"
    subtitles_path = output_dir / "subtitles.srt"

    _write_text(narration_path, plan.narration)
    _write_text(description_path, plan.description)
    _write_json(plan_path, plan.to_dict())
    _write_json(prompts_path, {f"scene_{scene.number:02d}": scene.image_prompt for scene in plan.scenes})
    write_srt(plan.scenes, subtitles_path)

    metadata = {
        "date": day.isoformat(),
        "title": plan.title,
        "description_file": str(description_path),
        "narration_file": str(narration_path),
        "plan_file": str(plan_path),
        "image_prompts_file": str(prompts_path),
        "subtitles_file": str(subtitles_path),
        "scene_count": len(plan.scenes),
        "duration_seconds": config.video_length_seconds,
        "tts_provider": config.tts_provider,
        "image_provider": config.image_provider,
        "topics": [topic.__dict__ for topic in topics],
        "dry_run": args.dry_run,
    }

    if args.dry_run:
        _write_json(output_dir / "metadata.json", metadata)
        print(json.dumps(metadata, indent=2))
        return 0

    music_path = Path(args.music_file) if args.music_file else output_dir / "background_music.wav"
    if not args.music_file:
        generate_background_music(music_path, duration_seconds=config.video_length_seconds)

    visual_assets = prepare_scene_visual_assets(
        plan,
        output_dir / "scene_assets",
        provider=config.image_provider,
    )
    metadata["visual_assets"] = [asset.to_dict() for asset in visual_assets]

    voice_path: Path | None = None
    if not args.no_voice:
        voice_path = synthesize_documentary_voice(
            plan.narration,
            output_dir / "voice.mp3",
            provider=config.tts_provider,
            fallback_path=output_dir / "silent_voice.wav",
            fallback_duration_seconds=config.video_length_seconds,
            attempts=config.tts_attempts,
            edge_voice=config.edge_tts_voice,
            edge_rate=config.edge_tts_rate,
            edge_pitch=config.edge_tts_pitch,
        )
        metadata["voice_file"] = str(voice_path)
    else:
        metadata["voice_file"] = None

    video_path = output_dir / f"daily_documentary_{day.isoformat()}.mp4"
    from .video import render_documentary_video

    render_documentary_video(
        plan,
        output_path=video_path,
        assets_dir=output_dir / "scene_assets",
        voice_path=voice_path,
        music_path=music_path,
        duration_seconds=config.video_length_seconds,
        subtitles_path=subtitles_path,
        scene_image_paths=[Path(asset.path) for asset in visual_assets],
        transition_seconds=config.transition_seconds,
    )
    metadata["video_file"] = str(video_path)

    if args.upload:
        from .upload import upload_video

        metadata["youtube_url"] = upload_video(
            video_path,
            title=plan.title,
            description=plan.description,
            category_id=config.youtube_category_id,
            privacy_status=config.youtube_privacy_status,
        )
        print(f"Uploaded: {metadata['youtube_url']}")
    else:
        print(f"Rendered: {video_path}")

    _write_json(output_dir / "metadata.json", metadata)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and optionally upload a daily cinematic documentary.")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Generate the daily documentary.")
    run_parser.add_argument("--date", help="ISO date to generate for. Defaults to today in UTC.")
    run_parser.add_argument("--output-dir", help="Directory for generated assets.")
    run_parser.add_argument("--offline", action="store_true", help="Use built-in fallback topics instead of Wikimedia.")
    run_parser.add_argument("--dry-run", action="store_true", help="Write script and metadata without TTS, video, or upload.")
    run_parser.add_argument("--upload", action="store_true", help="Upload the rendered video to YouTube.")
    run_parser.add_argument("--topic", help="Documentary topic. Defaults to DOCUMENTARY_TOPIC or the first daily topic.")
    run_parser.add_argument("--scene-count", type=int, help="Number of documentary scenes. Production default is 30.")
    run_parser.add_argument("--duration-seconds", type=int, help="Video duration. Production default is 480 seconds.")
    run_parser.add_argument("--tts-provider", choices=["edge", "silent"], help="Voice provider.")
    run_parser.add_argument("--image-provider", choices=["wikimedia", "fallback"], help="Visual provider.")
    run_parser.add_argument("--allow-short-render", action="store_true", help="Allow short renders for local smoke tests.")
    run_parser.add_argument(
        "--no-voice",
        "--skip-tts",
        dest="no_voice",
        action="store_true",
        help="Render without TTS narration. Intended only for local testing.",
    )
    run_parser.add_argument("--music-file", help="Optional custom background music file.")

    auth_parser = subparsers.add_parser("auth", help="Create a YouTube OAuth token file locally.")
    auth_parser.add_argument("--client-secret-file", required=True, help="OAuth client secret JSON from Google Cloud.")
    auth_parser.add_argument("--token-file", default="token.json", help="Where to write the authorized token JSON.")

    return parser


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


if __name__ == "__main__":
    raise SystemExit(main())
