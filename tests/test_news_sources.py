from datetime import datetime, timedelta, timezone

from ai_news.models import NewsItem
from ai_news.news_sources import dedupe_items, filter_recent_items, rank_items


def item(title, url, hours_old=2, source="Example", summary=""):
    return NewsItem(
        title=title,
        url=url,
        source=source,
        published_at=datetime.now(timezone.utc) - timedelta(hours=hours_old),
        summary=summary,
    )


def test_dedupe_items_removes_duplicate_urls_and_titles():
    items = [
        item("OpenAI releases new model", "https://example.com/a"),
        item("OpenAI releases new model!", "https://example.com/b"),
        item("Different story", "https://example.com/a"),
        item("Evaluation benchmark updated", "https://example.com/c"),
    ]

    deduped = dedupe_items(items)

    assert [news.title for news in deduped] == [
        "OpenAI releases new model",
        "Evaluation benchmark updated",
    ]


def test_filter_recent_items_expands_to_72_hours_when_needed():
    items = [
        item("Recent model news", "https://example.com/recent", hours_old=3),
        item("Older evaluation news", "https://example.com/older", hours_old=60),
        item("Too old", "https://example.com/too-old", hours_old=120),
    ]

    selected, expanded = filter_recent_items(items, min_items=2, now=datetime.now(timezone.utc))

    assert expanded is True
    assert [news.title for news in selected] == ["Recent model news", "Older evaluation news"]


def test_rank_items_prioritizes_ai_trainer_relevant_keywords():
    items = [
        item("AI startup funding", "https://example.com/funding", summary="business"),
        item("New prompt engineering evaluation guide", "https://example.com/eval", summary="LLM evaluation"),
        item("Sports result", "https://example.com/sports", summary="not ai"),
    ]

    ranked = rank_items(items, limit=2)

    assert [news.title for news in ranked] == [
        "New prompt engineering evaluation guide",
        "AI startup funding",
    ]
