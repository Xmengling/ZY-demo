# -*- coding: utf-8 -*-
"""用户确认的永久规则：识别纠正、写入 prompts/user_rules.md。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from ..config import BASE_DIR

PROMPTS_DIR = BASE_DIR / "prompts"
USER_RULES_FILE = "user_rules.md"
_MAX_RULE_LEN = 500
_MAX_SOURCE_LEN = 2000

_CORRECTION_MARKERS = (
    "错了",
    "不对",
    "不应该",
    "不该",
    "不是这样",
    "纠正",
    "应该改为",
    "应当",
    "须先",
    "应先",
    "必须先",
    "应该",
    "记住",
    "记下",
    "以后都",
    "别写",
    "禁止写",
    "不要写",
    "别",
    "不是先",
    "而非",
    "而不是",
)

_RULE_HINT_MARKERS = (
    "应该",
    "应当",
    "须",
    "必须",
    "不要",
    "禁止",
    "别",
    "先",
    "顺序",
    "规则",
)

_USER_RULES_HEADER = """# 用户确认的永久规则

> 由 AI 问答中经用户确认的纠正自动追加；优先级高于通用回答习惯。

## 规则列表

"""


def _user_rules_path() -> Path:
    return PROMPTS_DIR / USER_RULES_FILE


def _normalize_rule(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text or "").strip())
    value = value.strip("。；;，,")
    return value[:_MAX_RULE_LEN]


def looks_like_rule_correction(text: str) -> bool:
    q = (text or "").strip()
    if len(q) < 6 or len(q) > _MAX_SOURCE_LEN:
        return False
    if not any(marker in q for marker in _CORRECTION_MARKERS):
        return False
    if (q.endswith("?") or q.endswith("？")) and not any(
        marker in q for marker in ("应该", "应当", "须", "必须", "别", "不要")
    ):
        return False
    return True


def extract_rule_text(text: str) -> str:
    q = (text or "").strip()
    for marker in ("应该先", "应当先", "须先", "应先", "必须先", "应该", "应当", "必须", "不要", "禁止", "别"):
        idx = q.find(marker)
        if idx >= 0:
            return _normalize_rule(q[idx:])
    candidates: list[str] = []
    for sep in ("，", "。", "；", ",", ";", "：", ":"):
        candidates.extend(part.strip() for part in q.split(sep) if part.strip())
    candidates.append(q)
    for part in reversed(candidates):
        if any(marker in part for marker in _RULE_HINT_MARKERS):
            return _normalize_rule(part)
    return _normalize_rule(q)


def build_rule_suggestion(text: str) -> dict[str, str] | None:
    if not looks_like_rule_correction(text):
        return None
    rule_text = extract_rule_text(text)
    if len(rule_text) < 6:
        return None
    return {
        "rule_text": rule_text,
        "source_message": str(text).strip()[:_MAX_SOURCE_LEN],
    }


def _read_rules_body() -> str:
    path = _user_rules_path()
    if not path.is_file():
        return ""
    raw = path.read_text(encoding="utf-8")
    match = re.search(r"^##\s*规则列表\s*$([\s\S]*)", raw, flags=re.MULTILINE)
    if not match:
        return ""
    lines: list[str] = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            lines.append(stripped[2:].strip())
    return "\n".join(lines).strip()


def _existing_rule_set() -> set[str]:
    body = _read_rules_body()
    existing: set[str] = set()
    for line in body.splitlines():
        normalized = _normalize_rule(re.sub(r"^（\d{4}-\d{2}-\d{2}）", "", line))
        if normalized:
            existing.add(normalized)
    return existing


def load_user_rules_prompt() -> str:
    body = _read_rules_body()
    if not body:
        return ""
    items = [line.strip() for line in body.splitlines() if line.strip()]
    if not items:
        return ""
    numbered = "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))
    return (
        "【用户确认的永久规则】\n"
        "以下为医生在问答中确认记入的纠正，须优先遵守；与本轮口头纠正冲突时以本规则为准。\n"
        f"{numbered}"
    )


def append_user_rule(rule_text: str, *, source_message: str = "") -> tuple[bool, str]:
    normalized = _normalize_rule(rule_text)
    if len(normalized) < 6:
        return False, "规则内容过短"
    if normalized in _existing_rule_set():
        return False, "该规则已存在，无需重复记入"

    path = _user_rules_path()
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_text(_USER_RULES_HEADER, encoding="utf-8")

    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    line = f"- （{stamp}）{normalized}"
    if source_message and source_message.strip() and source_message.strip() != normalized:
        line += f"  <!-- 来源：{source_message.strip()[:120]} -->"

    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{line}\n")

    from .prompt_loader import invalidate_prompt_cache

    invalidate_prompt_cache()
    return True, "已记入永久规则"
