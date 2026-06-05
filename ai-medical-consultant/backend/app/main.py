# -*- coding: utf-8 -*-
"""FastAPI 应用入口。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .seed import run_seed
from .services.knowledge_base import knowledge_base
from .services.llm_service import llm_service
from .routers import consult, formulas, knowledge, users, ws
from .services import jingfang_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_seed()
    knowledge_base.ensure_ready()
    jingfang_store.ensure_ready()
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
app.include_router(ws.router)


@app.get("/")
def root():
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
