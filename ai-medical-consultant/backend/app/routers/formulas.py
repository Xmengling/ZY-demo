# -*- coding: utf-8 -*-
"""100 首方剂解读 API。"""

from __future__ import annotations

import mimetypes
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from ..deps import get_current_user
from ..models import User
from ..services import jingfang_store

router = APIRouter(prefix="/api/v1/formulas", tags=["formulas"])


@router.get("")
def list_formulas():
    return {
        "categories": jingfang_store.CATEGORIES,
        "formulas": jingfang_store.list_formulas(),
        "herbs": jingfang_store.list_herbs(),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_formula(payload: dict, _user: User = Depends(get_current_user)):
    return jingfang_store.save_formula(payload)


@router.put("/{formula_id}")
def update_formula(
    formula_id: str,
    payload: dict,
    _user: User = Depends(get_current_user),
):
    payload["id"] = unquote(formula_id)
    return jingfang_store.save_formula(payload)


@router.delete("/{formula_id}")
def remove_formula(formula_id: str, _user: User = Depends(get_current_user)):
    deleted = jingfang_store.delete_formula(unquote(formula_id))
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "formula not found")
    return {"ok": True, "id": formula_id}


@router.get("/herbs/{filename}")
def get_herb_image(filename: str):
    safe_name = unquote(filename).replace("\\", "/").split("/")[-1]
    target = jingfang_store.resolve_herb_file(safe_name)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "herb image not found")
    media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return FileResponse(target, media_type=media_type)
