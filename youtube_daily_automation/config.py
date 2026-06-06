from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AutomationConfig:
    """Runtime settings loaded from environment variables and CLI flags."""

    output_dir: Path = Path("dist")
    topic_count: int = 10
    video_length_seconds: int = 60
    youtube_privacy_status: str = "private"
    youtube_category_id: str = "24"
    voice: str = "en-US-AriaNeural"
    channel_name: str = "Daily Interesting Top 10"
    tts_rate: str = "+0%"
    tts_pitch: str = "+0Hz"

    @classmethod
    def from_env(cls, *, output_dir: str | None = None) -> "AutomationConfig":
        return cls(
            output_dir=Path(output_dir or os.getenv("OUTPUT_DIR", "dist")),
            topic_count=int(os.getenv("TOPIC_COUNT", "10")),
            video_length_seconds=int(os.getenv("VIDEO_LENGTH_SECONDS", "60")),
            youtube_privacy_status=os.getenv("YOUTUBE_PRIVACY_STATUS", "private"),
            youtube_category_id=os.getenv("YOUTUBE_CATEGORY_ID", "24"),
            voice=os.getenv("TTS_VOICE", "en-US-AriaNeural"),
            channel_name=os.getenv("CHANNEL_NAME", "Daily Interesting Top 10"),
            tts_rate=os.getenv("TTS_RATE", "+0%"),
            tts_pitch=os.getenv("TTS_PITCH", "+0Hz"),
        )

    def ensure_output_dir(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir
