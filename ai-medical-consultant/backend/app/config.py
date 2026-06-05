# -*- coding: utf-8 -*-
"""应用配置：统一从环境变量 / .env 读取。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    openai_api_key: str = ""
    openai_api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    openai_chat_model: str = "qwen-plus"

    # App
    database_url: str = "sqlite:///./medical.db"
    jwt_secret: str = "dev-secret-please-change"
    jwt_expire_minutes: int = 1440
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # 向量库目录
    vectorstore_dir: str = str(BASE_DIR / "vectorstore")
    # 知识库种子文件：默认中医方证知识库（由 ingest_tcm.py 生成）
    knowledge_file: str = str(BASE_DIR / "data" / "tcm_knowledge.json")

    # 100 首方剂解读（SQLite + 中药图片）
    jingfang_db_path: str = str(BASE_DIR / "data" / "jingfang.sqlite3")
    jingfang_source_db: str = r"D:\AI\ZY-Study\web\db\jingfang.sqlite3"
    jingfang_herb_dir: str = r"D:\AI\ZY-Study\img\伤寒金匮方剂思维导图"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        """是否配置了可用的 LLM。未配置时系统自动降级为规则回答。"""
        return bool(self.openai_api_key and self.openai_api_key.startswith("sk-"))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
