from pathlib import Path


def test_daily_workflow_avoids_top_of_hour_schedule():
    workflow = Path(".github/workflows/daily-ai-news.yml").read_text(encoding="utf-8")

    assert 'cron: "17 11 * * *"' in workflow
    assert 'cron: "0 11 * * *"' not in workflow


def test_daily_workflow_syncs_before_pushing_reports():
    workflow = Path(".github/workflows/daily-ai-news.yml").read_text(encoding="utf-8")

    assert "concurrency:" in workflow
    assert "git fetch origin main" in workflow
    assert "git rebase origin/main" in workflow
    assert "git push origin HEAD:main" in workflow
    assert "git push\n" not in workflow
