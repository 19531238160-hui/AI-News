from datetime import timezone

from ai_news.config import AppConfig
from ai_news.news_sources import DEFAULT_RSS_FEEDS, fetch_all_news, parse_feed_entries


class FakeFeed:
    entries = [
        {
            "title": "OpenAI shares evaluation update",
            "link": "https://example.com/openai-eval",
            "published_parsed": (2026, 4, 30, 8, 0, 0, 0, 0, 0),
            "summary": "Evaluation details for AI trainers.",
        },
        {
            "title": "",
            "link": "https://example.com/empty",
        },
    ]


def test_default_rss_feeds_cover_ai_sources():
    names = [name for name, _url in DEFAULT_RSS_FEEDS]

    assert "OpenAI Blog" in names
    assert "Google DeepMind Blog" in names
    assert "Hugging Face Blog" in names


def test_parse_feed_entries_skips_entries_without_title():
    items = parse_feed_entries("OpenAI Blog", FakeFeed.entries)

    assert len(items) == 1
    assert items[0].title == "OpenAI shares evaluation update"
    assert items[0].published_at.tzinfo == timezone.utc


def test_fetch_all_news_uses_rss_when_news_api_missing(monkeypatch):
    def fake_parse(url):
        assert url
        return FakeFeed()

    config = AppConfig(
        ai_api_key="ai-key",
        ai_base_url="https://api.example.com",
        ai_model="model",
        ai_api_style="responses",
        mail_host="smtp.163.com",
        mail_port=465,
        mail_username="sender@163.com",
        mail_password="auth",
        mail_from="sender@163.com",
        mail_to="reader@example.com",
        news_api_provider="",
        news_api_key="",
        dry_run=False,
    )

    items, metadata = fetch_all_news(
        config,
        rss_feeds=[("OpenAI Blog", "https://example.com/rss")],
        feed_parser=fake_parse,
    )

    assert len(items) == 1
    assert items[0].source == "OpenAI Blog"
    assert metadata["news_api_used"] is False
