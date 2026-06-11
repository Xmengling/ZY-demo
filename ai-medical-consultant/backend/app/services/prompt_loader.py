# -*- coding: utf-8 -*-
"""从 Markdown 文件加载 AI Prompt。"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from ..config import BASE_DIR

PROMPTS_DIR = BASE_DIR / "prompts"
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_TYPE_RE = re.compile(r"^###\s+(\w+)\s*$", re.MULTILINE)

CONSULT_CASE_FILE = "consult_case.md"
HOME_LEARN_FILE = "home_learn.md"


def _strip_md_noise(text: str) -> str:
    lines: list[str] = []
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith(">") or stripped.startswith("#"):
            continue
        lines.append(line.rstrip())
    body = "\n".join(lines).strip()
    return re.sub(r"\n{3,}", "\n\n", body)


def _split_sections(text: str, *, strip_body: bool = True) -> dict[str, str]:
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        return {"": _strip_md_noise(text) if strip_body else text.strip()}

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]
        sections[title] = _strip_md_noise(body) if strip_body else body.strip()
    return sections


def _split_type_guidance(guidance_text: str) -> dict[str, str]:
    if not guidance_text:
        return {}
    matches = list(_TYPE_RE.finditer(guidance_text))
    if not matches:
        return {}

    blocks: dict[str, str] = {}
    for index, match in enumerate(matches):
        key = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(guidance_text)
        blocks[key] = _strip_md_noise(guidance_text[start:end])
    return blocks


@lru_cache(maxsize=16)
def _load_prompt_md_cached(filename: str, mtime_ns: int) -> tuple[str, dict[str, str]]:
    path = PROMPTS_DIR / filename
    raw = path.read_text(encoding="utf-8")
    sections = _split_sections(raw, strip_body=True)
    raw_sections = _split_sections(raw, strip_body=False)
    base_parts = [
        sections.get("基础规则", ""),
        sections.get("回答结构", ""),
    ]
    base = "\n\n".join(part for part in base_parts if part).strip()
    type_blocks = _split_type_guidance(raw_sections.get("问题类型指引", ""))
    for key in list(type_blocks.keys()):
        type_blocks[key] = _strip_md_noise(type_blocks[key])
    return base, type_blocks


def _load_prompt_from_file(filename: str, question_type: str, *, fallback_type: str) -> str:
    path = PROMPTS_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Prompt 文件不存在：{path}")
    mtime_ns = path.stat().st_mtime_ns
    base, type_blocks = _load_prompt_md_cached(filename, mtime_ns)
    guidance = type_blocks.get(question_type) or type_blocks.get(fallback_type, "")
    parts = [part for part in (base, guidance) if part]
    return "\n\n".join(parts)


def load_consult_case_prompt(question_type: str) -> str:
    return _load_prompt_from_file(CONSULT_CASE_FILE, question_type, fallback_type="full_case")


def load_home_learn_prompt(question_type: str) -> str:
    return _load_prompt_from_file(HOME_LEARN_FILE, question_type, fallback_type="knowledge")


@lru_cache(maxsize=4)
def _load_user_rules_cached(mtime_ns: int) -> str:
    from .user_rules import load_user_rules_prompt

    return load_user_rules_prompt()


def load_user_rules_block() -> str:
    path = PROMPTS_DIR / "user_rules.md"
    if not path.is_file():
        return ""
    return _load_user_rules_cached(path.stat().st_mtime_ns)


def invalidate_prompt_cache() -> None:
    _load_prompt_md_cached.cache_clear()
    _load_user_rules_cached.cache_clear()
