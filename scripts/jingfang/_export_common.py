# -*- coding: utf-8 -*-
"""方剂卡片 PDF 导出：复用 ai-medical-consultant 网页预览。"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable

import urllib.error
import urllib.request

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = Path(__file__).resolve().parent

# ZY-demo 源数据
DB_PATH = PROJECT_ROOT / "ai-medical-consultant/backend/data/jingfang.sqlite3"
HERB_DIR = PROJECT_ROOT / "ai-medical-consultant/backend/data/herbs"
HERB_DIR_DEMO = HERB_DIR

EXPORT_SERVER = SCRIPTS_DIR / "export_web_server.py"
EXPORT_PORT = int(os.getenv("JINGFANG_EXPORT_PORT", "15188"))
URL = f"http://127.0.0.1:{EXPORT_PORT}"

OUT_DIR = PROJECT_ROOT / "docs/exports/formula_cards"


def load_formula_summary() -> list[dict]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"未找到数据库：{DB_PATH}")
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "select payload, updated_at from formulas order by updated_at desc"
        ).fetchall()
    formulas: list[dict] = []
    for payload, updated_at in rows:
        item = json.loads(payload)
        formulas.append(
            {
                "id": item.get("id"),
                "name": item.get("name") or "未命名方剂",
                "categories": item.get("categories") or [],
                "points": item.get("diagnosisPoints") or [],
                "updated_at": updated_at,
            }
        )
    return formulas


def load_formulas() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "select payload, updated_at from formulas order by updated_at desc"
        ).fetchall()
    formulas: list[dict] = []
    for payload, updated_at in rows:
        item = json.loads(payload)
        item["_updated_at"] = updated_at
        formulas.append(item)
    return formulas


def url_ready(url: str, timeout: float = 1.0) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ZY-demo-export/1.0"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=timeout) as response:
            return response.status == 200
    except urllib.error.HTTPError as exc:
        return exc.code == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def wait_for_url(url: str, timeout: float = 30.0, processes: Iterable[subprocess.Popen] | None = None) -> None:
    start = time.time()
    while time.time() - start < timeout:
        if processes:
            for proc in processes:
                if proc.poll() is not None:
                    raise RuntimeError(f"方剂导出 Web 服务启动失败：{proc.args}")
        if url_ready(url, timeout=1.5):
            return
        time.sleep(0.25)
    raise RuntimeError(f"等待方剂导出 Web 服务超时：{url}")


def start_server() -> subprocess.Popen | None:
    """启动或复用本地方剂导出网页（export_formula_cards_*_from_web 所需）。"""
    if not EXPORT_SERVER.exists():
        raise FileNotFoundError(f"未找到导出网页服务：{EXPORT_SERVER}")
    if url_ready(URL):
        return None

    env = os.environ.copy()
    env.setdefault("JINGFANG_EXPORT_PORT", str(EXPORT_PORT))
    env.setdefault("NO_PROXY", "127.0.0.1,localhost")
    backend_root = PROJECT_ROOT / "ai-medical-consultant/backend"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(backend_root), env.get("PYTHONPATH", "")]
    ).strip(os.pathsep)

    kwargs: dict = {
        "cwd": str(PROJECT_ROOT),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.PIPE,
        "env": env,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    process = subprocess.Popen([sys.executable, str(EXPORT_SERVER)], **kwargs)
    deadline = time.time() + 30
    while time.time() < deadline:
        if url_ready(URL):
            if process.poll() is not None:
                return None
            return process
        if process.poll() is not None:
            stderr = (process.stderr.read() or b"").decode("utf-8", errors="replace").strip()
            detail = stderr or "进程已退出"
            raise RuntimeError(
                "方剂导出 Web 服务未能启动；请手动运行："
                f"python {EXPORT_SERVER}\n{detail}"
            )
        time.sleep(0.25)
    process.terminate()
    raise RuntimeError(f"等待方剂导出 Web 服务超时：{URL}")


def stop_server(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


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


def truetype_font(size: int, bold: bool = False):
    from PIL import ImageFont

    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
    ]
    for path in candidates:
        p = Path(path)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except OSError:
                continue
    return ImageFont.load_default()
