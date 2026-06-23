# -*- coding: utf-8 -*-
"""《伤寒论》条文解读：SQLite 存储。"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
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
    conn.execute(
        """
        create table if not exists shanghan_study_progress (
            user_id text primary key,
            payload text not null,
            updated_at integer not null
        )
        """
    )
    conn.execute(
        """
        create table if not exists shanghan_study_sessions (
            id text primary key,
            user_id text not null,
            payload text not null,
            updated_at integer not null
        )
        """
    )
    conn.execute(
        """
        create table if not exists shanghan_study_reviews (
            id text primary key,
            user_id text not null,
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


DEFAULT_PROGRESS = {
    "currentRound": 1,
    "nextArticleNo": 1,
    "defaultMode": "standard",
    "currentLevel": "太阳病入门",
    "points": 0,
    "lastSessionDate": "",
    "todayRead": [],
    "masteryByArticle": {},
}


MODE_LABELS = {
    "light": "轻量版",
    "standard": "标准版",
    "deep": "深入版",
}


STATE_LABELS = {
    "clear": "清醒",
    "normal": "一般",
    "scattered": "很散",
}


def _user_key(user_id: int | str) -> str:
    return str(user_id)


def _article_number(article: dict) -> int:
    raw_number = str(article.get("number") or article.get("articleNo") or "0").strip()
    try:
        return int(raw_number)
    except ValueError:
        return 0


def _find_article(article_no: int | str | None) -> dict:
    articles = list_articles()
    if not articles:
        return dict(SEED_ARTICLES[0])

    try:
        target = int(str(article_no or "").strip())
    except ValueError:
        target = 0

    for article in articles:
        if _article_number(article) == target:
            return article
    return articles[0]


def _plain_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(_plain_text(item) for item in value if item)
    if isinstance(value, dict):
        return "\n".join(_plain_text(v) for v in value.values() if v)
    return str(value).strip()


def _first_nonempty(*values) -> str:
    for value in values:
        text = _plain_text(value)
        if text:
            return text
    return ""


def get_progress(user_id: int | str) -> dict:
    key = _user_key(user_id)
    with db() as conn:
        row = conn.execute(
            "select payload from shanghan_study_progress where user_id = ?",
            (key,),
        ).fetchone()
    progress = dict(DEFAULT_PROGRESS)
    if row:
        try:
            progress.update(json.loads(row["payload"]))
        except json.JSONDecodeError:
            pass

    next_article = _find_article(progress.get("nextArticleNo"))
    progress["nextArticleNo"] = _article_number(next_article) or progress.get("nextArticleNo") or 1
    progress["nextArticleTitle"] = f"第{progress['nextArticleNo']}条"
    progress["articleCount"] = len(list_articles())
    progress["hasReview"] = bool(list_reviews(user_id))
    return progress


def save_progress(user_id: int | str, payload: dict) -> dict:
    key = _user_key(user_id)
    progress = dict(DEFAULT_PROGRESS)
    progress.update(payload or {})
    now = int(time.time())
    with db() as conn:
        conn.execute(
            """
            insert into shanghan_study_progress(user_id, payload, updated_at) values(?, ?, ?)
            on conflict(user_id) do update set payload = excluded.payload, updated_at = excluded.updated_at
            """,
            (key, json.dumps(progress, ensure_ascii=False), now),
        )
        conn.commit()
    return get_progress(user_id)


def _make_segments(article: dict, mode: str) -> list[dict]:
    number = str(article.get("number") or "").strip()
    original = _first_nonempty(article.get("originalText"), article.get("original"))
    terms = _first_nonempty(article.get("terms"), article.get("termItems"))
    hu = _first_nonempty(article.get("huExcerpt"), article.get("huXishu"))
    li = _first_nonempty(article.get("liExcerpt"), article.get("liGuanjie"))
    summary = _first_nonempty(article.get("summary"), article.get("boundaryNotes"))
    core_question = "这条第一眼先抓哪个症状或症状组合？"

    if mode == "light":
        return [
            {
                "id": "original",
                "title": "片段1/2：原文",
                "kind": "original",
                "content": original or f"第{number}条原文待补充。",
                "question": core_question,
                "requiresAnswer": True,
            },
            {
                "id": "quiz",
                "title": "片段2/2：一句话记忆与小测",
                "kind": "quiz",
                "content": summary or terms or "先抓原文症状组合，再判断病位和边界。",
                "question": "请用一句话复述这一条的临床抓手。",
                "requiresAnswer": True,
            },
        ]

    segments = [
        {
            "id": "original",
            "title": "片段1/5：原文",
            "kind": "original",
            "content": original or f"第{number}条原文待补充。",
            "question": core_question,
            "requiresAnswer": True,
        },
        {
            "id": "hu-read",
            "title": "片段2/5：胡希恕原文阅读",
            "kind": "source_reading",
            "source": "胡希恕",
            "content": hu or "当前结构化条文暂未补充胡希恕讲稿节选，可先按原文抓症状组合。",
            "question": "你先归纳一下，这段主要在说什么？",
            "requiresAnswer": True,
        },
        {
            "id": "li-read",
            "title": "片段3/5：李冠杰原文阅读",
            "kind": "source_reading",
            "source": "李冠杰",
            "content": li or "当前结构化条文暂未补充李冠杰讲稿节选，可先围绕症状平台和辨证边界归纳。",
            "question": "你先归纳一下，这段主要在提醒什么辨证边界？",
            "requiresAnswer": True,
        },
        {
            "id": "pathology",
            "title": "片段4/5：病理分类与边界",
            "kind": "summary",
            "content": summary or terms or "先保留讲稿原始病理术语，再用表里寒热虚实、水血气作辅助判断。",
            "question": "这一条最容易和哪类症状或方证混淆？",
            "requiresAnswer": True,
        },
        {
            "id": "quiz",
            "title": "片段5/5：一句话记忆与本条小测",
            "kind": "quiz",
            "content": "小测：用自己的话说出本条抓手，并判断它提示的主要病位或边界。",
            "question": "请用一句话复述这一条的临床抓手。",
            "requiresAnswer": True,
        },
    ]
    if mode == "deep":
        segments.insert(
            4,
            {
                "id": "compare",
                "title": "加深片段：类方与误治边界",
                "kind": "deep",
                "content": "深入版需要把本条和相邻条文、相似方证放在一起辨。当前先记录你的类方鉴别想法，后续可接入更完整题库。",
                "question": "这条如果误判，最可能误治在哪里？",
                "requiresAnswer": True,
            },
        )
        for index, segment in enumerate(segments, start=1):
            segment["title"] = segment["title"].replace("/5", f"/{len(segments)}")
    return segments


def start_session(user_id: int | str, mode: str = "standard", state: str = "normal") -> dict:
    progress = get_progress(user_id)
    if state == "scattered" and mode != "light":
        mode = "light"
    article = _find_article(progress.get("nextArticleNo"))
    article_no = _article_number(article) or 1
    session = {
        "id": f"shl-study-{uuid.uuid4().hex[:12]}",
        "articleNo": article_no,
        "articleId": article.get("id"),
        "articleTitle": f"第{article_no}条",
        "mode": mode,
        "modeLabel": MODE_LABELS.get(mode, "标准版"),
        "state": state,
        "stateLabel": STATE_LABELS.get(state, "一般"),
        "taskCard": {
            "article": f"第{article_no}条",
            "mainLine": "先抓原文症状组合，再辨病理和边界。",
            "mustKnow": [
                "核心症状组合",
                "讲稿中的原始病理术语",
                "本条最容易误解或误治的地方",
            ],
            "finalQuestion": "用自己的话复述本条抓手。",
        },
        "preCheck": _build_precheck(user_id),
        "article": article,
        "segments": _make_segments(article, mode),
        "currentSegmentIndex": 0,
        "answers": [],
        "createdAt": int(time.time()),
    }
    now = int(time.time())
    with db() as conn:
        conn.execute(
            "insert into shanghan_study_sessions(id, user_id, payload, updated_at) values(?, ?, ?, ?)",
            (session["id"], _user_key(user_id), json.dumps(session, ensure_ascii=False), now),
        )
        conn.commit()
    return session


def get_session(user_id: int | str, session_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "select payload from shanghan_study_sessions where id = ? and user_id = ?",
            (session_id, _user_key(user_id)),
        ).fetchone()
    if not row:
        return None
    return json.loads(row["payload"])


def save_session(user_id: int | str, session: dict) -> dict:
    now = int(time.time())
    with db() as conn:
        conn.execute(
            """
            insert into shanghan_study_sessions(id, user_id, payload, updated_at) values(?, ?, ?, ?)
            on conflict(id) do update set payload = excluded.payload, updated_at = excluded.updated_at
            """,
            (session["id"], _user_key(user_id), json.dumps(session, ensure_ascii=False), now),
        )
        conn.commit()
    return session


def answer_session(user_id: int | str, session_id: str, payload: dict) -> dict:
    session = get_session(user_id, session_id)
    if not session:
        raise KeyError("session not found")
    segments = session.get("segments") or []
    index = int(payload.get("segmentIndex", session.get("currentSegmentIndex") or 0))
    segment = segments[index] if 0 <= index < len(segments) else {}
    action = str(payload.get("action") or "answer")
    answer = str(payload.get("answer") or "").strip()
    feedback = _feedback_for(segment, answer, action)

    if action == "answer":
        session.setdefault("answers", []).append(
            {
                "segmentId": segment.get("id"),
                "answer": answer,
                "feedback": feedback,
                "createdAt": int(time.time()),
            }
        )
        if index < len(segments) - 1:
            session["currentSegmentIndex"] = index + 1
    elif action == "skip" and index < len(segments) - 1:
        session["currentSegmentIndex"] = index + 1
    elif action == "stop":
        session["stopped"] = True
    save_session(user_id, session)

    return {
        "session": session,
        "feedback": feedback,
        "currentSegmentIndex": session.get("currentSegmentIndex", index),
        "done": session.get("currentSegmentIndex", index) >= len(segments) - 1 and action == "answer",
    }


def complete_article(user_id: int | str, session_id: str, payload: dict | None = None) -> dict:
    session = get_session(user_id, session_id)
    if not session:
        raise KeyError("session not found")
    article_no = int(session.get("articleNo") or 1)
    mastery = str((payload or {}).get("mastery") or "半熟")
    quiz_level = str((payload or {}).get("quizLevel") or "B")
    score = int((payload or {}).get("score") or 8)

    progress = get_progress(user_id)
    today_read = list(progress.get("todayRead") or [])
    if article_no not in today_read:
        today_read.append(article_no)
    mastery_by_article = dict(progress.get("masteryByArticle") or {})
    mastery_by_article[str(article_no)] = mastery
    progress.update(
        {
            "nextArticleNo": article_no + 1,
            "lastSessionDate": time.strftime("%Y-%m-%d"),
            "todayRead": today_read,
            "points": int(progress.get("points") or 0) + score,
            "lastQuizLevel": quiz_level,
            "lastMastery": mastery,
            "masteryByArticle": mastery_by_article,
        }
    )
    progress = save_progress(user_id, progress)
    session["completed"] = True
    session["result"] = {"mastery": mastery, "quizLevel": quiz_level, "score": score}
    save_session(user_id, session)

    if mastery in {"生", "卡住"}:
        add_review(
            user_id,
            {
                "articleNo": article_no,
                "question": "请复述本条核心抓手和病理边界。",
                "correctAnswer": "先合看原文症状组合，再判断病理和误治边界。",
                "weakPoint": "复述与边界",
                "reviewPrompt": f"第{article_no}条最重要的症状组合是什么？",
                "status": "待复习",
            },
        )

    return {"progress": progress, "session": session}


def complete_article_number(user_id: int | str, payload: dict | None = None) -> dict:
    data = payload or {}
    try:
        article_no = int(data.get("articleNo") or get_progress(user_id).get("nextArticleNo") or 1)
    except (TypeError, ValueError):
        article_no = 1
    mastery = str(data.get("mastery") or "半熟")
    quiz_level = str(data.get("quizLevel") or "B")
    score = int(data.get("score") or 8)

    progress = get_progress(user_id)
    today_read = list(progress.get("todayRead") or [])
    if article_no not in today_read:
        today_read.append(article_no)
    mastery_by_article = dict(progress.get("masteryByArticle") or {})
    mastery_by_article[str(article_no)] = mastery
    progress.update(
        {
            "nextArticleNo": article_no + 1,
            "lastSessionDate": time.strftime("%Y-%m-%d"),
            "todayRead": today_read,
            "points": int(progress.get("points") or 0) + score,
            "lastQuizLevel": quiz_level,
            "lastMastery": mastery,
            "masteryByArticle": mastery_by_article,
        }
    )
    progress = save_progress(user_id, progress)
    if mastery in {"生", "卡住"}:
        add_review(
            user_id,
            {
                "articleNo": article_no,
                "question": "请复述本条核心抓手和病理边界。",
                "correctAnswer": "先合看原文症状组合，再判断病理和误治边界。",
                "weakPoint": "复述与边界",
                "reviewPrompt": f"第{article_no}条最重要的症状组合是什么？",
                "status": "待复习",
            },
        )
    return {"progress": progress}


def _feedback_for(segment: dict, answer: str, action: str) -> dict:
    if action == "hint":
        return {
            "title": "提示一",
            "text": "先看原文里的症状词，再把它们合成一个症状组合，不要只抓单个字。",
            "level": 1,
        }
    if action == "answer_key":
        return {
            "title": "参考答案",
            "text": "本段应先抓核心症状组合，再判断它提示的病位、病理和边界。讲稿里的原始术语要优先保留。",
            "level": 3,
        }
    if action == "rephrase":
        return {
            "title": "换个说法",
            "text": "你可以把这一段当成临床现场：先看病人最明显的症状组合，再问它属于表、里、半，寒、热、虚、实中的哪一类。",
            "level": 0,
        }
    if action == "stop":
        return {"title": "已暂停", "text": "已记录当前课堂状态，下次可以继续。", "level": 0}
    if action == "skip":
        return {"title": "已跳过", "text": "这一段先标记为薄弱点，继续下一片段。", "level": 0}
    if not answer:
        return {"title": "需要回答", "text": "先用一句话归纳当前片段，再进入下一步。", "level": 0}
    if segment.get("kind") == "source_reading":
        return {
            "title": f"{segment.get('source') or '讲稿'}点评",
            "text": "你的归纳已经进入方向。接下来重点补两点：第一，保留讲稿原始病理术语；第二，把症状和辨证边界合在一起看。",
            "level": 0,
        }
    if segment.get("kind") == "quiz":
        return {
            "title": "小测反馈",
            "text": "回答已记录。若能同时说出症状组合、病理术语和误治边界，本条可判为半熟以上。",
            "level": 0,
        }
    return {
        "title": "片段反馈",
        "text": "先这样抓：原文症状组合是入口，病理和边界是本条真正要掌握的部分。",
        "level": 0,
    }


def _build_precheck(user_id: int | str) -> dict:
    reviews = list_reviews(user_id)
    if reviews:
        review = reviews[0]
        return {
            "source": "错题复问",
            "question": review.get("reviewPrompt") or review.get("question"),
            "articleNo": review.get("articleNo"),
        }
    progress = get_progress(user_id)
    next_no = int(progress.get("nextArticleNo") or 1)
    previous = max(next_no - 1, 1)
    return {
        "source": "上次抓手",
        "question": f"第{previous}条最重要的一个症状组合是什么？",
        "articleNo": previous,
    }


def add_review(user_id: int | str, payload: dict) -> dict:
    review = dict(payload or {})
    review["id"] = review.get("id") or f"review-{uuid.uuid4().hex[:12]}"
    now = int(time.time())
    with db() as conn:
        conn.execute(
            """
            insert into shanghan_study_reviews(id, user_id, payload, updated_at) values(?, ?, ?, ?)
            on conflict(id) do update set payload = excluded.payload, updated_at = excluded.updated_at
            """,
            (review["id"], _user_key(user_id), json.dumps(review, ensure_ascii=False), now),
        )
        conn.commit()
    return review


def list_reviews(user_id: int | str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "select payload from shanghan_study_reviews where user_id = ? order by updated_at desc",
            (_user_key(user_id),),
        ).fetchall()
    reviews = []
    for row in rows:
        try:
            reviews.append(json.loads(row["payload"]))
        except json.JSONDecodeError:
            continue
    return reviews


def get_article_for_study(article_no: int | str | None = None) -> dict:
    return _find_article(article_no)


def article_context(article: dict) -> str:
    number = str(article.get("number") or "").strip()
    fields = [
        ("条文原文", _first_nonempty(article.get("originalText"), article.get("original"))),
        ("名词解释", _first_nonempty(article.get("terms"), article.get("termItems"))),
        ("胡希恕", _first_nonempty(article.get("huExcerpt"), article.get("huXishu"))),
        ("李冠杰", _first_nonempty(article.get("liExcerpt"), article.get("liGuanjie"))),
        ("本条总结", _first_nonempty(article.get("summary"), article.get("boundaryNotes"))),
    ]
    parts = [f"当前条文：伤寒论第{number or '?'}条"]
    for label, text in fields:
        if text:
            parts.append(f"【{label}】\n{text}")
    return "\n\n".join(parts)


def _chat_session_id(user_id: int | str) -> str:
    return f"shanghan-study-chat-{_user_key(user_id)}"


def get_chat_history(user_id: int | str) -> list[dict]:
    session = get_session(user_id, _chat_session_id(user_id))
    if not session:
        return []
    messages = session.get("messages")
    return messages if isinstance(messages, list) else []


def save_chat_history(user_id: int | str, messages: list[dict]) -> dict:
    session = {
        "id": _chat_session_id(user_id),
        "type": "ai_chat",
        "messages": messages[-40:],
        "updatedAt": int(time.time()),
    }
    return save_session(user_id, session)


def append_chat_exchange(user_id: int | str, question: str, reply: str, article_no: int | str | None) -> list[dict]:
    messages = get_chat_history(user_id)
    now = int(time.time())
    messages.append(
        {
            "role": "user",
            "content": question,
            "articleNo": article_no,
            "createdAt": now,
        }
    )
    messages.append(
        {
            "role": "assistant",
            "content": reply,
            "articleNo": article_no,
            "createdAt": int(time.time()),
        }
    )
    save_chat_history(user_id, messages)
    return messages
