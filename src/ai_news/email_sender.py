from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Callable

import markdown

from .config import AppConfig


def markdown_to_html(markdown_text: str) -> str:
    body = markdown.markdown(markdown_text, extensions=["extra", "sane_lists"])
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.65; color: #222; }}
    code, pre {{ background: #f6f8fa; border-radius: 4px; }}
    pre {{ padding: 12px; overflow-x: auto; }}
    blockquote {{ border-left: 4px solid #ddd; padding-left: 12px; color: #555; }}
    a {{ color: #0969da; }}
  </style>
</head>
<body>
{body}
</body>
</html>"""


def build_email_message(config: AppConfig, markdown_text: str, report_date: str) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = f"每日 AI 热点新闻简报 - {report_date}"
    message["From"] = config.mail_from
    message["To"] = config.mail_to
    message.set_content(markdown_text, subtype="plain", charset="utf-8")
    message.add_alternative(markdown_to_html(markdown_text), subtype="html", charset="utf-8")
    return message


def send_email(
    config: AppConfig,
    markdown_text: str,
    report_date: str,
    smtp_ssl: Callable = smtplib.SMTP_SSL,
) -> None:
    message = build_email_message(config, markdown_text, report_date)
    try:
        with smtp_ssl(config.mail_host, config.mail_port) as smtp:
            smtp.login(config.mail_username, config.mail_password)
            smtp.send_message(message)
    except smtplib.SMTPAuthenticationError as exc:
        raise RuntimeError(
            "Email authentication failed. For NetEase email, MAIL_PASSWORD must be "
            "the SMTP authorization code, not your normal login password."
        ) from exc
