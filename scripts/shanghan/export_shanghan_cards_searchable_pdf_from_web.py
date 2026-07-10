#!/usr/bin/env python3
"""Export Shanghan article web preview cards as a searchable PDF."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "ai-medical-consultant/backend"
WEB_DIR = PROJECT_ROOT / "ai-medical-consultant/frontend/public/shanghan"
OUT_DIR = PROJECT_ROOT / "docs/exports/shanghan_cards"
HOST = os.getenv("SHANGHAN_EXPORT_HOST", "127.0.0.1")
PORT = int(os.getenv("SHANGHAN_EXPORT_PORT", "15189"))
URL = f"http://{HOST}:{PORT}"
LEVELS = ["一级", "二级", "三级"]
FOOTER_TEXT = "© 小小梦学中医｜学习资料，仅供中医学习交流，不作为诊疗依据。"
CARD_FOOTER_HEIGHT = 74

sys.path.insert(0, str(BACKEND_ROOT))
from app.services import shanghan_store  # noqa: E402


def article_number(article: dict) -> int | None:
    raw = str(article.get("number") or article.get("articleNo") or "").strip()
    try:
        return int(raw)
    except ValueError:
        return None


def parse_levels(raw: str | None) -> set[str]:
    if not raw:
        return set(LEVELS)
    levels = {item.strip() for item in raw.split(",") if item.strip()}
    unknown = levels - set(LEVELS)
    if unknown:
        raise ValueError("不支持的条文等级：" + "、".join(sorted(unknown)))
    if not levels:
        raise ValueError("请至少选择一个条文等级")
    return levels


def selected_articles(levels: set[str], start: int | None, end: int | None) -> list[dict]:
    articles = []
    for article in shanghan_store.list_articles():
        if (article.get("level") or "一级") not in levels:
            continue
        number = article_number(article)
        if start is not None and (number is None or number < start):
            continue
        if end is not None and (number is None or number > end):
            continue
        articles.append(article)
    return articles


class Handler(BaseHTTPRequestHandler):
    def send_json(self, body: object, status: int = 200) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        if path.suffix.lower() in {".html", ".css", ".js"}:
            self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path in ("/api/v1/shanghan", "/api/shanghan"):
            self.send_json({"articles": shanghan_store.list_articles()})
            return
        if path in ("/", "/index.html"):
            self.send_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
            return
        target = (WEB_DIR / path.lstrip("/")).resolve()
        if WEB_DIR.resolve() in target.parents and target.exists():
            types = {
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
                ".svg": "image/svg+xml",
            }
            self.send_file(target, types.get(target.suffix.lower(), mimetypes.guess_type(target.name)[0] or "application/octet-stream"))
            return
        self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        return


def start_server() -> ThreadingHTTPServer:
    shanghan_store.ensure_ready()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    return server


def browser_executable() -> Path | None:
    candidates = [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
        Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def launch_browser(playwright):
    executable_path = browser_executable()
    kwargs = {"headless": True}
    if executable_path:
        kwargs["executable_path"] = str(executable_path)
    return playwright.chromium.launch(**kwargs)


def write_cover_pdf(browser, articles: list[dict], output_path: Path, total_pages: int) -> None:
    names = "、".join(f"第{article.get('number') or ''}条" for article in articles[:36])
    if len(articles) > 36:
        names = f"{names} 等共 {len(articles)} 条"
    exported_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    html_source = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <style>
    @page {{ size: 1080px 1501px; margin: 0; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      width: 1080px;
      height: 1501px;
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", Arial, sans-serif;
      background: #f8fbff;
      color: #172033;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}
    .page {{
      position: relative;
      width: 1080px;
      height: 1501px;
      border: 5px solid #477cff;
      border-radius: 12px;
      background: #fff;
      box-shadow: inset 0 0 0 20px #f8fbff, inset 0 0 0 23px #d8e5ff;
      padding: 96px 96px 140px;
    }}
    .page::after {{
      content: "小小梦学中医";
      position: absolute;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%) rotate(-30deg);
      color: rgba(36, 94, 214, .055);
      font-size: 76px;
      font-weight: 900;
      white-space: nowrap;
      pointer-events: none;
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
  </style>
</head>
<body>
  <main class="page">
    <h1>伤寒论条文解读</h1>
    <h2>条文卡片合集 PDF</h2>
    <div class="line"></div>
    <div class="row"><span class="label">条文数量</span><span class="value">{len(articles)} 条</span></div>
    <div class="row"><span class="label">资料定位</span><span class="value">中医条文学习资料</span></div>
    <div class="section-title">本次包含</div>
    <div class="names">{names}</div>
    <div class="footer"><span>导出时间：{exported_at}　{FOOTER_TEXT}</span><span>第 1 / {total_pages} 页</span></div>
  </main>
</body>
</html>"""
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


def render_card_pdfs(browser, output_dir: Path, articles: list[dict], total_pages: int) -> list[Path]:
    paths: list[Path] = []
    for index, article in enumerate(articles):
        page = browser.new_page(viewport={"width": 1320, "height": 2600}, locale="zh-CN")
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_selector("#article-card")
        page.wait_for_function("typeof state !== 'undefined' && state.articles && state.articles.length > 0", timeout=60000)
        result = page.evaluate(
            """async ({ articleId, articleNumber, index, totalPages, footerHeight, footerText }) => {
              const sourceIndex = state.articles.findIndex((item) => {
                if (articleId && item.id === articleId) return true;
                return articleNumber && String(item.number || item.articleNo || '') === String(articleNumber);
              });
              if (sourceIndex < 0) throw new Error(`未找到条文：${articleNumber || articleId}`);
              const article = { ...state.articles[sourceIndex] };
              fillForm(article);
              renderPreview(article);
              await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
              layoutSummaryMindMapLines();
              fitArticleCardPreview();
              await new Promise((resolve) => requestAnimationFrame(resolve));
              await Promise.all([...document.images].map((img) => img.complete ? true : new Promise((resolve) => {
                img.addEventListener('load', resolve, { once: true });
                img.addEventListener('error', resolve, { once: true });
              })));
              const card = document.querySelector('#article-card');
              card.style.transform = 'none';
              const width = Math.ceil(card.scrollWidth || card.offsetWidth || 1080);
              const height = Math.ceil(Math.max(card.scrollHeight, card.offsetHeight, 1501));
              const clone = card.cloneNode(true);
              clone.querySelector('.card-footer')?.remove();
              document.body.innerHTML = '';
              document.body.appendChild(clone);
              const cleanTextNode = (node) => {
                node.nodeValue = String(node.nodeValue || '')
                  .replace(/\\[\\[\\*\\*/g, '')
                  .replace(/\\*\\*\\]\\]/g, '')
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
              const watermark = document.createElement('div');
              watermark.className = 'pdf-watermark';
              watermark.textContent = '小小梦学中医';
              clone.appendChild(watermark);
              const footer = document.createElement('div');
              footer.className = 'pdf-card-footer';
              const footerLeft = document.createElement('span');
              footerLeft.textContent = footerText;
              const footerRight = document.createElement('span');
              footerRight.textContent = `第 ${index + 2} / ${totalPages} 页`;
              footer.append(footerLeft, footerRight);
              clone.appendChild(footer);
              const style = document.createElement('style');
              style.textContent = `
                * {
                  -webkit-print-color-adjust: exact !important;
                  print-color-adjust: exact !important;
                }
                #article-card {
                  overflow: visible !important;
                  display: flex !important;
                  flex-direction: column !important;
                }
                .card-body {
                  flex: 1 0 auto !important;
                }
                .pdf-watermark {
                  position: absolute;
                  left: 50%;
                  top: 50%;
                  transform: translate(-50%, -50%) rotate(-30deg);
                  color: rgba(36, 94, 214, .055);
                  font: 900 76px "Microsoft YaHei", "PingFang SC", "Noto Sans SC", Arial, sans-serif;
                  white-space: nowrap;
                  pointer-events: none;
                  z-index: 99;
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
                @page { margin: 0; size: ${width}px ${height}px; }
              `;
              document.head.appendChild(style);
              const finalHeight = Math.ceil(Math.max(clone.scrollHeight, clone.offsetHeight, height));
              document.documentElement.style.height = `${finalHeight}px`;
              document.body.style.height = `${finalHeight}px`;
              style.textContent = style.textContent.replace(`size: ${width}px ${height}px`, `size: ${width}px ${finalHeight}px`);
              return { name: article.number ? `第${article.number}条` : (article.id || `article-${index + 1}`), width, height: finalHeight };
            }""",
            {
                "articleId": article.get("id"),
                "articleNumber": article.get("number") or article.get("articleNo"),
                "index": index,
                "totalPages": total_pages,
                "footerHeight": CARD_FOOTER_HEIGHT,
                "footerText": FOOTER_TEXT,
            },
        )
        safe_name = "".join(ch for ch in result["name"] if ch not in '<>:"/\\|?*').strip() or f"article-{index + 1}"
        path = output_dir / f"{index + 1:03d}_{safe_name}.pdf"
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--levels", default=",".join(LEVELS), help="逗号分隔的条文等级")
    parser.add_argument("--start", type=int, default=None, help="起始条文序号")
    parser.add_argument("--end", type=int, default=None, help="结束条文序号")
    args = parser.parse_args()

    if args.start is not None and args.end is not None and args.start > args.end:
        raise ValueError("起始条文不能大于结束条文")
    levels = parse_levels(args.levels)
    articles = selected_articles(levels, args.start, args.end)
    if not articles:
        raise RuntimeError("没有符合筛选条件的条文")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    level_label = "".join(level.replace("级", "") for level in LEVELS if level in levels)
    range_label = ""
    if args.start is not None or args.end is not None:
        range_label = f"_{args.start or '起'}-{args.end or '止'}"
    output_path = OUT_DIR / f"伤寒论条文卡片合集_{level_label or '全部'}{range_label}_共{len(articles)}条_{stamp}.pdf"

    server = start_server()
    import threading

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)
    try:
        with tempfile.TemporaryDirectory(prefix="shanghan-searchable-pdf-") as tmp_name:
            tmp = Path(tmp_name)
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = launch_browser(p)
                cover_path = tmp / "00_cover.pdf"
                total_pages = len(articles) + 1
                write_cover_pdf(browser, articles, cover_path, total_pages)
                card_paths = render_card_pdfs(browser, tmp, articles, total_pages)
                browser.close()
            merge_pdfs([cover_path, *card_paths], output_path)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    import fitz

    with fitz.open(str(output_path)) as doc:
        sample_text = doc[1].get_text().strip()[:80] if doc.page_count > 1 else ""
        print(f"导出条文：{len(articles)} 条")
        print(f"PDF：{output_path}")
        print(f"页数：{doc.page_count}")
        print(f"文本层示例：{sample_text}")


if __name__ == "__main__":
    main()
