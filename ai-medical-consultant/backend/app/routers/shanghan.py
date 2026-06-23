# -*- coding: utf-8 -*-
"""《伤寒论》条文解读 API。"""

from __future__ import annotations

import re
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import get_current_user
from ..models import User
from ..services import shanghan_store
from ..services.consult_knowledge import consult_knowledge
from ..services.llm_service import llm_service
from ..services.shanghan_teacher_prompt import build_system_prompt, build_user_prompt

router = APIRouter(prefix="/api/v1/shanghan", tags=["shanghan"])


def _last_assistant_prompt(history: list[dict]) -> str:
    for item in reversed(history):
        if item.get("role") == "assistant":
            return str(item.get("content") or "").strip()
    return ""


def _is_answer_to_previous_prompt(question: str, last_assistant: str) -> bool:
    if not last_assistant:
        return False
    ask_markers = ("先答", "请你先", "你先", "小问题", "问题：", "请回答", "回答这个问题")
    if not any(marker in last_assistant for marker in ask_markers):
        return False
    new_lesson_markers = ("开始", "继续", "派任务", "任务卡", "讲第", "学习第", "抽查", "小测", "换成")
    if any(marker in question for marker in new_lesson_markers):
        return False
    return bool(re.search(r"[\u4e00-\u9fffA-Za-z0-9]", question))


@router.get("")
def list_articles():
    return {"articles": shanghan_store.list_articles()}


@router.get("/study/progress")
def get_study_progress(user: User = Depends(get_current_user)):
    return {"progress": shanghan_store.get_progress(user.id)}


@router.post("/study/session/start")
def start_study_session(payload: dict, user: User = Depends(get_current_user)):
    mode = str(payload.get("mode") or "standard")
    state = str(payload.get("state") or "normal")
    session = shanghan_store.start_session(user.id, mode=mode, state=state)
    return {"session": session, "progress": shanghan_store.get_progress(user.id)}


@router.post("/study/session/{session_id}/answer")
def answer_study_session(
    session_id: str,
    payload: dict,
    user: User = Depends(get_current_user),
):
    try:
        return shanghan_store.answer_session(user.id, session_id, payload)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "study session not found") from None


@router.post("/study/session/{session_id}/complete-article")
def complete_study_article(
    session_id: str,
    payload: dict,
    user: User = Depends(get_current_user),
):
    try:
        return shanghan_store.complete_article(user.id, session_id, payload)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "study session not found") from None


@router.post("/study/complete-article")
def complete_study_article_by_number(
    payload: dict,
    user: User = Depends(get_current_user),
):
    return shanghan_store.complete_article_number(user.id, payload)


@router.get("/study/reviews")
def list_study_reviews(user: User = Depends(get_current_user)):
    return {"reviews": shanghan_store.list_reviews(user.id)}


@router.get("/study/chat")
def get_study_chat(user: User = Depends(get_current_user)):
    progress = shanghan_store.get_progress(user.id)
    article = shanghan_store.get_article_for_study(progress.get("nextArticleNo"))
    return {
        "messages": shanghan_store.get_chat_history(user.id),
        "progress": progress,
        "article": article,
        "llmEnabled": llm_service.available,
    }


@router.post("/study/chat")
def study_chat(payload: dict, user: User = Depends(get_current_user)):
    question = str(payload.get("message") or "").strip()
    if not question:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "消息不能为空")
    if not llm_service.available:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI 未配置，请检查 DeepSeek / OPENAI_API_KEY")

    progress = shanghan_store.get_progress(user.id)
    article_no = payload.get("articleNo") or progress.get("nextArticleNo")
    article = shanghan_store.get_article_for_study(article_no)
    mode = str(payload.get("mode") or progress.get("defaultMode") or "standard")
    state = str(payload.get("state") or "normal")
    history = shanghan_store.get_chat_history(user.id)[-10:]
    last_assistant = _last_assistant_prompt(history)
    interaction_mode = (
        "answer_feedback"
        if _is_answer_to_previous_prompt(question, last_assistant)
        else "ask"
    )

    llm_messages: list[dict] = [{"role": "system", "content": build_system_prompt()}]
    for item in history:
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            llm_messages.append({"role": role, "content": content})
    llm_messages.append(
        {
            "role": "user",
            "content": build_user_prompt(
                question=question,
                article=article,
                progress=progress,
                mode=mode,
                state=state,
                interaction_mode=interaction_mode,
                last_assistant=last_assistant,
            ),
        }
    )

    try:
        reply = llm_service.chat(llm_messages, temperature=0.08)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "AI 回复失败，请稍后重试") from exc

    messages = shanghan_store.append_chat_exchange(
        user.id,
        question=question,
        reply=reply,
        article_no=article.get("number") or article_no,
    )
    return {
        "reply": reply,
        "messages": messages,
        "progress": progress,
        "article": article,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_article(payload: dict, _user: User = Depends(get_current_user)):
    saved = shanghan_store.save_article(payload)
    consult_knowledge.invalidate()
    return saved


@router.put("/{article_id}")
def update_article(
    article_id: str,
    payload: dict,
    _user: User = Depends(get_current_user),
):
    payload["id"] = unquote(article_id)
    saved = shanghan_store.save_article(payload)
    consult_knowledge.invalidate()
    return saved


@router.delete("/{article_id}")
def remove_article(article_id: str, _user: User = Depends(get_current_user)):
    deleted = shanghan_store.delete_article(unquote(article_id))
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "article not found")
    consult_knowledge.invalidate()
    return {"ok": True, "id": article_id}
