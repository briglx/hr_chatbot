from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    print("Starting up...")
    yield
    print("Shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="HR AI Chatbot",
        description="AI-powered HR assistant for Microsoft Teams",
        version="0.1.0",
    )

    app.include_router(router)
    
    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
