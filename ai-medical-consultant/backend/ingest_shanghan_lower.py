# -*- coding: utf-8 -*-
"""将《伤寒论-下册》讲稿按「第 N 条」切片导入知识库（一条文一片段）。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from app.database import SessionLocal, init_db
from app.models import KnowledgeDoc
from app.services.file_parser import _read_docx, split_by_separators
from app.services.knowledge_base import knowledge_base

SOURCE_FILE = Path(
    r"D:\AI\ZY-Study\data\《伤寒论-下册》胡希恕、李冠杰讲稿合订本-原文标注.docx"
)
SOURCE_NAME = SOURCE_FILE.name
CATEGORY = "伤寒论讲稿"
DEPARTMENT = "胡希恕·李冠杰讲稿"
ARTICLE_PATTERN = r"^第\d+\s*条\s*\n\s*原文[：:]"


def _article_title(piece: str, index: int) -> str:
    first = (piece.strip().split("\n")[0] or "").strip()
    m = re.match(r"^第(\d+)\s*条", first)
    if m:
        return f"伤寒论下册·第{m.group(1)}条"
    return f"伤寒论下册·片段{index}"


def parse_articles(raw: bytes) -> list[dict]:
    text = _read_docx(raw)
    pieces = split_by_separators(text, [ARTICLE_PATTERN], max_size=0)
    docs: list[dict] = []
    idx = 0
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if not re.match(r"^第\d+\s*条", piece):
            continue
        idx += 1
        docs.append(
            {
                "category": CATEGORY,
                "title": _article_title(piece, idx),
                "department": DEPARTMENT,
                "content": piece,
            }
        )
    return docs


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
    if not SOURCE_FILE.is_file():
        raise SystemExit(f"文件不存在：{SOURCE_FILE}")

    init_db()
    raw = SOURCE_FILE.read_bytes()
    docs = parse_articles(raw)
    if not docs:
        raise SystemExit("未解析到条文片段，请检查文件格式")

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
        print(f"已导入 {len(docs)} 条（分类：{CATEGORY}）")
        _rebuild_index(db)
        print("向量索引已重建")
    finally:
        db.close()


if __name__ == "__main__":
    ingest(replace="--append" not in sys.argv)
