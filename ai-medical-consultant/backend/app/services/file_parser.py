# -*- coding: utf-8 -*-
"""上传文件解析：txt / md / docx / json(jsonl) → 知识库文档列表。

零新增依赖：docx 通过 zip + XML 解析正文。
解析结果统一为 [{category, title, department, content}, ...]。
"""

from __future__ import annotations

import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from typing import Dict, List

# 支持的扩展名白名单
ALLOWED_EXTS = {".txt", ".md", ".docx", ".json", ".jsonl"}
# 单文件大小上限（字节）
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
# 文本切片参数
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100


class FileParseError(Exception):
    pass


def get_ext(filename: str) -> str:
    name = (filename or "").lower()
    dot = name.rfind(".")
    return name[dot:] if dot >= 0 else ""


def _clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _read_docx(raw: bytes) -> str:
    """读取 docx 正文：docx 本质是 zip，正文在 word/document.xml。"""
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            root = ET.fromstring(zf.read("word/document.xml"))
    except Exception as e:
        raise FileParseError(f"docx 解析失败：{e}")

    paras = []
    for para in root.findall(".//w:p", ns):
        texts = [t.text or "" for t in para.findall(".//w:t", ns)]
        line = "".join(texts).strip()
        if line:
            paras.append(line)
    return _clean_text("\n\n".join(paras))


def _decode_text(raw: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "gb18030", "gbk"):
        try:
            return _clean_text(raw.decode(enc))
        except UnicodeDecodeError:
            continue
    return _clean_text(raw.decode("utf-8", errors="ignore"))


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """按段落聚合并按长度切片，尽量在中文标点处断开。"""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    # 先按段落分，再贪心填充到接近 size
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: List[str] = []
    buf = ""
    for p in paras:
        if len(buf) + len(p) + 1 <= size:
            buf = f"{buf}\n{p}" if buf else p
        else:
            if buf:
                chunks.append(buf)
            # 单段超长则进一步硬切
            if len(p) > size:
                chunks.extend(_hard_split(p, size, overlap))
                buf = ""
            else:
                buf = p
    if buf:
        chunks.append(buf)
    return chunks


def _hard_split(text: str, size: int, overlap: int) -> List[str]:
    seps = "。！？；\n"
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        # 尝试在标点处断开
        window = text[start:end]
        cut = max(window.rfind(s) for s in seps)
        if cut > size * 0.5:
            end = start + cut + 1
        chunks.append(text[start:end].strip())
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def split_by_paragraph(text: str, max_size: int = CHUNK_SIZE) -> List[str]:
    """按空行分段，并把相邻短段合并到 max_size 以内；超长段再硬切。"""
    text = (text or "").strip()
    if not text:
        return []
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    merged: List[str] = []
    buf = ""
    for p in paras:
        if not buf:
            buf = p
        elif max_size and len(buf) + len(p) + 2 <= max_size:
            buf = f"{buf}\n\n{p}"
        else:
            merged.append(buf)
            buf = p
    if buf:
        merged.append(buf)

    out: List[str] = []
    for c in merged:
        if max_size and len(c) > max_size:
            out.extend(_hard_split(c, max_size, 0))
        else:
            out.append(c)
    return [c for c in out if c]


def _normalize_separator_patterns(patterns: List[str]) -> List[str]:
    """将常见的 Markdown 标题写法规范为「行首匹配」，避免误切且与 ## 标题语义一致。"""
    out: List[str] = []
    for p in patterns:
        raw = p.strip()
        if not raw:
            continue
        if raw in ("##", "## "):
            out.append(r"^##\s+")
        elif raw in ("###", "### "):
            out.append(r"^###\s+")
        else:
            out.append(raw)
    return out


def split_by_separators(text: str, patterns: List[str], max_size: int = 0) -> List[str]:
    """按分隔符/标题切片：在每个匹配处断开，分隔符保留在所在片段开头。

    patterns 支持正则（如 第\\d+条、^##\\s）；非法正则按字面量处理。
    max_size>0 时才会对超长单块做二次硬切（默认 0，仅按分隔符切）。
    """
    text = (text or "").strip()
    if not text:
        return []
    patterns = _normalize_separator_patterns(patterns)
    if not patterns:
        return chunk_text(text)

    combined = "|".join(f"(?:{p})" for p in patterns)
    try:
        regex = re.compile(combined, re.M)
    except re.error:
        regex = re.compile("|".join(re.escape(p) for p in patterns), re.M)

    matches = list(regex.finditer(text))
    if not matches:
        return [text]

    chunks: List[str] = []
    preamble = text[: matches[0].start()].strip()
    if preamble:
        chunks.append(preamble)
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        seg = text[start:end].strip()
        if seg:
            chunks.append(seg)

    if max_size:
        out: List[str] = []
        for c in chunks:
            if len(c) > max_size:
                out.extend(_hard_split(c, max_size, 0))
            else:
                out.append(c)
        return out
    return chunks


SHANGHAN_ARTICLE_HEAD_RE = re.compile(r"^第\s*(\d+)\s*条\s*原文[：:]", re.M)
SHANGHAN_ARTICLE_SPLIT_PATTERN = r"^第\s*\d+\s*条\s*原文[：:]"


def split_shanghan_lecture_articles(text: str) -> List[tuple[str, str]]:
    """按「第 N 条 + 原文」切分伤寒论讲稿，返回 [(条号, 正文), ...]。"""
    text = (text or "").strip()
    if not text:
        return []
    pieces = split_by_separators(text, [SHANGHAN_ARTICLE_SPLIT_PATTERN], max_size=0)
    articles: List[tuple[str, str]] = []
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        match = SHANGHAN_ARTICLE_HEAD_RE.match(piece)
        if not match:
            continue
        number = str(int(match.group(1)))
        articles.append((number, piece))
    return articles


def split_text(text: str, config: Dict | None = None) -> List[str]:
    """切片策略分发：fixed / paragraph / separator / whole。"""
    config = config or {}
    strategy = config.get("strategy", "fixed")
    size = int(config.get("size") or CHUNK_SIZE)
    overlap = int(config.get("overlap") or 0)

    if strategy == "whole":
        t = (text or "").strip()
        return [t] if t else []
    if strategy == "paragraph":
        return split_by_paragraph(text, size)
    if strategy == "separator":
        max_sz = int(config.get("size") or 0)
        return split_by_separators(text, config.get("separators") or [], max_sz)
    return chunk_text(text, size, overlap or CHUNK_OVERLAP)


def _parse_structured(raw: bytes, default_category: str) -> List[Dict]:
    """解析 json / jsonl：兼容 {title, category, department, content} 记录。"""
    text = _decode_text(raw)
    records: List[Dict] = []

    # 优先按整体 JSON 数组解析
    try:
        data = json.loads(text)
        if isinstance(data, list):
            records = [r for r in data if isinstance(r, dict)]
        elif isinstance(data, dict):
            records = [data]
    except json.JSONDecodeError:
        # 退化为 jsonl 逐行解析
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    records.append(obj)
            except json.JSONDecodeError:
                continue

    docs: List[Dict] = []
    for i, r in enumerate(records, 1):
        content = str(r.get("content") or r.get("text") or "").strip()
        if not content:
            continue
        docs.append(
            {
                "category": str(r.get("category") or default_category).strip(),
                "title": str(r.get("title") or r.get("formula") or f"条目{i}").strip(),
                "department": str(r.get("department") or "").strip(),
                "content": content,
            }
        )
    return docs


def parse_file(
    filename: str,
    raw: bytes,
    default_category: str = "上传资料",
    chunk_config: Dict | None = None,
) -> List[Dict]:
    """主入口：根据扩展名解析文件为知识库文档列表。

    chunk_config: {strategy, size, overlap, separators}，仅对 txt/md/docx 生效；
    json/jsonl 始终按记录结构化导入。
    """
    ext = get_ext(filename)
    if ext not in ALLOWED_EXTS:
        raise FileParseError(f"不支持的文件类型：{ext or '未知'}")
    if len(raw) > MAX_FILE_SIZE:
        raise FileParseError("文件超过大小上限（10MB）")

    base_title = re.sub(r"\.[^.]+$", "", filename).strip() or "上传文档"

    if ext in {".json", ".jsonl"}:
        docs = _parse_structured(raw, default_category)
        if not docs:
            raise FileParseError("未从文件中解析到有效内容")
        return docs

    if ext == ".docx":
        text = _read_docx(raw)
    else:  # .txt / .md
        text = _decode_text(raw)

    if not text:
        raise FileParseError("文件内容为空或无法识别")

    pieces = split_text(text, chunk_config)
    if not pieces:
        raise FileParseError("切片结果为空，请调整切片方式或参数")
    total = len(pieces)
    docs = []
    for i, piece in enumerate(pieces, 1):
        title = base_title if total == 1 else f"{base_title} - 片段{i}/{total}"
        docs.append(
            {
                "category": default_category,
                "title": title,
                "department": "",
                "content": piece,
            }
        )
    return docs
