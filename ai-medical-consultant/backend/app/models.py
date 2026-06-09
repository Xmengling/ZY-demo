# -*- coding: utf-8 -*-
"""ORM 模型：用户 / 问诊会话 / 消息 / 知识库条目。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    full_name: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sessions: Mapped[list["ConsultSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ConsultSession(Base):
    __tablename__ = "consult_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(128), default="新的问诊")
    patient_name: Mapped[str] = mapped_column(String(64), default="")
    phone: Mapped[str] = mapped_column(String(32), default="")
    address: Mapped[str] = mapped_column(String(256), default="")
    gender: Mapped[str] = mapped_column(String(16), default="")
    age: Mapped[str] = mapped_column(String(16), default="")
    modern_diagnosis: Mapped[str] = mapped_column(String(256), default="")
    status: Mapped[str] = mapped_column(String(32), default="collecting")
    intake_data: Mapped[str] = mapped_column(Text, default="")
    case_text: Mapped[str] = mapped_column(Text, default="")
    # 结构化分诊结论（JSON 字符串），由 Agent 写入
    triage: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("consult_sessions.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # user / assistant
    content: Mapped[str] = mapped_column(Text)
    # 附加信息（引用来源、分诊等），JSON 字符串
    meta: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["ConsultSession"] = relationship(back_populates="messages")


class ConsultModuleHint(Base):
    """各证候采集模块后的问诊提示，可在页面编辑。"""

    __tablename__ = "consult_module_hints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_key: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    module_order: Mapped[int] = mapped_column(Integer, default=0)
    hints: Mapped[str] = mapped_column(Text, default="[]")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConsultSymptomPreset(Base):
    """问诊常见症状预设，供前端采集表动态读取。"""

    __tablename__ = "consult_symptom_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_key: Mapped[str] = mapped_column(String(32), index=True)
    module_order: Mapped[int] = mapped_column(Integer, default=0)
    module_title: Mapped[str] = mapped_column(String(64))
    module_tag: Mapped[str] = mapped_column(String(64), default="")
    module_tone: Mapped[str] = mapped_column(String(32), default="")
    block_label: Mapped[str] = mapped_column(String(32), index=True)
    block_order: Mapped[int] = mapped_column(Integer, default=0)
    symptoms: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KnowledgeCategory(Base):
    """知识库分类登记（可无条目，供上传前预建分类）。"""

    __tablename__ = "knowledge_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(128), index=True)
    department: Mapped[str] = mapped_column(String(64), default="")
    content: Mapped[str] = mapped_column(Text)
    # 来源文件名（上传导入时写入；种子数据为空），用于按来源批量删除
    source: Mapped[str] = mapped_column(String(256), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
