from email.message import EmailMessage

from ai_news.config import AppConfig
from ai_news.email_sender import build_email_message, markdown_to_html, send_email


def config():
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
        dry_run=False,
    )


def test_markdown_to_html_renders_heading_and_list():
    html = markdown_to_html("# 标题\n\n- 要点")

    assert "<h1>标题</h1>" in html
    assert "<li>要点</li>" in html


def test_build_email_message_contains_plain_and_html_parts():
    message = build_email_message(config(), "# 标题", "2026-04-30")

    assert isinstance(message, EmailMessage)
    assert message["Subject"] == "每日 AI 热点新闻简报 - 2026-04-30"
    assert message["From"] == "sender@163.com"
    assert message["To"] == "reader@example.com"
    assert message.is_multipart()


def test_send_email_uses_ssl_smtp():
    calls = {}

    class FakeSMTP:
        def __init__(self, host, port):
            calls["host"] = host
            calls["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def login(self, username, password):
            calls["login"] = (username, password)

        def send_message(self, message):
            calls["subject"] = message["Subject"]

    send_email(config(), "# 标题", "2026-04-30", smtp_ssl=FakeSMTP)

    assert calls["host"] == "smtp.163.com"
    assert calls["port"] == 465
    assert calls["login"] == ("sender@163.com", "auth")
    assert calls["subject"] == "每日 AI 热点新闻简报 - 2026-04-30"
