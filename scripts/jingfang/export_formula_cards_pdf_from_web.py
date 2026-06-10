#!/usr/bin/env python3
"""Export the real web preview cards as a high-resolution PDF.

This script opens the local web app with Playwright, renders each formula with
the same DOM/CSS used by the preview pane, screenshots the card at 3x scale,
and combines those images into a PDF.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _export_common import (  # noqa: E402
    DB_PATH,
    OUT_DIR,
    URL,
    browser_executable,
    load_formula_summary,
    start_server,
    stop_server,
    truetype_font,
)

W, H = 1080, 1501
BG = (248, 251, 255)
PAPER = (255, 255, 255)
BLUE = (71, 124, 255)
BLUE_DARK = (36, 94, 214)
LINE = (216, 229, 255)
INK = (23, 32, 51)
MUTED = (90, 104, 128)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return truetype_font(size, bold)


F_TITLE = font(58, True)
F_H1 = font(34, True)
F_H2 = font(24, True)
F_BODY = font(20)
F_SMALL = font(16)


def draw_text_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    width: int,
    fnt: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int] = INK,
    line_gap: int = 8,
    max_y: int | None = None,
) -> int:
    line = ""
    for ch in text:
        trial = line + ch
        if fnt.getlength(trial) <= width:
            line = trial
            continue
        if max_y and y + fnt.size > max_y:
            draw.text((x, y), "...", font=fnt, fill=MUTED)
            return y + fnt.size + line_gap
        draw.text((x, y), line, font=fnt, fill=fill)
        y += fnt.size + line_gap
        line = ch
    if line:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += fnt.size + line_gap
    return y


def cover_page(formulas: list[dict]) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((34, 34, W - 34, H - 34), radius=12, fill=PAPER, outline=BLUE, width=5)
    d.rounded_rectangle((58, 58, W - 58, H - 58), radius=10, outline=LINE, width=3)
    d.text((96, 140), "方剂梳理", font=F_TITLE, fill=INK)
    d.text((100, 230), "方剂卡片合集 PDF 预览版", font=F_H1, fill=BLUE_DARK)
    d.line((96, 310, W - 96, 310), fill=LINE, width=3)

    rows = [
        ("当前导出", f"{len(formulas)} 首"),
        ("导出方式", "复用 Web 预览样式，3x 高清截图"),
        ("资料定位", "中医方剂学习资料"),
    ]
    y = 410
    for label, value in rows:
        d.rounded_rectangle((96, y, 246, y + 52), radius=8, fill=(237, 244, 255), outline=BLUE, width=2)
        d.text((126, y + 13), label, font=F_H2, fill=INK)
        d.text((284, y + 8), value, font=F_H1 if label == "当前导出" else F_H2, fill=INK)
        y += 86

    names = "、".join(item["name"] for item in formulas[:20])
    d.text((96, 720), "本次包含", font=F_H1, fill=INK)
    draw_text_wrapped(d, names or "暂无方剂", 96, 778, W - 192, F_BODY, fill=MUTED, max_y=1045)

    note = "学习资料，仅供中医学习交流，不作为诊疗处方依据。具体用药请咨询专业医师。"
    d.rounded_rectangle((96, 1160, W - 96, 1278), radius=8, outline=BLUE, width=2)
    draw_text_wrapped(d, note, 124, 1200, W - 248, F_BODY, fill=INK)
    d.text((96, H - 126), datetime.now().strftime("导出时间：%Y-%m-%d %H:%M"), font=F_SMALL, fill=MUTED)
    d.text((96, H - 92), "小小梦学中医", font=F_SMALL, fill=BLUE_DARK)
    return img


def toc_page(formulas: list[dict]) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((34, 34, W - 34, H - 34), radius=12, fill=PAPER, outline=BLUE, width=5)
    d.text((82, 78), "目录索引", font=font(44, True), fill=INK)
    d.text((84, 134), "按当前数据库更新时间排序", font=F_SMALL, fill=MUTED)
    d.line((82, 180, W - 82, 180), fill=LINE, width=3)
    y = 226
    for index, formula in enumerate(formulas, 1):
        if y > H - 128:
            d.text((82, y), "...", font=F_H2, fill=MUTED)
            break
        cats = " / ".join(formula["categories"] or ["未归类"])
        point = "；".join(str(x) for x in formula["points"][:2])
        d.text((88, y), f"{index:02d}", font=F_H2, fill=BLUE_DARK)
        d.text((154, y - 1), formula["name"], font=F_H2, fill=INK)
        d.text((392, y + 3), cats, font=F_SMALL, fill=BLUE_DARK)
        if point:
            draw_text_wrapped(d, point, 154, y + 36, 810, F_SMALL, fill=MUTED, line_gap=4, max_y=y + 78)
        d.line((82, y + 90, W - 82, y + 90), fill=(232, 240, 255), width=2)
        y += 106
    return img


def export_card_images(out_dir: Path, scale: float) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        executable_path = browser_executable()
        launch_kwargs = {"headless": True}
        if executable_path:
            launch_kwargs["executable_path"] = str(executable_path)
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(
            viewport={"width": 1320, "height": 2100},
            device_scale_factor=scale,
            locale="zh-CN",
        )
        page = context.new_page()
        page.goto(URL, wait_until="networkidle")
        page.wait_for_selector("#formula-card")
        page.wait_for_function("typeof state !== 'undefined' && state.formulas && state.formulas.length > 0")
        page.add_style_tag(
            content="""
              html, body {
                width: max-content !important;
                height: max-content !important;
                overflow: visible !important;
                background: #eef5ff !important;
              }
              .top-menu,
              .list-panel,
              .editor-panel,
              .card-side-actions,
              .workspace-toggle {
                display: none !important;
              }
              .app-shell,
              .main-workspace,
              .preview-panel,
              .preview-card-area,
              .formula-card-viewport {
                display: block !important;
                width: auto !important;
                height: auto !important;
                max-height: none !important;
                overflow: visible !important;
                margin: 0 !important;
                padding: 0 !important;
              }
              #formula-card {
                transform: none !important;
                transform-origin: top left !important;
                margin: 0 !important;
              }
            """
        )
        count = page.evaluate("state.formulas.length")
        paths: list[Path] = []
        for index in range(count):
            name = page.evaluate(
                """async (index) => {
                  fillForm(state.formulas[index]);
                  renderPreview(state.formulas[index]);
                  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                  await Promise.all([...document.images].map((img) => img.complete ? true : new Promise((resolve) => {
                    img.addEventListener('load', resolve, { once: true });
                    img.addEventListener('error', resolve, { once: true });
                  })));
                  const card = document.querySelector('#formula-card');
                  card.style.transform = 'none';
                  document.querySelector('.formula-card-viewport').style.width = `${card.scrollWidth}px`;
                  document.querySelector('.formula-card-viewport').style.height = `${card.scrollHeight}px`;
                  return state.formulas[index].name || `formula-${index + 1}`;
                }""",
                index,
            )
            safe_name = "".join(ch for ch in name if ch not in '<>:"/\\|?*').strip() or f"formula-{index + 1}"
            path = out_dir / f"{index + 1:02d}_{safe_name}.png"
            page.locator("#formula-card").screenshot(path=str(path), animations="disabled")
            paths.append(path)
        context.close()
        browser.close()
        return paths


def combine_pdf(formulas: list[dict], card_paths: list[Path], pdf_path: Path) -> None:
    pages: list[Image.Image] = [cover_page(formulas), toc_page(formulas)]
    pages.extend(Image.open(path).convert("RGB") for path in card_paths)
    pages[0].save(pdf_path, "PDF", resolution=300.0, save_all=True, append_images=pages[1:])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, default=3.0, help="browser device scale factor for screenshots")
    args = parser.parse_args()

    formulas = load_formula_summary()
    if not formulas:
        raise RuntimeError(f"数据库中没有方剂：{DB_PATH}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    image_dir = OUT_DIR / f"方剂卡片合集_网页高清图_{stamp}"
    pdf_path = OUT_DIR / f"方剂卡片合集_网页预览高清版_现有{len(formulas)}首_{stamp}.pdf"

    process = start_server()
    try:
        card_paths = export_card_images(image_dir, args.scale)
        combine_pdf(formulas, card_paths, pdf_path)
    finally:
        stop_server(process)

    print(f"导出方剂：{len(formulas)} 首")
    print(f"截图倍率：{args.scale}x")
    print(f"高清卡片图目录：{image_dir}")
    print(f"PDF：{pdf_path}")


if __name__ == "__main__":
    main()
