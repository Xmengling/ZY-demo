# -*- coding: utf-8 -*-
"""医学知识库：列表、检索、新增（新增后重建向量索引）。"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import KnowledgeCategory, KnowledgeDoc, User
from ..schemas import (
    CategoryCreate,
    CategoryRename,
    KnowledgeCreate,
    KnowledgeListPage,
    KnowledgeOut,
    KnowledgeSearchResult,
)
from ..services.file_parser import (
    ALLOWED_EXTS,
    FileParseError,
    get_ext,
    parse_file,
)
from ..services.knowledge_base import knowledge_base

_VALID_STRATEGIES = {"fixed", "paragraph", "separator", "whole"}
_CATEGORY_MAX_LEN = 64


def _normalize_category_name(name: str) -> str:
    cat = (name or "").strip()
    if not cat:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "分类名称不能为空")
    if len(cat) > _CATEGORY_MAX_LEN:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"分类名称不能超过 {_CATEGORY_MAX_LEN} 个字符",
        )
    return cat


def _category_names_with_counts(db: Session) -> dict[str, int]:
    rows = (
        db.query(KnowledgeDoc.category, func.count(KnowledgeDoc.id))
        .group_by(KnowledgeDoc.category)
        .all()
    )
    return {cat: cnt for cat, cnt in rows if cat}


def _list_categories_merged(db: Session) -> list[dict]:
    counts = _category_names_with_counts(db)
    registry = {r.name for r in db.query(KnowledgeCategory.name).all()}
    all_names = set(counts.keys()) | registry
    items = [{"name": n, "count": counts.get(n, 0)} for n in all_names]
    items.sort(key=lambda x: (-x["count"], x["name"]))
    return items


def _build_chunk_config(
    strategy: str, size: int, overlap: int, separators: str
) -> dict:
    strategy = (strategy or "fixed").strip()
    if strategy not in _VALID_STRATEGIES:
        strategy = "fixed"
    seps = [s.strip() for s in (separators or "").splitlines() if s.strip()]
    # 按分隔符切片：默认不在块内按长度二次截断，避免把同一方剂切成多段
    if strategy == "separator":
        chunk_size = 0
        chunk_overlap = 0
    else:
        chunk_size = max(50, min(int(size or 600), 5000))
        chunk_overlap = max(0, min(int(overlap or 0), 1000))
    return {
        "strategy": strategy,
        "size": chunk_size,
        "overlap": chunk_overlap,
        "separators": seps,
    }

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


def _rebuild_index(db: Session) -> None:
    docs = [
        {
            "title": d.title,
            "category": d.category,
            "department": d.department,
            "content": d.content,
        }
        for d in db.query(KnowledgeDoc).all()
    ]
    knowledge_base.rebuild_from_docs(docs)


@router.get("", response_model=KnowledgeListPage)
def list_knowledge(
    category: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(KnowledgeDoc)
    if category:
        q = q.filter(KnowledgeDoc.category == category)
    total = q.count()
    pages = max(1, (total + page_size - 1) // page_size) if total else 1
    page = min(page, pages)
    offset = (page - 1) * page_size
    rows = (
        q.order_by(KnowledgeDoc.id)
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return KnowledgeListPage(
        items=[KnowledgeOut.model_validate(d) for d in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    """分类列表（含空分类登记）及每个分类下的片段数量。"""
    return _list_categories_merged(db)


@router.post("/categories")
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """新建空分类，便于上传前预先规划分类结构。"""
    name = _normalize_category_name(payload.name)
    if db.query(KnowledgeDoc).filter(KnowledgeDoc.category == name).first():
        raise HTTPException(status.HTTP_409_CONFLICT, f"分类「{name}」已存在")
    if db.query(KnowledgeCategory).filter(KnowledgeCategory.name == name).first():
        raise HTTPException(status.HTTP_409_CONFLICT, f"分类「{name}」已存在")
    db.add(KnowledgeCategory(name=name))
    db.commit()
    return {"name": name, "count": 0, "message": f"已创建分类「{name}」"}


@router.patch("/categories")
def rename_category(
    payload: CategoryRename,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """重命名分类：同步更新该分类下全部知识条目，并重建向量索引。"""
    old_name = _normalize_category_name(payload.old_name)
    new_name = _normalize_category_name(payload.new_name)
    if old_name == new_name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "新名称不能与旧名称相同")

    has_old_docs = (
        db.query(KnowledgeDoc.id).filter(KnowledgeDoc.category == old_name).first()
        is not None
    )
    has_old_reg = (
        db.query(KnowledgeCategory.id)
        .filter(KnowledgeCategory.name == old_name)
        .first()
        is not None
    )
    if not has_old_docs and not has_old_reg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"未找到分类「{old_name}」")

    if (
        db.query(KnowledgeDoc.id).filter(KnowledgeDoc.category == new_name).first()
        is not None
        or db.query(KnowledgeCategory.id)
        .filter(KnowledgeCategory.name == new_name)
        .first()
        is not None
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, f"分类「{new_name}」已存在")

    updated = (
        db.query(KnowledgeDoc)
        .filter(KnowledgeDoc.category == old_name)
        .update({KnowledgeDoc.category: new_name}, synchronize_session=False)
    )
    reg = (
        db.query(KnowledgeCategory).filter(KnowledgeCategory.name == old_name).first()
    )
    if reg:
        reg.name = new_name
    db.commit()
    if updated:
        _rebuild_index(db)
    return {
        "old_name": old_name,
        "new_name": new_name,
        "updated": updated,
        "message": f"已将分类「{old_name}」重命名为「{new_name}」（更新 {updated} 条）",
    }


@router.get("/search", response_model=List[KnowledgeSearchResult])
def search_knowledge(q: str = Query(..., min_length=1), k: int = 5):
    docs = knowledge_base.search(q, k=k)
    results = []
    for d in docs:
        content = d.get("content", "")
        results.append(
            KnowledgeSearchResult(
                title=d.get("title", ""),
                category=d.get("category", ""),
                department=d.get("department", ""),
                snippet=content[:160] + ("…" if len(content) > 160 else ""),
                score=round(d.get("score", 0.0), 3),
            )
        )
    return results


@router.post("", response_model=KnowledgeOut)
def create_knowledge(
    payload: KnowledgeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = KnowledgeDoc(
        category=payload.category,
        title=payload.title,
        department=payload.department,
        content=payload.content,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    _rebuild_index(db)
    return KnowledgeOut.model_validate(doc)


def _read_upload(file: UploadFile) -> tuple[str, str]:
    filename = file.filename or ""
    ext = get_ext(filename)
    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"不支持的文件类型：{ext or '未知'}（仅支持 {', '.join(sorted(ALLOWED_EXTS))}）",
        )
    return filename, ext


@router.post("/preview")
async def preview_knowledge(
    file: UploadFile = File(...),
    category: str = Form(default="上传资料"),
    chunk_strategy: str = Form(default="fixed"),
    chunk_size: int = Form(default=600),
    chunk_overlap: int = Form(default=100),
    separators: str = Form(default=""),
    user: User = Depends(get_current_user),
):
    """仅解析+切片，不入库；返回片段数与前几片预览，供上传前调参。"""
    filename, _ = _read_upload(file)
    raw = await file.read()
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "文件为空")

    category = (category or "上传资料").strip() or "上传资料"
    config = _build_chunk_config(chunk_strategy, chunk_size, chunk_overlap, separators)
    try:
        docs = parse_file(filename, raw, default_category=category, chunk_config=config)
    except FileParseError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    preview = [
        {
            "title": d.get("title", ""),
            "length": len(d.get("content", "")),
            "snippet": d.get("content", "")[:200] + ("…" if len(d.get("content", "")) > 200 else ""),
        }
        for d in docs[:5]
    ]
    return {
        "filename": filename,
        "strategy": config["strategy"],
        "total": len(docs),
        "preview": preview,
    }


@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    category: str = Form(default="上传资料"),
    chunk_strategy: str = Form(default="fixed"),
    chunk_size: int = Form(default=600),
    chunk_overlap: int = Form(default=100),
    separators: str = Form(default=""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """上传文件导入知识库：解析 → 切片 → 入库 → 重建向量索引。

    支持类型：txt / md / docx / json(jsonl)。
    切片方式：fixed（固定长度）/ paragraph（按段落）/ separator（按分隔符）/ whole（整篇不切）。
    """
    filename, _ = _read_upload(file)
    raw = await file.read()
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "文件为空")

    category = (category or "上传资料").strip() or "上传资料"
    config = _build_chunk_config(chunk_strategy, chunk_size, chunk_overlap, separators)
    try:
        docs = parse_file(filename, raw, default_category=category, chunk_config=config)
    except FileParseError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    if not docs:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "未从文件中解析到有效内容")

    for d in docs:
        db.add(
            KnowledgeDoc(
                category=d.get("category", category),
                title=d.get("title", ""),
                department=d.get("department", ""),
                content=d.get("content", ""),
                source=filename,
            )
        )
    db.commit()
    _rebuild_index(db)

    return {
        "filename": filename,
        "category": category,
        "chunks": len(docs),
        "message": f"已导入 {len(docs)} 条知识片段",
    }


@router.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    """列出上传来源文件及其片段数（仅含通过上传导入、source 非空的条目）。"""
    rows = (
        db.query(
            KnowledgeDoc.source,
            func.count(KnowledgeDoc.id),
            func.min(KnowledgeDoc.category),
        )
        .filter(KnowledgeDoc.source != "")
        .group_by(KnowledgeDoc.source)
        .order_by(func.count(KnowledgeDoc.id).desc())
        .all()
    )
    return [
        {"source": src, "count": cnt, "category": cat or ""}
        for src, cnt, cat in rows
    ]


@router.delete("/source")
def delete_source(
    source: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按来源文件批量删除其导入的全部片段，并重建向量索引。"""
    deleted = (
        db.query(KnowledgeDoc)
        .filter(KnowledgeDoc.source == source)
        .delete(synchronize_session=False)
    )
    db.commit()
    if deleted == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "未找到该来源的知识条目")
    _rebuild_index(db)
    return {"source": source, "deleted": deleted, "message": f"已删除 {deleted} 条"}


@router.delete("/category")
def delete_category(
    category: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除指定分类下的全部知识片段，并重建向量索引。"""
    cat = _normalize_category_name(category)
    deleted = (
        db.query(KnowledgeDoc)
        .filter(KnowledgeDoc.category == cat)
        .delete(synchronize_session=False)
    )
    reg_deleted = (
        db.query(KnowledgeCategory)
        .filter(KnowledgeCategory.name == cat)
        .delete(synchronize_session=False)
    )
    db.commit()
    if deleted == 0 and reg_deleted == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "未找到该分类")
    if deleted:
        _rebuild_index(db)
    msg = f"已删除分类「{cat}」"
    if deleted:
        msg += f"下的 {deleted} 条片段"
    elif reg_deleted:
        msg += "（空分类）"
    return {"category": cat, "deleted": deleted, "message": msg}
