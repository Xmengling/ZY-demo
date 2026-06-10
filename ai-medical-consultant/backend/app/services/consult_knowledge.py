# -*- coding: utf-8 -*-
"""问诊 AI 问答专用知识检索：仅来自上传资料、100首方剂、伤寒论条文。"""

from __future__ import annotations

import re
from typing import Dict, List

from sqlalchemy.orm import Session

from . import jingfang_store, shanghan_store
from .file_parser import FileParseError, parse_file
from .knowledge_files import list_files, resolve_file_path
from .vector_store import FaissVectorStore

MARKUP_RE = re.compile(r"\[\[\*\*(.+?)\*\*\]\]")
MAX_DOC_CHARS = 6000
MAX_CONTEXT_CHARS = 1400

FORMULA_FIELDS = [
    ("组成", "composition"),
    ("病理", "pathology"),
    ("病理症状", "pathologySymptoms"),
    ("主要症状", "mainSymptoms"),
    ("临床症状", "clinicalSymptoms"),
    ("现代疾病", "modernDiseases"),
    ("腹诊", "abdominalDiagnosis"),
    ("辩证要点", "diagnosisPoints"),
    ("相关条文", "classicTexts"),
    ("胡希恕", "huXishuAnalysis"),
    ("李冠杰", "liGuanjieAnalysis"),
    ("对比", "compare"),
    ("医案", "cases"),
    ("注意", "caution"),
]


def strip_markup(text: str) -> str:
    if not text:
        return ""
    return MARKUP_RE.sub(r"\1", str(text))


def _stringify_value(value) -> str:
    if value is None or value is False:
        return ""
    if isinstance(value, list):
        parts = [strip_markup(str(item).strip()) for item in value if str(item).strip()]
        return "、".join(parts)
    return strip_markup(str(value).strip())


def formula_to_doc(formula: dict) -> Dict:
    name = str(formula.get("name") or "未命名方剂").strip()
    categories = _stringify_value(formula.get("categories"))
    lines: List[str] = []
    for label, key in FORMULA_FIELDS:
        text = _stringify_value(formula.get(key))
        if text:
            lines.append(f"{label}：{text}")
    case_items = formula.get("caseItems")
    if isinstance(case_items, list) and case_items:
        for i, item in enumerate(case_items, 1):
            if isinstance(item, dict):
                chunk = _stringify_value(item.get("text") or item.get("content") or item)
            else:
                chunk = _stringify_value(item)
            if chunk:
                lines.append(f"医案{i}：{chunk}")
    content = "\n".join(lines).strip()
    if len(content) > MAX_DOC_CHARS:
        content = content[:MAX_DOC_CHARS] + "…"
    return {
        "title": name,
        "category": "100首方剂解读",
        "department": categories,
        "content": content or name,
        "source": "jingfang",
    }


def article_to_doc(article: dict) -> Dict:
    number = str(article.get("number") or "").strip()
    title = f"伤寒论第{number}条" if number else "伤寒论条文"
    level = str(article.get("level") or "").strip()
    lines: List[str] = []
    for label, key in [
        ("原文", "original"),
        ("词解", "terms"),
        ("胡希恕", "huXishu"),
        ("李冠杰", "liGuanjie"),
        ("摘要", "summary"),
    ]:
        text = _stringify_value(article.get(key))
        if text:
            lines.append(f"{label}：{text}")
    term_items = article.get("termItems")
    if isinstance(term_items, list) and term_items:
        for item in term_items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            text = _stringify_value(item.get("text"))
            if label and text:
                lines.append(f"{label}：{text}")
    content = "\n".join(lines).strip()
    if len(content) > MAX_DOC_CHARS:
        content = content[:MAX_DOC_CHARS] + "…"
    return {
        "title": title,
        "category": "伤寒论条文解读",
        "department": level,
        "content": content or title,
        "source": "shanghan",
    }


def _load_upload_docs(db: Session) -> List[Dict]:
    docs: List[Dict] = []
    for row in list_files(db):
        path = resolve_file_path(row)
        if not path.is_file():
            continue
        try:
            raw = path.read_bytes()
            pieces = parse_file(
                row.filename,
                raw,
                default_category="知识库上传",
                chunk_config={"strategy": "whole"},
            )
        except FileParseError:
            continue
        for piece in pieces:
            doc = dict(piece)
            doc["category"] = "知识库上传"
            doc["title"] = str(doc.get("title") or row.filename).strip() or row.filename
            doc["department"] = row.filename
            doc["source"] = "upload"
            content = strip_markup(str(doc.get("content") or ""))
            if not content:
                continue
            if len(content) > MAX_DOC_CHARS:
                content = content[:MAX_DOC_CHARS] + "…"
            doc["content"] = content
            docs.append(doc)
    return docs


def _fingerprint(db: Session) -> str:
    parts: List[str] = []
    for row in list_files(db):
        parts.append(f"file:{row.id}:{row.file_size}")
    parts.append(f"formulas:{len(jingfang_store.list_formulas())}")
    parts.append(f"articles:{len(shanghan_store.list_articles())}")
    return "|".join(parts)


class ConsultKnowledgeRetriever:
    def __init__(self) -> None:
        self._store = FaissVectorStore(dim=768)
        self._fingerprint = ""
        self._ready = False

    def invalidate(self) -> None:
        self._ready = False
        self._fingerprint = ""

    def _build_docs(self, db: Session) -> List[Dict]:
        docs: List[Dict] = []
        docs.extend(_load_upload_docs(db))
        for formula in jingfang_store.list_formulas():
            docs.append(formula_to_doc(formula))
        for article in shanghan_store.list_articles():
            docs.append(article_to_doc(article))
        return docs

    def ensure_ready(self, db: Session) -> None:
        fp = _fingerprint(db)
        if self._ready and fp == self._fingerprint:
            return
        docs = self._build_docs(db)
        self._store.build(docs)
        self._fingerprint = fp
        self._ready = True

    def search(self, db: Session, query: str, k: int = 6) -> List[Dict]:
        self.ensure_ready(db)
        q = (query or "").strip()
        if not q or not self._store.metadatas:
            return []
        return self._store.search(q, k=k)

    @staticmethod
    def build_context(docs: List[Dict]) -> str:
        if not docs:
            return "（未在本地知识库中检索到相关内容）"
        parts: List[str] = []
        for i, doc in enumerate(docs, 1):
            content = strip_markup(str(doc.get("content") or ""))
            if len(content) > MAX_CONTEXT_CHARS:
                content = content[:MAX_CONTEXT_CHARS] + "…"
            parts.append(
                f"[{i}] 《{doc.get('title', '')}》（{doc.get('category', '')}）\n{content}"
            )
        return "\n\n".join(parts)

    @staticmethod
    def build_references(docs: List[Dict]) -> List[Dict]:
        return [
            {
                "title": d.get("title", ""),
                "category": d.get("category", ""),
                "department": d.get("department", ""),
                "source": d.get("source", ""),
                "score": round(float(d.get("score", 0.0)), 3),
            }
            for d in docs
        ]

    @staticmethod
    def build_inventory(db: Session) -> str:
        """完整目录：与知识库页上传列表、方剂库、条文库一致。"""
        uploads = [row.filename for row in list_files(db)]
        formulas = [
            str(item.get("name") or "").strip()
            for item in jingfang_store.list_formulas()
            if str(item.get("name") or "").strip()
        ]
        articles: List[str] = []
        for item in shanghan_store.list_articles():
            number = str(item.get("number") or "").strip()
            articles.append(f"伤寒论第{number}条" if number else "伤寒论条文")

        lines = [
            "【知识库完整目录】",
            "说明：回答「有哪些文件/资料/方剂/条文」时，必须完整照抄下列目录，"
            "不得把下方「检索摘录」误当作全部文件。",
            "",
            f"一、知识库上传（{len(uploads)} 个文件）",
        ]
        if uploads:
            lines.extend(f"  {i}. {name}" for i, name in enumerate(uploads, 1))
        else:
            lines.append("  （暂无上传文件）")

        lines.append("")
        lines.append(f"二、100首方剂解读（{len(formulas)} 个方剂）")
        if formulas:
            lines.append("  " + "、".join(formulas))
        else:
            lines.append("  （暂无）")

        lines.append("")
        lines.append(f"三、伤寒论条文解读（{len(articles)} 条）")
        if articles:
            lines.append("  " + "、".join(articles))
        else:
            lines.append("  （暂无）")

        return "\n".join(lines)


consult_knowledge = ConsultKnowledgeRetriever()
