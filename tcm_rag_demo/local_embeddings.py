# -*- coding: utf-8 -*-
"""
纯本地哈希向量：零模型下载，入门演示可运行。
"""

from __future__ import annotations

import hashlib
from typing import List

import numpy as np
from langchain_core.embeddings import Embeddings


class LocalHashEmbeddings(Embeddings):
    """将文本按字符哈希到固定维度向量，并做 L2 归一化。"""

    def __init__(self, dim: int = 768):
        self.dim = dim

    def _text_to_vec(self, text: str) -> List[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        if not text:
            return vec.tolist()

        for ch in text:
            digest = hashlib.md5(ch.encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % self.dim
            vec[idx] += 1.0

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._text_to_vec(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._text_to_vec(text)
