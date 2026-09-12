import pytest
from app.config import get_settings, reset_settings_cache
from app.providers.errors import ProviderConfigError
from app.providers.registry import build_provider


def test_unknown_provider_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATS_PROVIDER", "not-a-real-ats")
    reset_settings_cache()
    with pytest.raises(ProviderConfigError, match="Unknown ATS_PROVIDER"):
        build_provider(get_settings())
    reset_settings_cache()


def test_workable_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATS_PROVIDER", "workable")
    monkeypatch.setenv("WORKABLE_SUBDOMAIN", "")
    monkeypatch.setenv("WORKABLE_ACCESS_TOKEN", "")
    reset_settings_cache()
    with pytest.raises(ProviderConfigError, match="WORKABLE"):
        build_provider(get_settings())
    reset_settings_cache()


def test_workable_builds_with_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATS_PROVIDER", "workable")
    monkeypatch.setenv("WORKABLE_SUBDOMAIN", "acme")
    monkeypatch.setenv("WORKABLE_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("DRY_RUN", "false")
    reset_settings_cache()
    provider = build_provider(get_settings())
    assert provider.name == "workable"
    reset_settings_cache()
