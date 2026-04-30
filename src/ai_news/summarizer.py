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
