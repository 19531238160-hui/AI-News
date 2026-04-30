from __future__ import annotations

import argparse
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Callable

from .config import AppConfig, load_config
from .email_sender import send_email
from .news_sources import fetch_all_news, filter_recent_items, rank_items
from .report_store import save_report
from .summarizer import summarize_news


def run(
    config: AppConfig,
    today: date | None = None,
    root: Path | str = ".",
    fetch_news: Callable = fetch_all_news,
    summarize: Callable = summarize_news,
    send: Callable = send_email,
) -> Path:
    report_day = today or date.today()
    report_date = report_day.isoformat()

    fetched_items, metadata = fetch_news(config)
    report_end = datetime.combine(report_day, time(23, 59, 59, tzinfo=timezone.utc))
    recent_items, expanded_window = filter_recent_items(
        fetched_items,
        min_items=8,
        now=report_end,
    )
    ranked_items = rank_items(recent_items, limit=10)
    if not ranked_items:
        raise RuntimeError("No AI news items were found. Check RSS sources or NEWS_API settings.")

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

    config = load_config(dry_run_override=True if args.dry_run else None)

    run(config)
