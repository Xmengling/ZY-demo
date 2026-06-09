#!/usr/bin/env python3
"""本地方剂网页服务，仅供 PDF 导出脚本使用（只读、无需登录）。"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "ai-medical-consultant/backend"
WEB_DIR = PROJECT_ROOT / "ai-medical-consultant/frontend/public/jingfang"

sys.path.insert(0, str(BACKEND_ROOT))
from app.services import jingfang_store  # noqa: E402

jingfang_store.ensure_ready()

HOST = os.getenv("JINGFANG_EXPORT_HOST", "127.0.0.1")
PORT = int(os.getenv("JINGFANG_EXPORT_PORT", "15188"))


class Handler(BaseHTTPRequestHandler):
    def send_json(self, body: object, status: int = 200) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        if path.suffix.lower() in {".html", ".css", ".js"}:
            self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path in ("/api/v1/formulas", "/api/formulas"):
            self.send_json(
                {
                    "categories": jingfang_store.CATEGORIES,
                    "formulas": jingfang_store.list_formulas(),
                    "herbs": jingfang_store.list_herbs(),
                }
            )
            return

        if path.startswith("/api/v1/formulas/herbs/"):
            filename = path.removeprefix("/api/v1/formulas/herbs/").replace("\\", "/").split("/")[-1]
            target = jingfang_store.resolve_herb_file(filename)
            if target is None:
                self.send_error(404)
                return
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self.send_file(target, content_type)
            return

        if path in ("/", "/index.html"):
            self.send_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
            return

        target = (WEB_DIR / path.lstrip("/")).resolve()
        if WEB_DIR.resolve() in target.parents and target.exists():
            types = {
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".json": "application/json; charset=utf-8",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
                ".svg": "image/svg+xml",
            }
            self.send_file(target, types.get(target.suffix.lower(), "application/octet-stream"))
            return

        self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Jingfang export server running at http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
