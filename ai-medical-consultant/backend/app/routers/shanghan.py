# -*- coding: utf-8 -*-
"""《伤寒论》条文解读 API。"""

from __future__ import annotations

from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import get_current_user
from ..models import User
from ..services import shanghan_store
from ..services.consult_knowledge import consult_knowledge

router = APIRouter(prefix="/api/v1/shanghan", tags=["shanghan"])


@router.get("")
def list_articles():
    return {"articles": shanghan_store.list_articles()}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_article(payload: dict, _user: User = Depends(get_current_user)):
    saved = shanghan_store.save_article(payload)
    consult_knowledge.invalidate()
    return saved


@router.put("/{article_id}")
def update_article(
    article_id: str,
    payload: dict,
    _user: User = Depends(get_current_user),
):
    payload["id"] = unquote(article_id)
    saved = shanghan_store.save_article(payload)
    consult_knowledge.invalidate()
    return saved


@router.delete("/{article_id}")
def remove_article(article_id: str, _user: User = Depends(get_current_user)):
    deleted = shanghan_store.delete_article(unquote(article_id))
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "article not found")
    consult_knowledge.invalidate()
    return {"ok": True, "id": article_id}
