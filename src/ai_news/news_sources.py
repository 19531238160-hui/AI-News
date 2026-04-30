from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Iterable

from .models import NewsItem, normalize_title


TRAINER_KEYWORDS = {
    "ai": 2,
    "llm": 3,
    "model": 2,
    "openai": 3,
    "anthropic": 3,
    "deepmind": 3,
    "hugging face": 3,
    "prompt": 4,
    "prompt engineering": 5,
    "data labeling": 5,
    "annotation": 4,
    "evaluation": 5,
    "benchmark": 4,
    "safety": 4,
    "alignment": 4,
    "multimodal": 3,
    "agent": 3,
}

_WORD_PATTERN = re.compile(r"[a-z0-9]+")


def dedupe_items(items: Iterable[NewsItem]) -> list[NewsItem]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    result: list[NewsItem] = []

    for item in items:
        url_key = item.url.strip().lower()
        title_key = normalize_title(item.title)
        if not url_key or not title_key:
            continue
        if url_key in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url_key)
        seen_titles.add(title_key)
        result.append(item)

    return result


def filter_recent_items(
    items: Iterable[NewsItem],
    min_items: int = 8,
    now: datetime | None = None,
) -> tuple[list[NewsItem], bool]:
    current = now or datetime.now(timezone.utc)
    current = current.astimezone(timezone.utc)
    sorted_items = sorted(items, key=lambda news: news.published_utc(), reverse=True)

    recent = [
        news
        for news in sorted_items
        if timedelta(0) <= current - news.published_utc() <= timedelta(hours=48)
    ]
    if len(recent) >= min_items:
        return recent, False

    expanded = [
        news
        for news in sorted_items
        if timedelta(0) <= current - news.published_utc() <= timedelta(hours=72)
    ]
    return expanded, True


def _normalized_words(text: str) -> list[str]:
    return _WORD_PATTERN.findall(text.lower())


def _matches_keyword(keyword: str, words: list[str], normalized_text: str) -> bool:
    keyword_words = _normalized_words(keyword)
    if len(keyword_words) > 1:
        return f" {' '.join(keyword_words)} " in normalized_text
    if not keyword_words:
        return False
    keyword_word = keyword_words[0]
    return any(
        word == keyword_word and (index == 0 or words[index - 1] != "not")
        for index, word in enumerate(words)
    )


def _score_item(item: NewsItem) -> int:
    words = _normalized_words(f"{item.title} {item.summary} {item.source}")
    normalized_text = f" {' '.join(words)} "
    score = 0
    for keyword, weight in TRAINER_KEYWORDS.items():
        if _matches_keyword(keyword, words, normalized_text):
            score += weight
    return score


def rank_items(items: Iterable[NewsItem], limit: int = 10) -> list[NewsItem]:
    return sorted(
        items,
        key=lambda news: (_score_item(news), news.published_utc()),
        reverse=True,
    )[:limit]
