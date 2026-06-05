# -*- coding: utf-8 -*-
"""中医知识库构建：读取 ZY-Study 资料 → 结构化文档 → 写入 data/tcm_knowledge.json

数据来源（默认 D:\\AI\\ZY-Study\\data，可用 --dir 指定）：
  1. 05_常用经方100首方证分析（病理辨证体系版）.chunks.jsonl  —— 按「方剂+字段」聚合为每方一篇
  2. 胡希恕李冠杰 方证解读汇总 202105.chunks.jsonl           —— 每方一篇全文讲解
生成后运行：python -m app.seed --tcm   重建数据库与向量索引。
"""

from __future__ import annotations

import argparse
import collections
import json
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BACKEND_DIR / "data" / "tcm_knowledge.json"

JINGFANG_FILE = "05_常用经方100首方证分析（病理辨证体系版）.chunks.jsonl"
JIEDU_FILE = "胡希恕李冠杰 方证解读汇总 202105.chunks.jsonl"

# 字段展示顺序（临床逻辑：病机→症状→舌脉→方解→现代病）
SECTION_ORDER = ["病理", "症状", "舌质", "舌苔", "脉象", "方解", "现代疾病"]
# 单方全文最大保留字符，避免 RAG 上下文过长
MAX_CONTENT = 6000


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_jingfang_docs(path: Path) -> list[dict]:
    """经方100首：按 formula_no 聚合各字段为一篇结构化文档。"""
    rows = _read_jsonl(path)
    groups: "collections.OrderedDict[int, dict]" = collections.OrderedDict()
    for r in rows:
        no = r.get("formula_no")
        g = groups.setdefault(no, {"name": r.get("formula", ""), "secs": {}})
        sec = r.get("section", "")
        text = (r.get("text") or "").strip()
        if not text:
            continue
        g["secs"].setdefault(sec, []).append(text)

    docs = []
    for g in groups.values():
        name = g["name"]
        if not name:
            continue
        ordered = sorted(
            g["secs"].items(),
            key=lambda kv: SECTION_ORDER.index(kv[0]) if kv[0] in SECTION_ORDER else 99,
        )
        lines = [f"方剂：{name}"]
        for sec, texts in ordered:
            lines.append(f"【{sec}】{' '.join(texts)}")
        content = "\n".join(lines)[:MAX_CONTENT]
        docs.append(
            {
                "category": "经方方证",
                "title": name,
                "department": "中医·经方（常用经方100首）",
                "content": content,
            }
        )
    return docs


def build_jiedu_docs(path: Path) -> list[dict]:
    """方证解读汇总：每个切片（每方全文）为一篇文档。"""
    rows = _read_jsonl(path)
    docs = []
    for r in rows:
        name = (r.get("formula") or "").strip()
        text = (r.get("text") or "").strip()
        if not name or not text:
            continue
        docs.append(
            {
                "category": "经方方证",
                "title": name,
                "department": "中医·经方（胡希恕·李冠杰讲解）",
                "content": text[:MAX_CONTENT],
            }
        )
    return docs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dir",
        default=os.getenv("TCM_DATA_DIR", r"D:\AI\ZY-Study\data"),
        help="中医资料目录",
    )
    args = parser.parse_args()
    data_dir = Path(args.dir)

    docs: list[dict] = []

    jf = data_dir / JINGFANG_FILE
    if jf.exists():
        d = build_jingfang_docs(jf)
        print(f"经方100首：{len(d)} 方")
        docs.extend(d)
    else:
        print(f"未找到：{jf}")

    jd = data_dir / JIEDU_FILE
    if jd.exists():
        d = build_jiedu_docs(jd)
        print(f"方证解读汇总：{len(d)} 方")
        docs.extend(d)
    else:
        print(f"未找到：{jd}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=1)

    print(f"共写入 {len(docs)} 条中医知识 -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
