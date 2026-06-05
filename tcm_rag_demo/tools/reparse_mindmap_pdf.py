# -*- coding: utf-8 -*-
from pathlib import Path
import re

import fitz


PDF = Path(r"d:/AI/demo/tcm_rag_demo/data/伤寒金匮方剂思维导图.pdf")
OUT = Path(r"d:/AI/demo/tcm_rag_demo/data/伤寒金匮方剂思维导图.reparsed.txt")

SECTIONS = ["组成", "方解", "腹证", "病理", "辨证要点", "相关条文"]
FORMULA_RE = re.compile(r"^[\u4e00-\u9fffA-Za-z]{2,40}(汤|散|丸|饮|方)$")


def norm_text(text: str) -> str:
    return re.sub(r"\s+", "", text.replace("\x00", "")).strip()


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def is_page_number(text: str, x0: float, y0: float, page_rect) -> bool:
    return bool(re.fullmatch(r"\d{1,3}", text.strip())) and (
        y0 > page_rect.height - 45 or x0 < 25 or x0 > page_rect.width - 35
    )


def split_label_prefix(text: str):
    n = norm_text(text)
    for sec in SECTIONS:
        if n == sec:
            return sec, ""
        if n.startswith(sec):
            # 用正则在原文本里尽量保留标签后的原始内容
            pattern = r"\s*".join(list(sec))
            m = re.match(pattern + r"\s*(.*)$", text, flags=re.S)
            if m:
                return sec, clean_text(m.group(1))
            return sec, n[len(sec) :]
    return None, text


def looks_like_formula_title(text: str) -> bool:
    n = norm_text(text)
    if any(key in n for key in SECTIONS):
        return False
    if any(p in n for p in ["主之", "：", "。", "，", "、", "《", "》"]):
        return False
    return bool(FORMULA_RE.fullmatch(n))


def vertical_overlap(a, b) -> float:
    _, ay0, _, ay1 = a
    _, by0, _, by1 = b
    return max(0.0, min(ay1, by1) - max(ay0, by0))


def assign_section(block, labels):
    bx0, by0, bx1, by1 = block["bbox"]
    bcy = (by0 + by1) / 2

    # 特殊版式：某些页（如桂枝汤）“相关条文”为中心竖排分支，
    # 其右侧整栏都是相关条文，不应按垂直距离误分到组成/方解等左侧分支。
    related_labels = [x for x in labels if x["section"] == "相关条文"]
    for label in related_labels:
        lx0, ly0, lx1, ly1 = label["bbox"]
        label_height = ly1 - ly0
        label_width = lx1 - lx0
        if label_height > label_width * 1.8 and bx0 > lx1 + 20:
            return "相关条文"

    best = None
    best_score = -10**9
    for label in labels:
        lx0, ly0, lx1, ly1 = label["bbox"]
        lcy = (ly0 + ly1) / 2
        overlap = vertical_overlap(block["bbox"], label["bbox"])
        dist = abs(bcy - lcy)
        # 思维导图分支通常与分支标题处于同一横向带：
        # 1) 垂直重叠最重要；2) 分支内容一般在标签右侧；3) 再考虑距离。
        score = overlap * 50 - dist * 2
        if bx0 >= lx0 - 8:
            score += 15
        if bx0 >= lx1 - 5:
            score += 20
        else:
            score -= 20
        # 跨栏内容容易误归，按水平距离做轻微惩罚。
        score -= min(35, abs(bx0 - lx0) / 25)
        if score > best_score:
            best = label
            best_score = score
    return best["section"] if best else None


def extract_page(page):
    raw_blocks = []
    for item in page.get_text("blocks"):
        x0, y0, x1, y1, text, *_ = item
        text = clean_text(text)
        if not text:
            continue
        if is_page_number(text, x0, y0, page.rect):
            continue
        raw_blocks.append({"bbox": (x0, y0, x1, y1), "text": text})

    if not raw_blocks:
        return None

    title_block = None
    for block in raw_blocks:
        if looks_like_formula_title(block["text"]):
            title_block = block
            break
    if not title_block:
        return None

    title = norm_text(title_block["text"])
    # 竖排方名有时会被抽成“桂 枝 汤”，norm_text 已合并；这里再清理异常空白。
    title = re.sub(r"\s+", "", title)
    labels = []
    content_blocks = []

    for block in raw_blocks:
        if block is title_block:
            continue
        sec, rest = split_label_prefix(block["text"])
        if sec:
            labels.append({"section": sec, "bbox": block["bbox"]})
            if rest:
                content_blocks.append({"bbox": block["bbox"], "text": rest, "forced": sec})
        else:
            content_blocks.append({**block, "forced": None})

    if not labels:
        return None

    sections = {sec: [] for sec in SECTIONS}
    for block in content_blocks:
        sec = block.get("forced") or assign_section(block, labels)
        if not sec:
            continue
        text = clean_text(block["text"])
        if text and text not in sections[sec]:
            sections[sec].append(text)

    return title, sections


def render_formula(title: str, sections: dict):
    out = [f"## {title}", ""]
    for sec in SECTIONS:
        out.append(sec)
        out.extend(sections.get(sec, []))
        out.append("")
    return out


def main():
    doc = fitz.open(PDF)
    formulas = []
    skipped = []
    # 前 10 页主要是封面/目录，从正文页开始；仍用识别结果兜底。
    for page_index in range(doc.page_count):
        result = extract_page(doc[page_index])
        if result:
            formulas.append((page_index + 1, *result))
        else:
            skipped.append(page_index + 1)

    out = []
    for idx, (page_no, title, sections) in enumerate(formulas):
        if idx:
            out.extend(["", ""])
        out.extend(render_formula(title, sections))

    while out and not out[-1].strip():
        out.pop()

    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"output: {OUT}")
    print(f"formulas: {len(formulas)}")
    print(f"skipped pages: {len(skipped)}")
    print("first pages:", [p for p, _, _ in formulas[:5]])


if __name__ == "__main__":
    main()
