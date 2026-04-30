import pytest

from ai_news.config import AppConfig, ConfigError, load_config


PROJECT_ENV_KEYS = [
    "AI_API_KEY",
    "AI_BASE_URL",
    "AI_MODEL",
    "AI_API_STYLE",
    "MAIL_HOST",
    "MAIL_PORT",
    "MAIL_USERNAME",
    "MAIL_PASSWORD",
    "MAIL_FROM",
    "MAIL_TO",
    "NEWS_API_PROVIDER",
    "NEWS_API_KEY",
    "DRY_RUN",
]


@pytest.fixture(autouse=True)
def isolate_config_environment(monkeypatch):
    for key in PROJECT_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr("ai_news.config.load_dotenv", lambda: None)


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


def test_load_config_rejects_non_numeric_mail_port(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "ai-key")
    monkeypatch.setenv("AI_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("AI_MODEL", "example-model")
    monkeypatch.setenv("MAIL_USERNAME", "sender@163.com")
    monkeypatch.setenv("MAIL_PASSWORD", "smtp-auth-code")
    monkeypatch.setenv("MAIL_FROM", "sender@163.com")
    monkeypatch.setenv("MAIL_TO", "reader@example.com")
    monkeypatch.setenv("MAIL_PORT", "not-a-number")

    with pytest.raises(ConfigError) as exc_info:
        load_config()

    message = str(exc_info.value)
    assert "MAIL_PORT" in message
    assert "must be a number" in message
    assert "465" in message
