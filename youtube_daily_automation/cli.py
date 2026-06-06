from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from .audio import generate_background_music, synthesize_voice
from .config import AutomationConfig
from .script import build_script
from .topics import fetch_daily_topics


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
    output_dir = config.ensure_output_dir()

    topics = fetch_daily_topics(day, count=config.topic_count, offline=args.offline)
    video_script = build_script(topics, day, channel_name=config.channel_name)
    _write_text(output_dir / "narration.txt", video_script.narration)
    _write_text(output_dir / "description.txt", video_script.description)

    metadata = {
        "date": day.isoformat(),
        "title": video_script.title,
        "description_file": str(output_dir / "description.txt"),
        "narration_file": str(output_dir / "narration.txt"),
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

    voice_path: Path | None = None
    if not args.skip_tts:
        voice_path = output_dir / "voice.mp3"
        synthesize_voice(
            video_script.narration,
            voice_path,
            voice=config.voice,
            rate=config.tts_rate,
            pitch=config.tts_pitch,
        )

    video_path = output_dir / f"daily_top_10_{day.isoformat()}.mp4"
    from .video import render_video

    render_video(
        topics,
        output_path=video_path,
        slides_dir=output_dir / "slides",
        voice_path=voice_path,
        music_path=music_path,
        duration_seconds=config.video_length_seconds,
    )
    metadata["video_file"] = str(video_path)

    if args.upload:
        from .upload import upload_video

        metadata["youtube_url"] = upload_video(
            video_path,
            title=video_script.title,
            description=video_script.description,
            category_id=config.youtube_category_id,
            privacy_status=config.youtube_privacy_status,
        )
        print(f"Uploaded: {metadata['youtube_url']}")
    else:
        print(f"Rendered: {video_path}")

    _write_json(output_dir / "metadata.json", metadata)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and optionally upload a daily top-10 YouTube video.")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Generate the daily video.")
    run_parser.add_argument("--date", help="ISO date to generate for. Defaults to today in UTC.")
    run_parser.add_argument("--output-dir", help="Directory for generated assets.")
    run_parser.add_argument("--offline", action="store_true", help="Use built-in fallback topics instead of Wikimedia.")
    run_parser.add_argument("--dry-run", action="store_true", help="Write script and metadata without TTS, video, or upload.")
    run_parser.add_argument("--upload", action="store_true", help="Upload the rendered video to YouTube.")
    run_parser.add_argument("--skip-tts", action="store_true", help="Render without narration. Intended only for local testing.")
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
