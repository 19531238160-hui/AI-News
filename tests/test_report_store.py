from pathlib import Path

from ai_news.report_store import report_path_for_date, save_report


def test_report_path_for_date_uses_reports_directory():
    path = report_path_for_date("2026-04-30")

    assert path == Path("reports") / "2026-04-30.md"


def test_save_report_creates_directory_and_writes_markdown(tmp_path):
    path = save_report("# 标题\n", "2026-04-30", root=tmp_path)

    assert path == tmp_path / "reports" / "2026-04-30.md"
    assert path.read_text(encoding="utf-8") == "# 标题\n"
