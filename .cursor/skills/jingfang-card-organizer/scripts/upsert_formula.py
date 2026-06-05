#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把经方方剂 JSON 载荷写入 formulas(payload)。"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

REQUIRED_FIELDS = [
    "id",
    "name",
    "composition",
    "pathology",
    "clinicalSymptoms",
    "modernDiseases",
    "diagnosisPoints",
    "classicTexts",
    "caseItems",
]

LIST_FIELDS = [
    "categories",
    "herbImages",
    "pathologySymptoms",
    "mainSymptoms",
    "clinicalSymptoms",
    "modernDiseases",
    "diagnosisPoints",
    "classicTexts",
    "caseItems",
]

VALID_CATEGORIES = {"表证", "里证", "半证", "水证", "血证", "气证", "阴证"}


def load_payload(path: str) -> dict:
    if path == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(path).read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("payload 必须是 JSON 对象")
    return payload


def normalize_payload(payload: dict) -> dict:
    missing = [field for field in REQUIRED_FIELDS if field not in payload or payload[field] in (None, "")]
    if missing:
        raise SystemExit(f"缺少必填字段：{', '.join(missing)}")

    for field in LIST_FIELDS:
        value = payload.get(field, [])
        if value is None:
            value = []
        if not isinstance(value, list):
            raise SystemExit(f"{field} 必须是列表")
        payload[field] = value

    bad_categories = [cat for cat in payload.get("categories", []) if cat not in VALID_CATEGORIES]
    if bad_categories:
        raise SystemExit(f"无效分类：{', '.join(bad_categories)}")

    pathology = payload.get("pathology", [])
    if not isinstance(pathology, list):
        raise SystemExit("pathology 必须是列表")
    for i, item in enumerate(pathology, 1):
        if not isinstance(item, dict):
            raise SystemExit(f"pathology 第 {i} 项必须是对象")
        for key in ("label", "text", "category"):
            if not item.get(key):
                raise SystemExit(f"pathology 第 {i} 项缺少 {key}")
        if item["category"] not in VALID_CATEGORIES:
            raise SystemExit(f"pathology 第 {i} 项分类无效：{item['category']}")

    case_items = payload.get("caseItems", [])
    payload["cases"] = "\n\n".join(str(item).strip() for item in case_items if str(item).strip())
    payload.setdefault("caution", "")
    payload.setdefault("abdominalDiagnosis", "")
    payload.setdefault("huXishuAnalysis", "")
    payload.setdefault("liGuanjieAnalysis", "")
    payload.setdefault("mainSymptoms", [])
    payload.setdefault("pathologySymptoms", [])
    payload.setdefault("herbImages", [])
    return payload


def upsert(db_path: Path, payload: dict) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            create table if not exists formulas (
              id text primary key,
              payload text not null,
              updated_at integer not null
            )
            """
        )
        conn.execute(
            """
            insert into formulas(id, payload, updated_at) values(?, ?, ?)
            on conflict(id) do update set payload = excluded.payload, updated_at = excluded.updated_at
            """,
            (payload["id"], json.dumps(payload, ensure_ascii=False), int(time.time())),
        )
        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="jingfang.sqlite3 数据库路径")
    parser.add_argument("--payload", required=True, help="JSON payload 文件路径；用 - 表示从 stdin 读取")
    args = parser.parse_args()

    payload = normalize_payload(load_payload(args.payload))
    upsert(Path(args.db), payload)
    print(json.dumps({
        "ok": True,
        "id": payload["id"],
        "name": payload["name"],
        "classic_count": len(payload.get("classicTexts", [])),
        "case_count": len(payload.get("caseItems", [])),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
