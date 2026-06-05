# -*- coding: utf-8 -*-
"""方剂卡片 PDF 导出：优先复用 ZY-Study 网页预览（:5188），与线上一致。"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable

import urllib.error
import urllib.request

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ZY_STUDY_ROOT = Path(os.getenv("ZY_STUDY_ROOT", "/Users/qingling/梦玲/ZY-Study"))

# ZY-demo 源数据
DB_PATH = PROJECT_ROOT / "ai-medical-consultant/backend/data/jingfang.sqlite3"
HERB_DIR_DEMO = PROJECT_ROOT / "ai-medical-consultant/backend/data/herbs"

# ZY-Study 网页导出栈（与 scripts/export_formula_cards_*_from_web.py 配套）
ZY_DB_PATH = ZY_STUDY_ROOT / "web/db/jingfang.sqlite3"
ZY_HERB_DIR = ZY_STUDY_ROOT / "img/伤寒金匮方剂思维导图"
ZY_SERVER = ZY_STUDY_ROOT / "web/server.py"
URL = "http://127.0.0.1:5188"

OUT_DIR = PROJECT_ROOT / "docs/exports/formula_cards"


def sync_to_zy_study() -> None:
    """把 ZY-demo 数据库与中药图同步到 ZY-Study，供 :5188 网页导出使用。"""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"未找到数据库：{DB_PATH}")
    ZY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB_PATH, ZY_DB_PATH)
    if HERB_DIR_DEMO.exists():
        ZY_HERB_DIR.mkdir(parents=True, exist_ok=True)
        for item in HERB_DIR_DEMO.iterdir():
            if item.is_file():
                target = ZY_HERB_DIR / item.name
                if not target.exists():
                    shutil.copy2(item, target)


def load_formula_summary() -> list[dict]:
    sync_to_zy_study()
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
                    raise RuntimeError(f"ZY-Study Web 服务启动失败：{proc.args}")
        if url_ready(url, timeout=1.5):
            return
        time.sleep(0.25)
    raise RuntimeError(f"等待 ZY-Study Web 服务超时：{url}")


def start_server() -> subprocess.Popen | None:
    """启动或复用 ZY-Study :5188 网页（export_formula_cards_*_from_web 所需）。"""
    if not ZY_SERVER.exists():
        raise FileNotFoundError(f"未找到 ZY-Study 网页服务：{ZY_SERVER}")
    sync_to_zy_study()
    if url_ready(URL):
        return None
    kwargs: dict = {
        "cwd": str(ZY_STUDY_ROOT),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    process = subprocess.Popen([sys.executable, str(ZY_SERVER)], **kwargs)
    deadline = time.time() + 30
    while time.time() < deadline:
        if url_ready(URL):
            if process.poll() is not None:
                return None
            return process
        if process.poll() is not None:
            if url_ready(URL):
                return None
            raise RuntimeError(
                "ZY-Study Web 服务未能启动；请手动运行："
                f"cd {ZY_STUDY_ROOT} && python3 web/server.py"
            )
        time.sleep(0.25)
    raise RuntimeError(f"等待 ZY-Study Web 服务超时：{URL}")


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
