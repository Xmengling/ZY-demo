# -*- coding: utf-8 -*-
"""Pydantic 数据模型（请求/响应）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


# ---------- 用户 / 认证 ----------
class UserRegister(BaseModel):
    username: str
    password: str
    full_name: str = ""


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- 问诊 ----------
class SessionCreate(BaseModel):
    title: Optional[str] = None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    meta: dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessionDetail(SessionOut):
    messages: List[MessageOut] = []


class ChatRequest(BaseModel):
    session_id: Optional[int] = None
    message: str


class ChatResponse(BaseModel):
    session_id: int
    reply: str
    references: List[dict[str, Any]] = []


# ---------- 知识库 ----------
class KnowledgeOut(BaseModel):
    id: int
    category: str
    title: str
    department: str
    content: str

    class Config:
        from_attributes = True


class KnowledgeCreate(BaseModel):
    category: str
    title: str
    department: str = ""
    content: str


class KnowledgeSearchResult(BaseModel):
    title: str
    category: str
    department: str
    snippet: str
    score: float


class KnowledgeListPage(BaseModel):
    items: List[KnowledgeOut]
    total: int
    page: int
    page_size: int
    pages: int


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


class CategoryRename(BaseModel):
    old_name: str = Field(..., min_length=1, max_length=64)
    new_name: str = Field(..., min_length=1, max_length=64)
