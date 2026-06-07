from __future__ import annotations

from pathlib import Path

from .documentary import DocumentaryScene


def write_srt(scenes: list[DocumentaryScene], output_path: Path) -> Path:
    cursor = 0.0
    blocks: list[str] = []
    for index, scene in enumerate(scenes, start=1):
        start = cursor
        end = cursor + scene.duration_seconds
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{_timestamp(start)} --> {_timestamp(end)}",
                    scene.subtitle,
                ]
            )
        )
        cursor = end

    output_path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    return output_path


def _timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
