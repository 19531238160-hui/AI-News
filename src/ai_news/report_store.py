from __future__ import annotations

from pathlib import Path


def report_path_for_date(report_date: str) -> Path:
    return Path("reports") / f"{report_date}.md"


def save_report(markdown: str, report_date: str, root: Path | str = ".") -> Path:
    root_path = Path(root)
    path = root_path / report_path_for_date(report_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path
