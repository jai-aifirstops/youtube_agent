from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

from .topics import InterestingTopic


@dataclass(frozen=True)
class VideoScript:
    title: str
    description: str
    narration: str
    hashtags: list[str]


def build_script(topics: list[InterestingTopic], day: dt.date, *, channel_name: str) -> VideoScript:
    if not topics:
        raise ValueError("At least one topic is required to build a video script.")

    date_text = day.strftime("%B %d, %Y").replace(" 0", " ")
    title = f"Top 10 Interesting Topics Today - {day.isoformat()}"
    hashtags = ["#Shorts", "#Top10", "#InterestingFacts", "#DailyFacts"]
    description_lines = [
        f"{channel_name} presents ten quick interesting topics for {date_text}.",
        "",
        *[f"{topic.rank}. {topic.title}: {topic.summary}" for topic in topics],
        "",
        "Generated with an automated daily educational video pipeline.",
        " ".join(hashtags),
    ]

    intro = f"Today's top ten interesting topics for {date_text}."
    topic_lines = [
        f"Number {topic.rank}: {topic.title}. {_one_sentence(topic.summary, max_words=7)}"
        for topic in topics
    ]
    outro = "Follow for tomorrow's one-minute list."

    return VideoScript(
        title=title,
        description="\n".join(description_lines),
        narration=" ".join([intro, *topic_lines, outro]),
        hashtags=hashtags,
    )


def _one_sentence(text: str, *, max_words: int) -> str:
    sentence = re.split(r"(?<=[.!?])\s+", text.strip())[0]
    words = sentence.split()
    if len(words) <= max_words:
        return sentence
    clipped_words = words[:max_words]
    while clipped_words and clipped_words[-1].rstrip(",;:").lower() in {"a", "an", "and", "in", "of", "or", "the", "to"}:
        clipped_words.pop()
    return " ".join(clipped_words).rstrip(",;:") + "."
