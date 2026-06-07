from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AutomationConfig:
    """Runtime settings loaded from environment variables and CLI flags."""

    output_dir: Path = Path("dist")
    topic_count: int = 8
    video_length_seconds: int = 360
    scene_count: int = 24
    youtube_privacy_status: str = "private"
    youtube_category_id: str = "24"
    channel_name: str = "Daily Documentary"
    documentary_topic: str = "A hidden story from history"
    tts_provider: str = "edge"
    edge_tts_voice: str = "en-US-GuyNeural"
    edge_tts_rate: str = "+0%"
    edge_tts_pitch: str = "+0Hz"
    tts_attempts: int = 3
    image_provider: str = "wikimedia"
    transition_seconds: float = 1.0

    @classmethod
    def from_env(cls, *, output_dir: str | None = None) -> "AutomationConfig":
        return cls(
            output_dir=Path(output_dir or os.getenv("OUTPUT_DIR", "dist")),
            topic_count=int(os.getenv("TOPIC_COUNT", "8")),
            video_length_seconds=int(os.getenv("VIDEO_LENGTH_SECONDS", "360")),
            scene_count=int(os.getenv("SCENE_COUNT", "24")),
            youtube_privacy_status=os.getenv("YOUTUBE_PRIVACY_STATUS", "private"),
            youtube_category_id=os.getenv("YOUTUBE_CATEGORY_ID", "24"),
            channel_name=os.getenv("CHANNEL_NAME", "Daily Documentary"),
            documentary_topic=os.getenv("DOCUMENTARY_TOPIC", "A hidden story from history"),
            tts_provider=os.getenv("TTS_PROVIDER", "edge").lower(),
            edge_tts_voice=os.getenv("EDGE_TTS_VOICE", "en-US-GuyNeural"),
            edge_tts_rate=os.getenv("EDGE_TTS_RATE", "+0%"),
            edge_tts_pitch=os.getenv("EDGE_TTS_PITCH", "+0Hz"),
            tts_attempts=int(os.getenv("TTS_ATTEMPTS", "3")),
            image_provider=os.getenv("IMAGE_PROVIDER", "wikimedia").lower(),
            transition_seconds=float(os.getenv("TRANSITION_SECONDS", "1.0")),
        )

    def ensure_output_dir(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir

    def validate_for_documentary(self) -> None:
        if not 300 <= self.video_length_seconds <= 480:
            raise ValueError("Documentary videos must be 5-8 minutes long unless --allow-short-render is used.")
        if not 20 <= self.scene_count <= 30:
            raise ValueError("Documentary videos must use 20-30 scenes unless --allow-short-render is used.")
