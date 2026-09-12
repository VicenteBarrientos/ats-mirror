from app.config import Settings
from app.logging_config import _redact
from app.providers.errors import ProviderConfigError
from app.providers.workable import WorkableATSProvider
from app.sync.service import _safe_message


def test_workable_requires_subdomain_and_token() -> None:
    settings = Settings(ATS_PROVIDER="workable", WORKABLE_SUBDOMAIN="", WORKABLE_ACCESS_TOKEN="")
    assert settings.provider_configured is False
    try:
        WorkableATSProvider(settings)
    except ProviderConfigError as exc:
        assert "WORKABLE_ACCESS_TOKEN" in str(exc)
        assert "test-token" not in str(exc)
    else:
        raise AssertionError("expected ProviderConfigError")


def test_workable_configured_when_both_present() -> None:
    settings = Settings(
        ATS_PROVIDER="workable",
        WORKABLE_SUBDOMAIN="groove-tech",
        WORKABLE_ACCESS_TOKEN="test-token",
    )
    assert settings.provider_configured is True


def test_logging_redacts_secret_keys() -> None:
    redacted = _redact(
        {
            "authorization": "Bearer real-secret",
            "workable_access_token": "real-secret",
            "path": "/jobs",
        }
    )
    assert redacted["authorization"] == "[redacted]"
    assert redacted["workable_access_token"] == "[redacted]"
    assert redacted["path"] == "/jobs"


def test_safe_message_redacts_bearer_token() -> None:
    message = _safe_message("Authorization: Bearer super-secret-token-value")
    assert "super-secret-token-value" not in message
    assert "[redacted]" in message
