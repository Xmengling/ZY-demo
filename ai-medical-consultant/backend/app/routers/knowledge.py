# -*- coding: utf-8 -*-
"""知识库：整文件上传与文件列表。"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import KnowledgeFileOut, KnowledgeFilePreviewOut
from ..services.file_parser import FileParseError
from ..services.consult_knowledge import consult_knowledge
from ..services.knowledge_files import delete_file, get_file, list_files, read_file_preview, save_upload

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.get("/files", response_model=List[KnowledgeFileOut])
def list_knowledge_files(db: Session = Depends(get_db)):
    return [KnowledgeFileOut.model_validate(row) for row in list_files(db)]


@router.post("/upload", response_model=KnowledgeFileOut)
async def upload_knowledge_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    raw = await file.read()
    try:
        row = save_upload(db, file, raw)
    except FileParseError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    consult_knowledge.invalidate()
    return KnowledgeFileOut.model_validate(row)


@router.get("/files/{file_id}/preview", response_model=KnowledgeFilePreviewOut)
def preview_knowledge_file(file_id: int, db: Session = Depends(get_db)):
    row = get_file(db, file_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文件不存在")
    try:
        preview = read_file_preview(row)
    except FileParseError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return KnowledgeFilePreviewOut.model_validate(preview)


@router.delete("/files/{file_id}")
def remove_knowledge_file(
    file_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = delete_file(db, file_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文件不存在")
    consult_knowledge.invalidate()
    return {"id": file_id, "filename": row.filename, "message": f"已删除「{row.filename}」"}
