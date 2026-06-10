# -*- coding: utf-8 -*-
"""知识库文件：整文件上传与列表（不做内容切片）。"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from ..config import BASE_DIR, settings
from ..models import KnowledgeFile
from .file_parser import (
    ALLOWED_EXTS,
    MAX_FILE_SIZE,
    FileParseError,
    _decode_text,
    _read_docx,
    get_ext,
)

UPLOAD_DIR = Path(settings.knowledge_upload_dir)
PREVIEW_MAX_CHARS = 300_000


def ensure_upload_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def _safe_filename(name: str) -> str:
    base = Path(name or "file").name
    base = re.sub(r"[^\w.\-一-龥()（）\s]", "_", base).strip() or "file"
    return base[:200]


def validate_upload(file: UploadFile, raw: bytes) -> str:
    filename = file.filename or ""
    ext = get_ext(filename)
    if ext not in ALLOWED_EXTS:
        raise FileParseError(
            f"不支持的文件类型：{ext or '未知'}（仅支持 {', '.join(sorted(ALLOWED_EXTS))}）"
        )
    if not raw:
        raise FileParseError("文件为空")
    if len(raw) > MAX_FILE_SIZE:
        raise FileParseError(f"文件超过 {MAX_FILE_SIZE // (1024 * 1024)}MB 上限")
    return filename


def save_upload(db: Session, file: UploadFile, raw: bytes) -> KnowledgeFile:
    filename = validate_upload(file, raw)
    ensure_upload_dir()
    stored_name = f"{uuid.uuid4().hex}_{_safe_filename(filename)}"
    target = UPLOAD_DIR / stored_name
    target.write_bytes(raw)

    row = KnowledgeFile(
        filename=Path(filename).name,
        stored_path=str(target.relative_to(BASE_DIR)),
        file_size=len(raw),
        content_type=file.content_type or "",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_files(db: Session) -> list[KnowledgeFile]:
    return (
        db.query(KnowledgeFile)
        .order_by(KnowledgeFile.created_at.desc(), KnowledgeFile.id.desc())
        .all()
    )


def rename_file(db: Session, file_id: int, new_filename: str) -> KnowledgeFile | None:
    row = get_file(db, file_id)
    if not row:
        return None

    name = (new_filename or "").strip()
    if not name:
        raise FileParseError("文件名不能为空")

    old_ext = get_ext(row.filename)
    new_ext = get_ext(name)
    if not new_ext and old_ext:
        name = f"{name}{old_ext}"
    elif new_ext and old_ext and new_ext != old_ext:
        raise FileParseError(f"不能修改文件扩展名，须保持 {old_ext}")

    safe_name = _safe_filename(name)
    if not safe_name:
        raise FileParseError("文件名无效")

    ext = get_ext(safe_name)
    if ext not in ALLOWED_EXTS:
        raise FileParseError(
            f"不支持的文件类型：{ext or '未知'}（仅支持 {', '.join(sorted(ALLOWED_EXTS))}）"
        )

    duplicate = (
        db.query(KnowledgeFile)
        .filter(KnowledgeFile.filename == safe_name, KnowledgeFile.id != file_id)
        .first()
    )
    if duplicate:
        raise FileParseError(f"已存在同名文件「{safe_name}」")

    row.filename = safe_name
    db.commit()
    db.refresh(row)
    return row


def delete_file(db: Session, file_id: int) -> KnowledgeFile | None:
    row = db.get(KnowledgeFile, file_id)
    if not row:
        return None
    path = BASE_DIR / row.stored_path
    if path.is_file():
        path.unlink(missing_ok=True)
    db.delete(row)
    db.commit()
    return row


def resolve_file_path(row: KnowledgeFile) -> Path:
    return BASE_DIR / row.stored_path


def get_file(db: Session, file_id: int) -> KnowledgeFile | None:
    return db.get(KnowledgeFile, file_id)


def _format_json_preview(text: str, ext: str) -> str:
    if ext == ".jsonl":
        lines: list[str] = []
        for i, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                lines.append(f"--- 第 {i} 行 ---\n{json.dumps(obj, ensure_ascii=False, indent=2)}")
            except json.JSONDecodeError:
                lines.append(f"--- 第 {i} 行 ---\n{line}")
        return "\n\n".join(lines) if lines else text
    try:
        data = json.loads(text)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return text


def _truncate_content(content: str) -> tuple[str, bool]:
    if len(content) <= PREVIEW_MAX_CHARS:
        return content, False
    return content[:PREVIEW_MAX_CHARS] + "\n\n…（内容过长，已截断预览）", True


def read_file_preview(row: KnowledgeFile) -> dict:
    path = resolve_file_path(row)
    if not path.is_file():
        raise FileParseError("文件不存在或已被删除")
    raw = path.read_bytes()
    ext = get_ext(row.filename)
    if ext not in ALLOWED_EXTS:
        raise FileParseError(f"不支持的文件类型：{ext or '未知'}")

    if ext == ".docx":
        content = _read_docx(raw)
        preview_format = "text"
    elif ext in {".json", ".jsonl"}:
        content = _format_json_preview(_decode_text(raw), ext)
        preview_format = "json"
    else:
        content = _decode_text(raw)
        preview_format = "text"

    if not content.strip():
        raise FileParseError("文件内容为空")

    content, truncated = _truncate_content(content)
    return {
        "id": row.id,
        "filename": row.filename,
        "format": preview_format,
        "content": content,
        "truncated": truncated,
    }
