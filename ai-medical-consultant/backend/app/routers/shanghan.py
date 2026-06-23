# -*- coding: utf-8 -*-
"""《伤寒论》条文解读 API。"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import get_current_user
from ..models import User
from ..services import shanghan_store
from ..services.consult_knowledge import consult_knowledge
from ..services.llm_service import llm_service
from ..services.shanghan_teacher_prompt import build_system_prompt, build_user_prompt

router = APIRouter(prefix="/api/v1/shanghan", tags=["shanghan"])


def _clean_markdown(text: str) -> str:
    return (
        text.replace("[[**", "")
        .replace("**]]", "")
        .replace("**", "")
        .replace("###", "")
        .replace("##", "")
        .strip()
    )


def _last_assistant_prompt(history: list[dict]) -> str:
    for item in reversed(history):
        if item.get("role") == "assistant":
            return str(item.get("content") or "").strip()
    return ""


def _normalize_question(text: str) -> str:
    cleaned = _clean_markdown(text)
    cleaned = re.sub(r"^[\-*、\d.\s：:]+", "", cleaned)
    cleaned = re.sub(r"\s+", "", cleaned)
    cleaned = cleaned.rstrip("？?。.!！")
    return cleaned


def _extract_questions(text: str) -> list[str]:
    cleaned = _clean_markdown(text)
    candidates: list[str] = []
    for match in re.finditer(r"([^。！？\n]{4,90}[？?])", cleaned):
        candidates.append(match.group(1).strip())
    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "问题：" in line or "小问题：" in line:
            question = re.split(r"问题：|小问题：", line, maxsplit=1)[-1].strip()
            if question and question not in candidates:
                candidates.append(question)
    unique: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        normalized = _normalize_question(item)
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(item)
    return unique


def _recent_assistant_questions(history: list[dict], limit: int = 6) -> list[str]:
    questions: list[str] = []
    seen: set[str] = set()
    for item in reversed(history):
        if item.get("role") != "assistant":
            continue
        for question in reversed(_extract_questions(str(item.get("content") or ""))):
            normalized = _normalize_question(question)
            if normalized and normalized not in seen:
                seen.add(normalized)
                questions.append(question)
            if len(questions) >= limit:
                return list(reversed(questions))
    return list(reversed(questions))


def _is_similar_question(candidate: str, asked_questions: set[str]) -> bool:
    normalized = _normalize_question(candidate)
    if not normalized:
        return False
    if normalized in asked_questions:
        return True
    for asked in asked_questions:
        if not asked:
            continue
        shorter, longer = sorted((normalized, asked), key=len)
        if len(shorter) >= 8 and shorter in longer:
            return True
        if SequenceMatcher(None, normalized, asked).ratio() >= 0.86:
            return True
    return False


def _fallback_question(article: dict, recent_questions: list[str]) -> str:
    candidates = [
        "请换个角度回答：这一条里哪一个词最能提示病位在表？",
        "你用一句话说说：为什么这些症状要合在一起看，不能拆开单独判断？",
        "这一条最容易被误解成具体病名，问题出在哪里？",
        "如果只记一个辨证边界，你会记哪一句？",
        "这一组症状成立太阳病的关键条件是什么？",
    ]
    asked = {_normalize_question(question) for question in recent_questions}
    for candidate in candidates:
        if not _is_similar_question(candidate, asked):
            return candidate
    number = article.get("number") or article.get("articleNo") or "当前"
    return f"请从第{number}条里另选一个你认为最重要的字词，说说它为什么是抓手。"


def _avoid_repeated_question(reply: str, recent_questions: list[str], article: dict) -> str:
    asked = {_normalize_question(question) for question in recent_questions}
    questions = _extract_questions(reply)
    if not questions:
        return reply
    last_question = questions[-1]
    if not _is_similar_question(last_question, asked):
        return reply
    replacement = _fallback_question(article, recent_questions)
    index = reply.rfind(last_question)
    if index < 0:
        return f"{reply.rstrip()}\n\n### 换一个角度追问\n{replacement}"
    return f"{reply[:index].rstrip()}\n\n### 换一个角度追问\n{replacement}"


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
    recent_questions = _recent_assistant_questions(history)
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
                recent_questions=recent_questions,
            ),
        }
    )

    try:
        reply = llm_service.chat(llm_messages, temperature=0.08)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "AI 回复失败，请稍后重试") from exc

    reply = _avoid_repeated_question(reply, recent_questions, article)
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
