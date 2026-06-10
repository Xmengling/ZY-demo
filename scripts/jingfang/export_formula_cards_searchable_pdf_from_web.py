#!/usr/bin/env python3
"""Export web preview cards as a searchable, copyable PDF.

Unlike the image-based exporter, this uses Chromium's PDF engine so the card
text remains real PDF text while the visual style still comes from the web app.
"""

from __future__ import annotations

import argparse
import html
import math
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import fitz
from playwright.sync_api import sync_playwright

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
ROWS_PER_TOC_PAGE = 18


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
      width: 1080px;
      height: 1501px;
      border: 5px solid #477cff;
      border-radius: 12px;
      background: white;
      box-shadow: inset 0 0 0 20px #f8fbff, inset 0 0 0 23px #d8e5ff;
      padding: 96px;
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
    td:nth-child(2) {{ width: 230px; font-weight: 900; }}
    td:nth-child(3) {{ width: 170px; color: #245ed6; }}
  </style>
  <title>{html.escape(title)}</title>
</head>
<body>{body}</body>
</html>"""


def footer_html(page_num: int, total_pages: int, prefix: str = "") -> str:
    label = f"第 {page_num} / {total_pages} 页"
    left = f"{prefix}　{FOOTER_TEXT}" if prefix else FOOTER_TEXT
    return f"""<div class="footer"><span>{html.escape(left)}</span><span>{html.escape(label)}</span></div>"""


def cover_html(formulas: list[dict], total_pages: int) -> str:
    preview_names = formulas[:24]
    names = "、".join(item["name"] for item in preview_names)
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


def toc_page_count(formulas: list[dict]) -> int:
    if not formulas:
        return 1
    return max(1, math.ceil(len(formulas) / ROWS_PER_TOC_PAGE))


def toc_html_pages(formulas: list[dict], total_pages: int) -> list[str]:
    pages: list[str] = []
    total_toc_pages = toc_page_count(formulas)
    for page_idx in range(total_toc_pages):
        start = page_idx * ROWS_PER_TOC_PAGE
        chunk = formulas[start : start + ROWS_PER_TOC_PAGE]
        rows = []
        for index, formula in enumerate(chunk, start + 1):
            cats = " / ".join(formula["categories"] or ["未归类"])
            points = "；".join(str(x) for x in formula["points"][:2])
            rows.append(
                "<tr>"
                f"<td>{index:02d}</td>"
                f"<td>{html.escape(formula['name'])}</td>"
                f"<td>{html.escape(cats)}</td>"
                f"<td>{html.escape(points)}</td>"
                "</tr>"
            )
        title_suffix = f"（{page_idx + 1}/{total_toc_pages}）" if total_toc_pages > 1 else ""
        page_num = 2 + page_idx
        body = f"""
    <main class="page">
      <h1>目录索引{html.escape(title_suffix)}</h1>
      <h2>按当前数据库更新时间排序</h2>
      <table>
        <thead><tr><th>序号</th><th>方剂</th><th>归类</th><th>辨证要点</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
      {footer_html(page_num, total_pages, "点击目录中的方剂名可跳转到对应卡片")}
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
    toc_pages: int = 1,
) -> list[Path]:
    first_card_page = toc_pages + 2
    probe = browser.new_page()
    probe.goto(URL, wait_until="domcontentloaded")
    probe.wait_for_function("typeof state !== 'undefined' && state.formulas && state.formulas.length > 0", timeout=60000)
    count = probe.evaluate("state.formulas.length")
    probe.close()

    paths: list[Path] = []
    for index in range(count):
        page = browser.new_page(viewport={"width": 1320, "height": 2600}, locale="zh-CN")
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_selector("#formula-card")
        page.wait_for_function("typeof state !== 'undefined' && state.formulas && state.formulas.length > 0", timeout=60000)
        result = page.evaluate(
            """async ({ index, footerText, totalPages, firstCardPage }) => {
              fillForm(state.formulas[index]);
              renderPreview(state.formulas[index]);
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
              fitSingleLine('#card-composition', 14);
              const style = document.createElement('style');
              style.textContent = `
                * {
                  -webkit-print-color-adjust: exact !important;
                  print-color-adjust: exact !important;
                }
                #formula-card {
                  overflow: visible !important;
                }
                .pdf-card-footer {
                  min-height: 58px;
                  display: flex;
                  align-items: center;
                  justify-content: space-between;
                  gap: 24px;
                  padding: 0 70px;
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
                #card-title,
                #card-composition {
                  white-space: nowrap !important;
                  overflow-wrap: normal !important;
                  word-break: keep-all !important;
                }
                @page { margin: 0; size: ${width}px ${height}px; }
              `;
              document.head.appendChild(style);
              const finalHeight = Math.ceil(Math.max(clone.scrollHeight, clone.offsetHeight, height));
              document.documentElement.style.height = `${finalHeight}px`;
              document.body.style.height = `${finalHeight}px`;
              style.textContent = style.textContent.replace(`size: ${width}px ${height}px`, `size: ${width}px ${finalHeight}px`);
              return { name: state.formulas[index].name || `formula-${index + 1}`, width, height: finalHeight };
            }""",
            {
                "index": index,
                "footerText": FOOTER_TEXT,
                "totalPages": total_pages,
                "firstCardPage": first_card_page,
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
    merged = fitz.open()
    for path in inputs:
        with fitz.open(str(path)) as doc:
            merged.insert_pdf(doc)
    merged.save(str(output_path), garbage=4, deflate=True)
    merged.close()


def add_toc_links(pdf_path: Path, formulas: list[dict], toc_pages: int = 1) -> int:
    """Add internal links from TOC formula names to their card pages."""
    if len(formulas) == 0:
        return 0

    tmp_path = pdf_path.with_suffix(".linked.pdf")
    link_count = 0
    with fitz.open(str(pdf_path)) as doc:
        if doc.page_count < toc_pages + 2:
            return 0
        for index, formula in enumerate(formulas, 1):
            name = str(formula.get("name") or "").strip()
            if not name:
                continue
            toc_page_idx = (index - 1) // ROWS_PER_TOC_PAGE
            toc_page = doc[1 + toc_page_idx]
            matches = toc_page.search_for(name)
            if not matches:
                continue
            rect = matches[0]
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
                    "page": toc_pages + index,
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
    toc_pages = toc_page_count(formulas)
    total_pages = len(formulas) + 1 + toc_pages

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_path = OUT_DIR / f"方剂卡片合集_网页预览可搜索版_现有{len(formulas)}首_{stamp}.pdf"
    process: subprocess.Popen | None = start_server()

    with tempfile.TemporaryDirectory(prefix="formula-searchable-pdf-") as tmp_name:
        tmp = Path(tmp_name)
        try:
            with sync_playwright() as p:
                browser = launch_browser(p)
                cover_path = tmp / "00_cover.pdf"
                toc_paths: list[Path] = []
                write_static_pdf(browser, cover_html(formulas, total_pages), cover_path)
                for page_idx, toc_source in enumerate(toc_html_pages(formulas, total_pages)):
                    toc_path = tmp / f"01_toc_{page_idx:02d}.pdf"
                    write_static_pdf(browser, toc_source, toc_path)
                    toc_paths.append(toc_path)
                card_paths = render_card_pdfs(browser, tmp, total_pages, toc_pages)
                browser.close()
            merge_pdfs([cover_path, *toc_paths, *card_paths], output_path)
            link_count = add_toc_links(output_path, formulas, toc_pages)
        finally:
            stop_server(process)

    with fitz.open(str(output_path)) as doc:
        first_card_page_idx = 1 + toc_pages
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
