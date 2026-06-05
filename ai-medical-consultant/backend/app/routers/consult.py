# -*- coding: utf-8 -*-
"""问诊会话管理：创建会话、发送消息、查询历史。"""

from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import ConsultSession, Message, User
from ..schemas import (
    ChatRequest,
    ChatResponse,
    MessageOut,
    SessionCreate,
    SessionDetail,
    SessionOut,
)
from ..services.agent import medical_agent

router = APIRouter(prefix="/api/v1/consult", tags=["consult"])


def _loads(text: str) -> dict:
    try:
        return json.loads(text) if text else {}
    except Exception:
        return {}


def _session_out(s: ConsultSession) -> SessionOut:
    return SessionOut(
        id=s.id,
        title=s.title,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _message_out(m: Message) -> MessageOut:
    return MessageOut(
        id=m.id, role=m.role, content=m.content, meta=_loads(m.meta), created_at=m.created_at
    )


def _get_owned_session(db: Session, session_id: int, user: User) -> ConsultSession:
    s = db.get(ConsultSession, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "问诊会话不存在")
    return s


@router.post("/sessions", response_model=SessionOut)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = ConsultSession(user_id=user.id, title=payload.title or "新的问诊")
    db.add(s)
    db.commit()
    db.refresh(s)
    return _session_out(s)


@router.get("/sessions", response_model=List[SessionOut])
def list_sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(ConsultSession)
        .filter(ConsultSession.user_id == user.id)
        .order_by(ConsultSession.updated_at.desc())
        .all()
    )
    return [_session_out(s) for s in rows]


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    s = _get_owned_session(db, session_id, user)
    detail = SessionDetail(**_session_out(s).model_dump())
    detail.messages = [_message_out(m) for m in s.messages]
    return detail


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    s = _get_owned_session(db, session_id, user)
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    text = (payload.message or "").strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "消息不能为空")

    # 取得或新建会话
    if payload.session_id:
        s = _get_owned_session(db, payload.session_id, user)
    else:
        s = ConsultSession(user_id=user.id, title=text[:20])
        db.add(s)
        db.commit()
        db.refresh(s)

    history = [{"role": m.role, "content": m.content} for m in s.messages]

    # 保存用户消息
    db.add(Message(session_id=s.id, role="user", content=text))

    # Agent 生成回复
    reply, references = medical_agent.respond(history, text)

    meta = {"references": references}
    db.add(Message(session_id=s.id, role="assistant", content=reply, meta=json.dumps(meta, ensure_ascii=False)))

    if s.title in ("新的问诊", "") or s.title == text[:20]:
        s.title = text[:20]
    db.commit()

    return ChatResponse(session_id=s.id, reply=reply, references=references)
