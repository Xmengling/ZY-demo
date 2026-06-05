# -*- coding: utf-8 -*-
"""本地哈希向量：零模型下载，结合字符 bigram 提升中文检索区分度。"""

from __future__ import annotations

import hashlib
from typing import List

import numpy as np


class LocalHashEmbeddings:
    """将文本按字符及相邻字符二元组哈希到固定维度向量，并做 L2 归一化。"""

    def __init__(self, dim: int = 768):
        self.dim = dim

    def _tokens(self, text: str) -> List[str]:
        chars = list(text)
        bigrams = [text[i : i + 2] for i in range(len(text) - 1)]
        return chars + bigrams

    def embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        if not text:
            return vec
        for tok in self._tokens(text):
            digest = hashlib.md5(tok.encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % self.dim
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.vstack([self.embed(t) for t in texts])

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed(text)
