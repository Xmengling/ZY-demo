# -*- coding: utf-8 -*-
"""知识库管理：构建/加载 FAISS 向量库，提供检索。进程内单例。"""

from __future__ import annotations

import json
import os
from typing import Dict, List

from ..config import settings
from .vector_store import FaissVectorStore


class KnowledgeBase:
    def __init__(self):
        self.store = FaissVectorStore(dim=768)
        self._ready = False

    def load_seed_docs(self) -> List[Dict]:
        if not os.path.exists(settings.knowledge_file):
            return []
        with open(settings.knowledge_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def build_from_seed(self) -> int:
        docs = self.load_seed_docs()
        self.store.build(docs)
        self.store.save(settings.vectorstore_dir)
        self._ready = True
        return len(docs)

    def ensure_ready(self) -> None:
        """优先加载已有索引，没有则用种子数据构建。"""
        if self._ready:
            return
        if self.store.load(settings.vectorstore_dir):
            self._ready = True
        else:
            self.build_from_seed()

    def rebuild_from_docs(self, docs: List[Dict]) -> int:
        """用数据库中的全部文档重建索引（知识库新增后调用）。"""
        self.store.build(docs)
        self.store.save(settings.vectorstore_dir)
        self._ready = True
        return len(docs)

    def search(self, query: str, k: int = 4) -> List[Dict]:
        self.ensure_ready()
        return self.store.search(query, k=k)


knowledge_base = KnowledgeBase()
