from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Autonomous Coding Agent",
    description="Self-correcting Python execution agent API.",
    version="0.1.0",
)

app.include_router(router)
