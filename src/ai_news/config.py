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


def _get_mail_port() -> int:
    value = _get("MAIL_PORT", "465")
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError("MAIL_PORT must be a number, for example 465.") from exc


def load_config(dry_run_override: bool | None = None) -> AppConfig:
    load_dotenv()

    dry_run = _truthy(os.getenv("DRY_RUN")) if dry_run_override is None else dry_run_override
    config = AppConfig(
        ai_api_key=_get("AI_API_KEY"),
        ai_base_url=_get("AI_BASE_URL"),
        ai_model=_get("AI_MODEL"),
        ai_api_style=_get("AI_API_STYLE", "responses"),
        mail_host=_get("MAIL_HOST", "smtp.163.com"),
        mail_port=_get_mail_port(),
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
