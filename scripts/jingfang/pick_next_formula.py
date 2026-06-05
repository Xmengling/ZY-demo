#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从待整理队列中选出下一个尚未写入 jingfang.sqlite3 的方剂。"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "ai-medical-consultant/backend/data/jingfang.sqlite3"
TCM_JSON = PROJECT_ROOT / "ai-medical-consultant/backend/data/tcm_knowledge.json"
CARDS_DIR = PROJECT_ROOT / "ai-medical-consultant/backend/data/formula_cards"
STATE_PATH = PROJECT_ROOT / "scratch/jingfang-daily-queue.json"
ZY_STUDY_NOTE = Path(
    os.getenv("ZY_STUDY_ROOT", "/Users/qingling/梦玲/ZY-Study")
) / "note/方剂整理.txt"


def slugify(name: str) -> str:
    table = str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz0123456789",
    )
    raw = name.strip().lower()
    raw = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", raw)
    raw = raw.strip("-")
    if not raw:
        raw = "formula"
    if raw.isascii():
        return raw.translate(table)
    return raw


def load_done_names() -> set[str]:
    done: set[str] = set()
    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute("select payload from formulas").fetchall()
        for (payload,) in rows:
            try:
                item = json.loads(payload)
            except json.JSONDecodeError:
                continue
            name = str(item.get("name") or "").strip()
            if name:
                done.add(name)
    if CARDS_DIR.exists():
        for path in CARDS_DIR.glob("*.json"):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            name = str(item.get("name") or "").strip()
            if name:
                done.add(name)
    return done


def load_candidates() -> list[dict]:
    if not TCM_JSON.exists():
        raise SystemExit(f"未找到知识库：{TCM_JSON}")
    data = json.loads(TCM_JSON.read_text(encoding="utf-8"))
    candidates: list[dict] = []
    seen: set[str] = set()
    for item in data:
        name = str(item.get("title") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        candidates.append(
            {
                "name": name,
                "id": slugify(name),
                "department": item.get("department") or "",
                "category": item.get("category") or "",
                "content_preview": (item.get("content") or "")[:1200],
            }
        )
    return candidates


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"last_index": -1, "history": []}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict, pick: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    history = state.get("history") or []
    history.append(
        {
            "name": pick["name"],
            "id": pick["id"],
            "picked_at": pick["picked_at"],
        }
    )
    state["last_index"] = pick["index"]
    state["history"] = history[-120:]
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def pick_next() -> dict:
    from datetime import datetime, timezone

    done = load_done_names()
    candidates = load_candidates()
    state = load_state()
    start = int(state.get("last_index", -1)) + 1

    for index in range(start, len(candidates)):
        item = candidates[index]
        if item["name"] in done:
            continue
        pick = {
            **item,
            "index": index,
            "picked_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "db_path": str(DB_PATH),
            "zy_study_note": str(ZY_STUDY_NOTE) if ZY_STUDY_NOTE.exists() else "",
            "already_done_count": len(done),
            "pending_count": sum(1 for c in candidates if c["name"] not in done),
        }
        save_state(state, pick)
        return pick

    raise SystemExit("队列已耗尽：tcm_knowledge.json 中的方剂都已写入数据库。")


def main() -> int:
    pick = pick_next()
    print(json.dumps(pick, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
