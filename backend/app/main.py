from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import cors_origin_list, get_settings
from app.core.db import SessionLocal
from app.services.seed import seed_demo_if_empty


@asynccontextmanager
async def lifespan(_: FastAPI):
    Path(get_settings().media_dir).mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        seed_demo_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Sweety", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origin_list(),
    allow_origin_regex=r"https://.*\.(up\.railway\.app|railway\.app|fly\.dev)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api/v1")
media_path = Path(get_settings().media_dir)
media_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_path)), name="media")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "name": "sweety"}
