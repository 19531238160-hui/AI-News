import smtplib
from email.message import EmailMessage

import pytest

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
        mail_password="secret-password",
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


def test_markdown_to_html_escapes_raw_html_but_keeps_markdown_rendering():
    html = markdown_to_html("# Title\n\n<script>alert(1)</script>\n<img src=x>\n\n`<tag>`")

    assert "<h1>Title</h1>" in html
    assert "<script>" not in html
    assert "<img" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&lt;img src=x&gt;" in html
    assert "<code>&lt;tag&gt;</code>" in html


def test_markdown_to_html_removes_dangerous_link_protocols():
    html = markdown_to_html("[safe](https://example.com) [bad](javascript:alert(1))")

    assert 'href="https://example.com"' in html
    assert "javascript:" not in html


def test_markdown_to_html_removes_dangerous_attributes_from_allowed_tags():
    html = markdown_to_html('<h1 style="color:red">Title</h1>')

    assert "<h1>Title</h1>" in html
    assert "style=" not in html


def test_markdown_to_html_keeps_safe_anchor_href_and_removes_dangerous_attributes():
    html = markdown_to_html('<a href="https://example.com" onclick="alert(1)" style="color:red">safe</a>')

    assert '<a href="https://example.com">safe</a>' in html
    assert "onclick=" not in html
    assert "style=" not in html


def test_markdown_to_html_renders_markdown_links_with_safe_href():
    html = markdown_to_html("[safe](https://example.com)")

    assert '<a href="https://example.com">safe</a>' in html


def test_build_email_message_contains_plain_and_html_parts():
    message = build_email_message(config(), "# 标题", "2026-04-30")

    assert isinstance(message, EmailMessage)
    assert message["Subject"] == "每日 AI 热点新闻简报 - 2026-04-30"
    assert message["From"] == "sender@163.com"
    assert message["To"] == "reader@example.com"
    assert message.is_multipart()
    assert message.get_content_type() == "multipart/alternative"

    parts = message.get_payload()
    assert len(parts) == 2
    assert parts[0].get_content_type() == "text/plain"
    assert parts[0].get_content_charset() == "utf-8"
    assert parts[1].get_content_type() == "text/html"
    assert parts[1].get_content_charset() == "utf-8"


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
    assert calls["login"] == ("sender@163.com", "secret-password")
    assert calls["subject"] == "每日 AI 热点新闻简报 - 2026-04-30"


def test_send_email_wraps_authentication_errors_without_password():
    class FailingSMTP:
        def __init__(self, host, port):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def login(self, username, password):
            raise smtplib.SMTPAuthenticationError(535, b"auth failed")

    with pytest.raises(RuntimeError) as exc_info:
        send_email(config(), "# Title", "2026-04-30", smtp_ssl=FailingSMTP)

    message = str(exc_info.value)
    assert "NetEase" in message
    assert "SMTP authorization code" in message
    assert "secret-password" not in message


@pytest.mark.parametrize("error", [smtplib.SMTPException("boom"), OSError("network down")])
def test_send_email_wraps_smtp_and_os_errors_with_connection_context(error):
    class FailingSMTP:
        def __init__(self, host, port):
            raise error

    with pytest.raises(RuntimeError) as exc_info:
        send_email(config(), "# Title", "2026-04-30", smtp_ssl=FailingSMTP)

    message = str(exc_info.value)
    assert "smtp.163.com" in message
    assert "465" in message
    assert "sender@163.com" in message
    assert "reader@example.com" in message
    assert "SMTP host" in message
    assert "authorization code" in message
    assert "recipient" in message
    assert "secret-password" not in message
