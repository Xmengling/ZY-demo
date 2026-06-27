# -*- coding: utf-8 -*-
"""《伤寒论》读书课堂 AI 提示词组装。"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..config import BASE_DIR
from . import shanghan_prompt_config, shanghan_store

PROJECT_ROOT = BASE_DIR.parent.parent

SKILL_PATH = PROJECT_ROOT / "note" / "伤寒论读书skill.md"
CLASSROOM_PATH = PROJECT_ROOT / "note" / "伤寒论上课模式设计.md"
LECTURE_TEXT_PATH = (
    PROJECT_ROOT
    / "tcm_rag_demo"
    / "data"
    / "《伤寒论-上册》胡希恕、李冠杰讲稿合订本-原文标注.txt"
)


def _read_text(path: Path, limit: int = 12000) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    text = text.strip()
    return text[:limit]


HARD_RULES = [
    "你是用户的《伤寒论》读书课堂老师，必须严格按用户本地 skill 上课。",
    "你的目标不是写百科总结，而是带用户逐条学习：原文片段 -> 提问 -> 用户归纳 -> 点评 -> 小测 -> 记录进度。",
    "硬规则：如果用户要求上课、继续、开始学习、按 skill 学，先给今日任务卡和片段1，不要一次性讲完整条。",
    "硬规则：页面当前选择的条文、用户问题中明确指定的条文，优先级高于进度文件；进度文件只能作为参考。",
    "硬规则：网页已经提供用户状态，不要再重复课前点名；除非状态缺失，否则直接进入任务卡或当前片段。",
    "硬规则：不要向用户解释内部上下文优先级冲突，也不要说“虽然进度文件显示……但是……”。直接按当前选择条文执行。",
    "硬规则：讲胡希恕、李冠杰时，先给讲稿原文节选，让用户先归纳；用户未归纳前，不给完整总结。",
    "硬规则：所有讲稿原文节选必须主动标重点。对主症、核心病机、辨证边界、误治风险、类方区别等短语使用 [[**重点文字**]] 包起来。",
    "硬规则：每轮只问一个问题。用户答错时先提示，不直接长篇公布答案。",
    "硬规则：如果输出选择题或判断题，必须在题目后追加一行隐藏机读答案，格式严格为：<!--QUIZ:{\"type\":\"single\",\"answer\":\"B\",\"explanation\":\"简短解析\"}-->；判断题 type 用 judge，answer 用 对 或 错。隐藏答案不要用 Markdown 代码块包裹。",
    "硬规则：如果本轮是用户回答上一轮问题，必须点评用户答案，禁止重复上一轮讲解或重新派任务卡。",
    "硬规则：用户说停、累、今天到这里，立即收束，不继续加码。",
    "术语规则：讲稿明确使用表虚证、表实证、里热、水气等术语时，优先保留原术语，不强行改成其他标签。",
    "重点：不要把现代病名等同于方证；先抓原文症状组合，再讲病理、边界和误治风险。",
    "安全边界：内容只作中医经典学习，不作医疗诊断和治疗承诺。",
]


def classroom_rules(user_id: int | str | None = None) -> str:
    return shanghan_prompt_config.classroom_rules_for_user(user_id)


@lru_cache(maxsize=1)
def _lecture_text() -> str:
    return _read_text(LECTURE_TEXT_PATH, 2_000_000)


def lecture_block(article_no: int | str | None, limit: int = 12000) -> str:
    try:
        number = int(str(article_no or "").strip())
    except (TypeError, ValueError):
        return ""

    text = _lecture_text()
    if not text:
        return ""

    start_pattern = re.compile(rf"(?m)^第\s*{number}\s*条\s*$")
    start_match = start_pattern.search(text)
    if not start_match:
        return ""

    next_pattern = re.compile(r"(?m)^第\s*\d+\s*条\s*$")
    next_match = next_pattern.search(text, start_match.end())
    end = next_match.start() if next_match else len(text)
    block = text[start_match.start() : end].strip()
    return block[:limit]


def build_system_prompt() -> str:
    return "\n".join(HARD_RULES)


def hard_rules_text() -> str:
    return build_system_prompt()


def build_user_prompt(
    *,
    question: str,
    article: dict[str, Any],
    progress: dict[str, Any],
    mode: str,
    state: str,
    interaction_mode: str = "ask",
    last_assistant: str = "",
    recent_questions: list[str] | None = None,
    user_id: int | str | None = None,
) -> str:
    article_no = article.get("number") or article.get("articleNo") or progress.get("nextArticleNo")
    local_card_context = shanghan_store.article_context(article)
    lecture = lecture_block(article_no)
    rules = classroom_rules(user_id)
    recent_questions = recent_questions or []
    recent_question_text = "\n".join(f"- {item}" for item in recent_questions)

    blocks = [
        f"【必须遵守的本地读书规则】\n{rules}" if rules else "",
        f"【结构化条文卡片】\n{local_card_context}",
    ]
    if lecture:
        blocks.append(f"【本地讲稿当前条文块】\n{lecture}")
    blocks.extend(
        [
            f"【页面当前选择条文】第{article_no}条",
            f"【今日模式】{mode}",
            f"【用户状态】{state}",
            f"【数据库当前进度】下一次从第{progress.get('nextArticleNo')}条开始；当前关卡：{progress.get('currentLevel')}。如果它与页面当前选择条文或用户问题冲突，以页面当前选择和用户问题为准。",
            f"【本轮交互模式】{interaction_mode}",
            f"【上一轮老师内容，仅用于判断用户是否在作答，不要照抄或重复追问】\n{last_assistant}" if last_assistant else "",
            f"【最近已经问过的问题，禁止原样或换皮重复】\n{recent_question_text}" if recent_question_text else "",
            f"【用户本轮输入】\n{question}",
            f"【再次强调】本轮必须围绕第{article_no}条回答，不要切换到其他条文。",
        ]
    )
    if interaction_mode == "answer_feedback":
        blocks.append(
            "【输出要求】\n"
            "1. 本轮用户是在回答上一轮问题，必须点评用户答案。\n"
            "2. 禁止重新输出上一轮任务卡、原文片段或完整讲解。\n"
            "3. 固定格式：\n"
            "   ### 你的回答点评\n"
            "   - 抓得对的是：...\n"
            "   - 需要补充或纠偏的是：...\n"
            "   ### 下一小步\n"
            "   只问一个更小的问题，并且必须避开【最近已经问过的问题】。\n"
            "4. 如果用户答错，先给提示一，不要直接长篇公布答案。"
            "\n5. 如果用户是在回答小测/选择题/判断题，先简要说明对错和理由，再进入下一小步；不要重复整道题干和全部选项。"
        )
    else:
        blocks.append(
            "【输出要求】\n"
            "1. 用中文回答。\n"
            "2. 如果是在上课，必须先给任务卡或当前片段，然后停在一个问题上。\n"
            "3. 如果是在点评用户回答，先指出抓对处，再补遗漏，再给一个更小的问题。\n"
            "4. 回答要像老师带读，不要像资料库百科。\n"
            "5. 不要解释系统如何选择条文，不要重复询问用户状态。"
            "\n6. 如果输出讲稿原文节选，必须在原文内部用 [[**...**]] 标出 3-8 个重点短语，帮助阅读。"
            "\n7. 结尾只能问一个问题，且必须避开【最近已经问过的问题】；如果需要继续追问，换成病理、边界、误治、类方鉴别等不同角度。"
            "\n8. 如果本轮包含选择题或判断题，题干和选项正常展示，但标准答案只能放在隐藏机读答案里，例如 <!--QUIZ:{\"type\":\"single\",\"answer\":\"D\",\"explanation\":\"口渴想饮冷水提示合并里热，不是单纯太阳病。\"}-->。"
        )
    return "\n\n".join(block for block in blocks if block)
