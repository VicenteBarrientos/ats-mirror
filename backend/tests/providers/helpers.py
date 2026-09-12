from app.providers.base import ATSProvider
from app.providers.mock import MockATSProvider


def contract_providers() -> list[ATSProvider]:
    """Every registered ATS adapter should be added here."""
    return [MockATSProvider()]
