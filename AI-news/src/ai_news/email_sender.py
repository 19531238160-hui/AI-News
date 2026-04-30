from __future__ import annotations

from html import escape
from html.parser import HTMLParser
import smtplib
from email.message import EmailMessage
from typing import Callable
from urllib.parse import urlsplit

import markdown

from .config import AppConfig

_ALLOWED_LINK_SCHEMES = {"http", "https", "mailto"}
_ALLOWED_HTML_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "ul",
}


class _LinkSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _ALLOWED_HTML_TAGS:
            self.parts.append(escape(self.get_starttag_text() or f"<{tag}>"))
            return
        self.parts.append(self.get_starttag_text_from(tag, self.sanitize_attrs(tag, attrs)))

    def handle_endtag(self, tag: str) -> None:
        if tag not in _ALLOWED_HTML_TAGS:
            self.parts.append(escape(f"</{tag}>"))
            return
        self.parts.append(f"</{tag}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _ALLOWED_HTML_TAGS:
            self.parts.append(escape(self.get_starttag_text() or f"<{tag}>"))
            return
        self.handle_starttag(tag, attrs)

    def handle_data(self, data: str) -> None:
        self.parts.append(escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.parts.append(f"&#{name};")

    def get_starttag_text_from(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        if not attrs:
            return f"<{tag}>"
        rendered_attrs = []
        for name, value in attrs:
            if value is None:
                rendered_attrs.append(name)
            else:
                rendered_attrs.append(f'{name}="{escape(value, quote=True)}"')
        return f"<{tag} {' '.join(rendered_attrs)}>"

    def sanitize_attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> list[tuple[str, str | None]]:
        if tag != "a":
            return []

        safe_attrs = []
        for name, value in attrs:
            attr_name = name.lower()
            if attr_name == "href" and value is not None:
                if urlsplit(value).scheme.lower() in _ALLOWED_LINK_SCHEMES:
                    safe_attrs.append(("href", value))
            elif attr_name == "title" and value is not None:
                safe_attrs.append(("title", value))
        return safe_attrs


def _sanitize_markdown_links(html_text: str) -> str:
    sanitizer = _LinkSanitizer()
    sanitizer.feed(html_text)
    sanitizer.close()
    return "".join(sanitizer.parts)


def markdown_to_html(markdown_text: str) -> str:
    body = markdown.markdown(markdown_text, extensions=["extra", "sane_lists"])
    body = _sanitize_markdown_links(body)
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
    except (smtplib.SMTPException, OSError) as exc:
        raise RuntimeError(
            "Email delivery failed via "
            f"{config.mail_host}:{config.mail_port} from {config.mail_from} to {config.mail_to}. "
            "Check SMTP host, SMTP port, SMTP authorization code, and recipient."
        ) from exc
