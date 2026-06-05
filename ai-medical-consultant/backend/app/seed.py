# -*- coding: utf-8 -*-
"""初始化种子数据：演示用户 + 知识库入库 + 构建向量索引。"""

from __future__ import annotations

from .database import SessionLocal, init_db
from .models import KnowledgeDoc, User
from .security import hash_password
from .services.knowledge_base import knowledge_base


def seed_demo_user(db) -> None:
    if not db.query(User).filter(User.username == "demo").first():
        db.add(
            User(
                username="demo",
                password_hash=hash_password("demo123"),
                full_name="演示用户",
            )
        )
        db.commit()


def seed_knowledge(db, force: bool = False) -> None:
    if force:
        db.query(KnowledgeDoc).delete()
        db.commit()
    elif db.query(KnowledgeDoc).count() > 0:
        return
    docs = knowledge_base.load_seed_docs()
    for d in docs:
        db.add(
            KnowledgeDoc(
                category=d.get("category", ""),
                title=d.get("title", ""),
                department=d.get("department", ""),
                content=d.get("content", ""),
            )
        )
    db.commit()


def run_seed(force_knowledge: bool = False) -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_demo_user(db)
        seed_knowledge(db, force=force_knowledge)
    finally:
        db.close()
    # 构建/加载向量索引
    knowledge_base.build_from_seed()


if __name__ == "__main__":
    import sys

    force = "--tcm" in sys.argv or "--force" in sys.argv
    run_seed(force_knowledge=force)
    count = len(knowledge_base.store.metadatas)
    print(f"初始化完成：演示账号 demo / demo123；知识库共 {count} 条，向量索引已就绪。")
