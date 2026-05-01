from pathlib import Path


def test_daily_workflow_uses_multiple_non_peak_schedule_attempts():
    workflow = Path(".github/workflows/daily-ai-news.yml").read_text(encoding="utf-8")

    assert 'cron: "17 11 * * *"' in workflow
    assert 'cron: "47 11 * * *"' in workflow
    assert 'cron: "17 12 * * *"' in workflow
    assert 'cron: "45 12 * * *"' in workflow
    assert 'cron: "15 13 * * *"' in workflow
    assert 'cron: "0 11 * * *"' not in workflow


def test_daily_workflow_skips_only_after_email_sent_marker_exists():
    workflow = Path(".github/workflows/daily-ai-news.yml").read_text(encoding="utf-8")

    assert "id: email_marker" in workflow
    assert 'TZ=Asia/Shanghai date +%F' in workflow
    assert 'reports/.email-sent-${report_date}' in workflow
    assert 'if: github.event_name != \'schedule\' || steps.email_marker.outputs.exists != \'true\'' in workflow
    assert "Generate and email daily report" in workflow
    assert "Mark email sent" in workflow
    assert "reports/.email-sent-*" in workflow


def test_daily_workflow_syncs_before_pushing_reports():
    workflow = Path(".github/workflows/daily-ai-news.yml").read_text(encoding="utf-8")

    assert "concurrency:" in workflow
    assert "fetch-depth: 0" in workflow
    assert "git fetch origin main:refs/remotes/origin/main" in workflow
    assert "git rebase origin/main" in workflow
    assert "git push origin HEAD:main" in workflow
    assert "git push\n" not in workflow


def test_daily_workflow_uses_node_24_compatible_actions():
    workflow = Path(".github/workflows/daily-ai-news.yml").read_text(encoding="utf-8")

    assert "uses: actions/checkout@v6" in workflow
    assert "uses: actions/setup-python@v6" in workflow
    assert "uses: actions/checkout@v4" not in workflow
    assert "uses: actions/setup-python@v5" not in workflow
