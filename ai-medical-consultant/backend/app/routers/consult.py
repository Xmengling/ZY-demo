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
from ..models import ConsultModuleHint, ConsultSymptomPreset
from ..schemas import (
    ChatRequest,
    ChatResponse,
    MessageOut,
    ModuleHintOut,
    ModuleHintUpdate,
    SessionCreate,
    SessionDetail,
    SessionIntakeUpdate,
    SessionOut,
    SymptomPresetBlock,
    SymptomPresetSection,
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
        patient_name=s.patient_name or "",
        phone=s.phone or "",
        address=s.address or "",
        gender=s.gender or "",
        age=s.age or "",
        modern_diagnosis=s.modern_diagnosis or "",
        status=s.status or "collecting",
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _message_out(m: Message) -> MessageOut:
    return MessageOut(
        id=m.id, role=m.role, content=m.content, meta=_loads(m.meta), created_at=m.created_at
    )


def _session_detail(s: ConsultSession) -> SessionDetail:
    detail = SessionDetail(**_session_out(s).model_dump())
    detail.messages = [_message_out(m) for m in s.messages]
    detail.intake_data = _loads(s.intake_data)
    detail.case_text = s.case_text or ""
    return detail


def _title_from_intake(payload: SessionIntakeUpdate) -> str:
    intake = payload.intake_data or {}
    base = (
        payload.title
        or payload.patient_name
        or intake.get("chief_complaint")
        or intake.get("main_symptoms")
        or "新的问诊"
    )
    return str(base).strip()[:40] or "新的问诊"


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


def _hint_map(db: Session) -> dict[str, list[str]]:
    rows = db.query(ConsultModuleHint).order_by(ConsultModuleHint.module_order).all()
    result: dict[str, list[str]] = {}
    for row in rows:
        hints = _loads(row.hints) if row.hints else []
        result[row.module_key] = [str(item).strip() for item in hints if str(item).strip()]
    return result


@router.get("/symptom-presets", response_model=List[SymptomPresetSection])
def list_symptom_presets(db: Session = Depends(get_db)):
    rows = (
        db.query(ConsultSymptomPreset)
        .order_by(
            ConsultSymptomPreset.module_order,
            ConsultSymptomPreset.block_order,
            ConsultSymptomPreset.id,
        )
        .all()
    )
    hints_by_module = _hint_map(db)
    sections: dict[str, SymptomPresetSection] = {}
    for row in rows:
        section = sections.get(row.module_key)
        if not section:
            section = SymptomPresetSection(
                key=row.module_key,
                order=row.module_order,
                title=row.module_title,
                tag=row.module_tag,
                tone=row.module_tone,
                blocks=[],
                inquiry_hints=hints_by_module.get(row.module_key, []),
            )
            sections[row.module_key] = section
        section.blocks.append(
            SymptomPresetBlock(
                label=row.block_label,
                tone=row.module_tone,
                symptoms=_loads(row.symptoms) if row.symptoms else [],
            )
        )
    return list(sections.values())


@router.put("/module-hints/{module_key}", response_model=ModuleHintOut)
def update_module_hints(
    module_key: str,
    payload: ModuleHintUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    del user
    hints = [str(item).strip() for item in (payload.hints or []) if str(item).strip()]
    row = db.query(ConsultModuleHint).filter(ConsultModuleHint.module_key == module_key).first()
    if not row:
        preset = (
            db.query(ConsultSymptomPreset)
            .filter(ConsultSymptomPreset.module_key == module_key)
            .order_by(ConsultSymptomPreset.module_order)
            .first()
        )
        if not preset:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "模块不存在")
        row = ConsultModuleHint(
            module_key=module_key,
            module_order=preset.module_order,
            hints=json.dumps(hints, ensure_ascii=False),
        )
        db.add(row)
    else:
        row.hints = json.dumps(hints, ensure_ascii=False)
    db.commit()
    db.refresh(row)
    return ModuleHintOut(module_key=row.module_key, hints=hints)


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    s = _get_owned_session(db, session_id, user)
    return _session_detail(s)


@router.patch("/sessions/{session_id}/intake", response_model=SessionDetail)
def update_session_intake(
    session_id: int,
    payload: SessionIntakeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = _get_owned_session(db, session_id, user)
    s.title = _title_from_intake(payload)
    s.patient_name = payload.patient_name.strip()
    s.phone = payload.phone.strip()
    s.address = payload.address.strip()
    s.gender = payload.gender.strip()
    s.age = payload.age.strip()
    s.modern_diagnosis = payload.modern_diagnosis.strip()
    s.status = payload.status.strip() or "collecting"
    s.intake_data = json.dumps(payload.intake_data or {}, ensure_ascii=False)
    s.case_text = payload.case_text.strip()
    db.commit()
    db.refresh(s)
    return _session_detail(s)


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
