# -*- coding: utf-8 -*-
"""100 首方剂解读：SQLite 存储与中药图片索引。"""

from __future__ import annotations

import json
import shutil
import sqlite3
import time
from pathlib import Path

from ..config import settings

CATEGORIES = ["表证", "里证", "半证", "水证", "血证", "气证", "阴证"]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _db_path() -> Path:
    return Path(settings.jingfang_db_path)


def _herb_dir() -> Path:
    return Path(settings.jingfang_herb_dir)


def _source_db_path() -> Path:
    return Path(settings.jingfang_source_db)


def ensure_ready() -> None:
    """首次启动时从 ZY-Study 复制数据库，并同步中药图片索引。"""
    target = _db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        source = _source_db_path()
        if source.exists():
            shutil.copy2(source, target)
    db()


def db() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
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
    sync_herb_library(conn)
    conn.commit()
    return conn


def herb_name_from_file(path: Path) -> str:
    return path.stem.strip()


def sync_herb_library(conn: sqlite3.Connection) -> None:
    herb_dir = _herb_dir()
    if not herb_dir.exists():
        return
    now = int(time.time())
    files = [
        item
        for item in herb_dir.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES
    ]
    rows = [
        (herb_name_from_file(item), item.name, now)
        for item in files
        if herb_name_from_file(item)
    ]
    conn.executemany(
        """
        insert into herbs(name, filename, updated_at) values(?, ?, ?)
        on conflict(name) do update set filename = excluded.filename, updated_at = excluded.updated_at
        """,
        rows,
    )
    filenames = {item.name for item in files}
    for row in conn.execute("select filename from herbs").fetchall():
        if row["filename"] not in filenames:
            conn.execute("delete from herbs where filename = ?", (row["filename"],))
    conn.commit()


def list_herbs() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "select name, filename from herbs order by length(name) desc, name asc"
        ).fetchall()
    return [{"name": row["name"], "filename": row["filename"]} for row in rows]


def list_formulas() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "select payload from formulas order by updated_at desc"
        ).fetchall()
    return [json.loads(row["payload"]) for row in rows]


def save_formula(payload: dict) -> dict:
    formula_id = payload.get("id") or f"formula-{int(time.time() * 1000)}"
    payload["id"] = formula_id
    now = int(time.time())
    with db() as conn:
        conn.execute(
            """
            insert into formulas(id, payload, updated_at) values(?, ?, ?)
            on conflict(id) do update set payload = excluded.payload, updated_at = excluded.updated_at
            """,
            (formula_id, json.dumps(payload, ensure_ascii=False), now),
        )
        conn.commit()
    return payload


def delete_formula(formula_id: str) -> bool:
    with db() as conn:
        cur = conn.execute("delete from formulas where id = ?", (formula_id,))
        conn.commit()
    return cur.rowcount > 0


def resolve_herb_file(filename: str) -> Path | None:
    herb_dir = _herb_dir().resolve()
    target = (herb_dir / filename).resolve()
    if target.exists() and herb_dir in target.parents:
        return target
    return None
