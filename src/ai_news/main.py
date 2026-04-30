from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

from .config import AppConfig, load_config
from .email_sender import send_email
from .news_sources import fetch_all_news, filter_recent_items, rank_items
from .report_store import save_report
from .summarizer import summarize_news


def _report_timezone():
    try:
        return ZoneInfo("Asia/Shanghai")
    except Exception:
        return timezone(timedelta(hours=8), "Asia/Shanghai")


REPORT_TIMEZONE = _report_timezone()
NO_NEWS_TROUBLESHOOTING = (
    "No AI news items were found. Check RSS source availability, "
    "NEWS_API_PROVIDER/NEWS_API_KEY configuration, and network access."
)
CLI_TROUBLESHOOTING = (
    "Troubleshooting: verify RSS feeds are reachable, NEWS_API_PROVIDER and "
    "NEWS_API_KEY are configured when using a news API, and network access is available."
)


def report_context(
    today: date | None = None,
    now: datetime | None = None,
) -> tuple[date, str, datetime]:
    if today is None:
        current = now or datetime.now(REPORT_TIMEZONE)
        report_day = current.astimezone(REPORT_TIMEZONE).date()
    else:
        report_day = today

    report_date = report_day.isoformat()
    report_end_beijing = datetime.combine(
        report_day,
        time(23, 59, 59),
        tzinfo=REPORT_TIMEZONE,
    )
    report_end_utc = report_end_beijing.astimezone(timezone.utc)
    return report_day, report_date, report_end_utc


def _redact_secrets(message: str, config: AppConfig | None) -> str:
    if config is None:
        return message

    redacted = message
    for secret in (config.ai_api_key, config.mail_password, config.news_api_key):
        if secret:
            redacted = redacted.replace(secret, "[redacted]")
    return redacted


def run(
    config: AppConfig,
    today: date | None = None,
    root: Path | str = ".",
    fetch_news: Callable = fetch_all_news,
    summarize: Callable = summarize_news,
    send: Callable = send_email,
) -> Path:
    _report_day, report_date, report_end = report_context(today=today)

    fetched_items, metadata = fetch_news(config)
    recent_items, expanded_window = filter_recent_items(
        fetched_items,
        min_items=8,
        now=report_end,
    )
    ranked_items = rank_items(recent_items, limit=10)
    if not ranked_items:
        raise RuntimeError(NO_NEWS_TROUBLESHOOTING)

    markdown = summarize(
        config,
        ranked_items,
        report_date,
        expanded_window,
        bool(metadata.get("news_api_used")),
    )
    path = save_report(markdown, report_date, root=root)

    if config.dry_run:
        print(f"Dry run enabled; email skipped. Report saved to {path}")
    else:
        send(config, markdown, report_date)
        print(f"Email sent to {config.mail_to}. Report saved to {path}")

    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and email a daily AI news report.")
    parser.add_argument("--dry-run", action="store_true", help="Generate Markdown without sending email.")
    args = parser.parse_args()

    config = None
    try:
        config = load_config(dry_run_override=True if args.dry_run else None)
        run(config)
    except Exception as exc:
        print(f"Error: {_redact_secrets(str(exc), config)}", file=sys.stderr)
        print(CLI_TROUBLESHOOTING, file=sys.stderr)
        raise SystemExit(1) from exc

    raise SystemExit(0)
