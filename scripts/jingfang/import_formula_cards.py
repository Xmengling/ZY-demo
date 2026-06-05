#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 data/formula_cards/*.json 导入 jingfang.sqlite3（本机拉取云端提交后运行）。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CARDS_DIR = PROJECT_ROOT / "ai-medical-consultant/backend/data/formula_cards"
DB_PATH = PROJECT_ROOT / "ai-medical-consultant/backend/data/jingfang.sqlite3"
UPSERT = PROJECT_ROOT / ".cursor/skills/jingfang-card-organizer/scripts/upsert_formula.py"


def main() -> int:
    if not CARDS_DIR.exists():
        print("无 formula_cards 目录，跳过")
        return 0
    files = sorted(CARDS_DIR.glob("*.json"))
    if not files:
        print("无待导入 JSON")
        return 0
    for path in files:
        subprocess.run(
            [sys.executable, str(UPSERT), "--db", str(DB_PATH), "--payload", str(path)],
            check=True,
        )
        print(f"imported: {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
