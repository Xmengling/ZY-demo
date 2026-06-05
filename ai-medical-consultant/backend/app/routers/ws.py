# -*- coding: utf-8 -*-
"""WebSocket 实时流式问答：/api/ws/chat?token=xxx"""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..database import SessionLocal
from ..models import ConsultSession, Message
from ..security import decode_token
from ..services.agent import medical_agent

router = APIRouter()


@router.websocket("/api/ws/chat")
async def ws_chat(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    user_id = decode_token(token)
    if user_id is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except Exception:
                await websocket.send_json({"type": "error", "message": "消息格式错误"})
                continue

            text = (data.get("message") or "").strip()
            session_id = data.get("session_id")
            if not text:
                await websocket.send_json({"type": "error", "message": "消息不能为空"})
                continue

            db = SessionLocal()
            try:
                # 取得或新建会话
                s = None
                if session_id:
                    s = db.get(ConsultSession, session_id)
                    if s and s.user_id != user_id:
                        s = None
                if s is None:
                    s = ConsultSession(user_id=user_id, title=text[:20])
                    db.add(s)
                    db.commit()
                    db.refresh(s)

                history = [{"role": m.role, "content": m.content} for m in s.messages]
                db.add(Message(session_id=s.id, role="user", content=text))
                db.commit()

                gen, references = medical_agent.stream(history, text)

                await websocket.send_json(
                    {
                        "type": "meta",
                        "session_id": s.id,
                        "references": references,
                    }
                )

                full = []
                for token_str in gen:
                    full.append(token_str)
                    await websocket.send_json({"type": "token", "content": token_str})

                reply = "".join(full)
                meta = {"references": references}
                db.add(
                    Message(
                        session_id=s.id,
                        role="assistant",
                        content=reply,
                        meta=json.dumps(meta, ensure_ascii=False),
                    )
                )
                db.commit()

                await websocket.send_json({"type": "done", "session_id": s.id})
            finally:
                db.close()
    except WebSocketDisconnect:
        return
    except Exception as e:  # pragma: no cover
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
