# Daily AI News Email Automation Design

## Goal

Build a GitHub Actions based Python project that automatically collects recent AI news every day, summarizes it for a beginner AI trainer, sends the report to a personal email inbox, and stores the Markdown report in the repository.

The report should be professional but not academic. It must use Markdown, include bullet points, and include one practical code example aimed at AI trainer learning.

## Audience

The primary reader is a beginner AI trainer who is learning AI trainer concepts. The report should explain why each news item matters, connect it to practical AI training work, and avoid assuming deep engineering or research background.

## Execution Environment

The project runs on GitHub Actions.

- Schedule: every day at 19:00 Beijing time.
- GitHub cron: `0 11 * * *`, because GitHub Actions schedules use UTC.
- Manual trigger: enabled with `workflow_dispatch` for testing.
- The user's local computer does not need to be turned on.

## Architecture

The system uses a small Python module layout:

- `src/main.py`: orchestrates the full workflow.
- `src/news_sources.py`: fetches news from RSS feeds and optional news search APIs.
- `src/summarizer.py`: calls the configured AI model and produces the Markdown report.
- `src/email_sender.py`: converts Markdown to HTML and sends email through SMTP.
- `src/report_store.py`: saves daily reports as Markdown files.
- `.github/workflows/daily-ai-news.yml`: runs the daily automation.
- `README.md`: explains setup and usage for a beginner.

The runtime flow is:

1. GitHub Actions starts on schedule or manual trigger.
2. The script reads configuration from environment variables and GitHub Secrets.
3. News candidates are fetched from RSS feeds.
4. If a news search API key is configured, the script fetches extra candidates from that API.
5. Candidates are normalized, deduplicated, filtered, and ranked.
6. The top 8-10 items are sent to the AI model for summarization.
7. The AI model returns a Chinese Markdown report.
8. The Markdown is converted to HTML and emailed through NetEase SMTP.
9. The Markdown report is saved to `reports/YYYY-MM-DD.md`.
10. GitHub Actions commits the new report back to the repository with `GITHUB_TOKEN`.

## Configuration

All secrets and deploy-time values are configured through GitHub Secrets or environment variables. No credentials are stored in code.

Required AI configuration:

```text
AI_API_KEY
AI_BASE_URL
AI_MODEL
AI_API_STYLE
```

`AI_API_STYLE` defaults to `responses`, which supports services such as an AICodeMirror Codex-style endpoint. The implementation should be structured so another style, such as `chat_completions`, can be added later without changing the rest of the workflow.

Required email configuration:

```text
MAIL_HOST=smtp.163.com
MAIL_PORT=465
MAIL_USERNAME
MAIL_PASSWORD
MAIL_FROM
MAIL_TO
```

For NetEase email, `MAIL_PASSWORD` means the SMTP authorization code, not the normal login password.

Optional news API configuration:

```text
NEWS_API_PROVIDER
NEWS_API_KEY
```

If no news API is configured, the project still runs with RSS sources only.

## News Collection

The project uses a hybrid source strategy:

- RSS and public feeds are the default source.
- A news search API is optional and only used when configured.

Default coverage should focus on:

- Global AI technology and product news.
- Model providers and labs such as OpenAI, Google DeepMind, Anthropic, Meta AI, and Microsoft AI.
- Open-source model and tooling ecosystems such as Hugging Face.
- AI trainer learning topics such as prompt engineering, data labeling, evaluation, AI safety, and multimodal model behavior.

Each news item is normalized to this shape:

```python
{
    "title": "News title",
    "url": "https://example.com/news",
    "source": "Source name",
    "published_at": "2026-04-30T10:00:00Z",
    "summary": "Optional source summary"
}
```

Filtering rules:

- Deduplicate by URL and normalized title.
- Prefer items from the last 24-48 hours.
- If there are not enough items, expand the window to 72 hours and mention this in the report.
- Prefer items about major model updates, product releases, AI policy and safety, training data, model evaluation, prompt engineering, and practical AI workflows.
- Select 8-10 final items for summarization.

## Report Format

The AI output must be Chinese Markdown.

The default structure is:

```markdown
# 每日 AI 热点新闻简报 - YYYY-MM-DD

## 今日速览
- ...

## 重点新闻
### 1. 新闻标题
- 来源：...
- 链接：...
- 发生了什么：...
- 为什么重要：...
- 初学者学习提示：...

## 今日概念补充
...

## 代码示例
...

## 延伸阅读
- ...
```

The tone should be:

- Chinese-first.
- Professional but not academic.
- Friendly to beginner AI trainers.
- Clear about practical relevance.

The code example should be AI-trainer oriented, such as:

- A prompt template.
- A data labeling JSON example.
- A small evaluation rubric.
- A simple Python example for reviewing labeled samples.

It should not default to advanced application engineering examples unless the day's news clearly calls for it.

## Email Delivery

The email sender uses NetEase SMTP by default:

- Host: `smtp.163.com`
- Port: `465`
- TLS mode: SMTP over SSL

The email body should be HTML converted from Markdown for readability. The original Markdown remains saved in `reports/YYYY-MM-DD.md`.

The recipient is configurable with `MAIL_TO`. It can initially be the same address as the sender and can be changed later without code changes.

## Report Storage And GitHub Commit

Daily reports are saved as:

```text
reports/YYYY-MM-DD.md
```

GitHub Actions automatically commits new reports to the repository using the built-in `GITHUB_TOKEN`.

Example commit message:

```text
chore: add AI news report for YYYY-MM-DD
```

The workflow should avoid committing when no report file changed.

## Error Handling

Errors should be actionable for a beginner.

Expected handling:

- Missing `AI_API_KEY`: fail with a message explaining that the AI Secret is required.
- Missing `AI_BASE_URL` or `AI_MODEL`: fail with setup guidance.
- Invalid NetEase SMTP authorization code: fail with a message explaining that `MAIL_PASSWORD` must be the SMTP authorization code.
- RSS source failure: skip the failing source and continue with other sources.
- Too few news items: expand the time window to 72 hours and note this in the report.
- AI API failure: fail the workflow rather than sending a low-quality empty report.
- Email sending failure: fail the workflow and point the user to SMTP host, port, authorization code, and recipient settings.
- Commit failure: report the error in logs. The email may already have been sent.

## Testing

Testing should stay practical and avoid real network calls by default.

Planned tests:

- News item deduplication.
- News ranking and filtering.
- Report file path generation.
- Missing configuration errors.
- Markdown-to-HTML conversion.
- Email sending with SMTP mocked.
- AI summarization with the HTTP client mocked.

The project should also support a local dry-run mode that generates Markdown without sending email.

## Documentation

The README should explain:

- What the project does.
- How the daily workflow works.
- How each source file is organized.
- How to configure GitHub Secrets.
- How to enable NetEase SMTP and get an authorization code.
- How to configure `AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL`, and `AI_API_STYLE`.
- How to manually run GitHub Actions.
- How to run locally in dry-run mode.
- How to change recipients, models, news sources, and schedule.
- How to read and learn from `reports/*.md`.

The explanation should be suitable for a beginner AI trainer and include concise code examples where useful.
