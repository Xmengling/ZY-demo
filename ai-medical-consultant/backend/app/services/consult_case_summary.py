# -*- coding: utf-8 -*-
"""问诊医案病例摘要构建（与前端 consultSymptoms.js 对齐）。"""

from __future__ import annotations

import re
from typing import Any


def _split_symptom_text(value: Any) -> list[str]:
    return [item.strip() for item in re.split(r"[、，,；;]+", str(value or "")) if item.strip()]


def _join_symptom_text(parts: list[str]) -> str:
    return "、".join(item for item in parts if item)


def _pathology_score_value(scores: dict[str, Any], label: str) -> int | None:
    try:
        num = float(scores.get(label) or 0)
    except (TypeError, ValueError):
        return None
    return int(num) if num > 0 else None


def build_pathology_block_text(
    block: dict[str, Any],
    notes: dict[str, Any],
    selected: dict[str, Any],
) -> str:
    label = str(block.get("label") or "")
    note = str(notes.get(label) or "").strip()
    chip_selected = [s for s in block.get("symptoms") or [] if selected.get(s)]
    chunks: list[str] = []
    if note:
        chunks.append(note)
    extra = [s for s in chip_selected if s not in note]
    if extra:
        chunks.append("，".join(extra))
    return "，".join(chunks)


def build_pathology_summary_lines(
    sections: list[dict[str, Any]],
    notes: dict[str, Any],
    selected: dict[str, Any],
    scores: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    scores = scores or {}
    lines: list[dict[str, Any]] = []
    for section in sections:
        for block in section.get("blocks") or []:
            text = build_pathology_block_text(block, notes, selected)
            if text:
                lines.append(
                    {
                        "label": block.get("label") or "",
                        "text": text,
                        "score": _pathology_score_value(scores, str(block.get("label") or "")),
                        "kind": "pathology",
                    }
                )
    return lines


def format_visit_date(visit_time: Any) -> str:
    if not visit_time:
        return ""
    match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", str(visit_time))
    if not match:
        return str(visit_time).strip()
    year, month, day = match.groups()
    return f"{year}年{int(month)}月{int(day)}日"


def build_patient_info_line(intake: dict[str, Any]) -> str:
    parts = [
        str(intake.get("patient_name") or "").strip(),
        str(intake.get("gender") or "").strip(),
        str(intake.get("age") or "").strip(),
        format_visit_date(intake.get("visit_time")),
    ]
    return " ".join(part for part in parts if part)


def build_tongue_pulse_abdominal_text(intake: dict[str, Any]) -> str:
    parts: list[str] = []
    tongue = str(intake.get("tongue_image") or "").strip()
    if tongue:
        parts.append(tongue)
    else:
        legacy_body = str(intake.get("tongue_body") or "").strip()
        legacy_coat = str(intake.get("tongue_coat") or "").strip()
        if legacy_body or legacy_coat:
            parts.append("，".join(item for item in [legacy_body, legacy_coat] if item))
    pulse = str(intake.get("pulse") or "").strip()
    if pulse:
        parts.append(pulse if pulse.startswith("脉") else f"脉{pulse}")
    abdominal = str(intake.get("abdominal") or "").strip()
    if abdominal:
        parts.append(abdominal if abdominal.startswith("腹诊") else f"腹诊{abdominal}")
    return "，".join(parts)


def build_prescription_summary_text(prescription: dict[str, Any] | None) -> str:
    rows = [
        row
        for row in (prescription or {}).get("rows") or []
        if str(row.get("name") or "").strip()
    ]
    if not rows:
        return ""
    parts: list[str] = []
    for row in rows:
        name = str(row.get("name") or "").strip()
        try:
            portions = int(float(row.get("portions") or 1))
        except (TypeError, ValueError):
            portions = 1
        parts.append(f"{name}{portions}份")
    return "，".join(parts)


def build_followup_change_groups(visit: dict[str, Any]) -> list[dict[str, str]]:
    changes = [item for item in (visit.get("changes") or []) if item]
    improved = _split_symptom_text(visit.get("improved_symptoms"))
    worsened = _split_symptom_text(visit.get("worsened_symptoms"))
    remaining = _split_symptom_text(visit.get("remaining_symptoms"))

    if "好转" in changes and not improved:
        improved.append("好转")
    if "加重" in changes and not worsened:
        worsened.append("加重")
    if "无变化" in changes and not remaining:
        remaining.append("无变化")
    if "新增症状" in changes and "新增症状" not in worsened:
        worsened.append("新增症状")

    return [
        {"key": "improved", "label": "好转的症状", "text": _join_symptom_text(improved), "tone": "green"},
        {"key": "worsened", "label": "加重的症状", "text": _join_symptom_text(worsened), "tone": "red"},
        {"key": "remaining", "label": "仍存在的症状", "text": _join_symptom_text(remaining), "tone": "orange"},
    ]


def format_consult_summary_line(item: dict[str, Any]) -> str:
    if item.get("kind") == "changeGroups":
        groups = item.get("groups") or []
        return "\n".join(
            f"{group.get('label')}：{str(group.get('text') or '').strip()}"
            for group in groups
            if str(group.get("text") or "").strip()
        )
    label = str(item.get("label") or "").strip()
    if item.get("score") is not None:
        label = f"{label} {item['score']}"
    return f"{label}：{str(item.get('text') or '').strip()}"


def format_consult_summary_text(lines: list[dict[str, Any]]) -> str:
    output: list[str] = []
    for item in lines or []:
        if item.get("kind") == "changeGroups":
            if any(str(group.get("text") or "").strip() for group in item.get("groups") or []):
                output.append(format_consult_summary_line(item))
            continue
        if str(item.get("text") or "").strip():
            output.append(format_consult_summary_line(item))
    return "\n".join(output)


def build_consult_summary_lines(
    intake: dict[str, Any],
    sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    info = build_patient_info_line(intake)
    if info:
        lines.append({"label": "信息", "text": info, "kind": "meta"})

    chief = str(intake.get("chief_complaint") or "").strip()
    if chief:
        lines.append({"label": "主诉", "text": chief, "kind": "meta"})

    notes = intake.get("notes") or {}
    selected = intake.get("selected") or {}
    scores = intake.get("scores") or {}
    lines.extend(build_pathology_summary_lines(sections, notes, selected, scores))

    tongue_pulse = build_tongue_pulse_abdominal_text(intake)
    if tongue_pulse:
        lines.append({"label": "舌脉腹", "text": tongue_pulse, "kind": "meta"})

    prescription_text = build_prescription_summary_text(intake.get("prescription"))
    if prescription_text:
        lines.append({"label": "方剂", "text": prescription_text, "kind": "meta"})
    return lines


def build_followup_summary_lines(
    visit: dict[str, Any],
    sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    change_groups = build_followup_change_groups(visit)
    if any(group.get("text") for group in change_groups):
        lines.append(
            {
                "label": "服药后变化",
                "text": "；".join(group["text"] for group in change_groups if group.get("text")),
                "kind": "changeGroups",
                "groups": change_groups,
            }
        )

    prescription_text = build_prescription_summary_text(visit.get("prescription"))
    if prescription_text:
        lines.append({"label": "本次调整方剂", "text": prescription_text, "kind": "meta"})
    return lines


def build_consult_summary_groups(
    intake: dict[str, Any],
    sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    first_lines = build_consult_summary_lines(intake, sections)
    if any(str(item.get("text") or "").strip() for item in first_lines):
        groups.append({"key": "first", "label": "首诊", "lines": first_lines})

    followup_labels = ["二诊", "三诊", "四诊", "五诊", "六诊", "七诊", "八诊", "九诊", "十诊"]
    for index, visit in enumerate(intake.get("followups") or []):
        lines = build_followup_summary_lines(visit, sections)
        if not any(str(item.get("text") or "").strip() for item in lines):
            continue
        label = str(visit.get("label") or "").strip() or (
            followup_labels[index] if index < len(followup_labels) else f"第{index + 2}诊"
        )
        groups.append({"key": visit.get("id") or f"followup-{index}", "label": label, "lines": lines})
    return groups


def format_consult_summary_groups(groups: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for group in groups or []:
        body = format_consult_summary_text(group.get("lines") or [])
        if body:
            chunks.append(f"【{group.get('label')}】\n{body}")
    return "\n\n".join(chunks)


def merge_session_intake(session: Any, intake_data: dict[str, Any]) -> dict[str, Any]:
    intake = dict(intake_data or {})
    field_map = {
        "patient_name": session.patient_name,
        "phone": session.phone,
        "address": session.address,
        "gender": session.gender,
        "age": session.age,
        "modern_diagnosis": session.modern_diagnosis,
    }
    for key, value in field_map.items():
        if not str(intake.get(key) or "").strip() and str(value or "").strip():
            intake[key] = value
    if not str(intake.get("chief_complaint") or "").strip():
        intake["chief_complaint"] = str(getattr(session, "title", "") or "")
    return intake
