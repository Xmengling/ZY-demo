# -*- coding: utf-8 -*-
"""问诊 AI 问答：问题分类与灵活回复指引。"""

from __future__ import annotations

import re
from typing import List

_COMPARE_KEYWORDS = ("鉴别", "区别", "对比", "如何区分", "怎么分", "异同", "相近方", "类方")
_FOLLOWUP_KEYWORDS = ("追问", "还需要问", "还需问", "补充什么", "还要了解", "缺什么信息")
_CASE_KEYWORDS = ("分析", "医案", "本例", "病例", "用方", "处方", "是否合理", "主方")
_COMPOSITION_KEYWORDS = ("组成", "药物", "药味", "剂量", "方解", "配伍")
_TREATMENT_ORDER_KEYWORDS = (
    "治疗顺序",
    "治疗次序",
    "施治顺序",
    "用药顺序",
    "用药先后",
    "治法先后",
    "先后次序",
    "先治什么",
    "先治哪",
    "次序怎么排",
    "顺序怎么排",
)
_FORMULA_NAME_RE = re.compile(r"([一-龥]{2,8}(?:汤|散|丸|饮|膏|方|证))")


def is_compare_query(text: str) -> bool:
    q = (text or "").strip()
    if not q:
        return False
    if any(k in q for k in _COMPARE_KEYWORDS):
        return True
    names = extract_formula_names_from_text(q)
    return len(names) >= 2


def is_composition_query(text: str) -> bool:
    q = (text or "").strip()
    return bool(q and any(k in q for k in _COMPOSITION_KEYWORDS))


def is_treatment_order_query(text: str) -> bool:
    q = (text or "").strip()
    return bool(q and any(k in q for k in _TREATMENT_ORDER_KEYWORDS))


def is_definition_query(text: str) -> bool:
    q = (text or "").strip()
    if not q:
        return False
    if not any(k in q for k in ("是什么", "何谓", "何意", "如何理解", "含义", "定义")):
        return False
    return any(k in q for k in ("证", "汤", "散", "丸", "条", "提纲", "方"))


def extract_formula_names_from_text(text: str) -> List[str]:
    if not text:
        return []
    seen: set[str] = set()
    result: List[str] = []
    chunks = re.split(r"[与和、,及/]", str(text))
    for chunk in chunks:
        for match in _FORMULA_NAME_RE.finditer(chunk):
            name = match.group(1).strip()
            key = re.sub(r"\s+", "", name)
            if key and key not in seen:
                seen.add(key)
                result.append(name)
    return result


def classify_assistant_question(
    text: str,
    *,
    has_case: bool,
    prescription_names: List[str] | None = None,
) -> str:
    q = (text or "").strip()
    names = prescription_names or []

    if has_case and any(k in q for k in _FOLLOWUP_KEYWORDS):
        return "followup"
    if is_compare_query(q) or (has_case and len(names) >= 2):
        return "compare"
    if is_composition_query(q) and not has_case:
        return "composition"
    if has_case and is_treatment_order_query(q):
        return "treatment_order"
    if has_case:
        return "full_case"
    if is_definition_query(q):
        return "definition"
    if any(k in q for k in _CASE_KEYWORDS):
        return "full_case"
    return "knowledge"


def build_home_system_prompt(question_type: str) -> str:
    from .prompt_loader import load_home_learn_prompt

    return load_home_learn_prompt(question_type)


def build_assistant_system_prompt(
    question_type: str,
    *,
    case_context: str = "",
    prescription_notice: str = "",
) -> str:
    from .prompt_loader import load_user_rules_block

    if case_context:
        from .prompt_loader import load_consult_case_prompt

        parts = [load_consult_case_prompt(question_type)]
    else:
        parts = [build_home_system_prompt(question_type)]

    user_rules = load_user_rules_block()
    if user_rules:
        parts.append(user_rules)
    if prescription_notice:
        parts.append(prescription_notice)
    if case_context:
        parts.append(f"【当前病例摘要】\n{case_context}")
    return "\n\n".join(parts)
