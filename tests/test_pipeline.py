from __future__ import annotations

import datetime as dt
import json

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
