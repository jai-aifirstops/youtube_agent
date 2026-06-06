from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class InterestingTopic:
    rank: int
    title: str
    summary: str


FALLBACK_TOPICS = [
    InterestingTopic(1, "Octopuses", "Octopuses have blue blood, three hearts, and problem-solving skills that can rival some mammals."),
    InterestingTopic(2, "Lightning", "A single lightning bolt can heat the surrounding air hotter than the surface of the sun."),
    InterestingTopic(3, "The Moon", "The moon is slowly drifting away from Earth by about the width of a fingernail each year."),
    InterestingTopic(4, "Honey", "Archaeologists have found honey in ancient tombs that remained edible after thousands of years."),
    InterestingTopic(5, "Bananas", "Bananas are berries by botanical definition, while strawberries are not."),
    InterestingTopic(6, "Sharks", "Sharks are older than trees, with ancestors swimming the oceans before forests existed."),
    InterestingTopic(7, "Glass", "Glass can behave like an extremely slow-moving amorphous solid rather than a normal crystal."),
    InterestingTopic(8, "Ants", "Some ant colonies farm fungi, herd aphids, and build complex climate-controlled nests."),
    InterestingTopic(9, "Space Smell", "Astronauts often describe space-exposed equipment as smelling metallic or like seared steak."),
    InterestingTopic(10, "Human Memory", "Memory is reconstructed each time we recall it, which is why details can shift over time."),
]


def fetch_daily_topics(day: dt.date, *, count: int = 10, offline: bool = False) -> list[InterestingTopic]:
    """Return ranked daily topics from Wikimedia, falling back to curated facts."""
    if offline:
        return FALLBACK_TOPICS[:count]

    try:
        topics = _fetch_wikimedia_on_this_day(day, count=count)
    except Exception:
        topics = []

    if len(topics) >= count:
        return topics[:count]

    needed = count - len(topics)
    fallback = [topic for topic in FALLBACK_TOPICS if topic.title not in {item.title for item in topics}]
    return topics + fallback[:needed]


def _fetch_wikimedia_on_this_day(day: dt.date, *, count: int) -> list[InterestingTopic]:
    import requests

    url = f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/events/{day.month:02d}/{day.day:02d}"
    response = requests.get(
        url,
        headers={"User-Agent": "youtube-agent/0.1 (daily educational video automation)"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()

    events = payload.get("events", [])
    random.Random(day.isoformat()).shuffle(events)

    topics: list[InterestingTopic] = []
    for event in events:
        pages = event.get("pages") or []
        title = _clean_text(pages[0].get("normalizedtitle") or pages[0].get("title")) if pages else None
        text = _clean_text(event.get("text"))
        year = event.get("year")

        if not title or not text:
            continue

        summary = f"In {year}, {text}" if year else text
        topics.append(InterestingTopic(len(topics) + 1, title=title, summary=summary))
        if len(topics) == count:
            break

    return topics


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").replace("_", " ").split())
