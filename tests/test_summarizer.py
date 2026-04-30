from datetime import datetime, timezone

import pytest

from ai_news.config import AppConfig
from ai_news.models import NewsItem
from ai_news.summarizer import SummarizerError, build_prompt, summarize_news


def config():
    return AppConfig(
        ai_api_key="ai-key",
        ai_base_url="https://api.example.com/api/codex/backend-api/codex",
        ai_model="gpt-5-codex",
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


def news_item():
    return NewsItem(
        title="OpenAI updates model evaluation",
        url="https://example.com/eval",
        source="OpenAI Blog",
        published_at=datetime(2026, 4, 30, 8, 0, tzinfo=timezone.utc),
        summary="Evaluation update",
    )


def test_build_prompt_targets_beginner_ai_trainers():
    prompt = build_prompt([news_item()], "2026-04-30", expanded_window=False, news_api_used=False)

    assert "AI 训练师初学者" in prompt
    assert "Markdown" in prompt
    assert "代码示例" in prompt
    assert "OpenAI updates model evaluation" in prompt


def test_summarize_news_calls_responses_api():
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"output_text": "# 每日 AI 热点新闻简报\n\n## 今日速览\n- 测试"}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    markdown = summarize_news(
        config(),
        [news_item()],
        "2026-04-30",
        expanded_window=False,
        news_api_used=False,
        post=fake_post,
    )

    assert captured["url"] == "https://api.example.com/api/codex/backend-api/codex/responses"
    assert captured["headers"]["Authorization"] == "Bearer ai-key"
    assert captured["json"]["model"] == "gpt-5-codex"
    assert markdown.startswith("# 每日 AI 热点新闻简报")


def test_summarize_news_fails_on_empty_model_output():
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"output_text": ""}

    with pytest.raises(SummarizerError):
        summarize_news(
            config(),
            [news_item()],
            "2026-04-30",
            expanded_window=False,
            news_api_used=False,
            post=lambda *args, **kwargs: FakeResponse(),
        )
