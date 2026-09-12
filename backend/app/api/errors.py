from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.providers.errors import (
    EntityNotFoundError,
    ProviderConfigError,
    ProviderUnavailableError,
    UnsupportedCapabilityError,
)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(EntityNotFoundError)
    async def not_found(_request: Request, exc: EntityNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(UnsupportedCapabilityError)
    async def unsupported(_request: Request, exc: UnsupportedCapabilityError) -> JSONResponse:
        return JSONResponse(status_code=501, content={"detail": str(exc)})

    @app.exception_handler(ProviderConfigError)
    async def bad_config(_request: Request, exc: ProviderConfigError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(ProviderUnavailableError)
    async def unavailable(_request: Request, exc: ProviderUnavailableError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})
