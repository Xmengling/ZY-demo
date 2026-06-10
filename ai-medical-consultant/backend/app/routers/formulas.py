# -*- coding: utf-8 -*-
"""100 首方剂解读 API。"""

from __future__ import annotations

import mimetypes
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from ..deps import get_current_user
from ..models import User
from ..services import jingfang_store
from ..services.consult_knowledge import consult_knowledge
from ..services.formula_pdf_export import export_formula_cards_pdf

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
    saved = jingfang_store.save_formula(payload)
    consult_knowledge.invalidate()
    return saved


@router.put("/{formula_id}")
def update_formula(
    formula_id: str,
    payload: dict,
    _user: User = Depends(get_current_user),
):
    payload["id"] = unquote(formula_id)
    saved = jingfang_store.save_formula(payload)
    consult_knowledge.invalidate()
    return saved


@router.delete("/{formula_id}")
def remove_formula(formula_id: str, _user: User = Depends(get_current_user)):
    deleted = jingfang_store.delete_formula(unquote(formula_id))
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "formula not found")
    consult_knowledge.invalidate()
    return {"ok": True, "id": formula_id}


@router.post("/export/pdf")
def export_all_cards_pdf(
    mode: str = Query(default="searchable", pattern="^(searchable|web-hd)$"),
):
    """批量导出全部方剂卡片 PDF（与 ZY-Study 网页预览一致的可搜索版）。"""
    try:
        pdf_path = export_formula_cards_pdf(mode=mode)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name,
    )


@router.get("/herbs/{filename}")
def get_herb_image(filename: str):
    safe_name = unquote(filename).replace("\\", "/").split("/")[-1]
    target = jingfang_store.resolve_herb_file(safe_name)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "herb image not found")
    media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return FileResponse(target, media_type=media_type)
