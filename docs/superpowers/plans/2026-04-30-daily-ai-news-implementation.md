# Daily AI News Email Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GitHub Actions Python automation that fetches AI news, summarizes it for beginner AI trainers, emails an HTML report, and commits the Markdown report.

**Architecture:** Create a small `ai_news` Python package with focused modules for configuration, news collection, summarization, email delivery, report storage, and orchestration. External network calls are isolated behind functions so tests can use mocks and the daily workflow can run in GitHub Actions with Secrets.

**Tech Stack:** Python 3.11, pytest, requests, feedparser, markdown, python-dotenv, GitHub Actions, NetEase SMTP.

---

## File Structure

- Create `pyproject.toml`: project metadata, runtime dependencies, pytest configuration.
- Create `src/ai_news/__init__.py`: package marker and version.
- Create `src/ai_news/config.py`: environment variable loading and validation.
- Create `src/ai_news/models.py`: `NewsItem` dataclass and title normalization helpers.
- Create `src/ai_news/news_sources.py`: RSS fetching, optional news API fetching, dedupe, filter, rank.
- Create `src/ai_news/summarizer.py`: prompt building and AI API calls for `responses` style.
- Create `src/ai_news/email_sender.py`: Markdown-to-HTML conversion and SMTP sending.
- Create `src/ai_news/report_store.py`: report path generation and file writing.
- Create `src/ai_news/main.py`: CLI and orchestration.
- Create `tests/`: focused unit tests with no real network calls.
- Create `.github/workflows/daily-ai-news.yml`: scheduled and manual workflow.
- Create `README.md`: beginner-friendly setup and learning guide.
- Create `reports/.gitkeep`: keep the reports directory present before first run.

---

### Task 1: Project Skeleton And Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `src/ai_news/__init__.py`
- Create: `src/ai_news/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing configuration tests**

Create `tests/test_config.py`:

```python
import pytest

from ai_news.config import AppConfig, ConfigError, load_config


def test_load_config_requires_ai_values(monkeypatch):
    for key in [
        "AI_API_KEY",
        "AI_BASE_URL",
        "AI_MODEL",
        "MAIL_USERNAME",
        "MAIL_PASSWORD",
        "MAIL_FROM",
        "MAIL_TO",
    ]:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ConfigError) as exc_info:
        load_config()

    message = str(exc_info.value)
    assert "AI_API_KEY" in message
    assert "GitHub Secrets" in message


def test_load_config_uses_defaults_and_optional_news_api(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "ai-key")
    monkeypatch.setenv("AI_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("AI_MODEL", "example-model")
    monkeypatch.setenv("MAIL_USERNAME", "sender@163.com")
    monkeypatch.setenv("MAIL_PASSWORD", "smtp-auth-code")
    monkeypatch.setenv("MAIL_FROM", "sender@163.com")
    monkeypatch.setenv("MAIL_TO", "reader@example.com")
    monkeypatch.setenv("NEWS_API_PROVIDER", "newsapi")
    monkeypatch.setenv("NEWS_API_KEY", "news-key")

    config = load_config()

    assert isinstance(config, AppConfig)
    assert config.ai_api_style == "responses"
    assert config.mail_host == "smtp.163.com"
    assert config.mail_port == 465
    assert config.news_api_provider == "newsapi"
    assert config.news_api_key == "news-key"
    assert config.dry_run is False


def test_dry_run_allows_missing_mail_values(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "ai-key")
    monkeypatch.setenv("AI_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("AI_MODEL", "example-model")
    monkeypatch.delenv("MAIL_USERNAME", raising=False)
    monkeypatch.delenv("MAIL_PASSWORD", raising=False)
    monkeypatch.delenv("MAIL_FROM", raising=False)
    monkeypatch.delenv("MAIL_TO", raising=False)
    monkeypatch.setenv("DRY_RUN", "true")

    config = load_config()

    assert config.dry_run is True
    assert config.mail_to == ""


def test_dry_run_override_allows_missing_mail_values(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "ai-key")
    monkeypatch.setenv("AI_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("AI_MODEL", "example-model")
    monkeypatch.delenv("MAIL_USERNAME", raising=False)
    monkeypatch.delenv("MAIL_PASSWORD", raising=False)
    monkeypatch.delenv("MAIL_FROM", raising=False)
    monkeypatch.delenv("MAIL_TO", raising=False)
    monkeypatch.delenv("DRY_RUN", raising=False)

    config = load_config(dry_run_override=True)

    assert config.dry_run is True
    assert config.mail_to == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_config.py -v
```

Expected: FAIL because `ai_news.config` does not exist.

- [ ] **Step 3: Add project metadata and package marker**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "ai-news"
version = "0.1.0"
description = "Daily AI news email automation for beginner AI trainers"
requires-python = ">=3.11"
dependencies = [
    "feedparser>=6.0.11",
    "markdown>=3.6",
    "python-dotenv>=1.0.1",
    "requests>=2.32.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
]

[project.scripts]
ai-news = "ai_news.main:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

Create `src/ai_news/__init__.py`:

```python
"""Daily AI news email automation package."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Implement configuration loading**

Create `src/ai_news/config.py`:

```python
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing."""


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class AppConfig:
    ai_api_key: str
    ai_base_url: str
    ai_model: str
    ai_api_style: str
    mail_host: str
    mail_port: int
    mail_username: str
    mail_password: str
    mail_from: str
    mail_to: str
    news_api_provider: str
    news_api_key: str
    dry_run: bool


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def load_config(dry_run_override: bool | None = None) -> AppConfig:
    load_dotenv()

    dry_run = _truthy(os.getenv("DRY_RUN")) if dry_run_override is None else dry_run_override
    config = AppConfig(
        ai_api_key=_get("AI_API_KEY"),
        ai_base_url=_get("AI_BASE_URL"),
        ai_model=_get("AI_MODEL"),
        ai_api_style=_get("AI_API_STYLE", "responses"),
        mail_host=_get("MAIL_HOST", "smtp.163.com"),
        mail_port=int(_get("MAIL_PORT", "465")),
        mail_username=_get("MAIL_USERNAME"),
        mail_password=_get("MAIL_PASSWORD"),
        mail_from=_get("MAIL_FROM"),
        mail_to=_get("MAIL_TO"),
        news_api_provider=_get("NEWS_API_PROVIDER"),
        news_api_key=_get("NEWS_API_KEY"),
        dry_run=dry_run,
    )

    required = {
        "AI_API_KEY": config.ai_api_key,
        "AI_BASE_URL": config.ai_base_url,
        "AI_MODEL": config.ai_model,
    }
    if not dry_run:
        required.update(
            {
                "MAIL_USERNAME": config.mail_username,
                "MAIL_PASSWORD": config.mail_password,
                "MAIL_FROM": config.mail_from,
                "MAIL_TO": config.mail_to,
            }
        )

    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ConfigError(
            "Missing required configuration: "
            + ", ".join(missing)
            + ". Add these values in GitHub Secrets or a local .env file. "
            + "For NetEase email, MAIL_PASSWORD must be the SMTP authorization code."
        )

    return config
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
pytest tests/test_config.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/ai_news/__init__.py src/ai_news/config.py tests/test_config.py
git commit -m "feat: add runtime configuration"
```

---

### Task 2: News Model, Deduplication, Filtering, And Ranking

**Files:**
- Create: `src/ai_news/models.py`
- Create: `src/ai_news/news_sources.py`
- Create: `tests/test_news_sources.py`

- [ ] **Step 1: Write failing news processing tests**

Create `tests/test_news_sources.py`:

```python
from datetime import datetime, timedelta, timezone

from ai_news.models import NewsItem
from ai_news.news_sources import dedupe_items, filter_recent_items, rank_items


def item(title, url, hours_old=2, source="Example", summary=""):
    return NewsItem(
        title=title,
        url=url,
        source=source,
        published_at=datetime.now(timezone.utc) - timedelta(hours=hours_old),
        summary=summary,
    )


def test_dedupe_items_removes_duplicate_urls_and_titles():
    items = [
        item("OpenAI releases new model", "https://example.com/a"),
        item("OpenAI releases new model!", "https://example.com/b"),
        item("Different story", "https://example.com/a"),
        item("Evaluation benchmark updated", "https://example.com/c"),
    ]

    deduped = dedupe_items(items)

    assert [news.title for news in deduped] == [
        "OpenAI releases new model",
        "Evaluation benchmark updated",
    ]


def test_filter_recent_items_expands_to_72_hours_when_needed():
    items = [
        item("Recent model news", "https://example.com/recent", hours_old=3),
        item("Older evaluation news", "https://example.com/older", hours_old=60),
        item("Too old", "https://example.com/too-old", hours_old=120),
    ]

    selected, expanded = filter_recent_items(items, min_items=2, now=datetime.now(timezone.utc))

    assert expanded is True
    assert [news.title for news in selected] == ["Recent model news", "Older evaluation news"]


def test_rank_items_prioritizes_ai_trainer_relevant_keywords():
    items = [
        item("AI startup funding", "https://example.com/funding", summary="business"),
        item("New prompt engineering evaluation guide", "https://example.com/eval", summary="LLM evaluation"),
        item("Sports result", "https://example.com/sports", summary="not ai"),
    ]

    ranked = rank_items(items, limit=2)

    assert [news.title for news in ranked] == [
        "New prompt engineering evaluation guide",
        "AI startup funding",
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_news_sources.py -v
```

Expected: FAIL because `ai_news.models` and `ai_news.news_sources` do not exist.

- [ ] **Step 3: Implement news item model**

Create `src/ai_news/models.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone


def normalize_title(title: str) -> str:
    lowered = title.lower()
    lowered = re.sub(r"[^\w\s]", "", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


@dataclass(frozen=True)
class NewsItem:
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str = ""

    def published_utc(self) -> datetime:
        if self.published_at.tzinfo is None:
            return self.published_at.replace(tzinfo=timezone.utc)
        return self.published_at.astimezone(timezone.utc)
```

- [ ] **Step 4: Implement dedupe, recent filtering, and ranking**

Create `src/ai_news/news_sources.py`:

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from .models import NewsItem, normalize_title


TRAINER_KEYWORDS = {
    "ai": 2,
    "llm": 3,
    "model": 2,
    "openai": 3,
    "anthropic": 3,
    "deepmind": 3,
    "hugging face": 3,
    "prompt": 4,
    "prompt engineering": 5,
    "data labeling": 5,
    "annotation": 4,
    "evaluation": 5,
    "benchmark": 4,
    "safety": 4,
    "alignment": 4,
    "multimodal": 3,
    "agent": 3,
}


def dedupe_items(items: Iterable[NewsItem]) -> list[NewsItem]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    result: list[NewsItem] = []

    for item in items:
        url_key = item.url.strip().lower()
        title_key = normalize_title(item.title)
        if not url_key or not title_key:
            continue
        if url_key in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url_key)
        seen_titles.add(title_key)
        result.append(item)

    return result


def filter_recent_items(
    items: Iterable[NewsItem],
    min_items: int = 8,
    now: datetime | None = None,
) -> tuple[list[NewsItem], bool]:
    current = now or datetime.now(timezone.utc)
    current = current.astimezone(timezone.utc)
    sorted_items = sorted(items, key=lambda news: news.published_utc(), reverse=True)

    recent = [
        news
        for news in sorted_items
        if current - news.published_utc() <= timedelta(hours=48)
    ]
    if len(recent) >= min_items:
        return recent, False

    expanded = [
        news
        for news in sorted_items
        if current - news.published_utc() <= timedelta(hours=72)
    ]
    return expanded, len(expanded) > len(recent)


def _score_item(item: NewsItem) -> int:
    text = f"{item.title} {item.summary} {item.source}".lower()
    score = 0
    for keyword, weight in TRAINER_KEYWORDS.items():
        if keyword in text:
            score += weight
    return score


def rank_items(items: Iterable[NewsItem], limit: int = 10) -> list[NewsItem]:
    return sorted(
        items,
        key=lambda news: (_score_item(news), news.published_utc()),
        reverse=True,
    )[:limit]
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
pytest tests/test_news_sources.py -v
```

Expected: PASS.

- [ ] **Step 6: Run all tests**

Run:

```bash
pytest -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/ai_news/models.py src/ai_news/news_sources.py tests/test_news_sources.py
git commit -m "feat: add news ranking utilities"
```

---

### Task 3: RSS Fetching And Optional News API

**Files:**
- Modify: `src/ai_news/news_sources.py`
- Create: `tests/test_fetchers.py`

- [ ] **Step 1: Write failing fetcher tests**

Create `tests/test_fetchers.py`:

```python
from datetime import timezone

from ai_news.config import AppConfig
from ai_news.news_sources import DEFAULT_RSS_FEEDS, fetch_all_news, parse_feed_entries


class FakeFeed:
    entries = [
        {
            "title": "OpenAI shares evaluation update",
            "link": "https://example.com/openai-eval",
            "published_parsed": (2026, 4, 30, 8, 0, 0, 0, 0, 0),
            "summary": "Evaluation details for AI trainers.",
        },
        {
            "title": "",
            "link": "https://example.com/empty",
        },
    ]


def test_default_rss_feeds_cover_ai_sources():
    names = [name for name, _url in DEFAULT_RSS_FEEDS]

    assert "OpenAI Blog" in names
    assert "Google DeepMind Blog" in names
    assert "Hugging Face Blog" in names


def test_parse_feed_entries_skips_entries_without_title():
    items = parse_feed_entries("OpenAI Blog", FakeFeed.entries)

    assert len(items) == 1
    assert items[0].title == "OpenAI shares evaluation update"
    assert items[0].published_at.tzinfo == timezone.utc


def test_fetch_all_news_uses_rss_when_news_api_missing(monkeypatch):
    def fake_parse(url):
        assert url
        return FakeFeed()

    config = AppConfig(
        ai_api_key="ai-key",
        ai_base_url="https://api.example.com",
        ai_model="model",
        ai_api_style="responses",
        mail_host="smtp.163.com",
        mail_port=465,
        mail_username="sender@163.com",
        mail_password="auth",
        mail_from="sender@163.com",
        mail_to="reader@example.com",
        news_api_provider="",
        news_api_key="",
        dry_run=False,
    )

    items, metadata = fetch_all_news(config, rss_feeds=[("OpenAI Blog", "https://example.com/rss")], feed_parser=fake_parse)

    assert len(items) == 1
    assert items[0].source == "OpenAI Blog"
    assert metadata["news_api_used"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_fetchers.py -v
```

Expected: FAIL because RSS fetch functions are not implemented.

- [ ] **Step 3: Implement RSS defaults and parsing**

Modify the imports at the top of `src/ai_news/news_sources.py` so the file includes:

```python
from time import mktime

import feedparser
import requests

from .config import AppConfig
```

Add:

```python
DEFAULT_RSS_FEEDS: list[tuple[str, str]] = [
    ("OpenAI Blog", "https://openai.com/news/rss.xml"),
    ("Google DeepMind Blog", "https://deepmind.google/blog/rss.xml"),
    ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
    ("Anthropic News", "https://www.anthropic.com/news/rss.xml"),
    ("Microsoft AI Blog", "https://blogs.microsoft.com/ai/feed/"),
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
    ("Planet AI Aggregate", "https://planet-ai.net/rss.xml"),
    ("The Batch", "https://www.deeplearning.ai/the-batch/rss.xml"),
    ("MIT News AI", "https://news.mit.edu/rss/topic/artificial-intelligence2"),
]


def _entry_datetime(entry: dict) -> datetime:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
    return datetime.now(timezone.utc)


def parse_feed_entries(source_name: str, entries: Iterable[dict]) -> list[NewsItem]:
    items: list[NewsItem] = []
    for entry in entries:
        title = str(entry.get("title", "")).strip()
        url = str(entry.get("link", "")).strip()
        if not title or not url:
            continue
        items.append(
            NewsItem(
                title=title,
                url=url,
                source=source_name,
                published_at=_entry_datetime(entry),
                summary=str(entry.get("summary", "")).strip(),
            )
        )
    return items
```

- [ ] **Step 4: Implement optional news API and combined fetch**

Add to `src/ai_news/news_sources.py`:

```python
def fetch_news_api_items(config: AppConfig) -> list[NewsItem]:
    if not config.news_api_provider or not config.news_api_key:
        return []

    provider = config.news_api_provider.lower()
    if provider != "newsapi":
        print(f"Unsupported NEWS_API_PROVIDER={config.news_api_provider}; skipping news API.")
        return []

    query = '(AI OR "artificial intelligence" OR LLM OR "prompt engineering" OR "model evaluation")'
    response = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 20,
            "apiKey": config.news_api_key,
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()

    items: list[NewsItem] = []
    for article in data.get("articles", []):
        title = str(article.get("title") or "").strip()
        url = str(article.get("url") or "").strip()
        if not title or not url:
            continue
        published_raw = str(article.get("publishedAt") or "")
        try:
            published = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
        except ValueError:
            published = datetime.now(timezone.utc)
        source = article.get("source") or {}
        items.append(
            NewsItem(
                title=title,
                url=url,
                source=str(source.get("name") or "NewsAPI"),
                published_at=published,
                summary=str(article.get("description") or "").strip(),
            )
        )
    return items


def fetch_all_news(
    config: AppConfig,
    rss_feeds: list[tuple[str, str]] | None = None,
    feed_parser=feedparser.parse,
) -> tuple[list[NewsItem], dict[str, bool]]:
    feeds = rss_feeds or DEFAULT_RSS_FEEDS
    items: list[NewsItem] = []

    for source_name, url in feeds:
        try:
            parsed_feed = feed_parser(url)
            items.extend(parse_feed_entries(source_name, parsed_feed.entries))
        except Exception as exc:
            print(f"RSS source failed: {source_name} ({url}) - {exc}")

    api_items: list[NewsItem] = []
    try:
        api_items = fetch_news_api_items(config)
    except Exception as exc:
        print(f"News API fetch failed; continuing with RSS only - {exc}")

    all_items = dedupe_items([*items, *api_items])
    return all_items, {"news_api_used": bool(api_items)}
```

- [ ] **Step 5: Run fetcher tests**

Run:

```bash
pytest tests/test_fetchers.py -v
```

Expected: PASS.

- [ ] **Step 6: Run news tests and all tests**

Run:

```bash
pytest tests/test_news_sources.py tests/test_fetchers.py -v
pytest -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/ai_news/news_sources.py tests/test_fetchers.py
git commit -m "feat: fetch ai news sources"
```

---

### Task 4: AI Summarizer

**Files:**
- Create: `src/ai_news/summarizer.py`
- Create: `tests/test_summarizer.py`

- [ ] **Step 1: Write failing summarizer tests**

Create `tests/test_summarizer.py`:

```python
from datetime import datetime, timezone

import pytest

from ai_news.config import AppConfig
from ai_news.models import NewsItem
from ai_news.summarizer import SummarizerError, build_prompt, summarize_news


def config():
    return AppConfig(
        ai_api_key="ai-key",
        ai_base_url="https://api.example.com/api/codex/backend-api/codex",
        ai_model="gpt-5-codex",
        ai_api_style="responses",
        mail_host="smtp.163.com",
        mail_port=465,
        mail_username="sender@163.com",
        mail_password="auth",
        mail_from="sender@163.com",
        mail_to="reader@example.com",
        news_api_provider="",
        news_api_key="",
        dry_run=False,
    )


def news_item():
    return NewsItem(
        title="OpenAI updates model evaluation",
        url="https://example.com/eval",
        source="OpenAI Blog",
        published_at=datetime(2026, 4, 30, 8, 0, tzinfo=timezone.utc),
        summary="Evaluation update",
    )


def test_build_prompt_targets_beginner_ai_trainers():
    prompt = build_prompt([news_item()], "2026-04-30", expanded_window=False, news_api_used=False)

    assert "AI 训练师初学者" in prompt
    assert "Markdown" in prompt
    assert "代码示例" in prompt
    assert "OpenAI updates model evaluation" in prompt


def test_summarize_news_calls_responses_api():
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"output_text": "# 每日 AI 热点新闻简报\n\n## 今日速览\n- 测试"}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    markdown = summarize_news(
        config(),
        [news_item()],
        "2026-04-30",
        expanded_window=False,
        news_api_used=False,
        post=fake_post,
    )

    assert captured["url"] == "https://api.example.com/api/codex/backend-api/codex/responses"
    assert captured["headers"]["Authorization"] == "Bearer ai-key"
    assert captured["json"]["model"] == "gpt-5-codex"
    assert markdown.startswith("# 每日 AI 热点新闻简报")


def test_summarize_news_fails_on_empty_model_output():
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"output_text": ""}

    with pytest.raises(SummarizerError):
        summarize_news(
            config(),
            [news_item()],
            "2026-04-30",
            expanded_window=False,
            news_api_used=False,
            post=lambda *args, **kwargs: FakeResponse(),
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_summarizer.py -v
```

Expected: FAIL because `ai_news.summarizer` does not exist.

- [ ] **Step 3: Implement prompt and Responses API summarizer**

Create `src/ai_news/summarizer.py`:

```python
from __future__ import annotations

import json
from typing import Callable

import requests

from .config import AppConfig
from .models import NewsItem


class SummarizerError(RuntimeError):
    """Raised when the AI service cannot produce a usable report."""


def build_prompt(
    items: list[NewsItem],
    report_date: str,
    expanded_window: bool,
    news_api_used: bool,
) -> str:
    source_note = "RSS + 新闻搜索 API" if news_api_used else "RSS/公开源"
    window_note = (
        "今天新闻数量不足，已扩展到最近 72 小时，请在报告中简短说明。"
        if expanded_window
        else "新闻主要来自最近 24-48 小时。"
    )
    news_lines = []
    for index, item in enumerate(items, start=1):
        news_lines.append(
            "\n".join(
                [
                    f"{index}. {item.title}",
                    f"   来源: {item.source}",
                    f"   链接: {item.url}",
                    f"   发布时间: {item.published_utc().isoformat()}",
                    f"   摘要: {item.summary or '无'}",
                ]
            )
        )

    return f"""
你是一名面向 AI 训练师初学者的中文学习型新闻编辑。

请基于下面的新闻候选，生成一份专业但不过于学术的 Markdown 简报。

要求：
- 使用中文。
- 面向 AI 训练师初学者，解释术语和实际学习价值。
- 保留每条重点新闻的原始链接。
- 选择 8-10 条重点新闻；如果候选不足，就全部使用。
- 每条新闻包含：来源、链接、发生了什么、为什么重要、初学者学习提示。
- 包含“今日速览”“重点新闻”“今日概念补充”“代码示例”“延伸阅读”。
- “代码示例”必须偏 AI 训练师学习，例如提示词模板、数据标注 JSON、评估表格或简单 Python 片段。
- 输出必须是 Markdown，不要输出额外解释。

报告日期：{report_date}
新闻来源策略：{source_note}
时间窗口说明：{window_note}

新闻候选：
{chr(10).join(news_lines)}
""".strip()


def _responses_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/responses"):
        return normalized
    return normalized + "/responses"


def _extract_output_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"].strip()

    chunks: list[str] = []
    for output in data.get("output", []):
        for content in output.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text", "")
                if isinstance(text, str):
                    chunks.append(text)
    return "\n".join(chunks).strip()


def summarize_news(
    config: AppConfig,
    items: list[NewsItem],
    report_date: str,
    expanded_window: bool,
    news_api_used: bool,
    post: Callable = requests.post,
) -> str:
    if config.ai_api_style != "responses":
        raise SummarizerError(
            f"Unsupported AI_API_STYLE={config.ai_api_style}. "
            "This project currently supports responses."
        )

    prompt = build_prompt(items, report_date, expanded_window, news_api_used)
    response = post(
        _responses_url(config.ai_base_url),
        headers={
            "Authorization": f"Bearer {config.ai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.ai_model,
            "input": prompt,
            "temperature": 0.3,
        },
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    markdown = _extract_output_text(data)
    if not markdown:
        raise SummarizerError(
            "AI service returned an empty report. Raw response: "
            + json.dumps(data, ensure_ascii=False)[:1000]
        )
    return markdown
```

- [ ] **Step 4: Run summarizer tests**

Run:

```bash
pytest tests/test_summarizer.py -v
```

Expected: PASS.

- [ ] **Step 5: Run all tests**

Run:

```bash
pytest -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ai_news/summarizer.py tests/test_summarizer.py
git commit -m "feat: summarize ai news with responses api"
```

---

### Task 5: Report Storage And Email Rendering

**Files:**
- Create: `src/ai_news/report_store.py`
- Create: `src/ai_news/email_sender.py`
- Create: `tests/test_report_store.py`
- Create: `tests/test_email_sender.py`
- Create: `reports/.gitkeep`

- [ ] **Step 1: Write failing report storage tests**

Create `tests/test_report_store.py`:

```python
from pathlib import Path

from ai_news.report_store import report_path_for_date, save_report


def test_report_path_for_date_uses_reports_directory():
    path = report_path_for_date("2026-04-30")

    assert path == Path("reports") / "2026-04-30.md"


def test_save_report_creates_directory_and_writes_markdown(tmp_path):
    path = save_report("# 标题\n", "2026-04-30", root=tmp_path)

    assert path == tmp_path / "reports" / "2026-04-30.md"
    assert path.read_text(encoding="utf-8") == "# 标题\n"
```

- [ ] **Step 2: Write failing email tests**

Create `tests/test_email_sender.py`:

```python
from email.message import EmailMessage

from ai_news.config import AppConfig
from ai_news.email_sender import build_email_message, markdown_to_html, send_email


def config():
    return AppConfig(
        ai_api_key="ai-key",
        ai_base_url="https://api.example.com",
        ai_model="model",
        ai_api_style="responses",
        mail_host="smtp.163.com",
        mail_port=465,
        mail_username="sender@163.com",
        mail_password="auth",
        mail_from="sender@163.com",
        mail_to="reader@example.com",
        news_api_provider="",
        news_api_key="",
        dry_run=False,
    )


def test_markdown_to_html_renders_heading_and_list():
    html = markdown_to_html("# 标题\n\n- 要点")

    assert "<h1>标题</h1>" in html
    assert "<li>要点</li>" in html


def test_build_email_message_contains_plain_and_html_parts():
    message = build_email_message(config(), "# 标题", "2026-04-30")

    assert isinstance(message, EmailMessage)
    assert message["Subject"] == "每日 AI 热点新闻简报 - 2026-04-30"
    assert message["From"] == "sender@163.com"
    assert message["To"] == "reader@example.com"
    assert message.is_multipart()


def test_send_email_uses_ssl_smtp():
    calls = {}

    class FakeSMTP:
        def __init__(self, host, port):
            calls["host"] = host
            calls["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def login(self, username, password):
            calls["login"] = (username, password)

        def send_message(self, message):
            calls["subject"] = message["Subject"]

    send_email(config(), "# 标题", "2026-04-30", smtp_ssl=FakeSMTP)

    assert calls["host"] == "smtp.163.com"
    assert calls["port"] == 465
    assert calls["login"] == ("sender@163.com", "auth")
    assert calls["subject"] == "每日 AI 热点新闻简报 - 2026-04-30"
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
pytest tests/test_report_store.py tests/test_email_sender.py -v
```

Expected: FAIL because the modules do not exist.

- [ ] **Step 4: Implement report storage**

Create `src/ai_news/report_store.py`:

```python
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
```

Create `reports/.gitkeep` as an empty file.

- [ ] **Step 5: Implement email sender**

Create `src/ai_news/email_sender.py`:

```python
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Callable

import markdown

from .config import AppConfig


def markdown_to_html(markdown_text: str) -> str:
    body = markdown.markdown(markdown_text, extensions=["extra", "sane_lists"])
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
```

- [ ] **Step 6: Run report and email tests**

Run:

```bash
pytest tests/test_report_store.py tests/test_email_sender.py -v
```

Expected: PASS.

- [ ] **Step 7: Run all tests**

Run:

```bash
pytest -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/ai_news/report_store.py src/ai_news/email_sender.py tests/test_report_store.py tests/test_email_sender.py reports/.gitkeep
git commit -m "feat: store and email reports"
```

---

### Task 6: Main Orchestration And Dry Run CLI

**Files:**
- Create: `src/ai_news/main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write failing orchestration tests**

Create `tests/test_main.py`:

```python
from datetime import date, datetime, timezone

from ai_news.config import AppConfig
from ai_news.main import run
from ai_news.models import NewsItem


def config(dry_run=True):
    return AppConfig(
        ai_api_key="ai-key",
        ai_base_url="https://api.example.com",
        ai_model="model",
        ai_api_style="responses",
        mail_host="smtp.163.com",
        mail_port=465,
        mail_username="sender@163.com",
        mail_password="auth",
        mail_from="sender@163.com",
        mail_to="reader@example.com",
        news_api_provider="",
        news_api_key="",
        dry_run=dry_run,
    )


def test_run_saves_report_and_skips_email_in_dry_run(tmp_path):
    calls = {"email": 0}

    def fake_fetch(_config):
        return (
            [
                NewsItem(
                    title="Prompt evaluation news",
                    url="https://example.com/eval",
                    source="Example",
                    published_at=datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc),
                    summary="Evaluation",
                )
            ],
            {"news_api_used": False},
        )

    def fake_summarize(_config, items, report_date, expanded_window, news_api_used):
        assert report_date == "2026-04-30"
        assert expanded_window is True
        assert news_api_used is False
        assert len(items) == 1
        return "# 每日 AI 热点新闻简报\n"

    def fake_send(*args, **kwargs):
        calls["email"] += 1

    path = run(
        config(dry_run=True),
        today=date(2026, 4, 30),
        root=tmp_path,
        fetch_news=fake_fetch,
        summarize=fake_summarize,
        send=fake_send,
    )

    assert calls["email"] == 0
    assert path == tmp_path / "reports" / "2026-04-30.md"
    assert path.read_text(encoding="utf-8").startswith("# 每日 AI 热点新闻简报")


def test_run_sends_email_when_not_dry_run(tmp_path):
    calls = {"email": 0}

    def fake_fetch(_config):
        return (
            [
                NewsItem(
                    title=f"AI news {index}",
                    url=f"https://example.com/{index}",
                    source="Example",
                    published_at=datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc),
                    summary="AI model evaluation",
                )
                for index in range(10)
            ],
            {"news_api_used": True},
        )

    def fake_summarize(*args, **kwargs):
        return "# 简报\n"

    def fake_send(_config, markdown, report_date):
        calls["email"] += 1
        assert markdown == "# 简报\n"
        assert report_date == "2026-04-30"

    run(
        config(dry_run=False),
        today=date(2026, 4, 30),
        root=tmp_path,
        fetch_news=fake_fetch,
        summarize=fake_summarize,
        send=fake_send,
    )

    assert calls["email"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_main.py -v
```

Expected: FAIL because `ai_news.main` does not exist.

- [ ] **Step 3: Implement main orchestration**

Create `src/ai_news/main.py`:

```python
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
```

- [ ] **Step 4: Run main tests**

Run:

```bash
pytest tests/test_main.py -v
```

Expected: PASS.

- [ ] **Step 5: Run all tests**

Run:

```bash
pytest -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ai_news/main.py tests/test_main.py
git commit -m "feat: orchestrate daily report generation"
```

---

### Task 7: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/daily-ai-news.yml`

- [ ] **Step 1: Create workflow**

Create `.github/workflows/daily-ai-news.yml`:

```yaml
name: Daily AI News

on:
  schedule:
    - cron: "0 11 * * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  daily-ai-news:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e ".[dev]"

      - name: Run tests
        run: pytest -v

      - name: Generate and email daily report
        env:
          AI_API_KEY: ${{ secrets.AI_API_KEY }}
          AI_BASE_URL: ${{ secrets.AI_BASE_URL }}
          AI_MODEL: ${{ secrets.AI_MODEL }}
          AI_API_STYLE: ${{ secrets.AI_API_STYLE || 'responses' }}
          MAIL_HOST: ${{ secrets.MAIL_HOST || 'smtp.163.com' }}
          MAIL_PORT: ${{ secrets.MAIL_PORT || '465' }}
          MAIL_USERNAME: ${{ secrets.MAIL_USERNAME }}
          MAIL_PASSWORD: ${{ secrets.MAIL_PASSWORD }}
          MAIL_FROM: ${{ secrets.MAIL_FROM }}
          MAIL_TO: ${{ secrets.MAIL_TO }}
          NEWS_API_PROVIDER: ${{ secrets.NEWS_API_PROVIDER }}
          NEWS_API_KEY: ${{ secrets.NEWS_API_KEY }}
        run: python -m ai_news.main

      - name: Commit report
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add reports/*.md
          if git diff --cached --quiet; then
            echo "No report changes to commit."
          else
            git commit -m "chore: add AI news report for $(date -u +%F)"
            git push
          fi
```

- [ ] **Step 2: Validate workflow file is present**

Run:

```bash
Test-Path .github/workflows/daily-ai-news.yml
```

Expected: `True`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/daily-ai-news.yml
git commit -m "ci: add daily ai news workflow"
```

---

### Task 8: Beginner-Friendly README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

Create `README.md`:

```markdown
# AI-news

`AI-news` 是一个每日自动化脚本项目：它会抓取最新 AI 热点新闻，调用 AI 模型生成中文 Markdown 简报，然后发送到你的个人邮箱，并把每日报告保存到 GitHub 仓库。

这个项目面向 AI 训练师初学者。你不需要先成为程序员，也可以通过它理解“新闻抓取、提示词、模型总结、邮件发送、自动化任务”这些基础流程。

## 每天会发生什么

北京时间每天 19:00，GitHub Actions 会自动运行：

1. 抓取 AI 新闻候选。
2. 去重、筛选最近 24-48 小时的重要内容。
3. 如果新闻太少，扩展到最近 72 小时。
4. 调用你配置的 AI 模型生成 Markdown 简报。
5. 把简报转成 HTML 邮件发给你。
6. 保存 `reports/YYYY-MM-DD.md`。
7. 自动提交报告到仓库。

## 简报内容

每封邮件包含：

- 今日速览
- 8-10 条重点新闻
- 每条新闻的“发生了什么”“为什么重要”“初学者学习提示”
- 今日概念补充
- AI 训练师学习向代码示例
- 原始链接列表

## 需要配置的 GitHub Secrets

进入 GitHub 仓库：

`Settings -> Secrets and variables -> Actions -> New repository secret`

添加这些值：

| Secret | 说明 |
| --- | --- |
| `AI_API_KEY` | AI 模型服务的 API Key |
| `AI_BASE_URL` | AI 接口地址，不是网页后台地址 |
| `AI_MODEL` | 模型名称 |
| `AI_API_STYLE` | 默认填 `responses` |
| `MAIL_HOST` | 网易邮箱填 `smtp.163.com` |
| `MAIL_PORT` | 网易邮箱 SSL 端口填 `465` |
| `MAIL_USERNAME` | 发件网易邮箱 |
| `MAIL_PASSWORD` | 网易邮箱 SMTP 授权码，不是登录密码 |
| `MAIL_FROM` | 发件邮箱 |
| `MAIL_TO` | 收件邮箱，可以和发件邮箱相同 |
| `NEWS_API_PROVIDER` | 可选，例如 `newsapi` |
| `NEWS_API_KEY` | 可选，新闻搜索 API Key |

## AI_BASE_URL 是什么

`AI_BASE_URL` 是程序调用模型的接口地址，不是浏览器里的后台页面。

例子：

```text
https://api.openai.com/v1
https://api.deepseek.com/v1
https://api.aicodemirror.com/api/codex/backend-api/codex
```

如果你使用 AICodeMirror，并且它给你的 Codex 接口是：

```text
https://api.aicodemirror.com/api/codex/backend-api/codex
```

可以先把它填到 `AI_BASE_URL`，并把 `AI_API_STYLE` 设置为 `responses`。

## 网易邮箱授权码

网易邮箱发信通常不能直接使用登录密码。你需要在网易邮箱设置里开启 SMTP，并生成“授权码”。

把授权码填入：

```text
MAIL_PASSWORD
```

## 本地测试

安装依赖：

```bash
python -m pip install -e ".[dev]"
```

运行测试：

```bash
pytest -v
```

只生成 Markdown，不发送邮件：

```bash
$env:DRY_RUN="true"
python -m ai_news.main --dry-run
```

## 项目结构

```text
src/ai_news/config.py        读取配置
src/ai_news/news_sources.py  抓取、去重、筛选新闻
src/ai_news/summarizer.py    调用 AI 模型生成 Markdown
src/ai_news/email_sender.py  转换 HTML 并发送邮件
src/ai_news/report_store.py  保存 reports/YYYY-MM-DD.md
src/ai_news/main.py          串起完整流程
```

## 如何修改

- 修改收件人：改 GitHub Secret `MAIL_TO`
- 修改发送时间：改 `.github/workflows/daily-ai-news.yml` 里的 cron
- 修改模型：改 `AI_MODEL`
- 修改模型接口：改 `AI_BASE_URL`
- 添加新闻源：编辑 `src/ai_news/news_sources.py` 里的 `DEFAULT_RSS_FEEDS`

## 给 AI 训练师初学者的学习建议

每天阅读报告时，可以重点看三件事：

1. 这条新闻改变了什么？
2. 它和提示词、数据标注、模型评估或安全有什么关系？
3. 如果我是 AI 训练师，我能从中学到哪个可操作的方法？
```

- [ ] **Step 2: Commit README**

```bash
git add README.md
git commit -m "docs: add beginner setup guide"
```

---

### Task 9: Final Verification

**Files:**
- No new files expected.

- [ ] **Step 1: Install project in editable mode**

Run:

```bash
python -m pip install -e ".[dev]"
```

Expected: dependencies install successfully.

- [ ] **Step 2: Run full test suite**

Run:

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Run dry configuration check with expected error**

Run without AI values:

```bash
python -m ai_news.main --dry-run
```

Expected: fails with a clear message listing missing `AI_API_KEY`, `AI_BASE_URL`, or `AI_MODEL`.

- [ ] **Step 4: Run git status**

Run:

```bash
git status --short
```

Expected: clean working tree.

- [ ] **Step 5: Confirm implementation coverage**

Check that these requirements are implemented:

- GitHub Actions schedule is `0 11 * * *`.
- Manual workflow trigger exists.
- RSS works without a news API key.
- Optional `NEWS_API_PROVIDER=newsapi` path exists.
- AI summarizer uses `AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL`, and `AI_API_STYLE`.
- Email uses NetEase SMTP defaults.
- Dry run skips email.
- Reports save to `reports/YYYY-MM-DD.md`.
- Workflow commits reports with `GITHUB_TOKEN`.

No commit is required if the working tree is already clean.
