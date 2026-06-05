# -*- coding: utf-8 -*-
"""MedicalAgent：症状分析 + RAG 检索增强 + 方证辨证建议。

设计为可在「有 LLM」和「无 LLM（离线规则）」两种模式下均可用。
"""

from __future__ import annotations

from typing import Dict, Iterator, List, Tuple

from .knowledge_base import knowledge_base
from .llm_service import llm_service

DISCLAIMER = (
    "⚠️ 温馨提示：以上内容由 AI 依据中医方证知识库生成，仅供学习与健康参考，"
    "不能替代执业中医师的面诊与辨证。中药需在医师指导下使用；如症状持续、加重或"
    "出现危急信号，请及时前往医院就诊或拨打 120。"
)

SYSTEM_PROMPT = """你是一位严谨、有温度的中医方证问诊助手，名为「智诊」，擅长以胡希恕、李冠杰经方医学的「方证辨证」思路分析问题。你的职责是通过多轮对话收集患者症状（含舌象、脉象、寒热、汗出、二便等），结合提供的【中医知识库】给出参考性的辨证方向与可能相关的方证。

请严格遵守：
1. 仅基于【中医知识库】中的方证内容作答，不得编造未出现的方剂、药味、剂量或病机。
2. 你不能下达确定性诊断或开具处方，只能给出"可能相关的方证方向"与学习参考。
3. 若患者描述信息不足，先用 1-2 个有针对性的中医问诊问题引导补充（如恶寒/发热、有汗/无汗、口渴否、舌苔脉象、大小便、部位与诱因等）。
4. 回答用中文，结构清晰，可用如下小标题（按需）：
   - 🔎 症状与辨证理解
   - 🤔 可能相关的方证（标注"可能"，引用知识库中的方剂名，不下定论）
   - 🌿 方义/病机说明（仅依据知识库）
   - 📋 调护与就医建议
   - ❗ 需要立即就医的情况
5. 语气专业、关切，避免制造恐慌；涉及用药务必提示需中医师指导。
6. 如出现危急信号（剧烈胸痛、呼吸困难、意识改变、大出血等），首要建议立即就医/拨打120，不要依赖自行用药。
"""


class MedicalAgent:
    def _retrieve(self, query: str, k: int = 4) -> List[Dict]:
        return knowledge_base.search(query, k=k)

    def _build_context(self, docs: List[Dict]) -> str:
        if not docs:
            return "（知识库未检索到高度相关的条目）"
        parts = []
        for i, d in enumerate(docs, 1):
            content = d.get("content", "")
            if len(content) > 1400:
                content = content[:1400] + "…"
            parts.append(
                f"[{i}] 《{d.get('title','')}》（{d.get('category','')}｜{d.get('department','')}）\n{content}"
            )
        return "\n\n".join(parts)

    def _build_references(self, docs: List[Dict]) -> List[Dict]:
        return [
            {
                "title": d.get("title", ""),
                "category": d.get("category", ""),
                "department": d.get("department", ""),
                "score": round(d.get("score", 0.0), 3),
            }
            for d in docs
        ]

    def _build_messages(
        self, history: List[Dict[str, str]], user_msg: str, context: str
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in history[-8:]:
            messages.append({"role": m["role"], "content": m["content"]})
        user_block = (
            f"【中医知识库（仅可据此作答）】\n{context}\n\n"
            f"【患者本次描述】\n{user_msg}"
        )
        messages.append({"role": "user", "content": user_block})
        return messages

    def respond(self, history: List[Dict[str, str]], user_msg: str) -> Tuple[str, List[Dict]]:
        recent_user = " ".join(
            [m["content"] for m in history[-4:] if m["role"] == "user"] + [user_msg]
        )
        docs = self._retrieve(recent_user, k=4)
        context = self._build_context(docs)
        references = self._build_references(docs)

        if llm_service.available:
            try:
                messages = self._build_messages(history, user_msg, context)
                reply = llm_service.chat(messages)
                return f"{reply}\n\n{DISCLAIMER}", references
            except Exception:
                pass

        return self._fallback_reply(user_msg, docs), references

    def stream(self, history: List[Dict[str, str]], user_msg: str) -> Tuple[Iterator[str], List[Dict]]:
        recent_user = " ".join(
            [m["content"] for m in history[-4:] if m["role"] == "user"] + [user_msg]
        )
        docs = self._retrieve(recent_user, k=4)
        context = self._build_context(docs)
        references = self._build_references(docs)

        def gen() -> Iterator[str]:
            if llm_service.available:
                try:
                    messages = self._build_messages(history, user_msg, context)
                    for token in llm_service.stream(messages):
                        yield token
                    yield "\n\n" + DISCLAIMER
                    return
                except Exception:
                    pass
            yield self._fallback_reply(user_msg, docs)

        return gen(), references

    def _fallback_reply(self, user_msg: str, docs: List[Dict]) -> str:
        lines: List[str] = []
        lines.append("🔎 症状与辨证理解")
        lines.append(f"您描述的情况是：「{user_msg.strip()}」。下面是基于本地中医方证知识库的参考分析。")
        lines.append("")

        if docs:
            lines.append("🤔 可能相关的方证（仅供参考，不构成诊断/处方）")
            for d in docs[:3]:
                summary = d.get("content", "")
                summary = summary[:140] + ("…" if len(summary) > 140 else "")
                lines.append(f"- 《{d.get('title','')}》：{summary}")
            lines.append("")

        lines.append("🌿 日常调护")
        lines.append("- 注意起居有常、饮食有节、避风寒、调情志，记录症状变化（寒热、汗出、舌脉、二便等）。")
        lines.append("- 如需用药，请到中医科由医师面诊辨证后开方；症状持续或加重请及时就医。")
        lines.append("")
        lines.append(DISCLAIMER)
        return "\n".join(lines)


medical_agent = MedicalAgent()
