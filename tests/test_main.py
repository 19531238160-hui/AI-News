from datetime import date, datetime, timezone

from ai_news.config import AppConfig
from ai_news.main import run
from ai_news.models import NewsItem


def config(dry_run=True):
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
        news_api_provider="",
        news_api_key="",
        dry_run=dry_run,
    )


def test_run_saves_report_and_skips_email_in_dry_run(tmp_path):
    calls = {"email": 0}

    def fake_fetch(_config):
        return (
            [
                NewsItem(
                    title="Prompt evaluation news",
                    url="https://example.com/eval",
                    source="Example",
                    published_at=datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc),
                    summary="Evaluation",
                )
            ],
            {"news_api_used": False},
        )

    def fake_summarize(_config, items, report_date, expanded_window, news_api_used):
        assert report_date == "2026-04-30"
        assert expanded_window is True
        assert news_api_used is False
        assert len(items) == 1
        return "# 每日 AI 热点新闻简报\n"

    def fake_send(*args, **kwargs):
        calls["email"] += 1

    path = run(
        config(dry_run=True),
        today=date(2026, 4, 30),
        root=tmp_path,
        fetch_news=fake_fetch,
        summarize=fake_summarize,
        send=fake_send,
    )

    assert calls["email"] == 0
    assert path == tmp_path / "reports" / "2026-04-30.md"
    assert path.read_text(encoding="utf-8").startswith("# 每日 AI 热点新闻简报")


def test_run_sends_email_when_not_dry_run(tmp_path):
    calls = {"email": 0}

    def fake_fetch(_config):
        return (
            [
                NewsItem(
                    title=f"AI news {index}",
                    url=f"https://example.com/{index}",
                    source="Example",
                    published_at=datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc),
                    summary="AI model evaluation",
                )
                for index in range(10)
            ],
            {"news_api_used": True},
        )

    def fake_summarize(*args, **kwargs):
        return "# 简报\n"

    def fake_send(_config, markdown, report_date):
        calls["email"] += 1
        assert markdown == "# 简报\n"
        assert report_date == "2026-04-30"

    run(
        config(dry_run=False),
        today=date(2026, 4, 30),
        root=tmp_path,
        fetch_news=fake_fetch,
        summarize=fake_summarize,
        send=fake_send,
    )

    assert calls["email"] == 1
