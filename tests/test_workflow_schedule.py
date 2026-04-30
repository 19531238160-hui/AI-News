from pathlib import Path


def test_daily_workflow_avoids_top_of_hour_schedule():
    workflow = Path(".github/workflows/daily-ai-news.yml").read_text(encoding="utf-8")

    assert 'cron: "17 11 * * *"' in workflow
    assert 'cron: "0 11 * * *"' not in workflow
