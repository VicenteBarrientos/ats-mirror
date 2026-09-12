from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.api.errors import register_error_handlers
from app.config import get_settings
from app.db.session import dispose_engine, init_engine
from app.logging_config import setup_logging
from app.providers.registry import build_provider


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(settings.log_level)
    init_engine(settings.database_url)
    app.state.settings = settings
    app.state.provider = build_provider(settings)
    yield
    dispose_engine()


def create_app() -> FastAPI:
    application = FastAPI(
        title="ATS Mirror",
        description="One recruiting data layer. Any ATS. Self-hosted read-only mirror of Applicant Tracking Systems.",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(application)
    application.include_router(api_router, prefix="/api")
    return application


app = create_app()
