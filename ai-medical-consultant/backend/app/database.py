# -*- coding: utf-8 -*-
"""数据库连接与会话管理（SQLAlchemy 2.0）。"""

from __future__ import annotations

import json

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖：提供请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  确保模型注册到 metadata

    Base.metadata.create_all(bind=engine)
    _run_lightweight_migrations()


def _run_lightweight_migrations() -> None:
    """对已存在的表做最小列补齐（适配 SQLite，无需 Alembic）。"""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    if "consult_sessions" in table_names:
        columns = {c["name"] for c in inspector.get_columns("consult_sessions")}
        consult_columns = {
            "patient_name": "VARCHAR(64) DEFAULT ''",
            "phone": "VARCHAR(32) DEFAULT ''",
            "address": "VARCHAR(256) DEFAULT ''",
            "gender": "VARCHAR(16) DEFAULT ''",
            "age": "VARCHAR(16) DEFAULT ''",
            "modern_diagnosis": "VARCHAR(256) DEFAULT ''",
            "status": "VARCHAR(32) DEFAULT 'collecting'",
            "intake_data": "TEXT DEFAULT ''",
            "case_text": "TEXT DEFAULT ''",
        }
        with engine.begin() as conn:
            for name, column_type in consult_columns.items():
                if name not in columns:
                    conn.execute(
                        text(f"ALTER TABLE consult_sessions ADD COLUMN {name} {column_type}")
                    )

    if "knowledge_docs" not in table_names:
        _seed_consult_symptom_presets(table_names)
        _seed_consult_module_hints(table_names)
        return
    columns = {c["name"] for c in inspector.get_columns("knowledge_docs")}
    with engine.begin() as conn:
        if "source" not in columns:
            conn.execute(
                text("ALTER TABLE knowledge_docs ADD COLUMN source VARCHAR(256) DEFAULT ''")
            )
    _seed_consult_symptom_presets(table_names)
    _seed_consult_module_hints(table_names)
    _patch_consult_ui_defaults(table_names)


def _seed_consult_symptom_presets(table_names: set[str]) -> None:
    if "consult_symptom_presets" not in table_names:
        return
    presets = [
        ("surface", 2, "表证", "表虚/表实", "tone-blue", "表虚", 1, ["恶风", "汗出", "自汗", "发热", "头痛", "鼻鸣", "干呕", "脉浮缓", "脉浮弱", "项背不舒", "身体痒", "啬啬恶寒"]),
        ("surface", 2, "表证", "表虚/表实", "tone-green", "表实", 2, ["恶寒", "发热", "无汗", "头痛", "身痛", "骨节疼痛", "项背强", "喘", "咳嗽", "脉浮紧", "脉浮数", "不得平卧"]),
        ("interior", 3, "里证", "里热/里寒/里虚/里实", "tone-amber", "里热", 1, ["口渴喜冷", "口苦", "烦躁", "便秘", "大便臭秽", "尿赤", "舌红苔黄", "蒸蒸发热", "反酸", "肛门灼热"]),
        ("interior", 3, "里证", "里热/里寒/里虚/里实", "tone-blue", "里寒", 2, ["畏寒", "喜热饮", "口不渴", "下利清谷", "腹痛喜温", "四肢厥冷", "舌淡苔白", "呕吐清水", "涎沫", "小便清长"]),
        ("interior", 3, "里证", "里热/里寒/里虚/里实", "tone-green", "里虚", 3, ["食少纳呆", "乏力", "自汗", "懒言", "面色萎黄", "不欲食", "腹软喜按", "便溏", "心悸", "脉弱"]),
        ("interior", 3, "里证", "里热/里寒/里虚/里实", "tone-red", "里实", 4, ["腹满痛", "便秘拒按", "潮热谵语", "大便硬", "舌苔厚腻", "按之疼痛", "嗳气腐臭", "心下痞硬", "不大便", "脉沉实"]),
        ("half", 4, "半证", "半热", "tone-blue", "半热", 1, ["胸胁苦满", "往来寒热", "口苦", "咽干", "目眩", "心烦", "默默不欲饮食", "喜呕", "胸闷", "低热", "胸胁不舒", "脉弦"]),
        ("water", 5, "水证", "水虚/水实", "tone-green", "水虚", 1, ["口干不欲饮", "小便清长", "夜尿频", "水肿按之陷", "眩晕", "消瘦", "腰膝酸软", "畏寒", "脉沉细"]),
        ("water", 5, "水证", "水虚/水实", "tone-amber", "水实", 2, ["小便不利", "心下悸", "痰多", "水肿", "呕吐清水", "身重", "饮水即胀", "咳喘痰白", "头眩", "脉沉滑"]),
        ("qi", 6, "气证", "气虚/气实", "tone-green", "气虚", 1, ["短气乏力", "声低", "懒言", "自汗", "动则喘", "面色白", "食欲差", "脉弱", "倦怠"]),
        ("qi", 6, "气证", "气虚/气实", "tone-amber", "气实", 2, ["胀满", "嗳气", "气上冲", "胸闷", "咽中如有物", "叹息", "情绪加重", "胁胀", "胸满", "脉弦"]),
        ("blood", 7, "血证", "血虚/血实", "tone-green", "血虚", 1, ["面色萎黄", "心悸失眠", "头晕", "经量少", "爪甲不荣", "唇色淡", "乏力", "脉细", "肌肤甲错"]),
        ("blood", 7, "血证", "血虚/血实", "tone-red", "血实", 2, ["刺痛固定", "少腹急结", "舌暗紫", "口唇暗", "经血块", "皮下瘀斑", "夜间痛甚", "出血", "脉涩", "拒按"]),
        ("yin", 8, "阴性", "阴性证据", "tone-amber", "阴性", 1, ["精神疲惫", "嗜睡", "萎靡", "懒言", "倦怠", "面色白", "声低", "脉微细", "不欲动"]),
    ]
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT COUNT(*) FROM consult_symptom_presets")).scalar()
        if exists:
            return
        for module_key, module_order, module_title, module_tag, module_tone, block_label, block_order, symptoms in presets:
            conn.execute(
                text(
                    """
                    INSERT INTO consult_symptom_presets
                    (module_key, module_order, module_title, module_tag, module_tone, block_label, block_order, symptoms, created_at)
                    VALUES
                    (:module_key, :module_order, :module_title, :module_tag, :module_tone, :block_label, :block_order, :symptoms, CURRENT_TIMESTAMP)
                    """
                ),
                {
                    "module_key": module_key,
                    "module_order": module_order,
                    "module_title": module_title,
                    "module_tag": module_tag,
                    "module_tone": module_tone,
                    "block_label": block_label,
                    "block_order": block_order,
                    "symptoms": json.dumps(symptoms, ensure_ascii=False),
                },
            )


def _seed_consult_module_hints(table_names: set[str]) -> None:
    if "consult_module_hints" not in table_names:
        return
    hints_rows = [
        (
            "surface",
            2,
            [
                "寒热",
                "汗出",
                "恶风",
                "头痛头晕",
                "皮肤",
                "身痒",
                "肢凉怕冷",
                "疼痛",
                "鼻塞流涕",
                "咽痒咳嗽",
                "项背不舒",
                "无汗恶寒",
            ],
        ),
        (
            "interior",
            3,
            ["食欲、食冷、反酸烧心，呕吐、大便、肠鸣等"],
        ),
        (
            "half",
            4,
            [
                "往来寒热",
                "胸胁苦满",
                "口苦咽干",
                "目眩心烦",
                "喜呕纳差",
                "默默不欲饮食",
                "腹满便溏",
            ],
        ),
        (
            "water",
            5,
            [
                "小便频次颜色",
                "口渴饮水欲",
                "水肿按之",
                "痰饮咳喘",
                "眩晕头重",
                "心悸短气",
                "身重乏力",
            ],
        ),
        (
            "qi",
            6,
            [
                "胀满",
                "嗳气叹息",
                "胸闷气短",
                "气上冲",
                "咽中梗阻",
                "情志因素",
                "胁肋不舒",
            ],
        ),
        (
            "blood",
            7,
            [
                "疼痛性质",
                "固定刺痛",
                "出血瘀斑",
                "月经血块",
                "面色唇甲",
                "心悸眩晕",
                "肌肤甲错",
            ],
        ),
        (
            "yin",
            8,
            [
                "畏寒肢冷",
                "精神萎靡",
                "嗜睡乏力",
                "四逆冷汗",
                "下利清谷",
                "脉微细",
                "不欲动",
            ],
        ),
    ]
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT COUNT(*) FROM consult_module_hints")).scalar()
        if exists:
            return
        for module_key, module_order, hints in hints_rows:
            conn.execute(
                text(
                    """
                    INSERT INTO consult_module_hints
                    (module_key, module_order, hints, updated_at)
                    VALUES
                    (:module_key, :module_order, :hints, CURRENT_TIMESTAMP)
                    """
                ),
                {
                    "module_key": module_key,
                    "module_order": module_order,
                    "hints": json.dumps(hints, ensure_ascii=False),
                },
            )


def _patch_consult_ui_defaults(table_names: set[str]) -> None:
    """幂等同步：模块标题去掉「采集」、里证默认提示。"""
    if "consult_symptom_presets" in table_names:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE consult_symptom_presets SET module_title = REPLACE(module_title, '采集', '') "
                    "WHERE module_title LIKE '%采集'"
                )
            )
    if "consult_module_hints" in table_names:
        interior_hints = json.dumps(["食欲、食冷、反酸烧心，呕吐、大便、肠鸣等"], ensure_ascii=False)
        with engine.begin() as conn:
            raw = conn.execute(
                text("SELECT hints FROM consult_module_hints WHERE module_key = 'interior'")
            ).scalar()
            if raw and "口渴饮水" in raw:
                conn.execute(
                    text(
                        """
                        UPDATE consult_module_hints
                        SET hints = :hints, updated_at = CURRENT_TIMESTAMP
                        WHERE module_key = 'interior'
                        """
                    ),
                    {"hints": interior_hints},
                )
