#!/usr/bin/env python3
"""Export formula cards from the local SQLite database into a preview PDF."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _export_common import DB_PATH, HERB_DIR, OUT_DIR, load_formulas, truetype_font

W, H = 1080, 1501
BG = (248, 251, 255)
PAPER = (255, 255, 255)
BLUE = (71, 124, 255)
BLUE_DARK = (36, 94, 214)
BLUE_SOFT = (237, 244, 255)
LINE = (216, 229, 255)
ORANGE = (255, 154, 53)
RED = (239, 59, 53)
PURPLE = (140, 97, 255)
INK = (23, 32, 51)
MUTED = (90, 104, 128)
GREEN = (47, 155, 105)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return truetype_font(size, bold)


F = {
    "cover_title": font(58, True),
    "cover_subtitle": font(28, True),
    "title": font(42, True),
    "h1": font(28, True),
    "h2": font(23, True),
    "body": font(20),
    "body_b": font(20, True),
    "small": font(17),
    "small_b": font(17, True),
    "tiny": font(14),
    "tiny_b": font(14, True),
}


def text_width(text: str, fnt: ImageFont.FreeTypeFont) -> int:
    return int(fnt.getlength(str(text)))


def strip_markup(text: str) -> str:
    text = str(text or "")
    text = re.sub(r"\[\[\*\*(.+?)\*\*\]\]", r"\1", text)
    text = re.sub(r"\*\*\[\[(.+?)\]\]\*\*", r"\1", text)
    text = re.sub(r"\[\[(.+?)\]\]", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return text


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", strip_markup(text)).strip()


def wrap(text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for para in strip_markup(text).splitlines() or [""]:
        para = para.strip()
        if not para:
            lines.append("")
            continue
        line = ""
        for ch in para:
            trial = line + ch
            if fnt.getlength(trial) <= max_width:
                line = trial
            else:
                if line:
                    lines.append(line)
                line = ch
        if line:
            lines.append(line)
    return lines


def draw_wrapped(
    d: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    max_width: int,
    fnt: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int] = INK,
    line_gap: int = 6,
    max_y: int | None = None,
    bullet: bool = False,
) -> int:
    line_h = fnt.size + line_gap
    lines = wrap(text, fnt, max_width - (22 if bullet else 0))
    for line in lines:
        if max_y is not None and y + line_h > max_y:
            d.text((x, y), "...", font=fnt, fill=MUTED)
            return y + line_h
        if not line:
            y += line_h // 2
            continue
        if bullet:
            d.ellipse((x, y + 9, x + 7, y + 16), fill=BLUE)
            d.text((x + 22, y), line, font=fnt, fill=fill)
        else:
            d.text((x, y), line, font=fnt, fill=fill)
        y += line_h
    return y


def rounded(
    d: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int = 8,
    fill: tuple[int, int, int] | None = None,
    outline: tuple[int, int, int] | None = BLUE,
    width: int = 2,
) -> None:
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def dashed_rect(
    d: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int] = BLUE,
    width: int = 2,
    dash: int = 8,
    gap: int = 6,
) -> None:
    x0, y0, x1, y1 = box
    x = x0
    while x < x1:
        d.line((x, y0, min(x + dash, x1), y0), fill=color, width=width)
        d.line((x, y1, min(x + dash, x1), y1), fill=color, width=width)
        x += dash + gap
    y = y0
    while y < y1:
        d.line((x0, y, x0, min(y + dash, y1)), fill=color, width=width)
        d.line((x1, y, x1, min(y + dash, y1)), fill=color, width=width)
        y += dash + gap


def pill(
    d: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    fnt: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int] = BLUE_SOFT,
    outline: tuple[int, int, int] = BLUE,
    text_fill: tuple[int, int, int] = INK,
    pad_x: int = 16,
    pad_y: int = 8,
    min_width: int = 0,
) -> tuple[int, int, int, int]:
    w = max(min_width, text_width(text, fnt) + pad_x * 2)
    h = fnt.size + pad_y * 2
    rounded(d, (x, y, x + w, y + h), 7, fill=fill, outline=outline, width=2)
    d.text((x + (w - text_width(text, fnt)) / 2, y + pad_y - 1), text, font=fnt, fill=text_fill)
    return (x, y, x + w, y + h)


def section_title(d: ImageDraw.ImageDraw, text: str, x: int, y: int) -> int:
    box = pill(d, text, x, y, F["h2"], fill=PAPER, outline=BLUE, pad_x=18, pad_y=9)
    tip_x = box[2]
    mid_y = (box[1] + box[3]) // 2
    d.polygon([(tip_x, box[1]), (tip_x + 22, mid_y), (tip_x, box[3])], fill=PAPER, outline=BLUE)
    return box[3] + 16


def as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [normalize_text(x) for x in value if normalize_text(x)]
    text = normalize_text(str(value or ""))
    if not text:
        return []
    return [x.strip() for x in re.split(r"[\n、，,]+", text) if x.strip()]


def case_items(formula: dict) -> list[str]:
    items = formula.get("caseItems")
    if isinstance(items, list) and items:
        return [normalize_text(x) for x in items if normalize_text(x)]
    text = strip_markup(formula.get("cases") or "")
    return [normalize_text(x) for x in re.split(r"\n{2,}", text) if normalize_text(x)]


def herb_names(formula: dict) -> list[str]:
    files = formula.get("herbImages") or []
    names = []
    for item in files:
        stem = Path(str(item)).stem
        if stem and stem not in names:
            names.append(stem)
    if names:
        return names
    composition = normalize_text(formula.get("composition") or "")
    return [x for x in re.split(r"\s+", composition) if x][:8]


def draw_herb_gallery(base: Image.Image, formula: dict, x: int, y: int) -> None:
    d = ImageDraw.Draw(base)
    files = list(formula.get("herbImages") or [])[:10]
    if not files:
        files = [f"{name}.jpg" for name in herb_names(formula)[:10]]
    cols = 3 if len(files) > 6 else 2
    size = 66
    gap_x = 24
    gap_y = 26
    for i, filename in enumerate(files[:10]):
        row = i // cols
        col = i % cols
        cx = x + col * (size + gap_x)
        cy = y + row * (size + gap_y)
        rounded(d, (cx, cy, cx + size, cy + size), size // 2, fill=(247, 241, 232), outline=None, width=0)
        path = HERB_DIR / str(filename)
        if path.exists():
            try:
                img = Image.open(path).convert("RGB")
                img.thumbnail((size, size), Image.Resampling.LANCZOS)
                crop = Image.new("L", (size, size), 0)
                cd = ImageDraw.Draw(crop)
                cd.ellipse((0, 0, size, size), fill=255)
                canvas = Image.new("RGB", (size, size), (247, 241, 232))
                canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
                base.paste(canvas, (cx, cy), crop)
            except OSError:
                pass
        else:
            stem = Path(str(filename)).stem[:2]
            d.text((cx + (size - text_width(stem, F["small_b"])) / 2, cy + 19), stem, font=F["small_b"], fill=(122, 91, 50))
        label = Path(str(filename)).stem[:4]
        d.text((cx + (size - text_width(label, F["tiny"])) / 2, cy + size + 5), label, font=F["tiny"], fill=MUTED)


def draw_cover(formulas: list[dict]) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((34, 34, W - 34, H - 34), radius=12, fill=PAPER, outline=BLUE, width=5)
    d.rounded_rectangle((58, 58, W - 58, H - 58), radius=10, outline=LINE, width=3)

    d.text((92, 132), "100首方剂解读", font=F["cover_title"], fill=INK)
    d.text((96, 214), "方剂卡片合集 PDF 预览版", font=F["cover_subtitle"], fill=BLUE_DARK)
    d.line((92, 282, W - 92, 282), fill=LINE, width=3)

    stats = [
        ("当前导出", f"{len(formulas)} 首"),
        ("资料形式", "方剂卡片 / 目录索引 / 学习提示"),
        ("定位", "中医方剂学习资料"),
    ]
    y = 365
    for label, value in stats:
        pill(d, label, 96, y, F["h2"], fill=BLUE_SOFT, outline=BLUE, min_width=128)
        d.text((260, y + 8), value, font=F["h1"], fill=INK)
        y += 86

    names = "、".join([item.get("name", "未命名") for item in formulas[:12]])
    d.text((96, 680), "本次包含", font=F["h1"], fill=INK)
    draw_wrapped(d, names or "暂无方剂", 96, 730, W - 192, F["body"], fill=MUTED, line_gap=10, max_y=1040)

    note = "学习资料，仅供中医学习交流，不作为诊疗处方依据。具体用药请咨询专业医师。"
    dashed_rect(d, (96, 1165, W - 96, 1278), color=ORANGE, width=3)
    draw_wrapped(d, note, 124, 1205, W - 248, F["body_b"], fill=INK, line_gap=8)

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    d.text((96, H - 145), f"导出时间：{stamp}", font=F["small"], fill=MUTED)
    d.text((96, H - 108), "小小梦学中医", font=F["small_b"], fill=BLUE_DARK)
    return img


def draw_toc(formulas: list[dict]) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((34, 34, W - 34, H - 34), radius=12, fill=PAPER, outline=BLUE, width=5)
    d.text((82, 78), "目录索引", font=F["title"], fill=INK)
    d.text((84, 132), "按当前数据库更新时间排序", font=F["small"], fill=MUTED)
    d.line((82, 178, W - 82, 178), fill=LINE, width=3)

    y = 222
    for index, formula in enumerate(formulas, 1):
        if y > H - 122:
            d.text((82, y), "...", font=F["h2"], fill=MUTED)
            break
        name = formula.get("name") or "未命名方剂"
        cats = " / ".join(formula.get("categories") or ["未归类"])
        points = "；".join(as_list(formula.get("diagnosisPoints"))[:2])
        d.text((88, y), f"{index:02d}", font=F["h2"], fill=BLUE_DARK)
        d.text((154, y - 1), name, font=F["h2"], fill=INK)
        d.text((392, y + 2), cats, font=F["small_b"], fill=GREEN)
        if points:
            draw_wrapped(d, points, 154, y + 36, 820, F["small"], fill=MUTED, line_gap=4, max_y=y + 76)
        d.line((82, y + 88, W - 82, y + 88), fill=(232, 240, 255), width=2)
        y += 104
    return img


def draw_card(formula: dict, number: int, total: int) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((22, 22, W - 22, H - 22), radius=10, fill=PAPER, outline=BLUE, width=5)
    d.rounded_rectangle((36, 36, W - 36, H - 36), radius=8, outline=BLUE, width=2)
    d.line((36, 330, W - 36, 330), fill=LINE, width=3)
    d.line((338, 330, 338, H - 70), fill=LINE, width=3)

    draw_herb_gallery(img, formula, 70, 72)

    title = formula.get("name") or "未命名方剂"
    title_w = min(548, max(250, text_width(title, F["title"]) + 72))
    dashed_rect(d, (380, 72, 380 + title_w, 142), color=ORANGE, width=3, dash=7, gap=6)
    d.text((380 + (title_w - text_width(title, F["title"])) / 2, 84), title, font=F["title"], fill=INK)

    d.text((880, 80), f"{number:02d}/{total:02d}", font=F["h2"], fill=BLUE_DARK)
    cats = formula.get("categories") or []
    x = 380
    for cat in cats[:4]:
        box = pill(d, cat, x, 168, F["small_b"], fill=BLUE_SOFT, outline=BLUE, pad_x=14, pad_y=7)
        x = box[2] + 12
    if not cats:
        pill(d, "未归类", x, 168, F["small_b"], fill=(244, 246, 248), outline=(203, 213, 225), pad_x=14, pad_y=7)

    comp = normalize_text(formula.get("composition") or "未填写")
    pill(d, "组成", 380, 230, F["body_b"], fill=PAPER, outline=ORANGE, pad_x=16, pad_y=8, min_width=92)
    dashed_rect(d, (492, 230, W - 70, 290), color=ORANGE, width=3, dash=7, gap=6)
    draw_wrapped(d, comp, 512, 244, W - 600, F["body"], fill=INK, line_gap=4, max_y=286)

    left_x, left_w = 62, 238
    y = section_title(d, "病理", left_x, 372)
    pathology = formula.get("pathology") or []
    if pathology:
        tag_x, tag_y = left_x, y
        for item in pathology[:6]:
            label = normalize_text(item.get("label") if isinstance(item, dict) else str(item))
            if not label:
                continue
            box = pill(d, label, tag_x, tag_y, F["small_b"], fill=BLUE_SOFT, outline=BLUE, pad_x=11, pad_y=7, min_width=72)
            tag_x = box[2] + 8
            if tag_x > left_x + left_w - 72:
                tag_x = left_x
                tag_y = box[3] + 10
        y = tag_y + 54
    else:
        d.text((left_x, y), "未填写", font=F["small"], fill=MUTED)
        y += 38

    y = section_title(d, "病理症状", left_x, y + 26)
    for item in pathology[:5]:
        if not isinstance(item, dict):
            continue
        label = normalize_text(item.get("label"))
        text = normalize_text(item.get("text"))
        if not label and not text:
            continue
        pill(d, label or "症状", left_x, y, F["tiny_b"], fill=BLUE_SOFT, outline=BLUE, pad_x=10, pad_y=6, min_width=68)
        y = draw_wrapped(d, text or "未填写", left_x + 82, y + 3, left_w - 80, F["tiny_b"], fill=INK, line_gap=4, max_y=y + 62)
        y += 12

    symptoms = as_list(formula.get("clinicalSymptoms"))[:8]
    y = section_title(d, "临床症状", left_x, y + 20)
    y = draw_wrapped(d, "、".join(symptoms) or "未填写", left_x, y, left_w, F["small_b"], fill=INK, line_gap=5, max_y=1110)

    caution = normalize_text(formula.get("caution") or "")
    if caution and y < 1220:
        y = section_title(d, "慎用人群", left_x, y + 24)
        draw_wrapped(d, caution, left_x, y, left_w, F["small_b"], fill=RED, line_gap=5, max_y=1335)

    main_x, main_w = 390, 610
    y = section_title(d, "辨证要点", main_x, 372)
    points = as_list(formula.get("diagnosisPoints"))[:7]
    if not points:
        points = ["未填写"]
    for i, point in enumerate(points):
        fill = PURPLE if i == 0 else INK
        rounded(d, (main_x + 34, y, main_x + main_w - 8, y + 43), 22, fill=PAPER, outline=BLUE, width=2)
        d.text((main_x + 54, y + 10), point[:38], font=F["body_b"], fill=fill)
        y += 55

    y += 12
    callout_tops = [
        ("相关原文", formula.get("classicTexts") or []),
        ("医案", case_items(formula)),
        ("胡希恕解析", [formula.get("huXishuAnalysis") or ""]),
        ("李冠杰解析", [formula.get("liGuanjieAnalysis") or ""]),
    ]
    remaining_bottom = H - 120
    for title_text, body_items in callout_tops:
        if y > remaining_bottom - 90:
            break
        body = "\n".join([normalize_text(x) for x in body_items if normalize_text(x)]) or "未填写"
        natural_lines = wrap(body, F["small"], main_w - 54)
        box_h = min(190, max(92, len(natural_lines) * 24 + 58))
        dashed_rect(d, (main_x, y, main_x + main_w, y + box_h), color=BLUE, width=2, dash=7, gap=6)
        pill(d, title_text, main_x + 32, y - 24, F["h2"], fill=BLUE_SOFT, outline=BLUE, pad_x=20, pad_y=8)
        draw_wrapped(d, body, main_x + 28, y + 36, main_w - 56, F["small"], fill=INK, line_gap=6, max_y=y + box_h - 18)
        y += box_h + 58

    footer = "学习资料，仅供中医学习交流，不作为诊疗处方依据。"
    d.text((main_x, H - 82), footer, font=F["tiny"], fill=MUTED)
    d.text((70, H - 82), "小小梦学中医", font=F["tiny_b"], fill=BLUE_DARK)
    return img


def save_pdf(pages: Iterable[Image.Image], out_path: Path) -> None:
    page_list = [page.convert("RGB") for page in pages]
    if not page_list:
        raise RuntimeError("no pages to export")
    page_list[0].save(out_path, "PDF", resolution=144.0, save_all=True, append_images=page_list[1:])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    formulas = load_formulas()
    if not formulas:
        raise RuntimeError(f"数据库中没有方剂：{DB_PATH}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    pdf_path = OUT_DIR / f"方剂卡片合集_现有{len(formulas)}首_{stamp}.pdf"
    preview_path = OUT_DIR / f"方剂卡片合集_预览首图_{stamp}.png"

    pages = [draw_cover(formulas), draw_toc(formulas)]
    for index, formula in enumerate(formulas, 1):
        pages.append(draw_card(formula, index, len(formulas)))
    save_pdf(pages, pdf_path)
    pages[2].save(preview_path, quality=95)

    print(f"导出方剂：{len(formulas)} 首")
    print(f"PDF：{pdf_path}")
    print(f"首张预览图：{preview_path}")


if __name__ == "__main__":
    main()
