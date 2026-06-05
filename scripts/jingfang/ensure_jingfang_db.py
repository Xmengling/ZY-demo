#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确保 jingfang.sqlite3 与 formulas 表存在（云端/本地均可运行）。"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "ai-medical-consultant/backend/data/jingfang.sqlite3"


def ensure() -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            create table if not exists formulas (
              id text primary key,
              payload text not null,
              updated_at integer not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists herbs (
              name text primary key,
              filename text not null,
              updated_at integer not null
            )
            """
        )
        conn.commit()
    return DB_PATH


def main() -> int:
    path = ensure()
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
