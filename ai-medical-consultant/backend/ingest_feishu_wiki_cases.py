# -*- coding: utf-8 -*-
"""从飞书「方剂整理」知识库（本地镜像）导入医案：一案一片段。

数据源（与飞书 wiki 同一整理规范，见 ZY-Study/AGENTS.md）：
  1. web/db/jingfang.sqlite3  —— 优先，条目更全
  2. note/方剂整理.txt       —— 补充 sqlite 中尚未收录的方剂医案

飞书 wiki（需登录，无法自动抓取）：
  https://hcn939lxl2kb.feishu.cn/wiki/RzxRwhwNCi68F0kdMFyctpcPnxb
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

from app.database import SessionLocal, init_db
from app.models import KnowledgeDoc
from app.services.knowledge_base import knowledge_base

WIKI_URL = (
    "https://hcn939lxl2kb.feishu.cn/wiki/RzxRwhwNCi68F0kdMFyctpcPnxb"
)
SOURCE_NAME = "飞书知识库-方剂整理.wiki"
CATEGORY = "飞书方剂医案"
DEPARTMENT = "经方名家医案"

SQLITE_PATH = Path(r"D:\AI\ZY-Study\web\db\jingfang.sqlite3")
TXT_PATH = Path(r"D:\AI\ZY-Study\note\方剂整理.txt")

CASE_SPLIT = re.compile(r"(?<=\n)\s*医案\s*(\d+)", re.M)
FORMULA_SPLIT = re.compile(r"^##\s+(.+?)\s*$", re.M)


def _clean_markup(text: str) -> str:
    text = re.sub(r"\[\[\*\*(.+?)\*\*\]\]", r"\1", text)
    text = re.sub(r"\[\[(.+?)\]\]", r"\1", text)
    return text.strip()


def _extract_source_label(case_text: str) -> str:
    m = re.search(r"[（(]([^）)]+)[）)]", case_text)
    if m:
        return m.group(1).strip()[:64]
    m = re.match(r"^([^：:\n]+医案)", case_text.strip())
    if m:
        return m.group(1).strip()[:64]
    return ""


def _make_title(formula: str, index: int, case_text: str) -> str:
    src = _extract_source_label(case_text)
    if src:
        short = src if len(src) <= 28 else src[:28] + "…"
        return f"飞书医案·{formula}·{short}"
    return f"飞书医案·{formula}·案{index}"


def _case_key(formula: str, content: str) -> str:
    norm = re.sub(r"\s+", "", _clean_markup(content))[:200]
    return f"{formula}::{norm}"


def _docs_from_sqlite() -> list[dict]:
    if not SQLITE_PATH.is_file():
        return []
    docs: list[dict] = []
    con = sqlite3.connect(SQLITE_PATH)
    try:
        cur = con.cursor()
        cur.execute("SELECT payload FROM formulas")
        for (raw,) in cur.fetchall():
            data = json.loads(raw)
            formula = (data.get("name") or "").strip()
            if not formula:
                continue
            for i, item in enumerate(data.get("caseItems") or [], 1):
                content = _clean_markup(str(item or ""))
                if len(content) < 80:
                    continue
                docs.append(
                    {
                        "category": CATEGORY,
                        "title": _make_title(formula, i, content),
                        "department": DEPARTMENT,
                        "content": f"【{formula}】\n{content}",
                        "_key": _case_key(formula, content),
                    }
                )
    finally:
        con.close()
    return docs


def _parse_txt_cases(formula: str, block: str) -> list[dict]:
    m = re.search(r"###\s*医案\s*\n(.*?)(?=\n##\s|\Z)", block, re.S)
    if not m:
        return []
    body = m.group(1)
    parts = CASE_SPLIT.split(body)
    if not parts:
        return []
    docs: list[dict] = []
    # split 后首段可能是空；后续为 [num, text, num, text...]
    if parts[0].strip():
        chunks = [("", parts[0])]
        it = iter(parts[1:])
        for num in it:
            try:
                text = next(it)
            except StopIteration:
                break
            chunks.append((num, text))
    else:
        it = iter(parts[1:])
        chunks = []
        for num in it:
            try:
                text = next(it)
            except StopIteration:
                break
            chunks.append((num, text))
    for num, text in chunks:
        content = _clean_markup(text.strip())
        if len(content) < 80:
            continue
        idx = int(num) if str(num).isdigit() else len(docs) + 1
        head = f"医案{idx}"
        if not content.startswith("医案"):
            content = f"{head}\n{content}"
        docs.append(
            {
                "category": CATEGORY,
                "title": _make_title(formula, idx, content),
                "department": DEPARTMENT,
                "content": f"【{formula}】\n{content}",
                "_key": _case_key(formula, content),
            }
        )
    return docs


def _docs_from_txt(existing_keys: set[str]) -> list[dict]:
    if not TXT_PATH.is_file():
        return []
    text = TXT_PATH.read_text(encoding="utf-8")
    out: list[dict] = []
    blocks = re.split(r"(?=^##\s+)", text, flags=re.M)
    for block in blocks:
        m = FORMULA_SPLIT.search(block)
        if not m:
            continue
        formula = m.group(1).strip()
        for doc in _parse_txt_cases(formula, block):
            if doc["_key"] not in existing_keys:
                out.append(doc)
                existing_keys.add(doc["_key"])
    return out


def collect_docs() -> list[dict]:
    merged: list[dict] = []
    keys: set[str] = set()
    for doc in _docs_from_sqlite():
        k = doc.pop("_key")
        if k in keys:
            continue
        keys.add(k)
        merged.append(doc)
    merged.extend(_docs_from_txt(keys))
    for doc in merged:
        doc.pop("_key", None)
    return merged


def _rebuild_index(db) -> None:
    rows = db.query(KnowledgeDoc).all()
    knowledge_base.rebuild_from_docs(
        [
            {
                "title": d.title,
                "category": d.category,
                "department": d.department,
                "content": d.content,
            }
            for d in rows
        ]
    )


def ingest(replace: bool = True) -> None:
    docs = collect_docs()
    if not docs:
        raise SystemExit(
            "未解析到医案。请确认 ZY-Study 本地数据存在，或导出飞书 wiki 为文本后指定路径。"
        )

    init_db()
    db = SessionLocal()
    try:
        if replace:
            removed = (
                db.query(KnowledgeDoc)
                .filter(KnowledgeDoc.source == SOURCE_NAME)
                .delete(synchronize_session=False)
            )
            if removed:
                print(f"已删除同来源旧数据 {removed} 条")
        for d in docs:
            db.add(
                KnowledgeDoc(
                    category=d["category"],
                    title=d["title"],
                    department=d["department"],
                    content=d["content"],
                    source=SOURCE_NAME,
                )
            )
        db.commit()
        print(f"已导入 {len(docs)} 条医案（分类：{CATEGORY}）")
        print(f"来源说明：{WIKI_URL}")
        print(f"数据镜像：{SQLITE_PATH.name} + {TXT_PATH.name}")
        _rebuild_index(db)
        print("向量索引已重建")
    finally:
        db.close()


if __name__ == "__main__":
    ingest(replace="--append" not in sys.argv)
