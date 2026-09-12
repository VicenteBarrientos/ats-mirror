from __future__ import annotations

from collections.abc import Callable

from app.config import Settings
from app.providers.base import ATSProvider
from app.providers.dry_run import DryRunProvider
from app.providers.errors import ProviderConfigError
from app.providers.mock import MockATSProvider
from app.providers.workable import WorkableATSProvider

ProviderFactory = Callable[[Settings], ATSProvider]

_FACTORIES: dict[str, ProviderFactory] = {
    "mock": lambda _settings: MockATSProvider(),
    "workable": lambda settings: WorkableATSProvider(settings),
}

# Additional ATS adapters are registered as they are implemented.
_UNIMPLEMENTED = {
    "dover": "Dover is planned. Implement app/providers/dover.py and register it here.",
    "greenhouse": "Greenhouse is planned. Implement an adapter and register it here.",
    "lever": "Lever is planned. Implement an adapter and register it here.",
    "ashby": "Ashby is planned. Implement an adapter and register it here.",
}


def available_providers() -> list[str]:
    return sorted(_FACTORIES)


def register_provider(name: str, factory: ProviderFactory) -> None:
    _FACTORIES[name] = factory


def build_provider(settings: Settings) -> ATSProvider:
    name = settings.ats_provider
    factory = _FACTORIES.get(name)
    if factory is None:
        planned = _UNIMPLEMENTED.get(name)
        if planned:
            raise ProviderConfigError(planned)
        known = ", ".join(available_providers())
        raise ProviderConfigError(f"Unknown ATS_PROVIDER '{name}'. Available: {known}.")
    inner = factory(settings)
    if settings.dry_run:
        return DryRunProvider(inner)
    return inner
