# -*- coding: utf-8 -*-
"""问诊会话管理：创建会话、发送消息、查询历史。"""

from __future__ import annotations

import json
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import ConsultSession, Message, User
from ..models import ConsultModuleHint, ConsultSymptomPreset
from ..schemas import (
    AssistantChatRequest,
    ChatRequest,
    ChatResponse,
    ConsultAutoFillRequest,
    ConsultAutoFillResponse,
    ConsultAutoFillExampleOut,
    MessageOut,
    ModuleHintOut,
    BulkDeleteSessionsRequest,
    BulkDeleteSessionsResponse,
    MergeSessionsRequest,
    MergeSessionsResponse,
    ModuleHintUpdate,
    RuleSuggestionOut,
    SaveUserRuleRequest,
    SaveUserRuleResponse,
    SessionCreate,
    SessionDetail,
    SessionIntakeUpdate,
    SessionOut,
    SymptomPresetBlock,
    SymptomPresetSection,
)
from ..services.agent import medical_agent
from ..services.consult_autofill import build_autofill_examples_prompt, load_autofill_examples
from ..services.ai_reply_format import extract_followup_questions, format_ai_reply
from ..services.consult_chat_prompt import build_assistant_system_prompt, classify_assistant_question
from ..services.session_merge import merge_case_text, merge_intake_data
from ..services.user_rules import append_user_rule, build_rule_suggestion
from ..services.consult_knowledge import (
    build_prescription_authority_block,
    build_prescription_notice,
    collect_prescription_display_items,
    collect_prescription_names,
    consult_knowledge,
)
from ..services.image_chat import ImageValidationError, build_user_content, message_to_llm, validate_image_data_urls
from ..services.llm_service import llm_service

router = APIRouter(prefix="/api/v1/consult", tags=["consult"])

AUTOFILL_FIELDS = {
    "patient_name",
    "phone",
    "address",
    "gender",
    "age",
    "visit_time",
    "doctor",
    "modern_diagnosis",
    "chief_complaint",
    "history",
    "tongue_image",
    "pulse",
    "abdominal",
}

AUTOFILL_FIELD_LABELS = {
    "patient_name": "姓名",
    "phone": "电话",
    "address": "住址",
    "gender": "性别",
    "age": "年龄",
    "visit_time": "就诊时间，尽量输出 YYYY-MM-DD",
    "doctor": "主诊医生",
    "modern_diagnosis": "现代诊断/检查",
    "chief_complaint": "主诉",
    "history": "病程、诱因、既往史、用药史",
    "tongue_body": "舌质",
    "tongue_coat": "舌苔",
    "pulse": "脉象",
    "abdominal": "腹诊",
}

PATHOLOGY_NOTE_ALIASES = {
    "水证": "水实",
}


def _loads(text: str) -> dict:
    try:
        return json.loads(text) if text else {}
    except Exception:
        return {}


def _first_visit_text(text: str) -> str:
    markers = ["复诊", "二诊", "三诊", "再诊"]
    cut = min([idx for marker in markers if (idx := text.find(marker)) >= 0] or [len(text)])
    return text[:cut]


def _extract_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _symptom_catalog(db: Session) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    rows = (
        db.query(ConsultSymptomPreset)
        .order_by(
            ConsultSymptomPreset.module_order,
            ConsultSymptomPreset.block_order,
            ConsultSymptomPreset.id,
        )
        .all()
    )
    catalog: list[dict[str, Any]] = []
    allowed: set[str] = set()
    allowed_blocks: set[str] = set()
    for row in rows:
        symptoms = _loads(row.symptoms) if row.symptoms else []
        if not isinstance(symptoms, list):
            symptoms = []
        cleaned = [str(item).strip() for item in symptoms if str(item).strip()]
        allowed.update(cleaned)
        if row.block_label:
            allowed_blocks.add(str(row.block_label).strip())
        catalog.append(
            {
                "module": row.module_title,
                "block": row.block_label,
                "symptoms": cleaned,
            }
        )
    return catalog, allowed, allowed_blocks


def _normalize_auto_fill_payload(
    data: dict[str, Any],
    allowed_symptoms: set[str],
    allowed_blocks: set[str],
) -> dict[str, Any]:
    raw_fields = data.get("fields") if isinstance(data.get("fields"), dict) else {}
    fields: dict[str, str] = {}
    for key in AUTOFILL_FIELDS:
        value = raw_fields.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        if key == "gender":
            if "女" in text:
                text = "女"
            elif "男" in text:
                text = "男"
            else:
                continue
        if key == "age":
            text = text.replace("岁", "").strip()
        if key == "visit_time":
            text = text.replace("年", "-").replace("月", "-").replace("日", "").strip()
        fields[key] = text[:500]

    tongue_body = str(raw_fields.get("tongue_body") or "").strip()
    tongue_coat = str(raw_fields.get("tongue_coat") or "").strip()
    tongue_image = str(raw_fields.get("tongue_image") or "").strip()
    if tongue_body or tongue_coat:
        fields["tongue_image"] = "，".join(part for part in (tongue_body, tongue_coat) if part)[:500]
    elif tongue_image:
        fields["tongue_image"] = tongue_image[:500]

    symptoms: list[str] = []
    seen: set[str] = set()
    raw_symptoms = data.get("symptoms") if isinstance(data.get("symptoms"), list) else []
    for item in raw_symptoms:
        symptom = str(item).strip()
        if symptom and symptom in allowed_symptoms and symptom not in seen:
            symptoms.append(symptom)
            seen.add(symptom)

    raw_notes = data.get("notes") if isinstance(data.get("notes"), list) else []
    notes = [str(item).strip()[:120] for item in raw_notes if str(item).strip()]

    pathology_notes: dict[str, str] = {}
    raw_pathology_notes = (
        data.get("pathology_notes") if isinstance(data.get("pathology_notes"), dict) else {}
    )
    for label, value in raw_pathology_notes.items():
        block_label = str(label).strip()
        block_label = PATHOLOGY_NOTE_ALIASES.get(block_label, block_label)
        text = str(value).strip()
        if block_label in allowed_blocks and text:
            pathology_notes[block_label] = text[:500]

    return {
        "fields": fields,
        "symptoms": symptoms,
        "pathology_notes": pathology_notes,
        "notes": notes[:5],
    }


def _intake_has_case_content(intake: dict[str, Any]) -> bool:
    if not intake:
        return False
    text_fields = (
        "patient_name",
        "chief_complaint",
        "history",
        "doctor",
        "phone",
        "address",
        "gender",
        "age",
        "modern_diagnosis",
        "pulse",
        "abdominal",
        "tongue_image",
        "visit_time",
    )
    if any(str(intake.get(field) or "").strip() for field in text_fields):
        return True
    selected = intake.get("selected") or {}
    if any(selected.values()):
        return True
    notes = intake.get("notes") or {}
    if any(str(value).strip() for value in notes.values()):
        return True
    prescription = intake.get("prescription") or {}
    rows = prescription.get("rows") or []
    return any(str(row.get("name") or "").strip() for row in rows)


def _session_linked_case(s: ConsultSession) -> bool:
    if (s.patient_name or "").strip() or (s.case_text or "").strip():
        return True
    if _intake_has_case_content(_loads(s.intake_data)):
        return True
    for message in s.messages:
        meta = _loads(message.meta)
        if meta.get("case_linked"):
            return True
    return False


def _session_out(s: ConsultSession) -> SessionOut:
    intake = _loads(s.intake_data)
    return SessionOut(
        id=s.id,
        title=s.title,
        chief_complaint=str(intake.get("chief_complaint") or s.title or ""),
        patient_name=s.patient_name or "",
        doctor=str(intake.get("doctor") or ""),
        phone=s.phone or "",
        address=s.address or "",
        gender=s.gender or "",
        age=s.age or "",
        modern_diagnosis=s.modern_diagnosis or "",
        status=s.status or "collecting",
        linked_case=_session_linked_case(s),
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
def list_sessions(
    chief_complaint: str | None = None,
    patient_name: str | None = None,
    doctor: str | None = None,
    ai_chat: bool = Query(False, description="仅返回含 AI 问答记录的会话"),
    case_only: bool = Query(False, description="仅返回已关联医案内容的会话"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(ConsultSession).filter(ConsultSession.user_id == user.id)
    if ai_chat:
        assistant_exists = exists(select(Message.id).where(
            Message.session_id == ConsultSession.id,
            Message.role == "assistant",
        ))
        query = query.filter(assistant_exists)
    rows = query.order_by(ConsultSession.created_at.desc()).all()
    result = [_session_out(s) for s in rows]
    if case_only:
        result = [s for s in result if s.linked_case]
    chief_q = (chief_complaint or "").strip()
    patient_q = (patient_name or "").strip()
    doctor_q = (doctor or "").strip()
    if chief_q:
        result = [s for s in result if chief_q in (s.chief_complaint or s.title)]
    if patient_q:
        result = [s for s in result if patient_q in s.patient_name]
    if doctor_q:
        result = [s for s in result if doctor_q in s.doctor]
    return result


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


@router.get("/auto-fill/examples", response_model=List[ConsultAutoFillExampleOut])
def list_autofill_examples():
    return [
        ConsultAutoFillExampleOut(
            title=str(item.get("title") or f"案例{index}"),
            raw_text=str(item.get("raw_text") or "").strip(),
        )
        for index, item in enumerate(load_autofill_examples(), 1)
    ]


@router.post("/auto-fill", response_model=ConsultAutoFillResponse)
def auto_fill_intake(
    payload: ConsultAutoFillRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    del user
    text = _first_visit_text((payload.raw_text or "").strip())
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请先粘贴医案文本")
    if not llm_service.available:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "LLM 未配置，已回退本地解析")

    catalog, allowed_symptoms, allowed_blocks = _symptom_catalog(db)
    field_lines = "\n".join(
        f"- {key}: {label}" for key, label in AUTOFILL_FIELD_LABELS.items()
    )
    examples_prompt = build_autofill_examples_prompt()
    messages = [
        {
            "role": "system",
            "content": (
                "你是中医问诊资料结构化助手，只做信息抽取，不做诊断、不补充文本里没有的信息。"
                "遇到复诊、二诊、三诊、再诊之后的内容视为无效。"
                "输出必须是严格 JSON，不要 Markdown，不要解释。"
            ),
        },
        {
            "role": "user",
            "content": (
                "请从下面医案/病历文本中抽取问诊表单字段，并匹配症状。\n\n"
                "字段只能放在 fields 对象中，允许字段如下：\n"
                f"{field_lines}\n\n"
                "症状只能从 symptom_catalog 中原样选择，不允许改写、合并或新增；否定症状不要选择。\n"
                "如果文本没有明确给出某字段，字段值留空或省略。\n"
                "history 只写起病背景、病程演变、诱因、既往史、用药史；不要把所有现症、舌脉腹诊和检查都塞进去。\n"
                "modern_diagnosis 可放现代诊断、检查、检验、辅助检查。\n\n"
                "pathology_notes 用来填写每个病理项的“本例所见”。key 必须使用 symptom_catalog 中的 block 名称，"
                "例如：里虚、里寒、里热、里实、半热、水实、水虚、气实、血实、血虚、阴性等；"
                "水证要拆成水实或水虚，不要输出水证。"
                "value 应直接摘取或轻微归纳原文证据，不要诊断化，不要使用文本外信息。"
                "如果某病理项没有明确证据，不要输出该 key。\n\n"
                f"{examples_prompt}\n\n"
                "返回格式：\n"
                "{\"fields\":{\"patient_name\":\"\",\"gender\":\"\",\"age\":\"\",\"phone\":\"\",\"address\":\"\","
                "\"visit_time\":\"\",\"doctor\":\"\","
                "\"modern_diagnosis\":\"\",\"chief_complaint\":\"\",\"history\":\"\","
                "\"tongue_body\":\"\",\"tongue_coat\":\"\",\"pulse\":\"\",\"abdominal\":\"\"},"
                "\"symptoms\":[],\"pathology_notes\":{},\"notes\":[]}\n\n"
                f"symptom_catalog:\n{json.dumps(catalog, ensure_ascii=False)}\n\n"
                f"文本：\n{text[:9000]}"
            ),
        },
    ]
    try:
        raw = llm_service.chat(messages, temperature=0.05)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "AI 解析失败，已回退本地解析") from exc

    parsed = _extract_json_object(raw)
    normalized = _normalize_auto_fill_payload(parsed, allowed_symptoms, allowed_blocks)
    return ConsultAutoFillResponse(
        fields=normalized["fields"],
        symptoms=normalized["symptoms"],
        pathology_notes=normalized["pathology_notes"],
        notes=normalized["notes"],
        source="ai",
    )


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


@router.post("/sessions/bulk-delete", response_model=BulkDeleteSessionsResponse)
def bulk_delete_sessions(
    payload: BulkDeleteSessionsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ids = sorted({int(item) for item in payload.session_ids})
    deleted = 0
    for session_id in ids:
        s = _get_owned_session(db, session_id, user)
        db.delete(s)
        deleted += 1
    db.commit()
    return BulkDeleteSessionsResponse(deleted_count=deleted)


@router.post("/sessions/merge", response_model=MergeSessionsResponse)
def merge_sessions(
    payload: MergeSessionsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ids = sorted({int(item) for item in payload.session_ids})
    target_id = int(payload.target_id)
    if target_id not in ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "合并目标必须在所选医案内")
    if len(ids) < 2:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请至少选择 2 条医案再合并")

    sessions = [_get_owned_session(db, session_id, user) for session_id in ids]
    target = next(item for item in sessions if item.id == target_id)
    others = [item for item in sessions if item.id != target_id]

    merged_intake = _loads(target.intake_data)
    merged_case_text = target.case_text or ""
    for item in others:
        merged_intake = merge_intake_data(merged_intake, _loads(item.intake_data))
        merged_case_text = merge_case_text(merged_case_text, item.case_text or "")

    target.intake_data = json.dumps(merged_intake, ensure_ascii=False)
    target.case_text = merged_case_text.strip()
    target.title = _title_from_intake(
        SessionIntakeUpdate(
            title=target.title,
            patient_name=merged_intake.get("patient_name") or target.patient_name,
            modern_diagnosis=merged_intake.get("modern_diagnosis") or target.modern_diagnosis,
            intake_data=merged_intake,
        )
    )
    target.patient_name = str(merged_intake.get("patient_name") or target.patient_name or "").strip()
    target.phone = str(merged_intake.get("phone") or target.phone or "").strip()
    target.address = str(merged_intake.get("address") or target.address or "").strip()
    target.gender = str(merged_intake.get("gender") or target.gender or "").strip()
    target.age = str(merged_intake.get("age") or target.age or "").strip()
    target.modern_diagnosis = str(
        merged_intake.get("modern_diagnosis") or target.modern_diagnosis or ""
    ).strip()

    for item in others:
        db.delete(item)
    db.commit()
    db.refresh(target)
    return MergeSessionsResponse(session_id=target.id, merged_count=len(ids))


def _prepare_assistant_chat(
    db: Session,
    user: User,
    payload: AssistantChatRequest,
) -> dict[str, Any]:
    text = (payload.message or "").strip()
    try:
        images = validate_image_data_urls(payload.images or [])
    except ImageValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if not text and not images:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "消息不能为空")
    if not llm_service.available:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI 未配置，请设置 OPENAI_API_KEY")

    if payload.session_id:
        session = _get_owned_session(db, payload.session_id, user)
    else:
        session = ConsultSession(user_id=user.id, title=text[:20] or "图片问诊")
        db.add(session)
        db.commit()
        db.refresh(session)

    user_display = text or "（已发送图片）"
    user_meta: dict[str, Any] = {}
    if images:
        user_meta["images"] = images

    case_context = (payload.case_context or "").strip()
    if case_context:
        user_meta["case_linked"] = True

    intake_data = _loads(session.intake_data) if session.intake_data else None
    prescription_names = collect_prescription_names(case_context, intake_data)
    prescription_items = collect_prescription_display_items(case_context, intake_data)

    prescription_query = " ".join(prescription_names)
    retrieve_query = " ".join(
        part for part in (text, prescription_query, case_context[:1200]) if part
    ) or "舌象 脉象 症状"
    inventory = consult_knowledge.build_inventory(db)
    docs = consult_knowledge.search_enhanced(db, retrieve_query, prescription_names, k=6)
    kb_context = consult_knowledge.build_context(docs)
    references = consult_knowledge.build_references(docs)

    prescription_notice = build_prescription_notice(prescription_items)
    prescription_authority = build_prescription_authority_block(case_context, prescription_items)
    question_type = classify_assistant_question(
        text,
        has_case=bool(case_context),
        prescription_names=prescription_names,
    )
    system_content = build_assistant_system_prompt(
        question_type,
        case_context=case_context,
        prescription_notice=prescription_notice,
    )

    llm_messages: list[dict[str, Any]] = [{"role": "system", "content": system_content}]
    for message in session.messages[-12:]:
        if message.role not in ("user", "assistant"):
            continue
        llm_messages.append(message_to_llm(message.role, message.content, _loads(message.meta)))

    question_text = text or "请结合上传的图片（如舌象、检查单等）与病例摘要，给出辨证与方证学习参考。"
    user_parts = [inventory]
    if prescription_authority:
        user_parts.append(prescription_authority)
    user_parts.append(
        f"【与问题相关的检索摘录（仅 {len(docs)} 条，不等于全部资料；不得当作当前用方清单）】\n{kb_context}"
    )
    user_parts.append(f"【用户问题】\n{question_text}")
    user_block = "\n\n".join(user_parts)
    llm_messages.append({"role": "user", "content": build_user_content(user_block, images)})

    rule_suggestion = build_rule_suggestion(text)

    return {
        "session": session,
        "messages": llm_messages,
        "references": references,
        "user_display": user_display,
        "user_meta": user_meta,
        "text": text,
        "rule_suggestion": rule_suggestion,
    }


def _save_assistant_exchange(db: Session, ctx: dict[str, Any], reply: str) -> ConsultSession:
    session: ConsultSession = ctx["session"]
    user_meta: dict[str, Any] = ctx["user_meta"]
    references: list[dict[str, Any]] = ctx["references"]
    text: str = ctx["text"]
    user_display: str = ctx["user_display"]

    db.add(
        Message(
            session_id=session.id,
            role="user",
            content=user_display,
            meta=json.dumps(user_meta, ensure_ascii=False) if user_meta else "",
        )
    )
    followups = extract_followup_questions(reply)
    assistant_meta: dict[str, Any] = {"references": references}
    if followups:
        assistant_meta["followups"] = followups
    db.add(
        Message(
            session_id=session.id,
            role="assistant",
            content=reply,
            meta=json.dumps(assistant_meta, ensure_ascii=False),
        )
    )
    if session.title in ("新的问诊", "") or len(session.title or "") < 3:
        intake = _loads(session.intake_data)
        session.title = str(intake.get("chief_complaint") or text[:20] or user_display[:20] or "新的问诊")[:40]
    db.commit()
    db.refresh(session)
    return session


@router.post("/assistant", response_model=ChatResponse)
def assistant_chat(
    payload: AssistantChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ctx = _prepare_assistant_chat(db, user, payload)
    try:
        raw_reply = llm_service.chat(ctx["messages"], temperature=0.3)
        followups = extract_followup_questions(raw_reply)
        reply = format_ai_reply(raw_reply)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "AI 回复失败，请稍后重试") from exc

    session = _save_assistant_exchange(db, ctx, reply)
    rule_suggestion = ctx.get("rule_suggestion")
    return ChatResponse(
        session_id=session.id,
        reply=reply,
        references=ctx["references"],
        followups=followups,
        rule_suggestion=RuleSuggestionOut(**rule_suggestion) if rule_suggestion else None,
    )


@router.post("/assistant/stream")
def assistant_chat_stream(
    payload: AssistantChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ctx = _prepare_assistant_chat(db, user, payload)
    session_id = ctx["session"].id
    references = ctx["references"]
    rule_suggestion = ctx.get("rule_suggestion")

    def event_stream():
        parts: list[str] = []
        yield f"data: {json.dumps({'type': 'start', 'session_id': session_id}, ensure_ascii=False)}\n\n"
        try:
            for token in llm_service.stream(ctx["messages"], temperature=0.3):
                parts.append(token)
                yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
            raw_reply = "".join(parts)
            followups = extract_followup_questions(raw_reply)
            reply = format_ai_reply(raw_reply)
            _save_assistant_exchange(db, ctx, reply)
            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "done",
                        "session_id": session_id,
                        "reply": reply,
                        "references": references,
                        "followups": followups,
                        "rule_suggestion": rule_suggestion,
                    },
                    ensure_ascii=False,
                )
                + "\n\n"
            )
        except Exception:
            db.rollback()
            yield f"data: {json.dumps({'type': 'error', 'message': 'AI 回复失败，请稍后重试'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/assistant/rules", response_model=SaveUserRuleResponse)
def save_assistant_user_rule(
    payload: SaveUserRuleRequest,
    user: User = Depends(get_current_user),
):
    del user
    ok, message = append_user_rule(payload.rule_text, source_message=payload.source_message)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, message)
    return SaveUserRuleResponse(ok=True, message=message)


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
