from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AutomationConfig:
    """Runtime settings loaded from environment variables and CLI flags."""

    output_dir: Path = Path("dist")
    topic_count: int = 8
    video_length_seconds: int = 480
    scene_count: int = 30
    youtube_privacy_status: str = "private"
    youtube_category_id: str = "24"
    channel_name: str = "Daily Documentary"
    documentary_topic: str = "A hidden story from history"
    tts_provider: str = "openai"
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice: str = "alloy"
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    tts_attempts: int = 3
    transition_seconds: float = 1.0

    @classmethod
    def from_env(cls, *, output_dir: str | None = None) -> "AutomationConfig":
        return cls(
            output_dir=Path(output_dir or os.getenv("OUTPUT_DIR", "dist")),
            topic_count=int(os.getenv("TOPIC_COUNT", "8")),
            video_length_seconds=int(os.getenv("VIDEO_LENGTH_SECONDS", "480")),
            scene_count=int(os.getenv("SCENE_COUNT", "30")),
            youtube_privacy_status=os.getenv("YOUTUBE_PRIVACY_STATUS", "private"),
            youtube_category_id=os.getenv("YOUTUBE_CATEGORY_ID", "24"),
            channel_name=os.getenv("CHANNEL_NAME", "Daily Documentary"),
            documentary_topic=os.getenv("DOCUMENTARY_TOPIC", "A hidden story from history"),
            tts_provider=os.getenv("TTS_PROVIDER", "openai").lower(),
            openai_tts_model=os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
            openai_tts_voice=os.getenv("OPENAI_TTS_VOICE", "alloy"),
            elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
            elevenlabs_model_id=os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
            tts_attempts=int(os.getenv("TTS_ATTEMPTS", "3")),
            transition_seconds=float(os.getenv("TRANSITION_SECONDS", "1.0")),
        )

    def ensure_output_dir(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir

    def validate_for_documentary(self) -> None:
        if not 360 <= self.video_length_seconds <= 600:
            raise ValueError("Documentary videos must be 6-10 minutes long unless --allow-short-render is used.")
        if not 20 <= self.scene_count <= 40:
            raise ValueError("Documentary videos must use 20-40 scenes unless --allow-short-render is used.")
