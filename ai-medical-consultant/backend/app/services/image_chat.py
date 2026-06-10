# -*- coding: utf-8 -*-
"""AI 问答图片：校验与多模态消息组装。"""

from __future__ import annotations

import base64
import re
from typing import Any, Dict, List

MAX_IMAGES = 4
MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}

_DATA_URL_RE = re.compile(
    r"^data:(image/(?:jpeg|png|webp|gif));base64,([A-Za-z0-9+/=\s]+)$",
    re.IGNORECASE,
)


class ImageValidationError(ValueError):
    pass


def validate_image_data_urls(urls: List[str]) -> List[str]:
    if len(urls) > MAX_IMAGES:
        raise ImageValidationError(f"最多上传 {MAX_IMAGES} 张图片")
    cleaned: List[str] = []
    for raw in urls:
        url = str(raw or "").strip()
        if not url:
            continue
        match = _DATA_URL_RE.match(url)
        if not match:
            raise ImageValidationError("图片格式无效，请使用 jpg / png / webp / gif")
        mime = match.group(1).lower()
        if mime not in ALLOWED_IMAGE_MIME:
            raise ImageValidationError("不支持的图片类型")
        try:
            payload = base64.b64decode(match.group(2), validate=True)
        except Exception as exc:
            raise ImageValidationError("图片数据无法解析") from exc
        if len(payload) > MAX_IMAGE_BYTES:
            raise ImageValidationError(f"单张图片不能超过 {MAX_IMAGE_BYTES // (1024 * 1024)}MB")
        cleaned.append(f"data:{mime};base64,{match.group(2).strip()}")
    return cleaned


def build_user_content(text: str, images: List[str] | None = None) -> str | List[Dict[str, Any]]:
    images = images or []
    if not images:
        return text
    parts: List[Dict[str, Any]] = []
    if text:
        parts.append({"type": "text", "text": text})
    for url in images:
        parts.append({"type": "image_url", "image_url": {"url": url}})
    return parts


def message_to_llm(role: str, content: str, meta: dict | None = None) -> Dict[str, Any]:
    meta = meta or {}
    images = meta.get("images") if isinstance(meta.get("images"), list) else []
    images = [str(item) for item in images if str(item).strip()]
    if role == "user" and images:
        return {"role": "user", "content": build_user_content(content, images)}
    return {"role": role, "content": content}
