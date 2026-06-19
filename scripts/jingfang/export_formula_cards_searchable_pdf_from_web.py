#!/usr/bin/env python3
"""Export web preview cards as a searchable, copyable PDF.

Unlike the image-based exporter, this uses Chromium's PDF engine so the card
text remains real PDF text while the visual style still comes from the web app.
"""

from __future__ import annotations

import argparse
import html
import math
import re
import sys
import tempfile
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _export_common import (  # noqa: E402
    OUT_DIR,
    URL,
    browser_executable,
    load_formula_summary,
    start_server,
    stop_server,
)
FOOTER_TEXT = "© 小小梦学中医｜学习资料，仅供中医学习交流，不作为诊疗处方依据。"
ROWS_PER_TOC_PAGE = 8
STATIC_PAGES_BEFORE_TOC = 2
CARD_FOOTER_HEIGHT = 74
TOC_CATEGORY_ORDER = ["表证", "里证", "半证", "水证", "血证", "气证"]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
HERB_DOCX = PROJECT_ROOT / "tcm_rag_demo/data/李冠杰经方病理辨证体系经方药物集萃（目录)(1).docx"
SOURCE_KEY = "经方病理辨证体系"
CANON_LABELS = {
    "表实",
    "表虚",
    "里实",
    "里虚",
    "里寒",
    "里热",
    "半热",
    "半虚",
    "水实",
    "水虚",
    "血实",
    "血虚",
    "气实",
    "气虚",
    "阴证",
}
LABEL_ALIASES = {
    "表证": "表证",
    "阴性": "阴证",
    "辅助阴性": "阴证",
    "血瘀": "血实",
    "瘀血": "血实",
    "津虚": "水虚",
}
HERB_ALIASES = {
    "炙甘草": "甘草",
    "甘草炙": "甘草",
    "生甘草": "甘草",
    "生姜切": "生姜",
    "姜": "生姜",
    "大枣擘": "大枣",
    "半夏洗": "半夏",
    "葶苈": "葶苈子",
    "白芍": "芍药",
    "赤芍": "芍药",
    "茵陈": "茵陈蒿",
    "地黄": "生地",
    "生地黄": "生地",
    "熟地黄": "生地",
    "桂": "桂枝",
    "牡蛎熬": "牡蛎",
    "栝蒌根": "天花粉",
    "瓜蒌根": "天花粉",
    "括楼根": "天花粉",
    "黄耆": "黄芪",
    "薏苡": "薏苡仁",
    "苡仁": "薏苡仁",
}
LABEL_TO_CATEGORY = {
    "表实": "表证",
    "表虚": "表证",
    "里实": "里证",
    "里虚": "里证",
    "里寒": "里证",
    "里热": "里证",
    "半热": "半证",
    "半虚": "半证",
    "水实": "水证",
    "水虚": "水证",
    "血实": "血证",
    "血虚": "血证",
    "气实": "气证",
    "气虚": "气证",
}


def html_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <style>
    @page {{ size: 1080px 1501px; margin: 0; }}
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      width: 1080px;
      height: 1501px;
      background: #f8fbff;
      color: #172033;
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", Arial, sans-serif;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}
    .page {{
      position: relative;
      width: 1080px;
      height: 1501px;
      border: 5px solid #477cff;
      border-radius: 12px;
      background: white;
      box-shadow: inset 0 0 0 20px #f8fbff, inset 0 0 0 23px #d8e5ff;
      padding: 96px 96px 140px;
    }}
    h1 {{ margin: 0; font-size: 58px; line-height: 1.18; }}
    h2 {{ margin: 14px 0 0; font-size: 34px; color: #245ed6; }}
    .line {{ height: 3px; background: #d8e5ff; margin: 58px 0 72px; }}
    .row {{ display: flex; align-items: center; gap: 36px; margin: 34px 0; }}
    .label {{
      width: 150px;
      min-height: 52px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 2px solid #477cff;
      border-radius: 8px;
      background: #edf4ff;
      font-size: 24px;
      font-weight: 800;
    }}
    .value {{ font-size: 28px; font-weight: 800; }}
    .section-title {{ margin-top: 70px; font-size: 34px; font-weight: 900; }}
    .names {{ margin-top: 28px; font-size: 20px; line-height: 1.8; color: #5a6880; }}
    .note {{
      margin-top: 84px;
      border: 2px dashed #477cff;
      border-radius: 8px;
      padding: 28px;
      font-size: 20px;
      line-height: 1.7;
    }}
    .usage-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 22px;
      margin-top: 42px;
    }}
    .usage-card {{
      min-height: 170px;
      border: 2px solid #d8e5ff;
      border-radius: 10px;
      padding: 22px 24px;
      background: linear-gradient(180deg, #fff 0%, #f8fbff 100%);
    }}
    .usage-card h3 {{
      margin: 0 0 12px;
      color: #245ed6;
      font-size: 25px;
      line-height: 1.25;
    }}
    .usage-card p {{
      margin: 0;
      color: #4d5e78;
      font-size: 18px;
      line-height: 1.65;
    }}
    .usage-list {{
      margin: 42px 0 0;
      padding: 28px 34px;
      border-left: 6px solid #477cff;
      border-radius: 10px;
      background: #f4f8ff;
      color: #33445f;
      font-size: 20px;
      line-height: 1.75;
    }}
    .footer {{
      position: absolute;
      left: 96px;
      right: 96px;
      bottom: 92px;
      display: flex;
      justify-content: space-between;
      gap: 24px;
      color: #5a6880;
      font-size: 16px;
    }}
    .footer span {{
      white-space: nowrap;
    }}
    .footer span:first-child {{
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 48px; font-size: 19px; }}
    th {{ color: #245ed6; text-align: left; border-bottom: 3px solid #d8e5ff; padding: 12px 8px; }}
    td {{ border-bottom: 1px solid #e8f0ff; padding: 16px 8px; vertical-align: top; line-height: 1.45; }}
    td:first-child {{ width: 70px; color: #245ed6; font-weight: 900; }}
    td:nth-child(2) {{ width: 220px; font-weight: 900; }}
    td:nth-child(3) {{ width: 250px; color: #245ed6; }}
    .toc-label {{ display: inline-block; white-space: nowrap; }}
    .toc-sep {{ color: #9aabc4; padding: 0 3px; }}
  </style>
  <title>{html.escape(title)}</title>
</head>
<body>{body}</body>
</html>"""


def footer_html(page_num: int, total_pages: int, prefix: str = "") -> str:
    label = f"第 {page_num} / {total_pages} 页"
    left = f"{prefix}　{FOOTER_TEXT}" if prefix else FOOTER_TEXT
    return f"""<div class="footer"><span>{html.escape(left)}</span><span>{html.escape(label)}</span></div>"""


def clean_plain_text(value: object) -> str:
    """Remove note markup that should not leak into static PDF pages."""
    text = str(value or "")
    replacements = (
        ("[[**", ""),
        ("**]]", ""),
        ("**[[", ""),
        ("]]**", ""),
        ("[[", ""),
        ("]]", ""),
        ("**", ""),
        ("### ", ""),
        ("## ", ""),
        ("`", ""),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return " ".join(text.split())


def normalize_label(label: str) -> str:
    label = clean_plain_text(label).strip(" ：:，,、。；;")
    return LABEL_ALIASES.get(label, label)


def normalize_herb(name: str) -> str:
    name = re.sub(r"[（）()一二三四五六七八九十半升两枚分各切洗炙熬去皮尖]+$", "", name.strip())
    name = name.strip(" ：:，,、。；;")
    return HERB_ALIASES.get(name, name)


def docx_paragraph_texts(path: Path) -> list[str]:
    if not path.exists():
        return []
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    paragraphs: list[str] = []
    for para_xml in re.findall(r"<w:p\b.*?</w:p>", xml, flags=re.S):
        parts = [
            html.unescape(re.sub(r"<.*?>", "", text_xml))
            for text_xml in re.findall(r"<w:t[^>]*>.*?</w:t>", para_xml, flags=re.S)
        ]
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def parse_herb_labels() -> dict[str, list[str]]:
    labels: dict[str, list[str]] = {}
    for text in docx_paragraph_texts(HERB_DOCX):
        if SOURCE_KEY not in text:
            continue
        raw = text.split("：", 1)[1] if "：" in text else text.split(":", 1)[-1]
        raw = raw.strip().rstrip("。.")
        if "：" in raw:
            herb, rest = raw.split("：", 1)
        elif "，" in raw:
            herb, rest = raw.split("，", 1)
        elif "," in raw:
            herb, rest = raw.split(",", 1)
        else:
            continue
        herb = normalize_herb(herb)
        parts = [normalize_label(x) for x in re.split(r"[\s、，,]+", rest) if x.strip()]
        dedup: list[str] = []
        for part in parts:
            if part and part not in dedup:
                dedup.append(part)
        if herb and dedup:
            labels[herb] = dedup
    return labels


def parse_composition_herbs(text: object) -> list[str]:
    raw = clean_plain_text(text)
    raw = re.sub(r"（.*?）|\(.*?\)", " ", raw)
    raw = raw.replace("，", " ").replace(",", " ").replace("、", " ")
    herbs: list[str] = []
    for herb in re.findall(r"([\u4e00-\u9fff]+)\s*\d+(?:\.\d+)?", raw):
        herb = normalize_herb(herb)
        if herb and len(herb) <= 8 and herb not in herbs:
            herbs.append(herb)
    return herbs


def formula_pathology_labels(formula: dict) -> list[str]:
    labels: list[str] = []
    for item in formula.get("pathology") or []:
        label = item.get("label") if isinstance(item, dict) else item
        label = normalize_label(str(label or ""))
        if label in CANON_LABELS and label not in labels:
            labels.append(label)
    return labels


def formula_pathology_display(formula: dict) -> str:
    labels = formula_pathology_labels(formula)
    if labels:
        return " / ".join(labels)
    categories = [clean_plain_text(x) for x in (formula.get("categories") or []) if clean_plain_text(x)]
    return " / ".join(categories) or "未归类"


def formula_pathology_html(formula: dict) -> str:
    raw = formula_pathology_display(formula)
    labels = [item.strip() for item in raw.split("/") if item.strip()]
    if not labels:
        labels = ["未归类"]
    return '<span class="toc-sep"> / </span>'.join(
        f'<span class="toc-label">{html.escape(label)}</span>' for label in labels
    )


def herb_roles_for_formula(herb: str, formula_labels: list[str], herb_labels: dict[str, list[str]]) -> list[str]:
    fset = set(formula_labels)
    hset = set(herb_labels.get(herb, []))
    roles: list[str] = []
    for label in formula_labels:
        if label in hset and label in CANON_LABELS:
            roles.append(label)
    if "表证" in hset:
        for label in ("表实", "表虚"):
            if label in fset and label not in roles:
                roles.append(label)
    if not roles and not formula_labels:
        roles = [label for label in hset if label in CANON_LABELS]
    return roles


def primary_toc_category(formula: dict, herb_labels: dict[str, list[str]]) -> str:
    label_votes: Counter[str] = Counter()
    for herb in parse_composition_herbs(formula.get("composition")):
        for role in herb_roles_for_formula(herb, formula_pathology_labels(formula), herb_labels):
            category = LABEL_TO_CATEGORY.get(role)
            if category:
                label_votes[category] += 1
    if label_votes:
        return sorted(label_votes, key=lambda c: (-label_votes[c], TOC_CATEGORY_ORDER.index(c)))[0]
    for category in formula.get("categories") or []:
        category = clean_plain_text(category)
        if category in TOC_CATEGORY_ORDER:
            return category
    return "未归类"


def toc_entries_by_category(formulas: list[dict]) -> list[dict]:
    raw_entries: list[dict] = []
    herb_labels = parse_herb_labels()
    for card_index, formula in enumerate(formulas, 1):
        category = primary_toc_category(formula, herb_labels)
        if category not in TOC_CATEGORY_ORDER:
            continue
        raw_entries.append(
            {
                "category": category,
                "card_index": card_index,
                "formula": formula,
            }
        )
    entries: list[dict] = []
    for category in TOC_CATEGORY_ORDER:
        entries.extend(item for item in raw_entries if item["category"] == category)
    for display_index, entry in enumerate(entries, 1):
        entry["display_index"] = display_index
    return entries


def cover_html(formulas: list[dict], total_pages: int) -> str:
    preview_names = formulas[:24]
    names = "、".join(clean_plain_text(item["name"]) for item in preview_names)
    if len(formulas) > len(preview_names):
        names = f"{names} 等共 {len(formulas)} 首"
    exported_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = f"""
    <main class="page">
      <h1>方剂梳理</h1>
      <h2>方剂卡片合集 PDF 可搜索版</h2>
      <div class="line"></div>
      <div class="row"><span class="label">当前导出</span><span class="value">{len(formulas)} 首</span></div>
      <div class="row"><span class="label">导出方式</span><span class="value">复用 Web 预览样式，文字可复制检索</span></div>
      <div class="row"><span class="label">资料定位</span><span class="value">中医方剂学习资料</span></div>
      <div class="section-title">本次包含</div>
      <div class="names">{html.escape(names or "暂无方剂")}</div>
      <div class="note">学习资料，仅供中医学习交流，不作为诊疗处方依据。具体用药请咨询专业医师。</div>
      {footer_html(1, total_pages, f"导出时间：{exported_at}")} 
    </main>"""
    return html_page("封面", body)


def usage_html(total_pages: int) -> str:
    body = f"""
    <main class="page">
      <h1>如何使用本资料</h1>
      <h2>先辨方证，再看方名；先抓主症，再看兼症</h2>
      <div class="line"></div>
      <div class="usage-grid">
        <section class="usage-card">
          <h3>1. 先看目录</h3>
          <p>目录按当前数据库顺序列出方剂、病理归类和辨证要点。点击目录中的方剂名，可跳转到对应卡片。</p>
        </section>
        <section class="usage-card">
          <h3>2. 抓辨证要点</h3>
          <p>每张卡片优先看病理标签、方剂名病理、辨证要点和临床症状，不要只按现代病名套方。</p>
        </section>
        <section class="usage-card">
          <h3>3. 对照类方</h3>
          <p>遇到相似主症时，重点看“对比”部分，分清表里寒热、虚实、水血气等边界。</p>
        </section>
        <section class="usage-card">
          <h3>4. 医案用于校验</h3>
          <p>医案后的十二字病理分析用于复盘症状如何落到病理标签，不作为直接处方依据。</p>
        </section>
      </div>
      <div class="usage-list">
        建议学习顺序：目录定位 → 方剂卡片 → 相关条文 → 胡希恕/李冠杰要点 → 类方对比 → 医案复盘。<br>
        本资料用于学习、复习和辨方训练；临床用药必须结合面诊、舌脉、剂量、禁忌和专业医师判断。
      </div>
      {footer_html(2, total_pages, "使用说明")}
    </main>"""
    return html_page("如何使用本资料", body)


def toc_page_count(formulas: list[dict] | None = None, entries: list[dict] | None = None) -> int:
    entries = entries if entries is not None else toc_entries_by_category(formulas or [])
    if not entries:
        return 1
    total = 0
    for category in TOC_CATEGORY_ORDER:
        count = sum(1 for item in entries if item["category"] == category)
        if count:
            total += math.ceil(count / ROWS_PER_TOC_PAGE)
    return max(1, total)


def toc_html_pages(formulas: list[dict], total_pages: int, entries: list[dict] | None = None) -> list[str]:
    pages: list[str] = []
    page_idx = 0
    entries = entries if entries is not None else toc_entries_by_category(formulas)
    for category in TOC_CATEGORY_ORDER:
        category_entries = [item for item in entries if item["category"] == category]
        if not category_entries:
            continue
        category_pages = math.ceil(len(category_entries) / ROWS_PER_TOC_PAGE)
        for category_page_idx in range(category_pages):
            start = category_page_idx * ROWS_PER_TOC_PAGE
            chunk = category_entries[start : start + ROWS_PER_TOC_PAGE]
            rows = []
            for item in chunk:
                formula = item["formula"]
                cats = formula_pathology_html(formula)
                points = "；".join(clean_plain_text(x) for x in formula["points"][:2])
                rows.append(
                    "<tr>"
                    f"<td>{item['display_index']:02d}</td>"
                    f"<td>{html.escape(clean_plain_text(formula['name']))}</td>"
                    f"<td>{cats}</td>"
                    f"<td>{html.escape(points)}</td>"
                    "</tr>"
                )
            title_suffix = (
                f"（{category_page_idx + 1}/{category_pages}）"
                if category_pages > 1
                else ""
            )
            page_num = STATIC_PAGES_BEFORE_TOC + 1 + page_idx
            body = f"""
    <main class="page">
      <h1>{html.escape(category)}目录{html.escape(title_suffix)}</h1>
      <table>
        <thead><tr><th>序号</th><th>方剂</th><th>归类</th><th>辨证要点</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
      {footer_html(page_num, total_pages, "点击目录中的方剂名可跳转到对应卡片")}
    </main>"""
            pages.append(html_page(f"{category}目录", body))
            page_idx += 1
    if not pages:
        body = f"""
    <main class="page">
      <h1>目录索引</h1>
      <h2>暂无可归入六类的方剂</h2>
      {footer_html(STATIC_PAGES_BEFORE_TOC + 1, total_pages, "点击目录中的方剂名可跳转到对应卡片")}
    </main>"""
        pages.append(html_page("目录索引", body))
    return pages


def launch_browser(playwright):
    executable_path = browser_executable()
    kwargs = {"headless": True}
    if executable_path:
        kwargs["executable_path"] = str(executable_path)
    return playwright.chromium.launch(**kwargs)


def write_static_pdf(browser, html_source: str, output_path: Path) -> None:
    page = browser.new_page(viewport={"width": 1080, "height": 1501}, locale="zh-CN")
    page.set_content(html_source, wait_until="load")
    page.pdf(
        path=str(output_path),
        width="1080px",
        height="1501px",
        margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        print_background=True,
        prefer_css_page_size=True,
    )
    page.close()


def render_card_pdfs(
    browser,
    output_dir: Path,
    total_pages: int,
    ordered_formulas: list[dict],
    toc_pages: int = 1,
) -> list[Path]:
    first_card_page = STATIC_PAGES_BEFORE_TOC + toc_pages + 1
    paths: list[Path] = []
    for index, ordered_formula in enumerate(ordered_formulas):
        page = browser.new_page(viewport={"width": 1320, "height": 2600}, locale="zh-CN")
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_selector("#formula-card")
        page.wait_for_function("typeof state !== 'undefined' && state.formulas && state.formulas.length > 0", timeout=60000)
        result = page.evaluate(
            """async ({ index, formulaId, formulaName, footerText, totalPages, firstCardPage, footerHeight }) => {
              const sourceIndex = state.formulas.findIndex((item) => {
                if (formulaId && item.id === formulaId) return true;
                return formulaName && item.name === formulaName;
              });
              if (sourceIndex < 0) throw new Error(`未找到方剂：${formulaName || formulaId}`);
              const formula = { ...state.formulas[sourceIndex] };
              const sourceCases = Array.isArray(formula.caseItems) && formula.caseItems.length
                ? formula.caseItems
                : (typeof splitCaseText === 'function' ? splitCaseText(formula.cases || '') : []);
              if (sourceCases.length) {
                formula.caseItems = [sourceCases[0]];
                formula.cases = sourceCases[0];
              }
              fillForm(formula);
              renderPreview(formula);
              await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
              await Promise.all([...document.images].map((img) => img.complete ? true : new Promise((resolve) => {
                img.addEventListener('load', resolve, { once: true });
                img.addEventListener('error', resolve, { once: true });
              })));
              const card = document.querySelector('#formula-card');
              card.style.transform = 'none';
              const width = Math.ceil(card.scrollWidth || card.offsetWidth || 1080);
              const height = Math.ceil(Math.max(card.scrollHeight, card.offsetHeight, 1501));
              const clone = card.cloneNode(true);
              document.body.innerHTML = '';
              document.body.appendChild(clone);
              const cleanTextNode = (node) => {
                node.nodeValue = String(node.nodeValue || '')
                  .replace(/\\[\\[\\*\\*/g, '')
                  .replace(/\\*\\*\\]\\]/g, '')
                  .replace(/\\*\\*\\[\\[/g, '')
                  .replace(/\\]\\]\\*\\*/g, '')
                  .replace(/\\[\\[/g, '')
                  .replace(/\\]\\]/g, '')
                  .replace(/\\*\\*/g, '')
                  .replace(/^\\s*#{1,6}\\s+/gm, '')
                  .replace(/`/g, '');
              };
              const walker = document.createTreeWalker(clone, NodeFilter.SHOW_TEXT);
              const textNodes = [];
              while (walker.nextNode()) textNodes.push(walker.currentNode);
              textNodes.forEach(cleanTextNode);
              document.documentElement.style.margin = '0';
              document.documentElement.style.padding = '0';
              document.documentElement.style.width = `${width}px`;
              document.documentElement.style.height = `${height}px`;
              document.documentElement.style.overflow = 'hidden';
              document.body.style.margin = '0';
              document.body.style.padding = '0';
              document.body.style.width = `${width}px`;
              document.body.style.height = `${height}px`;
              document.body.style.overflow = 'hidden';
              document.body.style.background = '#eef5ff';
              clone.style.position = 'absolute';
              clone.style.left = '0';
              clone.style.top = '0';
              clone.style.margin = '0';
              clone.style.transform = 'none';
              clone.style.transformOrigin = 'top left';
              clone.style.display = 'flex';
              clone.style.flexDirection = 'column';
              clone.style.overflow = 'visible';
              const footer = document.createElement('div');
              footer.className = 'pdf-card-footer';
              const footerLeft = document.createElement('span');
              footerLeft.textContent = footerText;
              const footerRight = document.createElement('span');
              footerRight.textContent = `第 ${index + firstCardPage} / ${totalPages} 页`;
              footer.append(footerLeft, footerRight);
              clone.appendChild(footer);
              const fitSingleLine = (selector, minSize = 14) => {
                const el = clone.querySelector(selector);
                if (!el) return;
                const parent = el.parentElement;
                if (!parent) return;
                el.style.whiteSpace = 'nowrap';
                el.style.overflowWrap = 'normal';
                el.style.wordBreak = 'keep-all';
                let size = parseFloat(getComputedStyle(el).fontSize) || 20;
                const maxWidth = Math.max(1, parent.clientWidth - 8);
                while (size > minSize && el.scrollWidth > maxWidth) {
                  size -= 1;
                  el.style.fontSize = `${size}px`;
                }
              };
              fitSingleLine('#card-title', 24);
              const style = document.createElement('style');
              style.textContent = `
                * {
                  -webkit-print-color-adjust: exact !important;
                  print-color-adjust: exact !important;
                }
                #formula-card {
                  overflow: visible !important;
                  display: flex !important;
                  flex-direction: column !important;
                }
                .card-body {
                  flex: 1 0 auto !important;
                }
                .pdf-card-footer {
                  flex: 0 0 auto;
                  min-height: ${footerHeight}px;
                  display: flex;
                  align-items: center;
                  justify-content: space-between;
                  gap: 24px;
                  margin: 18px 42px 0;
                  padding: 0 28px;
                  border-top: 2px solid #d8e5ff;
                  color: #5a6880;
                  font: 400 14px "Microsoft YaHei", "PingFang SC", "Noto Sans SC", Arial, sans-serif;
                  white-space: nowrap;
                }
                .pdf-card-footer span:first-child {
                  min-width: 0;
                  overflow: hidden;
                  text-overflow: ellipsis;
                }
                #card-title {
                  white-space: nowrap !important;
                  overflow-wrap: normal !important;
                  word-break: keep-all !important;
                }
                #card-composition {
                  white-space: normal !important;
                  overflow-wrap: anywhere !important;
                  word-break: break-word !important;
                  line-height: 1.45 !important;
                }
                @page { margin: 0; size: ${width}px ${height}px; }
              `;
              document.head.appendChild(style);
              const finalHeight = Math.ceil(Math.max(clone.scrollHeight, clone.offsetHeight, height));
              document.documentElement.style.height = `${finalHeight}px`;
              document.body.style.height = `${finalHeight}px`;
              style.textContent = style.textContent.replace(`size: ${width}px ${height}px`, `size: ${width}px ${finalHeight}px`);
              return { name: formula.name || `formula-${index + 1}`, width, height: finalHeight };
            }""",
            {
                "index": index,
                "formulaId": ordered_formula.get("id"),
                "formulaName": ordered_formula.get("name"),
                "footerText": FOOTER_TEXT,
                "totalPages": total_pages,
                "firstCardPage": first_card_page,
                "footerHeight": CARD_FOOTER_HEIGHT,
            },
        )
        safe_name = "".join(ch for ch in result["name"] if ch not in '<>:"/\\|?*').strip() or f"formula-{index + 1}"
        path = output_dir / f"{index + 1:02d}_{safe_name}.pdf"
        page.pdf(
            path=str(path),
            width=f"{result['width']}px",
            height=f"{result['height']}px",
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            print_background=True,
            prefer_css_page_size=True,
        )
        paths.append(path)
        page.close()
    return paths


def merge_pdfs(inputs: list[Path], output_path: Path) -> None:
    import fitz

    merged = fitz.open()
    for path in inputs:
        with fitz.open(str(path)) as doc:
            merged.insert_pdf(doc)
    merged.save(str(output_path), garbage=4, deflate=True)
    merged.close()


def add_toc_links(pdf_path: Path, formulas: list[dict], toc_pages: int = 1, entries: list[dict] | None = None) -> int:
    """Add internal links from TOC formula names to their card pages."""
    import fitz

    if len(formulas) == 0:
        return 0

    tmp_path = pdf_path.with_suffix(".linked.pdf")
    link_count = 0
    toc_start_page_idx = STATIC_PAGES_BEFORE_TOC
    first_card_page_idx = STATIC_PAGES_BEFORE_TOC + toc_pages
    toc_link_entries: list[dict] = []
    current_toc_page = 0
    entries = entries if entries is not None else toc_entries_by_category(formulas)
    for category in TOC_CATEGORY_ORDER:
        category_entries = [item for item in entries if item["category"] == category]
        for offset, item in enumerate(category_entries):
            toc_link_entries.append(
                {
                    "toc_page_idx": current_toc_page + offset // ROWS_PER_TOC_PAGE,
                    "display_index": item["display_index"],
                    "name": clean_plain_text(item["formula"].get("name") or "").strip(),
                }
            )
        if category_entries:
            current_toc_page += math.ceil(len(category_entries) / ROWS_PER_TOC_PAGE)
    with fitz.open(str(pdf_path)) as doc:
        if doc.page_count < first_card_page_idx + 1:
            return 0
        used_rects: dict[int, list[fitz.Rect]] = {}
        for item in toc_link_entries:
            name = item["name"]
            if not name:
                continue
            toc_page = doc[toc_start_page_idx + item["toc_page_idx"]]
            matches = toc_page.search_for(name)
            if not matches:
                matches = toc_page.search_for(f"{item['display_index']:02d}")
            if not matches:
                continue
            page_used = used_rects.setdefault(toc_page.number, [])
            rect = next(
                (
                    match
                    for match in matches
                    if not any(match.intersects(existing) for existing in page_used)
                ),
                matches[0],
            )
            page_used.append(rect)
            click_rect = fitz.Rect(
                max(0, rect.x0 - 8),
                max(0, rect.y0 - 8),
                min(toc_page.rect.width, toc_page.rect.width - 72),
                min(toc_page.rect.height, rect.y1 + 8),
            )
            toc_page.insert_link(
                {
                    "kind": fitz.LINK_GOTO,
                    "from": click_rect,
                    "page": first_card_page_idx + item["display_index"] - 1,
                    "to": fitz.Point(0, 0),
                }
            )
            link_count += 1
        doc.save(str(tmp_path), garbage=4, deflate=True)
    tmp_path.replace(pdf_path)
    return link_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()

    formulas = load_formula_summary()
    if not formulas:
        raise RuntimeError("数据库中没有方剂")
    toc_entries = toc_entries_by_category(formulas)
    ordered_formulas = [entry["formula"] for entry in toc_entries]
    toc_pages = toc_page_count(entries=toc_entries)
    total_pages = len(formulas) + STATIC_PAGES_BEFORE_TOC + toc_pages

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_path = OUT_DIR / f"方剂卡片合集_网页预览可搜索版_现有{len(formulas)}首_{stamp}.pdf"
    process: subprocess.Popen | None = start_server()

    with tempfile.TemporaryDirectory(prefix="formula-searchable-pdf-") as tmp_name:
        tmp = Path(tmp_name)
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = launch_browser(p)
                cover_path = tmp / "00_cover.pdf"
                usage_path = tmp / "01_usage.pdf"
                toc_paths: list[Path] = []
                write_static_pdf(browser, cover_html(formulas, total_pages), cover_path)
                write_static_pdf(browser, usage_html(total_pages), usage_path)
                for page_idx, toc_source in enumerate(toc_html_pages(formulas, total_pages, toc_entries)):
                    toc_path = tmp / f"02_toc_{page_idx:02d}.pdf"
                    write_static_pdf(browser, toc_source, toc_path)
                    toc_paths.append(toc_path)
                card_paths = render_card_pdfs(browser, tmp, total_pages, ordered_formulas, toc_pages)
                browser.close()
            merge_pdfs([cover_path, usage_path, *toc_paths, *card_paths], output_path)
            link_count = add_toc_links(output_path, formulas, toc_pages, toc_entries)
        finally:
            stop_server(process)

    import fitz

    with fitz.open(str(output_path)) as doc:
        first_card_page_idx = STATIC_PAGES_BEFORE_TOC + toc_pages
        sample_text = (
            doc[first_card_page_idx].get_text().strip()[:80]
            if doc.page_count > first_card_page_idx
            else ""
        )
        print(f"导出方剂：{len(formulas)} 首")
        print(f"PDF：{output_path}")
        print(f"页数：{doc.page_count}")
        print(f"目录链接：{link_count} 个")
        print(f"文本层示例：{sample_text}")


if __name__ == "__main__":
    main()
