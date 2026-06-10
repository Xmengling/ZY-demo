# -*- coding: utf-8 -*-
"""问诊会话管理：创建会话、发送消息、查询历史。"""

from __future__ import annotations

import json
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
    ModuleHintUpdate,
    SessionCreate,
    SessionDetail,
    SessionIntakeUpdate,
    SessionOut,
    SymptomPresetBlock,
    SymptomPresetSection,
)
from ..services.agent import medical_agent
from ..services.consult_autofill import build_autofill_examples_prompt, load_autofill_examples
from ..services.ai_reply_format import format_ai_reply
from ..services.consult_knowledge import consult_knowledge
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
    rows = query.order_by(ConsultSession.updated_at.desc()).all()
    result = [_session_out(s) for s in rows]
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


ASSISTANT_SYSTEM_PROMPT = """你是中医经方学习与问诊助手，帮助医生整理思路、补充问诊与方证参考。

请严格遵守：
1. 仅可依据【本地知识库】中的内容作答，来源限于：用户上传资料、100首方剂解读、伤寒论条文解读。
2. 不得引用互联网、通用教材或知识库中未出现的方剂、条文、药味、剂量与病机说法。
3. 结合【当前病例摘要】与对话历史作答；可提示还需追问的舌脉腹、寒热汗出、二便等信息。
4. 若知识库未检索到相关内容，应明确说明「当前知识库中未检索到相关内容」，不要编造。
5. 用户询问「有哪些文件/资料/方剂/条文」时，只依据【知识库完整目录】作答，不要把【检索摘录】当成全部文件。
6. 用简洁中文，条理清楚；方证建议标注为「学习参考」，不下确定性诊断，不开具具体处方剂量。
7. 出现危急症状时，优先建议及时就医。
8. 若用户上传舌象、检查单等图片，可结合图片可见信息分析，但方证判断仍须以【本地知识库】为准，不得脱离知识库臆测。
9. 输出格式：纯中文纯文本，禁止使用 Markdown；不要用 #、*、-、> 等符号；分点用「1. 2.」或「一是…二是…」；需要小标题时直接写「标题：」即可，不要加粗、不要项目符号堆砌。"""


@router.post("/assistant", response_model=ChatResponse)
def assistant_chat(
    payload: AssistantChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
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
        s = _get_owned_session(db, payload.session_id, user)
    else:
        s = ConsultSession(user_id=user.id, title=text[:20] or "图片问诊")
        db.add(s)
        db.commit()
        db.refresh(s)

    user_display = text or "（已发送图片）"
    user_meta: dict[str, Any] = {}
    if images:
        user_meta["images"] = images

    case_context = (payload.case_context or "").strip()
    retrieve_query = " ".join(part for part in (text, case_context[:800]) if part) or "舌象 脉象 症状"
    inventory = consult_knowledge.build_inventory(db)
    docs = consult_knowledge.search(db, retrieve_query, k=6)
    kb_context = consult_knowledge.build_context(docs)
    references = consult_knowledge.build_references(docs)

    system_content = ASSISTANT_SYSTEM_PROMPT
    if case_context:
        system_content += f"\n\n【当前病例摘要】\n{case_context}"

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_content}]
    for m in s.messages[-12:]:
        if m.role not in ("user", "assistant"):
            continue
        messages.append(message_to_llm(m.role, m.content, _loads(m.meta)))

    question_text = text or "请结合上传的图片（如舌象、检查单等）与病例摘要，给出辨证与方证学习参考。"
    user_block = (
        f"{inventory}\n\n"
        f"【与问题相关的检索摘录（仅 {len(docs)} 条，不等于全部资料）】\n{kb_context}\n\n"
        f"【用户问题】\n{question_text}"
    )
    messages.append({"role": "user", "content": build_user_content(user_block, images)})

    try:
        reply = format_ai_reply(llm_service.chat(messages, temperature=0.3))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "AI 回复失败，请稍后重试") from exc

    db.add(
        Message(
            session_id=s.id,
            role="user",
            content=user_display,
            meta=json.dumps(user_meta, ensure_ascii=False) if user_meta else "",
        )
    )

    meta = {"references": references}
    db.add(
        Message(
            session_id=s.id,
            role="assistant",
            content=reply,
            meta=json.dumps(meta, ensure_ascii=False),
        )
    )
    if s.title in ("新的问诊", "") or len(s.title or "") < 3:
        intake = _loads(s.intake_data)
        s.title = str(intake.get("chief_complaint") or text[:20] or user_display[:20] or "新的问诊")[:40]
    db.commit()

    return ChatResponse(session_id=s.id, reply=reply, references=references)


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
