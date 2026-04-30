"""Main entry point for the HR AI Chatbot application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import structlog

from app.api.routes import router as api_router
from app.config.logging import setup_logging
from app.config.settings import get_settings
from app.memory.stores.redis_store import RedisStore

setup_logging()
logger = structlog.get_logger()
logger.info("Application initialized")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for FastAPI application. This function is responsible for setting up and tearing down resources that the application depends on, such as the Redis connection pool. It is executed once when the application starts and once when it shuts down."""
    logger = structlog.get_logger()
    logger.info("Starting up...")
    settings = get_settings()

    logger.info("Connecting to Redis at ", url=settings.redis_url)
    redis_store = RedisStore(settings.redis_url)
    await redis_store.connect()

    app.state.redis_store = redis_store

    yield

    logger.info("Cleaning up resources...")
    await redis_store.disconnect()


def create_app() -> FastAPI:
    """Factory function to create and configure the FastAPI application."""
    app = FastAPI(
        title="HR AI Chatbot",
        description="AI-powered HR assistant for Microsoft Teams",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(api_router)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    templates = Jinja2Templates(directory="app/templates")

    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        return templates.TemplateResponse(request=request, name="index.html")

    return app


app = create_app()
