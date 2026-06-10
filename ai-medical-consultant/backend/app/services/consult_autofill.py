# -*- coding: utf-8 -*-
"""问诊粘贴自动填充：few-shot 学习案例加载与 prompt 片段生成。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import BASE_DIR

EXAMPLES_PATH = BASE_DIR / "data" / "consult_autofill_examples.json"


def load_autofill_examples() -> list[dict[str, Any]]:
    if not EXAMPLES_PATH.is_file():
        return []
    try:
        data = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    examples = data.get("examples") if isinstance(data, dict) else []
    if not isinstance(examples, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for item in examples:
        if not isinstance(item, dict):
            continue
        raw_text = str(item.get("raw_text") or "").strip()
        expected = item.get("expected") if isinstance(item.get("expected"), dict) else {}
        if raw_text and expected:
            cleaned.append(item)
    return cleaned


def _format_expected_block(expected: dict[str, Any]) -> str:
    fields = expected.get("fields") if isinstance(expected.get("fields"), dict) else {}
    pathology_notes = (
        expected.get("pathology_notes") if isinstance(expected.get("pathology_notes"), dict) else {}
    )
    parts: list[str] = []
    for key, value in fields.items():
        text = str(value).strip()
        if text:
            parts.append(f"fields.{key}={text}")
    for label, value in pathology_notes.items():
        text = str(value).strip()
        if text:
            parts.append(f"pathology_notes.{label}={text}")
    return "；".join(parts)


def build_autofill_examples_prompt() -> str:
    examples = load_autofill_examples()
    if not examples:
        return ""
    blocks: list[str] = []
    for index, item in enumerate(examples, 1):
        title = str(item.get("title") or f"案例{index}").strip()
        raw_text = str(item.get("raw_text") or "").strip()
        expected = item.get("expected") if isinstance(item.get("expected"), dict) else {}
        blocks.append(
            f"案例{index}（{title}）\n"
            f"原文：{raw_text}\n"
            f"期望抽取：{_format_expected_block(expected)}"
        )
    return "学习案例（按同样规则抽取新文本，病理项用 block 原名如水实/水虚，不要写水证）：\n\n" + "\n\n".join(blocks)
