#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 data/formula_cards/*.json 导入 jingfang.sqlite3（本机拉取云端提交后运行）。

默认保护网页编辑过的数据：数据库记录已校对完成，或数据库更新时间比 JSON 新时，
不会被 JSON 覆盖。确需用 JSON 重刷数据库时，显式传入 --force。
"""

from __future__ import annotations

import json
import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CARDS_DIR = PROJECT_ROOT / "ai-medical-consultant/backend/data/formula_cards"
DB_PATH = PROJECT_ROOT / "ai-medical-consultant/backend/data/jingfang.sqlite3"
UPSERT = PROJECT_ROOT / ".cursor/skills/jingfang-card-organizer/scripts/upsert_formula.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="强制用 JSON 覆盖数据库已有记录")
    args = parser.parse_args()

    if not CARDS_DIR.exists():
        print("无 formula_cards 目录，跳过")
        return 0
    files = sorted(CARDS_DIR.glob("*.json"))
    if not files:
        print("无待导入 JSON")
        return 0
    for path in files:
        command = [sys.executable, str(UPSERT), "--db", str(DB_PATH), "--payload", str(path)]
        if args.force:
            command.append("--force")
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            print(result.stdout.strip())
        try:
            status = json.loads(result.stdout)
        except json.JSONDecodeError:
            status = {}
        action = "skipped" if status.get("skipped") else "imported"
        print(f"{action}: {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
