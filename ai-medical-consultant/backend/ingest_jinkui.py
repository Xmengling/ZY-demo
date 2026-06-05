# -*- coding: utf-8 -*-
"""将《金匮要略》讲稿按条文切片导入知识库（原文 + 胡希恕/李冠杰讲解，一条文一片段）。"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

from app.database import SessionLocal, init_db
from app.models import KnowledgeDoc
from app.services.file_parser import _read_docx
from app.services.knowledge_base import knowledge_base

SOURCE_FILE = next(
    Path(r"D:\AI\ZY-Study\data").glob("*金匮*条文*.docx"),
    None,
)
if SOURCE_FILE is None:
    SOURCE_FILE = Path(
        r"D:\AI\ZY-Study\data\《金匮要略》胡希恕、李冠杰讲稿合订本-条文标注.docx"
    )
SOURCE_NAME = SOURCE_FILE.name
CATEGORY = "金匮要略讲稿"
DEPARTMENT = "胡希恕·李冠杰讲稿"

# 条文号 (101+) 后接原文，再跟讲解；与伤寒论「第 N 条 + 原文：」等价的分界
ARTICLE_END = re.compile(
    r"\((?P<num>[1-9]\d{2,})\)(?:[^\n]*)?\n{1,2}"
    r"(?:-----条文原文-----\n{1,2})?胡希恕：",
    re.M,
)


def _article_title(num: str, seen: Counter[str]) -> str:
    seen[num] += 1
    if seen[num] == 1:
        return f"金匮要略·第{num}条"
    return f"金匮要略·第{num}条（{seen[num]}）"


def parse_articles(raw: bytes) -> list[dict]:
    text = _read_docx(raw)
    matches = list(ARTICLE_END.finditer(text))
    if not matches:
        raise ValueError("未匹配到条文分界，请检查文件格式")

    seen: Counter[str] = Counter()
    docs: list[dict] = []
    for i, m in enumerate(matches):
        num = m.group("num")
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        if i == 0:
            orig_start = text.rfind("\n\n", 0, m.start())
            orig_start = 0 if orig_start < 0 else orig_start + 2
        else:
            prev_end = matches[i - 1].end()
            orig_start = text.rfind("\n\n", prev_end, m.start())
            orig_start = prev_end if orig_start < 0 else orig_start + 2
        piece = text[orig_start:end].strip()
        if len(piece) < 50:
            continue
        docs.append(
            {
                "category": CATEGORY,
                "title": _article_title(num, seen),
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
        raise SystemExit("未解析到条文片段")

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
