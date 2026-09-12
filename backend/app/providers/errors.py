from __future__ import annotations

from app.models.enums import Capability


class ProviderError(Exception):
    """Base error for ATS adapter failures."""


class UnsupportedCapabilityError(ProviderError):
    def __init__(self, provider: str, capability: Capability) -> None:
        self.provider = provider
        self.capability = capability
        super().__init__(
            f"Provider '{provider}' does not support capability '{capability.value}'."
        )


class EntityNotFoundError(ProviderError):
    def __init__(self, entity_type: str, entity_id: str) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} '{entity_id}' was not found.")


class ProviderConfigError(ProviderError):
    """Raised when the configured provider cannot be constructed."""


class ProviderUnavailableError(ProviderError):
    """Raised when the ATS is unreachable or returned a transport error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)
