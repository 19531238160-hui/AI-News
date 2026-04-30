from datetime import datetime, timezone

import pytest

from ai_news.config import AppConfig
from ai_news.news_sources import (
    DEFAULT_RSS_FEEDS,
    NewsSourceError,
    fetch_all_news,
    fetch_news_api_items,
    parse_feed_entries,
)


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


def make_config(news_api_provider="", news_api_key=""):
    return AppConfig(
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
        news_api_provider=news_api_provider,
        news_api_key=news_api_key,
        dry_run=False,
    )


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


def test_parse_feed_entries_treats_parsed_time_as_utc():
    items = parse_feed_entries("OpenAI Blog", FakeFeed.entries)

    assert items[0].published_at == datetime(2026, 4, 30, 8, 0, tzinfo=timezone.utc)


def test_fetch_all_news_uses_rss_when_news_api_missing(monkeypatch):
    def fake_parse(url):
        assert url
        return FakeFeed()

    def fail_get(*args, **kwargs):
        raise AssertionError("requests.get should not be called")

    monkeypatch.setattr("ai_news.news_sources.requests.get", fail_get)
    config = make_config()

    items, metadata = fetch_all_news(
        config,
        rss_feeds=[("OpenAI Blog", "https://example.com/rss")],
        feed_parser=fake_parse,
    )

    assert len(items) == 1
    assert items[0].source == "OpenAI Blog"
    assert metadata["news_api_used"] is False


def test_fetch_news_api_items_returns_empty_when_unconfigured(monkeypatch):
    def fail_get(*args, **kwargs):
        raise AssertionError("requests.get should not be called")

    monkeypatch.setattr("ai_news.news_sources.requests.get", fail_get)

    assert fetch_news_api_items(make_config()) == []


def test_fetch_news_api_items_requests_newsapi_and_parses_articles(monkeypatch):
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "articles": [
                    {
                        "title": "New model evaluation benchmark",
                        "url": "https://example.com/model-eval",
                        "publishedAt": "2026-04-30T08:00:00Z",
                        "description": "Benchmark details for AI trainers.",
                        "source": {"name": "Example News"},
                    },
                    {
                        "title": "",
                        "url": "https://example.com/skip",
                    },
                ]
            }

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        return FakeResponse()

    monkeypatch.setattr("ai_news.news_sources.requests.get", fake_get)

    items = fetch_news_api_items(make_config("newsapi", "secret-key"))

    assert calls == [
        (
            "https://newsapi.org/v2/everything",
            {
                "q": '(AI OR "artificial intelligence" OR LLM OR "prompt engineering" OR "model evaluation")',
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 20,
                "apiKey": "secret-key",
            },
            20,
        )
    ]
    assert len(items) == 1
    assert items[0].title == "New model evaluation benchmark"
    assert items[0].url == "https://example.com/model-eval"
    assert items[0].source == "Example News"
    assert items[0].published_at == datetime(2026, 4, 30, 8, 0, tzinfo=timezone.utc)
    assert items[0].summary == "Benchmark details for AI trainers."


def test_fetch_news_api_items_raises_newsapi_status_error(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"status": "error", "message": "API key disabled"}

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("ai_news.news_sources.requests.get", fake_get)

    with pytest.raises(NewsSourceError, match="API key disabled"):
        fetch_news_api_items(make_config("newsapi", "secret-key"))


def test_fetch_all_news_raises_when_configured_news_api_fails(monkeypatch):
    def fake_parse(url):
        assert url
        return FakeFeed()

    def fail_get(*args, **kwargs):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr("ai_news.news_sources.requests.get", fail_get)

    with pytest.raises(NewsSourceError):
        fetch_all_news(
            make_config("newsapi", "secret-key"),
            rss_feeds=[("OpenAI Blog", "https://example.com/rss")],
            feed_parser=fake_parse,
        )
