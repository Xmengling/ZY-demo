# -*- coding: utf-8 -*-
"""将《彩虹医案训练营第三期》docx 按医案切片导入知识库（一案一片段）。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from app.database import SessionLocal, init_db
from app.models import KnowledgeDoc
from app.services.file_parser import _read_docx
from app.services.knowledge_base import knowledge_base

SOURCE_PATH = Path(r"D:\中医\李冠杰\彩虹医案训练营第三期.docx")
SOURCE_NAME = SOURCE_PATH.name
CATEGORY = "彩虹医案训练营第三期"
DEPARTMENT = "临床医案"

PLAIN_SPLIT = re.compile(r"Plain Text(?:文字版)?")
SECTION_LINE = re.compile(r"^([^\n\[]{2,48})\n+\[", re.M)
SUB_CASE = re.compile(r"(?=第二个(?:医案|病人)|第二个医案为)")
INTRO_SPLIT = re.compile(
    r"(?=\d{4}年\d{1,2}月(?:\d{1,2}日)?(?:接诊|，)|"
    r"(?<=。)\s*2024年|"
    r"(?<=。)\s*2025年|"
    r"(?<=。)\s*今年\s*\d+月|"
    r"(?<=。)\s*这是一位姓|"
    r"(?<=。)\s*是一位姓)"
)
TUMOR_SPLIT = re.compile(r"(?=第二个病人，)")


def _resolve_source() -> Path:
    if SOURCE_PATH.is_file():
        return SOURCE_PATH
    raise FileNotFoundError(f"未找到：{SOURCE_PATH}")


def load_text(path: Path) -> str:
    return _read_docx(path.read_bytes())


def _speaker_map(text: str) -> list[tuple[int, str]]:
    return [(m.start(), m.group(1).strip()) for m in SECTION_LINE.finditer(text)]


def _speaker_at(speakers: list[tuple[int, str]], offset: int) -> str:
    label = ""
    for pos, name in speakers:
        if pos <= offset:
            label = name
        else:
            break
    return label


def _extract_subtitle(piece: str) -> str:
    for pat in (
        r"主诉[：:]\s*([^\n。；;]{4,48})",
        r"患者\s*(\S{1,6}[，,][^\n。]{0,24})",
        r"第一个是姓?(\S{1,4})\s*的?女",
        r"姓(\S{1,4})\s*的?女病人",
        r"姓\s*(\S{1,4})\s*[,，]?\s*(?:男|女|男士|女士)",
        r"是一位姓(\S{1,4})",
        r"姓\s*(\S{1,4})\*",
        r"(\S{1,4})\*主诉",
    ):
        m = re.search(pat, piece)
        if m:
            sub = m.group(1).strip()
            sub = re.sub(r"\s+", "", sub)
            if len(sub) >= 2 and sub not in ("的", "是", "人"):
                return sub[:40]
    first = re.sub(r"\s+", " ", piece[:80]).strip()
    return first[:36] if first else "医案"


def _is_lecture_only(piece: str) -> bool:
    if "新病历表" not in piece and "患者" not in piece and "接诊" not in piece:
        if "阴阳不协调" in piece or "全面辨证" in piece[:200] and "份" not in piece:
            return True
    if len(piece) > 900 and "主诉" in piece and ("处方" in piece or ("汤" in piece and "份" in piece)):
        return False
    markers = ("患者", "主诉", "接诊", "复诊", "初诊", "新病历表")
    if not any(k in piece for k in markers):
        return True
    if len(piece) < 280 and "主诉" not in piece and "接诊" not in piece:
        return True
    return False


def _split_subcases(piece: str) -> list[str]:
    if "两个关于肿瘤" in piece or "脑胶质瘤" in piece:
        tumor = [p.strip() for p in TUMOR_SPLIT.split(piece) if p.strip()]
        if len(tumor) > 1:
            return tumor
    parts = [p.strip() for p in SUB_CASE.split(piece) if p.strip()]
    if len(parts) <= 1 and "第一个是" in piece:
        m = re.search(
            r"(第一个是.+?)(?=第二个(?:病人|医案)|$)",
            piece,
            re.S,
        )
        if m:
            head = piece[: m.start()].strip()
            first = (head + "\n" + m.group(1)).strip() if head else m.group(1).strip()
            rest = piece[m.end() :].strip()
            out = []
            if len(first) > 180:
                out.append(first)
            if len(rest) > 180:
                out.append(rest)
            if out:
                return out
    if len(parts) <= 1:
        intro = INTRO_SPLIT.split(piece)
        if len(intro) > 1:
            merged: list[str] = []
            buf = intro[0].strip()
            for seg in intro[1:]:
                seg = seg.strip()
                if len(buf) > 200:
                    merged.append(buf)
                buf = seg
            if len(buf) > 200:
                merged.append(buf)
            if len(merged) > 1:
                return merged
    return parts if parts else [piece]


def parse_cases(text: str) -> list[dict]:
    speakers = _speaker_map(text)
    parts = PLAIN_SPLIT.split(text)
    docs: list[dict] = []
    seen: set[str] = set()

    cursor = 0
    for part in parts:
        part = part.strip()
        if len(part) < 150:
            continue
        needle = part[: min(50, len(part))]
        offset = text.find(needle, cursor)
        if offset < 0:
            offset = text.find(needle)
        else:
            cursor = offset + len(needle)
        speaker = _speaker_at(speakers, max(0, offset))

        for sub in _split_subcases(part):
            if _is_lecture_only(sub):
                continue
            norm = re.sub(r"\s+", "", sub)[:240]
            if norm in seen:
                continue
            seen.add(norm)

            subtitle = _extract_subtitle(sub)
            title = f"彩虹第三期·{subtitle}"
            if speaker:
                title = f"彩虹第三期·{speaker}·{subtitle}"
                sub = f"【分享：{speaker}】\n{sub}"

            docs.append(
                {
                    "category": CATEGORY,
                    "title": title[:120],
                    "department": DEPARTMENT,
                    "content": sub,
                }
            )

    if len(docs) < 5:
        raise ValueError(f"仅解析到 {len(docs)} 条医案，数量过少，请检查源文件")
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
    print(f"使用源文件：{source}")

    init_db()
    text = load_text(source)
    print(f"正文约 {len(text)} 字（docx 内嵌音视频较多，正文主要在 Plain Text 段落）")
    docs = parse_cases(text)

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
        for i, d in enumerate(docs[:5], 1):
            print(f"  [{i}] {d['title']}")
        if len(docs) > 5:
            print(f"  ... 共 {len(docs)} 条")
        _rebuild_index(db)
        print("向量索引已重建")
    finally:
        db.close()


if __name__ == "__main__":
    ingest(replace="--append" not in sys.argv)
