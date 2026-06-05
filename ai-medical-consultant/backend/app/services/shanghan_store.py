# -*- coding: utf-8 -*-
"""《伤寒论》条文解读：SQLite 存储。"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from ..config import settings


def _db_path() -> Path:
    return Path(settings.jingfang_db_path)


SEED_ARTICLES = [
    {
        "id": "shl-001",
        "number": "1",
        "level": "一级",
        "original": "顶格条文：[[**太阳之为病，脉浮，头项强痛而恶寒。**]]",
        "termItems": [
            {
                "label": "太阳病",
                "text": "不是具体的某一种病，而是一般的证，有[[**脉浮、头项强痛、恶寒**]]这一系列症候反应的，都叫太阳病。",
            },
            {
                "label": "脉浮",
                "text": "潜在动脉高度充血，血中水分增多，提示[[**病位在表，正气趋表**]]。",
            },
            {
                "label": "恶寒",
                "text": "体表温度升高，空气温差骤然变大，会感觉外面空气很冷，是[[**太阳表证的重要抓手**]]。",
            },
            {
                "label": "想要出汗的原因",
                "text": "人体正邪相争在表，机体打算利用发汗的机能把疾病排除在外；排除失败，就出现[[**欲汗不得汗**]]，上半身充血，所以有脉浮、头项强痛而恶寒。",
            },
        ],
        "terms": "\n".join(
            [
                "太阳病：不是具体的某一种病，而是一般的证，有[[**脉浮、头项强痛、恶寒**]]这一系列症候反应的，都叫太阳病。",
                "脉浮：潜在动脉高度充血，血中水分增多，提示[[**病位在表，正气趋表**]]。",
                "恶寒：体表温度升高，空气温差骤然变大，会感觉外面空气很冷，是[[**太阳表证的重要抓手**]]。",
                "想要出汗的原因：人体正邪相争在表，机体打算利用发汗的机能把疾病排除在外；排除失败，就出现[[**欲汗不得汗**]]，上半身充血，所以有脉浮、头项强痛而恶寒。",
            ]
        ),
        "huXishu": "胡希恕讲太阳病，重点不把它看成固定病名，而是看成[[**人体在表的一种抗病反应**]]。外邪侵袭人体，机体首先在体表进行抵抗，想通过发汗把病邪排出。太阳病的关键是：[[**病在表，正气趋表，欲汗不得汗**]]。",
        "liGuanjie": "李冠杰讲这一条，强调它是[[**太阳病的总纲**]]。判断太阳病，不是看现代医学病名，而是看有没有[[**脉浮、头项强痛、恶寒**]]这一组核心反应。恶寒尤其重要，提示表证未解。",
        "summary": "\n".join(
            [
                "第1条是[[**太阳病总纲**]]，不是某个具体疾病名称。",
                "太阳病核心证候是：[[**脉浮、头项强痛、恶寒**]]。",
                "病位在表，病理关键是：[[**正邪相争于表，欲汗不得汗**]]。",
                "治疗大方向是[[**解表**]]，具体用方还要结合有汗无汗、发热、喘、身痛等继续辨证。",
            ]
        ),
    }
]


def ensure_ready() -> None:
    with db() as conn:
        now = int(time.time())
        for article in SEED_ARTICLES:
            exists = conn.execute(
                "select 1 from shanghan_articles where id = ?",
                (article["id"],),
            ).fetchone()
            if exists:
                continue
            conn.execute(
                """
                insert into shanghan_articles(id, payload, updated_at) values(?, ?, ?)
                """,
                (article["id"], json.dumps(article, ensure_ascii=False), now),
            )
        conn.commit()


def db() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        create table if not exists shanghan_articles (
            id text primary key,
            payload text not null,
            updated_at integer not null
        )
        """
    )
    conn.commit()
    return conn


def list_articles() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "select payload from shanghan_articles order by updated_at desc"
        ).fetchall()
    articles = [json.loads(row["payload"]) for row in rows]

    def sort_key(article: dict) -> tuple[int, int, str]:
        raw_number = str(article.get("number") or "").strip()
        try:
            number = int(raw_number)
            return (0, number, article.get("level") or "")
        except ValueError:
            return (1, 0, article.get("level") or raw_number)

    return sorted(articles, key=sort_key)


def save_article(payload: dict) -> dict:
    article_id = payload.get("id") or f"shanghan-{int(time.time() * 1000)}"
    payload["id"] = article_id
    now = int(time.time())
    with db() as conn:
        conn.execute(
            """
            insert into shanghan_articles(id, payload, updated_at) values(?, ?, ?)
            on conflict(id) do update set payload = excluded.payload, updated_at = excluded.updated_at
            """,
            (article_id, json.dumps(payload, ensure_ascii=False), now),
        )
        conn.commit()
    return payload


def delete_article(article_id: str) -> bool:
    with db() as conn:
        cur = conn.execute("delete from shanghan_articles where id = ?", (article_id,))
        conn.commit()
    return cur.rowcount > 0
