# -*- coding: utf-8 -*-
"""问诊附件：图片与文件上传、读取、删除。"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from fastapi.responses import FileResponse

from ..config import settings

ATTACHMENT_DIR = Path(settings.consult_attachment_dir)
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".heif"}
FILE_EXTS = {
    ".pdf",
    ".doc",
    ".docx",
    ".txt",
    ".md",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".rar",
    ".7z",
    ".csv",
}
ALLOWED_EXTS = IMAGE_EXTS | FILE_EXTS
MAX_FILE_SIZE = 20 * 1024 * 1024


class ConsultAttachmentError(Exception):
    pass


def get_ext(filename: str) -> str:
    name = (filename or "").lower()
    dot = name.rfind(".")
    return name[dot:] if dot >= 0 else ""


def _safe_filename(name: str) -> str:
    base = Path(name or "file").name
    base = re.sub(r"[^\w.\-一-龥()（）\s]", "_", base).strip() or "file"
    return base[:180]


def _session_dir(session_id: int) -> Path:
    return ATTACHMENT_DIR / str(session_id)


def _stored_path(session_id: int, attachment_id: str, filename: str) -> Path:
    return _session_dir(session_id) / f"{attachment_id}_{_safe_filename(filename)}"


def _resolve_stored_path(session_id: int, attachment_id: str) -> Path | None:
    folder = _session_dir(session_id)
    if not folder.is_dir():
        return None
    prefix = f"{attachment_id}_"
    matches = [path for path in folder.iterdir() if path.is_file() and path.name.startswith(prefix)]
    return matches[0] if matches else None


def _guess_mime(filename: str, content_type: str) -> str:
    if content_type:
        return content_type.split(";", 1)[0].strip().lower()
    ext = get_ext(filename)
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    return mapping.get(ext, "application/octet-stream")


def validate_upload(file: UploadFile, raw: bytes) -> str:
    filename = file.filename or ""
    ext = get_ext(filename)
    if ext not in ALLOWED_EXTS:
        allowed = ", ".join(sorted(ALLOWED_EXTS))
        raise ConsultAttachmentError(f"不支持的文件类型：{ext or '未知'}（支持 {allowed}）")
    if not raw:
        raise ConsultAttachmentError("文件为空")
    if len(raw) > MAX_FILE_SIZE:
        raise ConsultAttachmentError(f"文件超过 {MAX_FILE_SIZE // (1024 * 1024)}MB 上限")
    return Path(filename).name


def save_attachment(session_id: int, file: UploadFile, raw: bytes) -> dict:
    filename = validate_upload(file, raw)
    attachment_id = uuid.uuid4().hex
    folder = _session_dir(session_id)
    folder.mkdir(parents=True, exist_ok=True)
    target = _stored_path(session_id, attachment_id, filename)
    target.write_bytes(raw)
    mime_type = _guess_mime(filename, file.content_type or "")
    return {
        "id": attachment_id,
        "name": filename,
        "size": len(raw),
        "mimeType": mime_type,
        "isImage": get_ext(filename) in IMAGE_EXTS,
        "uploadedAt": datetime.now(timezone.utc).isoformat(),
    }


def delete_attachment(session_id: int, attachment_id: str) -> bool:
    path = _resolve_stored_path(session_id, attachment_id)
    if not path:
        return False
    path.unlink(missing_ok=True)
    folder = _session_dir(session_id)
    if folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()
    return True


def build_file_response(session_id: int, attachment_id: str, *, inline: bool = True) -> FileResponse:
    path = _resolve_stored_path(session_id, attachment_id)
    if not path or not path.is_file():
        raise ConsultAttachmentError("附件不存在或已被删除")
    filename = path.name.split("_", 1)[-1]
    media_type = _guess_mime(filename, "")
    disposition = "inline" if inline else "attachment"
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )


def read_attachment_path(session_id: int, attachment_id: str) -> Path | None:
    return _resolve_stored_path(session_id, attachment_id)


def read_attachment_bytes(session_id: int, attachment_id: str) -> tuple[bytes, str] | None:
    path = _resolve_stored_path(session_id, attachment_id)
    if not path or not path.is_file():
        return None
    filename = path.name.split("_", 1)[-1]
    return path.read_bytes(), filename


def remove_session_attachments(session_id: int) -> None:
    folder = _session_dir(session_id)
    if not folder.is_dir():
        return
    for path in folder.iterdir():
        if path.is_file():
            path.unlink(missing_ok=True)
    folder.rmdir()
