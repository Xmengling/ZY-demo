# -*- coding: utf-8 -*-
"""批量导出方剂卡片 PDF（复用 scripts/jingfang 网页可搜索版）。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = PROJECT_ROOT / "scripts/jingfang"
OUT_DIR = PROJECT_ROOT / "docs/exports/formula_cards"

EXPORT_MODES = {
    "searchable": SCRIPTS_DIR / "export_formula_cards_searchable_pdf_from_web.py",
    "web-hd": SCRIPTS_DIR / "export_formula_cards_pdf_from_web.py",
}


def _parse_pdf_path(stdout: str) -> Path | None:
    for line in stdout.splitlines():
        if line.startswith("PDF：") or line.startswith("PDF:"):
            raw = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            if raw:
                return Path(raw)
    return None


def _latest_pdf() -> Path | None:
    if not OUT_DIR.exists():
        return None
    pdfs = sorted(OUT_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    return pdfs[0] if pdfs else None


def export_formula_cards_pdf(mode: str = "searchable") -> Path:
    script = EXPORT_MODES.get(mode)
    if script is None:
        raise ValueError(f"不支持的导出模式：{mode}")
    if not script.exists():
        raise FileNotFoundError(f"未找到导出脚本：{script}")

    env = os.environ.copy()
    env.setdefault("NO_PROXY", "127.0.0.1,localhost")
    backend_root = PROJECT_ROOT / "ai-medical-consultant/backend"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(backend_root), env.get("PYTHONPATH", "")]
    ).strip(os.pathsep)

    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=900,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("PDF 导出超时，请稍后重试") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "导出进程失败").strip()
        if "playwright" in detail.lower() or "No module named" in detail:
            detail += (
                "\n请在本机执行：pip install -r scripts/jingfang/requirements-export.txt "
                "&& playwright install chromium"
            )
        raise RuntimeError(detail)

    pdf_path = _parse_pdf_path(proc.stdout) or _latest_pdf()
    if pdf_path is None or not pdf_path.exists():
        raise RuntimeError("导出完成但未找到 PDF 文件")
    return pdf_path.resolve()
