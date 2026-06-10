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

    return s.strip()
