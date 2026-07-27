#!/usr/bin/env python3
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "covers" / "shanghan_liang_grams_douyin_1242x1656.png"
BASE = ROOT / "output" / "covers" / "guizhi_family_tcm_full_bleed_1242x1656.png"
AVATAR = ROOT / "avatar.jpg"
FONT_BOLD = "/System/Library/Fonts/STHeiti Medium.ttc"
FONT_REG = "/System/Library/Fonts/STHeiti Light.ttc"


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, min_size: int = 40) -> ImageFont.FreeTypeFont:
    size = start_size
    while size >= min_size:
        fnt = font(size)
        if draw.textbbox((0, 0), text, font=fnt, stroke_width=8)[2] <= max_width:
            return fnt
        size -= 4
    return font(min_size)


def rounded_rect(draw: ImageDraw.ImageDraw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_centered_text(draw, xy, text, fnt, fill, stroke_fill, stroke_width):
    x, y = xy
    box = draw.textbbox((0, 0), text, font=fnt, stroke_width=stroke_width)
    draw.text((x - (box[2] - box[0]) / 2, y), text, font=fnt, fill=fill, stroke_fill=stroke_fill, stroke_width=stroke_width)


def main() -> None:
    w, h = 1242, 1656
    random.seed(7)
    bg = Image.new("RGB", (w, h), (246, 229, 180))

    canvas = Image.new("RGBA", (w, h))
    canvas.paste(bg.convert("RGBA"), (0, 0))
    draw = ImageDraw.Draw(canvas)

    # Warm paper wash and subtle ink texture.
    for y in range(h):
        shade = int(20 * math.sin(y / 95) + 10 * math.sin(y / 37))
        draw.line([(0, y), (w, y)], fill=(246 + shade // 5, 229 + shade // 6, 180 + shade // 7, 255))
    for _ in range(1800):
        x = random.randrange(w)
        y = random.randrange(h)
        a = random.randrange(8, 24)
        color = (145, 97, 42, a) if random.random() < 0.55 else (255, 247, 220, a)
        draw.point((x, y), fill=color)

    # Ink mountains and bamboo silhouettes.
    for ridge, y0 in enumerate((205, 260, 1140)):
        pts = []
        for x in range(-80, w + 100, 95):
            peak = y0 - random.randint(30, 115)
            pts.extend([(x, y0 + random.randint(15, 50)), (x + 48, peak)])
        pts.append((w + 100, h if y0 > 1000 else y0 + 190))
        pts.append((-100, h if y0 > 1000 else y0 + 190))
        draw.polygon(pts, fill=(72, 67, 52, 28 if ridge < 2 else 34))
    for x in (34, 1180):
        for offset in range(0, 250, 42):
            draw.line((x, 0 + offset, x + (55 if x < 100 else -55), 135 + offset), fill=(36, 65, 39, 85), width=5)
            leaf_x = x + 75 if x < 100 else x - 75
            draw.ellipse((min(x - 8, leaf_x), 55 + offset, max(x - 8, leaf_x), 77 + offset), fill=(36, 65, 39, 45))

    # Header brush stroke.
    draw.rounded_rectangle((70, 78, 490, 178), radius=18, fill=(148, 22, 18, 238))
    draw.text((118, 97), "经方剂量", font=font(52), fill=(255, 247, 231), stroke_width=3, stroke_fill=(72, 18, 12))
    draw.text((525, 108), "一两到底换几克？", font=font(40), fill=(68, 37, 16), stroke_width=2, stroke_fill=(255, 246, 214))

    # Main title card.
    rounded_rect(draw, (58, 245, 1186, 885), 42, (252, 235, 186, 232), (94, 54, 23, 210), 5)
    rounded_rect(draw, (86, 275, 1158, 855), 30, (255, 246, 215, 180), (177, 28, 22, 150), 3)
    draw.line((130, 815, 1110, 815), fill=(140, 35, 24, 160), width=6)

    title_lines = ["《伤寒论》", "一两到底", "多少克？"]
    sizes = [142, 166, 164]
    ys = [298, 465, 635]
    for line, size, y in zip(title_lines, sizes, ys):
        fnt = fit_text(draw, line, 1020, size)
        draw_centered_text(draw, (w / 2, y), line, fnt, (255, 198, 42), (18, 18, 15), 10)
        draw_centered_text(draw, (w / 2, y), line, fnt, (255, 207, 54), (255, 250, 230), 3)

    # Lower explanatory cards.
    card_y = 940
    items = [("古方一两", "不是现代 50 克"), ("剂量换算", "先看汉制与煎服法"), ("桂枝汤疑问", "真要一次喝完吗？")]
    for idx, (top, bottom) in enumerate(items):
        x0 = 65 + idx * 387
        x1 = x0 + 340
        rounded_rect(draw, (x0, card_y, x1, card_y + 180), 24, (114, 22, 17, 230), (246, 211, 129, 230), 4)
        draw.text((x0 + 34, card_y + 24), top, font=font(44), fill=(255, 231, 135), stroke_width=2, stroke_fill=(43, 17, 10))
        draw.text((x0 + 34, card_y + 96), bottom, font=font(30), fill=(255, 248, 230), stroke_width=1, stroke_fill=(43, 17, 10))

    # Ancient book / scale accent.
    rounded_rect(draw, (76, 1190, 620, 1500), 30, (239, 211, 154, 225), (91, 53, 20, 210), 4)
    draw.text((118, 1228), "古籍原文", font=font(50), fill=(93, 40, 18), stroke_width=2, stroke_fill=(255, 241, 203))
    for i, line in enumerate(["桂枝三两", "芍药三两", "甘草二两", "生姜三两", "大枣十二枚"]):
        draw.text((130, 1308 + i * 36), line, font=font(28, False), fill=(62, 43, 24))
    draw.ellipse((430, 1260, 565, 1395), outline=(127, 83, 28), width=8)
    draw.line((498, 1198, 498, 1265), fill=(127, 83, 28), width=8)
    draw.line((440, 1395, 558, 1395), fill=(127, 83, 28), width=8)

    # Avatar sticker.
    if AVATAR.exists():
        av = Image.open(AVATAR).convert("RGB")
        side = min(av.size)
        left = (av.width - side) // 2
        top = (av.height - side) // 2
        av = av.crop((left, top, left + side, top + side)).resize((310, 310), Image.Resampling.LANCZOS)
        mask = Image.new("L", (310, 310), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse((0, 0, 309, 309), fill=255)
        draw.ellipse((812, 1166, 1152, 1506), fill=(255, 248, 226), outline=(148, 22, 18), width=10)
        av_rgba = av.convert("RGBA")
        av_rgba.putalpha(mask)
        canvas.alpha_composite(av_rgba, (827, 1181))
        draw.text((800, 1130), "讲清这一两", font=font(44), fill=(255, 236, 145), stroke_width=5, stroke_fill=(105, 20, 16))

    # Cinnabar seal and bottom strip.
    rounded_rect(draw, (88, 1532, 1154, 1618), 22, (255, 248, 223, 230), (128, 35, 22, 200), 4)
    draw.text((155, 1552), "避开剂量误区｜看懂经方原意", font=font(42), fill=(102, 34, 20), stroke_width=1, stroke_fill=(255, 242, 205))
    draw.rectangle((1035, 94, 1148, 210), outline=(157, 23, 21), width=7)
    draw.text((1058, 113), "伤寒", font=font(38), fill=(157, 23, 21))
    draw.text((1058, 158), "论", font=font(38), fill=(157, 23, 21))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(OUT, quality=96)
    print(f"saved {OUT} {w}x{h}")


if __name__ == "__main__":
    main()
