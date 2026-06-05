# -*- coding: utf-8 -*-
"""基于 FAISS 的医学知识向量库（内积/余弦相似度检索）。"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

import faiss
import numpy as np

from .embeddings import LocalHashEmbeddings


class FaissVectorStore:
    """封装 FAISS 索引 + 文档元数据，提供构建、保存、加载、检索。"""

    INDEX_FILE = "index.faiss"
    META_FILE = "meta.json"

    def __init__(self, dim: int = 768):
        self.dim = dim
        self.embedder = LocalHashEmbeddings(dim=dim)
        self.index: Optional[faiss.Index] = None
        self.metadatas: List[Dict] = []

    def build(self, docs: List[Dict]) -> None:
        """docs: [{title, category, department, content}, ...]"""
        texts = [self._doc_to_text(d) for d in docs]
        vectors = self.embedder.embed_documents(texts)
        index = faiss.IndexFlatIP(self.dim)
        if len(vectors) > 0:
            index.add(vectors)
        self.index = index
        self.metadatas = docs

    @staticmethod
    def _doc_to_text(d: Dict) -> str:
        return f"{d.get('title', '')} {d.get('department', '')} {d.get('content', '')}"

    def save(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, os.path.join(directory, self.INDEX_FILE))
        with open(os.path.join(directory, self.META_FILE), "w", encoding="utf-8") as f:
            json.dump(self.metadatas, f, ensure_ascii=False)

    def load(self, directory: str) -> bool:
        index_path = os.path.join(directory, self.INDEX_FILE)
        meta_path = os.path.join(directory, self.META_FILE)
        if not (os.path.exists(index_path) and os.path.exists(meta_path)):
            return False
        self.index = faiss.read_index(index_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            self.metadatas = json.load(f)
        return True

    def search(self, query: str, k: int = 4) -> List[Dict]:
        if self.index is None or not self.metadatas:
            return []
        qv = self.embedder.embed_query(query).reshape(1, -1)
        k = min(k, len(self.metadatas))
        scores, idxs = self.index.search(qv, k)
        results = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < 0:
                continue
            doc = dict(self.metadatas[idx])
            doc["score"] = float(score)
            results.append(doc)
        return results
