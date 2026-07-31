#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成并导入《伤寒论》398 条康平本排版层级。

数据依据：
1. 胡希恕、李冠杰《伤寒论讲稿合订本》中李冠杰逐条说明；
2. 按李冠杰整理、郭明校对的“康平本伤寒论条文背诵版”；
3. 《古本康平伤寒论》重排本保留的缩进结构，用于复核讲稿略述条文。

这里只整理宋本第 1—398 条对应的条文正文层级。方剂组成、方后注的缩进
不并入条文层级；同一宋本条号内存在两种版式时，保留为混合层级。
"""

from __future__ import annotations

import csv
import json
import sqlite3
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = (
    PROJECT_ROOT
    / "ai-medical-consultant"
    / "backend"
    / "data"
    / "shanghan_kangping_levels.json"
)
CSV_PATH = PROJECT_ROOT / "note" / "伤寒论398条康平本层级分类.csv"
MARKDOWN_PATH = PROJECT_ROOT / "note" / "伤寒论398条康平本层级分类.md"
DB_PATH = (
    PROJECT_ROOT
    / "ai-medical-consultant"
    / "backend"
    / "data"
    / "jingfang.sqlite3"
)


TOP_ONLY = {
    1, 2, 3, 12, 13, 14, 15, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
    31, 32, 33, 34, 35, 38, 39, 40, 41, 42, 43, 44, 46, 48, 55, 59, 60,
    61, 67, 68, 69, 70, 71, 72, 73, 74, 76, 77, 78, 79, 80, 82, 91, 94,
    96, 99, 100, 102, 103, 104, 106, 107, 110, 111, 112, 114, 117, 118,
    123, 124, 125, 126, 134, 135, 136, 137, 138, 139, 144, 146, 147, 148,
    149, 150, 152, 153, 154, 155, 156, 157, 158, 159, 161, 163, 164, 165,
    168, 169, 170, 172, 173, 174, 175, 176, 177, 180, 212, 219, 220, 221,
    222, 223, 228, 229, 231, 232, 236, 237, 238, 241, 243, 248, 260, 261,
    263, 266, 267, 273, 279, 281, 301, 302, 303, 304, 305, 306, 307, 309,
    310, 311, 314, 315, 317, 318, 319, 320, 321, 323, 324, 326, 350, 351,
    352, 359, 385, 386, 388, 389, 390, 391, 393, 394, 395, 396, 397,
}

LEVEL_ONE_ONLY = {
    11, 18, 19, 47, 49, 50, 53, 57, 58, 62, 63, 66, 83, 84, 85, 86, 87,
    88, 89, 92, 97, 101, 113, 115, 116, 119, 121, 122, 131, 132, 133, 145,
    151, 160, 162, 166, 185, 191, 192, 194, 195, 199, 200, 203, 204, 210,
    211, 213, 217, 218, 225, 230, 233, 239, 240, 242, 244, 249, 250, 252,
    256, 259, 262, 264, 265, 268, 276, 277, 278, 282, 308, 312, 313, 337,
    338, 354, 355, 356, 357, 370, 371, 378, 379, 387, 392,
}

LEVEL_TWO_ONLY = {
    4, 5, 7, 8, 9, 10, 17, 30, 36, 37, 45, 51, 52, 54, 56, 64, 65, 75,
    81, 90, 95, 108, 109, 127, 128, 129, 130, 142, 143, 167, 171, 178,
    179, 181, 182, 183, 184, 186, 187, 188, 189, 190, 193, 196, 197, 198,
    201, 202, 205, 206, 207, 215, 216, 224, 226, 227, 234, 235, 245, 246,
    247, 251, 253, 254, 255, 257, 258, 269, 270, 271, 272, 274, 275, 280,
    283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296,
    297, 298, 299, 300, 322, 325, 327, 328, 329, 330, 331, 332, 333, 334,
    335, 336, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 353,
    358, 360, 361, 362, 363, 364, 365, 367, 368, 369, 372, 373, 374, 375,
    376, 377, 380, 381, 382, 383, 384, 398,
}

TOP_AND_ONE = {6, 16, 93, 98, 105, 120, 140, 141, 208, 209, 316}
ONE_AND_TWO = {214, 366}

SPECIAL_NOTES = {
    6: "条内多段，顶格与降一格交替排版。",
    16: "主体为顶格；“桂枝本为解肌……”一段为降一格。",
    93: "顶格正文后接降一格补充。",
    98: "先为降一格，转行后变为顶格；李冠杰认为排版存在传抄错误，不宜硬判为单一层级。",
    105: "同一宋本条号内含顶格正文与降一格补充。",
    120: "同一宋本条号内含顶格正文与降一格补充。",
    140: "顶格残文与降一格补充并存。",
    141: "“病在阳……”正文为顶格；“身热、皮粟不解……”为降一格。白散方另为降二格，但方剂版式不计入条文层级。",
    208: "“阳明病……”至“大承气汤主之”为顶格；“若汗出多……”为降一格。",
    209: "前一自然段为顶格，后一自然段为降一格。",
    214: "“小承气汤主之”以前为降一格，之后为降二格。",
    316: "正文为降一格；末尾“武汤主之”转行后误排成顶格，李冠杰明确判断为传抄笔误。",
    366: "“下利，脉沉而迟……”为降二格；“病人必微厥……”为降一格。",
    391: "康平本版式为顶格；李冠杰从语韵和内容判断，怀疑原本可能是降二格。",
    394: "康平本两个自然段均为顶格；李冠杰认为“脉浮者……”以下第二段可能原为降二格。",
}


def _levels_for(number: int) -> list[str]:
    if number in TOP_AND_ONE:
        return ["顶格", "降一格"]
    if number in ONE_AND_TWO:
        return ["降一格", "降二格"]
    if number in TOP_ONLY:
        return ["顶格"]
    if number in LEVEL_ONE_ONLY:
        return ["降一格"]
    if number in LEVEL_TWO_ONLY:
        return ["降二格"]
    raise ValueError(f"第 {number} 条没有层级")


def _classification_for(number: int, levels: list[str]) -> str:
    if number in {98, 316}:
        return "降一格 + 顶格"
    if number == 366:
        return "降二格 + 降一格"
    return " + ".join(levels)


def build_items() -> list[dict]:
    groups = [TOP_ONLY, LEVEL_ONE_ONLY, LEVEL_TWO_ONLY, TOP_AND_ONE, ONE_AND_TWO]
    flattened = [number for group in groups for number in group]
    if len(flattened) != 398 or set(flattened) != set(range(1, 399)):
        missing = sorted(set(range(1, 399)) - set(flattened))
        duplicates = sorted({number for number in flattened if flattened.count(number) > 1})
        raise ValueError(f"层级集合不完整：missing={missing}, duplicates={duplicates}")

    items = []
    for number in range(1, 399):
        levels = _levels_for(number)
        items.append(
            {
                "number": number,
                "classification": _classification_for(number, levels),
                "levels": levels,
                "note": SPECIAL_NOTES.get(number, ""),
            }
        )
    return items


def _statistics(items: list[dict]) -> dict:
    return {
        "articles": len(items),
        "topOnly": sum(item["levels"] == ["顶格"] for item in items),
        "levelOneOnly": sum(item["levels"] == ["降一格"] for item in items),
        "levelTwoOnly": sum(item["levels"] == ["降二格"] for item in items),
        "mixed": sum(len(item["levels"]) > 1 for item in items),
        "containsTop": sum("顶格" in item["levels"] for item in items),
        "containsLevelOne": sum("降一格" in item["levels"] for item in items),
        "containsLevelTwo": sum("降二格" in item["levels"] for item in items),
    }


def write_json(items: list[dict]) -> None:
    payload = {
        "schemaVersion": 1,
        "title": "《伤寒论》398条康平本排版层级",
        "scope": "宋本第1—398条对应的康平本条文正文；不把方剂组成、方后注缩进并入条文层级。",
        "levelAliases": {"顶格": "一级", "降一格": "二级", "降二格": "三级"},
        "statistics": _statistics(items),
        "sources": [
            "本地《伤寒论-上册_胡希恕_李冠杰讲稿合订本-原文标注》",
            "本地《伤寒论-下册_胡希恕_李冠杰讲稿合订本-原文标注》",
            "按李冠杰整理、郭明校对的《康平本伤寒论条文背诵版》：https://www.jfqmbz.com/jingfang/2024/shanghanlunyuanwen_0908/22486.html",
            "《古本康平伤寒论》重排本的缩进结构：https://jicheng.tw/tcm/book/古本康平傷寒論/index.html",
        ],
        "items": items,
    }
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_csv(items: list[dict]) -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["条文号", "康平本层级", "包含层级", "校勘说明"],
        )
        writer.writeheader()
        for item in items:
            writer.writerow(
                {
                    "条文号": item["number"],
                    "康平本层级": item["classification"],
                    "包含层级": "、".join(item["levels"]),
                    "校勘说明": item["note"],
                }
            )


def _format_numbers(numbers: list[int]) -> str:
    return "、".join(str(number) for number in numbers)


def write_markdown(items: list[dict]) -> None:
    stats = _statistics(items)
    by_classification: dict[str, list[int]] = {}
    for item in items:
        key = " + ".join(item["levels"])
        by_classification.setdefault(key, []).append(item["number"])

    lines = [
        "# 《伤寒论》398条康平本排版层级分类",
        "",
        "## 口径",
        "",
        "- 顶格＝一级；降一格＝二级；降二格＝三级。",
        "- 归类对象是宋本第1—398条对应的康平本条文正文；方剂组成和方后注的缩进不计入条文层级。",
        "- 同一宋本条号内若包含两种排版，保留为“混合层级”，不强行压成单一等级。",
        "- 版式归类与作者归属、学术价值不是同一个概念；这里记录的是康平本排版事实，并附李冠杰老师的校勘判断。",
        "",
        "## 统计",
        "",
        f"- 单一顶格：{stats['topOnly']} 条",
        f"- 单一降一格：{stats['levelOneOnly']} 条",
        f"- 单一降二格：{stats['levelTwoOnly']} 条",
        f"- 混合层级：{stats['mixed']} 条",
        f"- 按“包含该层级”统计：顶格 {stats['containsTop']} 条、降一格 {stats['containsLevelOne']} 条、降二格 {stats['containsLevelTwo']} 条。",
        "",
        "## 顶格（单一层级）",
        "",
        _format_numbers(by_classification["顶格"]),
        "",
        "## 降一格（单一层级）",
        "",
        _format_numbers(by_classification["降一格"]),
        "",
        "## 降二格（单一层级）",
        "",
        _format_numbers(by_classification["降二格"]),
        "",
        "## 混合层级",
        "",
    ]
    for item in items:
        if len(item["levels"]) > 1:
            lines.append(
                f"- 第{item['number']}条：{item['classification']}。{item['note']}"
            )
    lines.extend(
        [
            "",
            "## 康平本实排与李冠杰校勘判断不同的重点",
            "",
            f"- 第391条：{SPECIAL_NOTES[391]}",
            f"- 第394条：{SPECIAL_NOTES[394]}",
            "",
            "## 资料依据",
            "",
            "- 本地《伤寒论-上册_胡希恕_李冠杰讲稿合订本-原文标注》",
            "- 本地《伤寒论-下册_胡希恕_李冠杰讲稿合订本-原文标注》",
            "- [按李冠杰整理、郭明校对的《康平本伤寒论条文背诵版》](https://www.jfqmbz.com/jingfang/2024/shanghanlunyuanwen_0908/22486.html)",
            "- [《古本康平伤寒论》重排本](https://jicheng.tw/tcm/book/%E5%8F%A4%E6%9C%AC%E5%BA%B7%E5%B9%B3%E5%82%B7%E5%AF%92%E8%AB%96/index.html)",
            "",
        ]
    )
    MARKDOWN_PATH.write_text("\n".join(lines), encoding="utf-8")


def update_database(items: list[dict]) -> tuple[int, int]:
    now = int(time.time())
    annotated = 0
    legacy_level = {"顶格": "一级", "降一格": "二级", "降二格": "三级"}
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            create table if not exists shanghan_kangping_levels (
                number integer primary key,
                classification text not null,
                levels text not null,
                note text not null default '',
                updated_at integer not null
            )
            """
        )
        for item in items:
            conn.execute(
                """
                insert into shanghan_kangping_levels(
                    number, classification, levels, note, updated_at
                ) values(?, ?, ?, ?, ?)
                on conflict(number) do update set
                    classification = excluded.classification,
                    levels = excluded.levels,
                    note = excluded.note,
                    updated_at = excluded.updated_at
                """,
                (
                    item["number"],
                    item["classification"],
                    json.dumps(item["levels"], ensure_ascii=False),
                    item["note"],
                    now,
                ),
            )

        item_by_number = {item["number"]: item for item in items}
        rows = conn.execute("select id, payload from shanghan_articles").fetchall()
        for article_id, raw_payload in rows:
            payload = json.loads(raw_payload)
            try:
                number = int(str(payload.get("number") or "").strip())
            except ValueError:
                continue
            item = item_by_number.get(number)
            if not item:
                continue
            payload["kangpingLevel"] = item["classification"]
            payload["kangpingLevels"] = item["levels"]
            payload["kangpingLevelNote"] = item["note"]
            if len(item["levels"]) == 1:
                payload["level"] = legacy_level[item["levels"][0]]
            conn.execute(
                "update shanghan_articles set payload = ?, updated_at = ? where id = ?",
                (json.dumps(payload, ensure_ascii=False), now, article_id),
            )
            annotated += 1
        conn.commit()
    return len(items), annotated


def main() -> None:
    items = build_items()
    write_json(items)
    write_csv(items)
    write_markdown(items)
    imported, annotated = update_database(items)
    print(f"已导入 {imported} 条康平本层级；已标注现有条文卡 {annotated} 条。")
    print(DATA_PATH)
    print(CSV_PATH)
    print(MARKDOWN_PATH)
    print(DB_PATH)


if __name__ == "__main__":
    main()
