# -*- coding: utf-8 -*-
"""问诊 AI 问答：问题分类与灵活回复指引。"""

from __future__ import annotations

import re
from dataclasses import dataclass
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
_SUMMARY_LINE_RE = re.compile(r"^\s*(?:【[^】]+】\s*)?([^：:\n]{1,16})[：:]\s*(.*)$")
_PATHOLOGY_LABELS = {
    "表证",
    "表实",
    "表虚",
    "半证",
    "半表",
    "半热",
    "半虚",
    "里证",
    "里热",
    "里寒",
    "里虚",
    "里实",
    "水证",
    "水实",
    "水虚",
    "血证",
    "血虚",
    "血实",
    "气证",
    "气虚",
    "气实",
    "阴证",
    "阴性",
}
_META_ONLY_LABELS = {"信息", "姓名", "性别", "年龄", "电话", "住址", "就诊", "医生"}
_CHIEF_LABELS = {"主诉", "当前主诉"}
_SYMPTOM_LABELS = {"症状", "当前症状", "临床症状", "刻下", "现症", "病史", "病程"}
_TONGUE_PULSE_LABELS = {"舌脉腹", "舌脉腹变化", "舌象", "舌质", "舌苔", "脉象", "腹诊"}
_PRESCRIPTION_LABELS = {"方剂", "处方", "上次方剂", "本次调整方剂"}
_CHANGE_LABELS = {"服药后变化"}


@dataclass(frozen=True)
class CaseContextProfile:
    scene: str
    scene_label: str
    evidence_count: int
    labels: tuple[str, ...]
    missing_labels: tuple[str, ...]
    has_case_context: bool
    has_chief: bool
    has_symptoms: bool
    has_pathology: bool
    has_tongue_pulse: bool
    has_prescription: bool


def _summary_items(case_context: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for raw_line in str(case_context or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("【"):
            continue
        match = _SUMMARY_LINE_RE.match(line)
        if not match:
            continue
        label = match.group(1).strip()
        text = match.group(2).strip()
        if label and text and text not in {"未填写", "无", "暂无"}:
            items.append((label, text))
    return items


def analyze_case_context(case_context: str) -> CaseContextProfile:
    text = str(case_context or "").strip()
    items = _summary_items(text)
    labels = tuple(label for label, _ in items)
    label_set = set(labels)

    has_chief = bool(label_set & _CHIEF_LABELS)
    has_symptoms = bool(label_set & _SYMPTOM_LABELS)
    has_pathology = bool(label_set & _PATHOLOGY_LABELS)
    has_tongue_pulse = bool(label_set & _TONGUE_PULSE_LABELS)
    has_prescription = bool(label_set & _PRESCRIPTION_LABELS)
    has_changes = bool(label_set & _CHANGE_LABELS)

    pathology_count = sum(1 for label, _ in items if label in _PATHOLOGY_LABELS)
    symptom_evidence_count = sum(
        [
            has_chief,
            has_symptoms,
            has_tongue_pulse,
            has_changes,
            min(pathology_count, 3),
        ]
    )
    has_case_context = bool(text and items)

    missing: list[str] = []
    if not has_chief:
        missing.append("主诉")
    if not has_symptoms and not has_pathology:
        missing.append("当前症状/病理症状")
    if not has_tongue_pulse:
        missing.append("舌脉腹诊")
    if not any(label in label_set for label in ("二便", "饮食", "睡眠", "寒热", "汗")):
        missing.append("寒热汗、饮食、二便、睡眠")

    non_meta_items = [
        (label, value)
        for label, value in items
        if label not in _META_ONLY_LABELS and label not in _PRESCRIPTION_LABELS
    ]
    if not has_case_context:
        scene = "no_case"
        scene_label = "没有病例摘要"
    elif not non_meta_items or symptom_evidence_count == 0:
        scene = "identity_only"
        scene_label = "只有基本信息或处方，缺少症状"
    elif has_chief and symptom_evidence_count <= 1:
        scene = "chief_only"
        scene_label = "只有主诉，症状证据很少"
    elif symptom_evidence_count < 4:
        scene = "partial"
        scene_label = "病例信息不完整"
    else:
        scene = "complete"
        scene_label = "病例信息较完整"

    return CaseContextProfile(
        scene=scene,
        scene_label=scene_label,
        evidence_count=symptom_evidence_count,
        labels=labels,
        missing_labels=tuple(missing),
        has_case_context=has_case_context,
        has_chief=has_chief,
        has_symptoms=has_symptoms,
        has_pathology=has_pathology,
        has_tongue_pulse=has_tongue_pulse,
        has_prescription=has_prescription,
    )


def _case_response_strategy_block(profile: CaseContextProfile, question_type: str) -> str:
    missing_text = "、".join(profile.missing_labels) if profile.missing_labels else "暂无明显缺项"
    labels_text = "、".join(profile.labels) if profile.labels else "无"
    common = [
        "【病例信息完整度与回答策略】",
        f"当前场景：{profile.scene_label}",
        f"已检测字段：{labels_text}",
        f"缺少重点：{missing_text}",
        "回答前必须先按当前场景决定输出范围，禁止机械套固定模板。",
    ]
    if profile.scene in {"no_case", "identity_only"}:
        common.extend(
            [
                "硬性限制：当前没有足够症状证据，不能进行本例辨证、方证匹配、处方合理性判断、治疗顺序排序、类方鉴别或讲稿摘要。",
                "若用户要求分析本例医案，只回答：当前资料不足，说明缺少哪些信息，并列出需要补充的问诊项。",
                "若用户问某方是否合适，只能说明目前无法判断，并列出该方需要核对的核心证据；不得给出合适/不合适结论。",
                "本场景不要输出「学习要点」「胡希恕讲稿摘要」「李冠杰讲稿摘要」「类方鉴别」「建议处方」。",
            ]
        )
    elif profile.scene == "chief_only":
        common.extend(
            [
                "硬性限制：只有主诉或零散症状时，不得定方、不得作确定病机结论、不得输出讲稿摘要。",
                "可简要说明该主诉可能涉及的辨证方向，但必须标明「信息不足，暂不能定证」。",
                "优先给 5～8 个具体追问，围绕寒热汗、口渴饮水、饮食、二便、睡眠、舌脉腹诊、诱因与加重缓解。",
            ]
        )
    elif profile.scene == "partial":
        common.extend(
            [
                "当前可以做初步倾向分析，但所有判断必须写「暂定」「待确认」。",
                "只列与已知症状直接相关的病理倾向和追问点；不得为了凑结构输出完整五步。",
                "除非用户明确问条文/讲稿，否则不要常规输出胡希恕、李冠杰讲稿摘要。",
                "若涉及选方，只能写可能方证方向和缺失证据，不直接下处方结论。",
            ]
        )
    else:
        common.extend(
            [
                "病例信息较完整时，可按用户问题灵活展开：问全面分析才写完整五步；问局部就只答局部。",
                "类方鉴别、建议追问、讲稿摘要仍需与本例直接相关，有内容才写，不要固定附加。",
            ]
        )
    if question_type == "followup" and profile.scene in {"no_case", "identity_only"}:
        common.append("用户问追问时，也只给基础信息采集清单，不要假设已有病机分歧。")
    return "\n".join(common)


def should_skip_case_retrieval(profile: CaseContextProfile, question_type: str) -> bool:
    """资料不足时不检索知识库，避免界面显示与空医案无关的参考来源。"""
    if profile.scene not in {"no_case", "identity_only"}:
        return False
    return question_type in {"full_case", "followup", "treatment_order", "compare"}


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

    profile = analyze_case_context(case_context)
    parts.append(_case_response_strategy_block(profile, question_type))

    user_rules = load_user_rules_block()
    if user_rules:
        parts.append(user_rules)
    if prescription_notice:
        parts.append(prescription_notice)
    if case_context:
        parts.append(f"【当前病例摘要】\n{case_context}")
    return "\n\n".join(parts)
