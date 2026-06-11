# -*- coding: utf-8 -*-
"""FastAPI 应用入口。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .seed import run_seed
from .services.knowledge_base import knowledge_base
from .services.llm_service import llm_service
from .routers import consult, formulas, knowledge, shanghan, users, ws
from .services import jingfang_store, shanghan_store

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR / "static"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_seed()
    knowledge_base.ensure_ready()
    jingfang_store.ensure_ready()
    shanghan_store.ensure_ready()
    yield


app = FastAPI(
    title="AI Medical Consultant",
    description="AI 智能问诊系统 —— LLM + Agent + RAG",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(consult.router)
app.include_router(knowledge.router)
app.include_router(formulas.router)
app.include_router(shanghan.router)
app.include_router(ws.router)


@app.get("/")
def root():
    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)
    return {
        "name": "AI Medical Consultant",
        "status": "ok",
        "llm_enabled": llm_service.available,
        "model": settings.openai_chat_model if llm_service.available else "offline-rule",
        "docs": "/docs",
    }


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "llm_enabled": llm_service.available}


if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    for public_dir in ("jingfang", "shanghan"):
        directory = FRONTEND_DIST / public_dir
        if directory.exists():
            app.mount(f"/{public_dir}", StaticFiles(directory=directory, html=True), name=public_dir)


    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        if full_path.startswith(("api/", "docs", "openapi.json")):
            raise HTTPException(status_code=404)

        requested = (FRONTEND_DIST / full_path).resolve()
        try:
            requested.relative_to(FRONTEND_DIST.resolve())
        except ValueError:
            raise HTTPException(status_code=404) from None

        if requested.is_file():
            return FileResponse(requested)
        return FileResponse(FRONTEND_INDEX)
