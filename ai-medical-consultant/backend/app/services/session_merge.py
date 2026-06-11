# -*- coding: utf-8 -*-
"""医案会话合并：合并 intake_data 与病例字段。"""

from __future__ import annotations

import copy
from typing import Any


def _merge_text_field(target: str, source: str, *, append: bool = False) -> str:
    left = str(target or "").strip()
    right = str(source or "").strip()
    if not right:
        return left
    if not left:
        return right
    if append:
        if right in left:
            return left
        return f"{left}\n{right}"
    return left


def merge_intake_data(base: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base or {})
    other = other or {}

    fill_if_empty = (
        "patient_name",
        "phone",
        "address",
        "gender",
        "age",
        "visit_time",
        "doctor",
        "chief_complaint",
    )
    append_fields = ("history", "modern_diagnosis", "tongue_image", "pulse", "abdominal")

    for field in fill_if_empty:
        if not str(merged.get(field) or "").strip():
            merged[field] = other.get(field) or ""

    for field in append_fields:
        merged[field] = _merge_text_field(merged.get(field, ""), other.get(field, ""), append=True)

    selected = merged.setdefault("selected", {})
    for key, value in (other.get("selected") or {}).items():
        if value:
            selected[key] = True

    notes = merged.setdefault("notes", {})
    for key, value in (other.get("notes") or {}).items():
        text = str(value or "").strip()
        if not text:
            continue
        old = str(notes.get(key) or "").strip()
        if not old:
            notes[key] = text
        elif text not in old:
            notes[key] = f"{old}；{text}"

    scores = merged.setdefault("scores", {})
    for key, value in (other.get("scores") or {}).items():
        try:
            new_score = float(value)
            old_score = float(scores.get(key) or 0)
        except (TypeError, ValueError):
            continue
        if new_score > old_score:
            scores[key] = new_score

    chip_lists = merged.setdefault("chipLists", {})
    for key, items in (other.get("chipLists") or {}).items():
        current = list(chip_lists.get(key) or [])
        seen = set(current)
        for item in items or []:
            text = str(item).strip()
            if text and text not in seen:
                current.append(text)
                seen.add(text)
        chip_lists[key] = current

    prescription = merged.setdefault("prescription", {"targetDose": 200, "note": "", "rows": []})
    other_prescription = other.get("prescription") or {}
    if not str(prescription.get("note") or "").strip() and other_prescription.get("note"):
        prescription["note"] = other_prescription.get("note")
    if other_prescription.get("targetDose"):
        prescription["targetDose"] = other_prescription.get("targetDose")

    rows = list(prescription.get("rows") or [])
    row_by_name: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = str(row.get("name") or "").strip()
        if name:
            row_by_name[name] = row

    for row in other_prescription.get("rows") or []:
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        if name in row_by_name:
            existing = row_by_name[name]
            try:
                existing["portions"] = int(existing.get("portions") or 1) + int(row.get("portions") or 1)
            except (TypeError, ValueError):
                existing["portions"] = existing.get("portions") or row.get("portions") or 1
        else:
            rows.append(copy.deepcopy(row))
            row_by_name[name] = rows[-1]
    prescription["rows"] = rows

    return merged


def merge_case_text(base: str, other: str) -> str:
    return _merge_text_field(base, other, append=True)
