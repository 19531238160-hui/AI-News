from __future__ import annotations

import re
from datetime import date
from pathlib import Path

_REPORT_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def report_path_for_date(report_date: str) -> Path:
    if not _REPORT_DATE_RE.fullmatch(report_date):
        raise ValueError("report_date must use YYYY-MM-DD format")
    try:
        date.fromisoformat(report_date)
    except ValueError as exc:
        raise ValueError("report_date must be a valid YYYY-MM-DD date") from exc
    return Path("reports") / f"{report_date}.md"


def save_report(markdown: str, report_date: str, root: Path | str = ".") -> Path:
    root_path = Path(root)
    reports_root = (root_path / "reports").resolve()
    path = (root_path / report_path_for_date(report_date)).resolve()
    if path.parent != reports_root:
        raise ValueError("report path must stay inside the reports directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path
