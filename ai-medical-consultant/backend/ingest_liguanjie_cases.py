# -*- coding: utf-8 -*-
"""将《李冠杰医案100例》按「案 N」切片导入知识库（一案一片段）。"""

from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

from app.database import SessionLocal, init_db
from app.models import KnowledgeDoc
from app.services.knowledge_base import knowledge_base

warnings.filterwarnings("ignore", message="CropBox.*")

BASE_DIR = Path(r"D:\中医\李冠杰")
PDF_CANDIDATES = [
    BASE_DIR / "06_李冠杰医案100例.pdf",
    BASE_DIR / "李冠杰医案100例.pdf",
]
DOC_CANDIDATES = [
    BASE_DIR / "李冠杰医案100例.doc",
    BASE_DIR / "AI学习资料" / "李冠杰医案100例.doc",
]

CATEGORY = "李冠杰医案"
DEPARTMENT = "临床医案"

CASE_HEADER = re.compile(r"案\s*(\d+)\s*(?:[:：]|\s)(?!\d)", re.M)


def _resolve_source() -> Path:
    for p in PDF_CANDIDATES + DOC_CANDIDATES:
        if p.is_file():
            return p
    raise FileNotFoundError(f"未找到医案文件，已查找：{PDF_CANDIDATES + DOC_CANDIDATES}")


def _read_doc_utf16(path: Path) -> str:
    raw = path.read_bytes()
    text = raw.decode("utf-16le", errors="ignore")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"李冠杰医案\s*(\d+)\s*[:：]", r"案\1:", text)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _read_pdf(path: Path) -> str:
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return "\n\n".join(page.extract_text() or "" for page in pdf.pages)


def load_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return _read_pdf(path)
    if path.suffix.lower() == ".doc":
        return _read_doc_utf16(path)
    raise ValueError(f"不支持的格式：{path.suffix}")


def _is_toc_chunk(piece: str) -> bool:
    first = (piece.split("\n")[0] or "").strip()
    if re.search(r"\.{6,}", first) and "处方" not in piece[:600]:
        return True
    if len(piece) < 120:
        return True
    return False


def _content_start(text: str) -> int:
    for needle in ("2013年6月27日", "案1:", "案1：", "案 1 "):
        idx = text.find(needle)
        if idx >= 0:
            return idx
    return 0


def _extract_subtitle(piece: str, num: str) -> str:
    m = re.match(rf"案\s*{num}\s*[:：]?\s*(.+?)(?:\n|$)", piece.strip())
    if m:
        sub = re.sub(r"\.{3,}.*", "", m.group(1)).strip()
        if sub:
            return sub[:48]
    m = re.match(rf"案\s*{num}\s+(.+?)(?:\n|$)", piece.strip())
    if m:
        return m.group(1).strip()[:48]
    return ""


def _case1_from_preamble(full_text: str, body: str, first_match) -> dict | None:
    """首案正文常以日期开头，无「案1:」行；取正文起点到「案2」之间的内容。"""
    if first_match is None or int(first_match.group(1)) < 2:
        return None
    piece = body[: first_match.start()].strip()
    if len(piece) < 200 or "处方" not in piece:
        return None
    sub = "胃癌胃胀嗳气大便不通案"
    toc = re.search(r"案\s*1\s*[:：]\s*(.+?)(?:\.{4,}|\n)", full_text)
    if toc:
        sub = re.sub(r"\.{3,}.*", "", toc.group(1)).strip()[:48] or sub
    return {
        "category": CATEGORY,
        "title": f"医案100例·案1：{sub}",
        "department": DEPARTMENT,
        "content": f"案1: {sub}\n{piece}",
    }


def parse_cases(text: str) -> list[dict]:
    start = _content_start(text)
    body = text[start:]
    matches = list(CASE_HEADER.finditer(body))
    if not matches:
        raise ValueError("未识别到「案 N」标题，请检查文件格式")

    best: dict[int, dict] = {}
    case1 = _case1_from_preamble(text, body, matches[0])
    if case1:
        best[1] = case1
    for i, m in enumerate(matches):
        num = int(m.group(1))
        if num < 1 or num > 100:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        piece = body[m.start() : end].strip()
        if _is_toc_chunk(piece):
            continue
        if num not in best or len(piece) > len(best[num]["content"]):
            sub = _extract_subtitle(piece, str(num))
            title = f"医案100例·案{num}"
            if sub:
                title += f"：{sub}"
            best[num] = {
                "category": CATEGORY,
                "title": title,
                "department": DEPARTMENT,
                "content": piece,
            }

    docs = [best[n] for n in sorted(best)]
    if len(docs) < 50:
        raise ValueError(f"仅解析到 {len(docs)} 案，数量过少，请检查源文件")
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
    source = _resolve_source()
    source_name = source.name
    print(f"使用源文件：{source}")

    init_db()
    text = load_text(source)
    docs = parse_cases(text)

    db = SessionLocal()
    try:
        if replace:
            removed = (
                db.query(KnowledgeDoc)
                .filter(KnowledgeDoc.source == source_name)
                .delete(synchronize_session=False)
            )
            # 兼容曾用 doc 文件名导入
            alt = "李冠杰医案100例.doc"
            if source_name != alt:
                removed += (
                    db.query(KnowledgeDoc)
                    .filter(KnowledgeDoc.source == alt)
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
                    source=source_name,
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
