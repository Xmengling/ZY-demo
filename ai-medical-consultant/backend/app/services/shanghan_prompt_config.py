# -*- coding: utf-8 -*-
"""《伤寒论》读书课堂 prompt 配置。"""

from __future__ import annotations

import time
from functools import lru_cache
from pathlib import Path

from ..config import BASE_DIR
from . import shanghan_store

PROJECT_ROOT = BASE_DIR.parent.parent

SKILL_PATH = PROJECT_ROOT / "note" / "伤寒论读书skill.md"
CLASSROOM_PATH = PROJECT_ROOT / "note" / "伤寒论上课模式设计.md"

PROMPT_CONFIG_SESSION_ID = "shanghan-study-prompt-config"
MAX_PROMPT_TEXT_LENGTH = 20000


def _read_text(path: Path, limit: int = MAX_PROMPT_TEXT_LENGTH) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    return text.strip()[:limit]


@lru_cache(maxsize=1)
def default_prompt_config() -> dict:
    return {
        "skillText": _read_text(SKILL_PATH),
        "classroomText": _read_text(CLASSROOM_PATH),
    }


def _normalize_text(value: object) -> str:
    return str(value or "").strip()[:MAX_PROMPT_TEXT_LENGTH]


def _config_session_id(user_id: int | str) -> str:
    return f"{PROMPT_CONFIG_SESSION_ID}-{shanghan_store._user_key(user_id)}"


def get_prompt_config(user_id: int | str) -> dict:
    defaults = default_prompt_config()
    session = shanghan_store.get_session(user_id, _config_session_id(user_id)) or {}
    saved = session.get("config") if isinstance(session.get("config"), dict) else {}

    skill_text = _normalize_text(saved.get("skillText")) or defaults["skillText"]
    classroom_text = _normalize_text(saved.get("classroomText")) or defaults["classroomText"]

    return {
        "skillText": skill_text,
        "classroomText": classroom_text,
        "defaultSkillText": defaults["skillText"],
        "defaultClassroomText": defaults["classroomText"],
        "hardRulesText": "",
        "updatedAt": session.get("updatedAt"),
        "usingDefault": not bool(saved),
        "maxLength": MAX_PROMPT_TEXT_LENGTH,
    }


def save_prompt_config(user_id: int | str, payload: dict) -> dict:
    skill_text = _normalize_text(payload.get("skillText"))
    classroom_text = _normalize_text(payload.get("classroomText"))
    if not skill_text:
        raise ValueError("学习 Skill 不能为空")

    now = int(time.time())
    session = {
        "id": _config_session_id(user_id),
        "type": "prompt_config",
        "config": {
            "skillText": skill_text,
            "classroomText": classroom_text,
        },
        "updatedAt": now,
    }
    shanghan_store.save_session(user_id, session)
    return get_prompt_config(user_id)


def reset_prompt_config(user_id: int | str) -> dict:
    shanghan_store.delete_session(user_id, _config_session_id(user_id))
    return get_prompt_config(user_id)


def classroom_rules_for_user(user_id: int | str | None = None) -> str:
    if user_id is None:
        defaults = default_prompt_config()
        skill_text = defaults["skillText"]
        classroom_text = defaults["classroomText"]
    else:
        config = get_prompt_config(user_id)
        skill_text = config["skillText"]
        classroom_text = config["classroomText"]

    parts = [
        ("读书 skill", skill_text),
        ("上课模式", classroom_text),
    ]
    return "\n\n".join(f"【{title}】\n{content}" for title, content in parts if content)
