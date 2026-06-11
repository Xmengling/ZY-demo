# -*- coding: utf-8 -*-
"""问诊 AI 问答专用知识检索：仅来自上传资料、方剂梳理、伤寒论条文。"""

from __future__ import annotations

import re
from typing import Dict, List

from sqlalchemy.orm import Session

from . import jingfang_store, shanghan_store
from .file_parser import FileParseError, parse_file
from .knowledge_files import list_files, resolve_file_path
from .vector_store import FaissVectorStore

MARKUP_RE = re.compile(r"\[\[\*\*(.+?)\*\*\]\]")
PRESCRIPTION_SEGMENT_RE = re.compile(r"^(.+?)(\d+份)?$")
MAX_DOC_CHARS = 6000
MAX_CONTEXT_CHARS = 1400
MAX_RETRIEVE_DOCS = 10

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


def _normalize_formula_name(name: str) -> str:
    return re.sub(r"\s+", "", str(name or "").strip())


def _parse_prescription_segment(segment: str) -> str:
    text = str(segment or "").strip()
    if not text:
        return ""
    match = PRESCRIPTION_SEGMENT_RE.match(text)
    if match:
        return str(match.group(1) or "").strip()
    return text


def parse_prescription_names_from_context(case_context: str) -> List[str]:
    """从病例摘要「方剂：」行解析全部用方名。"""
    names: List[str] = []
    for line in str(case_context or "").splitlines():
        stripped = line.strip()
        if not stripped.startswith("方剂："):
            continue
        body = stripped.removeprefix("方剂：").strip()
        if not body:
            continue
        for segment in re.split(r"[，,、]", body):
            name = _parse_prescription_segment(segment)
            if name:
                names.append(name)
    return _dedupe_names(names)


def parse_prescription_names_from_intake(intake: dict) -> List[str]:
    prescription = intake.get("prescription") or {}
    rows = prescription.get("rows") or []
    names: List[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if name:
            names.append(name)
    return _dedupe_names(names)


def _dedupe_names(names: List[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for name in names:
        key = _normalize_formula_name(name)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(name.strip())
    return result


def _formula_name_index() -> dict[str, dict]:
    index: dict[str, dict] = {}
    for formula in jingfang_store.list_formulas():
        name = str(formula.get("name") or "").strip()
        if not name:
            continue
        index[_normalize_formula_name(name)] = formula
    return index


def lookup_formula_docs_by_names(names: List[str]) -> List[Dict]:
    if not names:
        return []
    index = _formula_name_index()
    docs: List[Dict] = []
    for name in names:
        formula = index.get(_normalize_formula_name(name))
        if formula:
            docs.append(formula_to_doc(formula))
    return docs


def merge_retrieved_docs(*groups: List[Dict], limit: int = MAX_RETRIEVE_DOCS) -> List[Dict]:
    merged: List[Dict] = []
    seen: set[str] = set()
    for group in groups:
        for doc in group:
            title = str(doc.get("title") or "").strip()
            key = _normalize_formula_name(title) or title
            if key in seen:
                continue
            seen.add(key)
            merged.append(doc)
            if len(merged) >= limit:
                return merged
    return merged


def parse_prescription_display_from_context(case_context: str) -> List[str]:
    """解析病例摘要「方剂：」行，保留「方名+份数」原文片段。"""
    displays: List[str] = []
    for line in str(case_context or "").splitlines():
        stripped = line.strip()
        if not stripped.startswith("方剂："):
            continue
        body = stripped.removeprefix("方剂：").strip()
        if not body:
            continue
        for segment in re.split(r"[，,、]", body):
            text = str(segment or "").strip()
            if text:
                displays.append(text)
    return displays


def parse_prescription_display_from_intake(intake: dict) -> List[str]:
    prescription = intake.get("prescription") or {}
    rows = prescription.get("rows") or []
    displays: List[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        portions = int(row.get("portions") or 1)
        displays.append(f"{name}{portions}份")
    return displays


def extract_prescription_line(case_context: str) -> str:
    for line in str(case_context or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("方剂：") and stripped.removeprefix("方剂：").strip():
            return stripped
    return ""


def collect_prescription_names(case_context: str = "", intake: dict | None = None) -> List[str]:
    """优先采用本次前端传来的病例摘要，避免数据库旧 intake 覆盖当前用方。"""
    from_context = parse_prescription_names_from_context(case_context)
    if from_context:
        return from_context
    if intake:
        return parse_prescription_names_from_intake(intake)
    return []


def collect_prescription_display_items(case_context: str = "", intake: dict | None = None) -> List[str]:
    from_context = parse_prescription_display_from_context(case_context)
    if from_context:
        return from_context
    if intake:
        return parse_prescription_display_from_intake(intake)
    return []


def build_prescription_notice(display_items: List[str]) -> str:
    if not display_items:
        return ""
    lines = [
        f"【当前病例用方】（共 {len(display_items)} 个，分析时必须全部提及，不得遗漏或替换方名）",
    ]
    for index, item in enumerate(display_items, 1):
        lines.append(f"  {index}. {item}")
    lines.append(
        "说明：以上为用方唯一权威清单；不得沿用历史对话中的旧用方，"
        "不得将检索摘录中的相似方名（如大柴胡汤与小柴胡汤）替换上述方名。"
    )
    return "\n".join(lines)


def build_prescription_authority_block(case_context: str, display_items: List[str]) -> str:
    if not display_items:
        return ""
    line = extract_prescription_line(case_context)
    if not line:
        line = "方剂：" + "，".join(display_items)
    return (
        "【本次问诊用方（唯一权威来源）】\n"
        f"{line}\n"
        "回答涉及「当前用方」「处方是否合理」时，必须先原样复述以上全部方名与份数，"
        "再展开分析；不得删减、不得替换、不得只提其中一两个。"
    )


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
        "category": "方剂梳理",
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
            doc["file_id"] = row.id
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

    def search_with_prescriptions(
        self,
        db: Session,
        query: str,
        prescription_names: List[str],
        k: int = 6,
        *,
        extra_formula_names: List[str] | None = None,
    ) -> List[Dict]:
        all_names = _dedupe_names(list(prescription_names) + list(extra_formula_names or []))
        prescription_docs = lookup_formula_docs_by_names(all_names)
        vector_docs = self.search(db, query, k=k) if (query or "").strip() else []
        merged = merge_retrieved_docs(prescription_docs, vector_docs)
        if not merged:
            return merged
        return self._boost_compare_docs(query, merged, all_names)

    @staticmethod
    def _boost_compare_docs(query: str, docs: List[Dict], formula_names: List[str]) -> List[Dict]:
        """鉴别类问题或多方并用时，把方剂「对比」字段前置到摘录内容。"""
        from .consult_chat_prompt import is_compare_query

        if not is_compare_query(query) and len(formula_names) < 2:
            return docs
        boosted: List[Dict] = []
        for doc in docs:
            if doc.get("source") != "jingfang" and doc.get("category") != "方剂梳理":
                boosted.append(doc)
                continue
            content = str(doc.get("content") or "")
            if "对比：" not in content:
                boosted.append(doc)
                continue
            compare_part = ""
            for line in content.splitlines():
                if line.startswith("对比："):
                    compare_part = line
                    break
            if compare_part:
                new_doc = dict(doc)
                new_doc["content"] = compare_part + "\n" + content
                boosted.append(new_doc)
            else:
                boosted.append(doc)
        return boosted

    def search_enhanced(
        self,
        db: Session,
        query: str,
        prescription_names: List[str],
        k: int = 6,
    ) -> List[Dict]:
        from .consult_chat_prompt import extract_formula_names_from_text, is_compare_query

        extra: List[str] = []
        if is_compare_query(query):
            extra = extract_formula_names_from_text(query)
        return self.search_with_prescriptions(
            db,
            query,
            prescription_names,
            k=k,
            extra_formula_names=extra,
        )

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
        refs: List[Dict] = []
        for d in docs:
            content = strip_markup(str(d.get("content") or ""))
            snippet = ""
            if content:
                snippet = content[:MAX_CONTEXT_CHARS] + ("…" if len(content) > MAX_CONTEXT_CHARS else "")
            ref: Dict = {
                "title": d.get("title", ""),
                "category": d.get("category", ""),
                "department": d.get("department", ""),
                "source": d.get("source", ""),
                "score": round(float(d.get("score", 0.0)), 3),
            }
            if snippet:
                ref["snippet"] = snippet
            if d.get("source") == "upload":
                file_id = d.get("file_id")
                if file_id is not None:
                    ref["file_id"] = int(file_id)
                filename = str(d.get("department") or d.get("title") or "").strip()
                if filename:
                    ref["filename"] = filename
            refs.append(ref)
        return refs

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
        lines.append(f"二、方剂梳理（{len(formulas)} 个方剂）")
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
