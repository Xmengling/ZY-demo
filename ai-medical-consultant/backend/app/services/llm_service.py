# -*- coding: utf-8 -*-
"""LLM 服务：封装 OpenAI 兼容接口（通义千问等），并提供无 key 时的降级。"""

from __future__ import annotations

from typing import Iterator, List, Dict

from ..config import settings

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


class LLMService:
    def __init__(self):
        self._client = None
        if settings.llm_enabled and OpenAI is not None:
            try:
                self._client = OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_api_base,
                )
            except Exception:
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        """非流式对话。不可用时抛异常，由调用方降级。"""
        if self._client is None:
            raise RuntimeError("LLM 未配置")
        resp = self._client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=messages,
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()

    def stream(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> Iterator[str]:
        """流式对话，逐 token 产出。"""
        if self._client is None:
            raise RuntimeError("LLM 未配置")
        stream = self._client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content


llm_service = LLMService()
