from __future__ import annotations

import datetime as dt
import json
import sys
import types
import wave

from youtube_daily_automation import audio
from youtube_daily_automation.cli import main
from youtube_daily_automation.script import build_script
from youtube_daily_automation.topics import fetch_daily_topics


def test_offline_topics_return_ranked_top_ten() -> None:
    topics = fetch_daily_topics(dt.date(2026, 6, 6), offline=True)

    assert len(topics) == 10
    assert [topic.rank for topic in topics] == list(range(1, 11))
    assert all(topic.title and topic.summary for topic in topics)


def test_build_script_contains_all_topics_and_metadata() -> None:
    day = dt.date(2026, 6, 6)
    topics = fetch_daily_topics(day, offline=True)

    video_script = build_script(topics, day, channel_name="Test Channel")

    assert video_script.title == "Top 10 Interesting Topics Today - 2026-06-06"
    assert "Test Channel presents ten quick interesting topics" in video_script.description
    assert "#Shorts" in video_script.hashtags
    for topic in topics:
        assert f"Number {topic.rank}: {topic.title}." in video_script.narration


def test_cli_dry_run_writes_metadata(tmp_path) -> None:
    exit_code = main(
        [
            "run",
            "--offline",
            "--dry-run",
            "--date",
            "2026-06-06",
            "--output-dir",
            str(tmp_path),
        ]
    )

    metadata = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    narration = (tmp_path / "narration.txt").read_text(encoding="utf-8")

    assert exit_code == 0
    assert metadata["dry_run"] is True
    assert metadata["date"] == "2026-06-06"
    assert len(metadata["topics"]) == 10
    assert "Number 10:" in narration


def test_tts_failure_retries_and_writes_silent_fallback(monkeypatch, tmp_path) -> None:
    attempts: list[str] = []

    async def fail_tts(*args, **kwargs):
        attempts.append("failed")
        raise RuntimeError("edge service unavailable")

    monkeypatch.setattr(audio, "synthesize_voice_async", fail_tts)

    output_path = tmp_path / "voice.mp3"
    fallback_path = tmp_path / "silent_voice.wav"
    returned_path = audio.synthesize_voice(
        "hello",
        output_path,
        voice="test",
        rate="+0%",
        pitch="+0Hz",
        fallback_path=fallback_path,
        fallback_duration_seconds=2,
        attempts=2,
        retry_delay_seconds=0,
    )

    assert attempts == ["failed", "failed"]
    assert returned_path == fallback_path
    assert not output_path.exists()
    with wave.open(str(fallback_path), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 44_100
        assert wav.getnframes() == 88_200


def test_no_voice_skips_tts_and_continues_to_render(monkeypatch, tmp_path) -> None:
    render_calls = []

    def fail_if_called(*args, **kwargs):
        raise AssertionError("TTS should not run with --no-voice")

    def fake_music(path, *, duration_seconds, volume=0.14):
        path.write_bytes(b"fake music")
        return path

    def fake_render(*args, **kwargs):
        render_calls.append(kwargs)
        kwargs["output_path"].write_bytes(b"fake video")
        return kwargs["output_path"]

    monkeypatch.setattr("youtube_daily_automation.cli.synthesize_voice", fail_if_called)
    monkeypatch.setattr("youtube_daily_automation.cli.generate_background_music", fake_music)
    monkeypatch.setitem(
        sys.modules,
        "youtube_daily_automation.video",
        types.SimpleNamespace(render_video=fake_render),
    )

    exit_code = main(
        [
            "run",
            "--offline",
            "--no-voice",
            "--date",
            "2026-06-06",
            "--output-dir",
            str(tmp_path),
        ]
    )

    metadata = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert metadata["voice_file"] is None
    assert len(render_calls) == 1
    assert render_calls[0]["voice_path"] is None
