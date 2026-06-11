# -*- coding: utf-8 -*-
"""AI 回复排版：去掉 Markdown 符号，便于阅读。"""

from __future__ import annotations

import re


def format_ai_reply(text: str) -> str:
    if not text:
        return ""
    s = str(text).replace("\r\n", "\n").replace("\r", "\n").strip()

    # 标题：### 标题 -> 标题
    s = re.sub(r"^#{1,6}\s*", "", s, flags=re.MULTILINE)
    # 加粗/斜体
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"__(.+?)__", r"\1", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", s)
    # 链接 [文字](url) -> 文字
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    # 引用块
    s = re.sub(r"^>\s?", "", s, flags=re.MULTILINE)
    # 无序列表符号 -> 顿号式圆点
    s = re.sub(r"^[\-*+]\s+", "· ", s, flags=re.MULTILINE)
    # 分隔线
    s = re.sub(r"^[\-*_]{3,}\s*$", "", s, flags=re.MULTILINE)
    # 行内代码
    s = re.sub(r"`([^`]+)`", r"\1", s)
    # 多余空行
    s = re.sub(r"\n{3,}", "\n\n", s)
    # 行首尾多余符号
    s = re.sub(r"[ \t]+", " ", s)
    s = "\n".join(line.strip() for line in s.split("\n"))
    s = normalize_list_line_breaks(s)

    return strip_empty_reply_sections(s.strip())


_CN_ENUM_RE = re.compile(r"[一二三四五六七八九十百]+是")
_NUM_ENUM_RE = re.compile(r"\d+[.、．]")


def normalize_list_line_breaks(text: str) -> str:
    """把挤在同段的「一是…二是…」或「1. … 2. …」拆成换行分条。"""
    if not text:
        return ""

    def _split_inline_points(block: str) -> str:
        s = block
        s = re.sub(r"([；;。])\s*(?=(?:[一二三四五六七八九十百]+是))", r"\1\n\n", s)
        s = re.sub(r"([：:])\s*(?=(?:[一二三四五六七八九十百]+是))", r"\1\n\n", s)
        s = re.sub(r"([；;。])\s*(?=\d+[.、．])", r"\1\n\n", s)
        s = re.sub(r"(?<=\S)\s+(?=(?:[一二三四五六七八九十百]+是))", r"\n\n", s)
        s = re.sub(r"(?<=\S)\s+(?=\d+[.、．])", r"\n\n", s)
        return s

    parts = re.split(
        r"(?=^[一二三四五六七八九十]+[、．.]\s*.+?[：:]|^(?:类方鉴别|建议追问)[：:])",
        text,
        flags=re.MULTILINE,
    )
    normalized: list[str] = []
    for part in parts:
        chunk = part.strip()
        if not chunk:
            continue
        match = re.match(
            r"^([一二三四五六七八九十]+[、．.]\s*.+?[：:]|(?:类方鉴别|建议追问)[：:])([\s\S]*)",
            chunk,
        )
        if not match:
            normalized.append(_split_inline_points(chunk))
            continue
        header, body = match.group(1), match.group(2)
        if body.strip():
            normalized.append(f"{header}\n{_split_inline_points(body.strip())}")
        else:
            normalized.append(header)

    result = "\n\n".join(normalized).strip()
    return re.sub(r"\n{3,}", "\n\n", result)


_SECTION_HEADER_RE = re.compile(
    r"^([一二三四五六七八九十]+[、．.]\s*.+?[：:]|(?:类方鉴别|建议追问)[：:])(.*)",
    re.MULTILINE | re.DOTALL,
)

_EMPTY_SECTION_BODIES = frozenset(
    {
        "（本节略）",
        "本节略",
        "暂无需追问",
        "暂无需追问。",
        "暂无对比条目",
        "知识库中暂无对比条目",
        "知识库中暂无对比条目。",
        "当前知识库未检索到胡希恕讲稿相关内容",
        "当前知识库未检索到胡希恕讲稿相关内容。",
        "当前知识库未检索到李冠杰讲稿相关内容",
        "当前知识库未检索到李冠杰讲稿相关内容。",
    }
)

_OPTIONAL_SECTION_KEYWORDS = ("类方鉴别", "建议追问", "胡希恕讲稿摘要", "李冠杰讲稿摘要")


def _normalize_section_body(body: str) -> str:
    return re.sub(r"\s+", "", str(body or "").strip().rstrip("。."))


def _is_empty_section_body(body: str) -> bool:
    text = str(body or "").strip()
    if not text:
        return True
    compact = _normalize_section_body(text)
    if compact in {re.sub(r"\s+", "", x) for x in _EMPTY_SECTION_BODIES}:
        return True
    for marker in ("（本节略）", "暂无需追问", "暂无对比条目", "未检索到胡希恕", "未检索到李冠杰"):
        if marker in text and len(compact) <= len(re.sub(r"\s+", "", marker)) + 12:
            return True
    if "未检索到" in text and ("胡希恕" in text or "李冠杰" in text) and len(compact) < 60:
        return True
    return False


def _is_optional_section(title: str) -> bool:
    return any(keyword in title for keyword in _OPTIONAL_SECTION_KEYWORDS)


_CN_NUMS = "一二三四五六七八九十"


def renumber_reply_sections(text: str) -> str:
    """去掉空段后，将剩余段标题重新连续编号。"""
    if not text:
        return ""
    parts = re.split(
        r"(?=^[一二三四五六七八九十]+[、．.]\s*.+?[：:]|^(?:类方鉴别|建议追问|胡希恕讲稿摘要|李冠杰讲稿摘要)[：:])",
        text,
        flags=re.MULTILINE,
    )
    blocks: list[tuple[str, str]] = []
    for part in parts:
        chunk = part.strip()
        if not chunk:
            continue
        match = re.match(
            r"^([一二三四五六七八九十]+[、．.]\s*.+?[：:]|(?:类方鉴别|建议追问|胡希恕讲稿摘要|李冠杰讲稿摘要)[：:])([\s\S]*)",
            chunk,
        )
        if not match:
            blocks.append(("", chunk))
            continue
        header, body = match.group(1), match.group(2).strip()
        title = re.sub(r"^[一二三四五六七八九十]+[、．.]\s*", "", header.split("：", 1)[0])
        blocks.append((title, body))

    renumbered: list[str] = []
    idx = 0
    for title, body in blocks:
        if not title:
            renumbered.append(body)
            continue
        idx += 1
        num = _CN_NUMS[idx - 1] if idx <= len(_CN_NUMS) else str(idx)
        renumbered.append(f"{num}、{title}：\n{body}".strip() if body else f"{num}、{title}：")

    result = "\n\n".join(renumbered).strip()
    return re.sub(r"\n{3,}", "\n\n", result)


def strip_empty_reply_sections(text: str) -> str:
    """去掉无实质内容的可选段（如类方鉴别、建议追问占位）。"""
    if not text:
        return ""
    s = str(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not s:
        return ""

    parts = re.split(
        r"(?=^[一二三四五六七八九十]+[、．.]\s*.+?[：:]|^(?:类方鉴别|建议追问|胡希恕讲稿摘要|李冠杰讲稿摘要)[：:])",
        s,
        flags=re.MULTILINE,
    )
    kept: list[str] = []
    for part in parts:
        chunk = part.strip()
        if not chunk:
            continue
        match = re.match(
            r"^([一二三四五六七八九十]+[、．.]\s*.+?[：:]|(?:类方鉴别|建议追问|胡希恕讲稿摘要|李冠杰讲稿摘要)[：:])([\s\S]*)",
            chunk,
        )
        if not match:
            kept.append(chunk)
            continue
        header, body = match.group(1), match.group(2).strip()
        title = header.split("：", 1)[0].split(":", 1)[0]
        if _is_optional_section(title) and _is_empty_section_body(body):
            continue
        kept.append(f"{header}\n{body}".strip() if body else header)

    result = "\n\n".join(kept).strip()
    result = re.sub(r"\n{3,}", "\n\n", result)
    return renumber_reply_sections(result)


_FOLLOWUP_SECTION_RE = re.compile(
    r"(?:[三四五六][、．.]\s*)?建议追问[：:]\s*(.*)",
    re.DOTALL,
)
_FOLLOWUP_ITEM_RE = re.compile(r"^\d+[.、．)\]]\s*|^[一二三四五六七八九十]+[是、．.]\s*")


def extract_followup_questions(text: str, *, limit: int = 3) -> list[str]:
    """从回复中解析「建议追问」条目（格式化前调用）。"""
    if not text:
        return []
    s = str(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    match = _FOLLOWUP_SECTION_RE.search(s)
    if not match:
        return []
    body = match.group(1).strip()
    if not body or "暂无需追问" in body or body == "（本节略）":
        return []

    questions: list[str] = []
    for raw_line in body.split("\n"):
        line = _FOLLOWUP_ITEM_RE.sub("", raw_line.strip()).strip()
        if not line or line == "（本节略）":
            continue
        if line.endswith("。") and "？" not in line and "?" not in line:
            line = line[:-1]
        if len(line) >= 4:
            questions.append(line)
    deduped: list[str] = []
    seen: set[str] = set()
    for item in questions:
        key = re.sub(r"\s+", "", item)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= limit:
            break
    return deduped
