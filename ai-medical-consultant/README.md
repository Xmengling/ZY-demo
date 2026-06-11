# AI Medical Consultant · AI 智能问诊系统

基于 **LLM 大模型 + Agent 架构 + RAG 检索增强** 的智能医疗问诊系统。

> ⚠️ 本项目仅用于学习/演示，AI 生成内容不能替代执业医师的诊断。如有不适请及时就医。

技术栈：**Vue3 + Element Plus + Pinia**（前端） / **FastAPI + SQLAlchemy**（后端） / **通义千问（OpenAI 兼容）+ FAISS 向量检索**（AI）

---

## ✨ 功能特性

| 模块 | 说明 |
| --- | --- |
| 🤖 智能问诊 | 多轮对话收集症状/舌脉，Agent 以「方证辨证」思路结合知识库分析，**WebSocket 流式输出** |
| 📚 知识库检索 | 基于 FAISS 向量数据库的**中医经方方证**知识精准检索（经方方证 / 方证解读） |
| 📋 辨证建议 | 给出可能相关的方证方向、方义说明、调护与就医建议 |
| 💾 问诊记录 | 持久化存储问诊会话与消息，支持回溯查看与删除 |
| 🔐 用户认证 | 注册 / 登录 / JWT 鉴权 |

## 🏗️ 系统架构

```
Vue3 前端 (5173)
   │  HTTP REST + WebSocket（经 Vite 代理 /api）
   ▼
FastAPI 后端 (8000)
   ├─ 路由层: /api/v1/user · /consult · /knowledge · /api/ws/chat
   ├─ Agent 层: MedicalAgent（症状分析 + RAG 编排 + 方证辨证）
   ├─ RAG 层:   LocalHashEmbeddings → FAISS 向量库 → 中医经方方证知识库
   ├─ LLM 层:   通义千问 qwen-plus（OpenAI 兼容接口，可降级为离线规则）
   └─ 数据层:   SQLAlchemy + SQLite（可切换 PostgreSQL）
```

> 说明：为做到「开箱即跑、零模型下载」，向量化采用**本地哈希向量**（字符 + bigram），
> 数据库默认 **SQLite**。两者均可按文档替换为线上 Embedding 模型 / PostgreSQL（改 `DATABASE_URL` 即可）。
> 当未配置可用的 LLM Key 时，系统会**自动降级为基于知识库的规则回答**，保证始终可用。

## 📁 目录结构

```
ai-medical-consultant/
├─ backend/
│  ├─ app/
│  │  ├─ main.py            # 应用入口
│  │  ├─ config.py          # 配置（.env）
│  │  ├─ database.py        # SQLAlchemy
│  │  ├─ models.py          # 用户/会话/消息/知识库 ORM
│  │  ├─ schemas.py         # Pydantic 模型
│  │  ├─ security.py        # 密码哈希 + JWT
│  │  ├─ seed.py            # 初始化：演示用户 + 知识库 + 向量索引
│  │  ├─ routers/           # user / consult / knowledge / ws
│  │  └─ services/          # embeddings / vector_store / knowledge_base / llm / agent
│  ├─ data/tcm_knowledge.json       # 中医经方方证知识库（由 ingest_tcm.py 生成，默认启用）
│  ├─ data/medical_knowledge.json   # 西医知识种子数据（备用样例）
│  ├─ ingest_tcm.py                 # 中医资料 → 知识库 JSON 的构建脚本
│  ├─ requirements.txt
│  └─ .env(.example)
├─ frontend/
│  ├─ src/
│  │  ├─ views/             # Home / Login / Chat / Records / Knowledge
│  │  ├─ layouts/MainLayout.vue
│  │  ├─ stores/auth.js     # Pinia
│  │  ├─ api/index.js       # axios 封装
│  │  └─ router/index.js
│  ├─ vite.config.js        # /api 代理（含 WebSocket）
│  └─ package.json
├─ start_backend.bat
└─ start_frontend.bat
```

## 🚀 快速开始

### 1. 后端

```bash
cd backend
pip install -r requirements.txt        # 国内可加 -i https://mirrors.aliyun.com/pypi/simple/

# 配置 LLM（可选，不配则离线规则模式）
copy .env.example .env                  # Windows
# 编辑 .env 填入 OPENAI_API_KEY / OPENAI_API_BASE / OPENAI_CHAT_MODEL

# 启动（首次启动会自动建库、写入知识库、构建向量索引）
python -m uvicorn app.main:app --reload --port 8000
```

后端文档：http://127.0.0.1:8000/docs

### 2. 前端

```bash
cd frontend
npm install                             # 国内可加 --registry=https://registry.npmmirror.com
npm run dev
```

访问：http://localhost:5173

> Windows 用户也可直接双击根目录的 `start_backend.bat` 和 `start_frontend.bat`。

### 3. 登录

演示账号：**demo / demo123**（也可自行注册）

## 🌐 单服务部署

本项目已经支持“单服务部署”：构建时先打包 Vue 前端，再由 FastAPI 同时提供网页和 `/api` 接口。上线后朋友只需要访问一个网址。

### 阿里云 ECS 部署

在 ECS 服务器上安装 Docker 后，可以在 `ai-medical-consultant` 目录使用 Docker Compose 同时启动应用和 PostgreSQL：

```bash
cp env.production.example .env.production
# 编辑 .env.production，至少修改 POSTGRES_PASSWORD 和 JWT_SECRET
docker compose up -d --build
```

默认对外暴露 `80` 端口。上线前需要在阿里云安全组放行 `80`，之后如绑定域名再配置 HTTPS。

### 推荐组合

- 后端和网页：Render / Railway / Fly.io 的 Docker Web Service
- 数据库：Neon PostgreSQL
- 模型：通义千问 OpenAI 兼容接口，或其他 OpenAI 兼容服务

不建议一开始就买云服务器。托管平台会自动处理 HTTPS、进程守护、部署日志和回滚，适合先给朋友试用。

### 1. 创建 PostgreSQL

在 Neon 创建项目后，复制连接串，并改成 SQLAlchemy 推荐格式：

```bash
postgresql+psycopg://user:password@host/dbname?sslmode=require
```

部署平台里设置：

```bash
DATABASE_URL=postgresql+psycopg://user:password@host/dbname?sslmode=require
```

### 2. 部署 Docker 服务

以 Render 为例：

1. 把代码推到 GitHub。
2. 在 Render 新建 `Web Service`，选择仓库。
3. Root Directory 填：

```bash
ai-medical-consultant
```

4. Environment 选择 `Docker`。
5. Health Check Path 填：

```bash
/api/v1/health
```

6. 添加环境变量：

```bash
DATABASE_URL=postgresql+psycopg://user:password@host/dbname?sslmode=require
OPENAI_API_KEY=你的模型密钥
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_CHAT_MODEL=qwen-plus
JWT_SECRET=换成一个很长的随机字符串
CORS_ORIGINS=
```

单服务部署时前端和 API 同源，`CORS_ORIGINS` 可以留空。

### 3. 本地验证 Docker

在 `ai-medical-consultant` 目录执行：

```bash
docker build -t zy-demo .
docker run --rm -p 8000:8000 --env-file backend/env.example zy-demo
```

访问：

- 网页：http://127.0.0.1:8000
- 健康检查：http://127.0.0.1:8000/api/v1/health

### 4. 上线前检查

- `JWT_SECRET` 必须修改，不能使用默认值。
- `OPENAI_API_KEY` 不要提交到 GitHub，只放在部署平台环境变量里。
- 正式多人使用建议使用 PostgreSQL，不要用容器里的 SQLite。
- 方剂库 `backend/data/jingfang.sqlite3` 目前仍作为随应用发布的 SQLite 文件使用；如果要多人在线编辑方剂，再单独迁移。

## ⚙️ 环境变量（backend/.env）

| 变量 | 说明 | 默认 |
| --- | --- | --- |
| `OPENAI_API_KEY` | LLM 密钥（OpenAI 兼容，留空则离线规则模式） | — |
| `OPENAI_API_BASE` | 接口地址 | 通义千问 DashScope |
| `OPENAI_CHAT_MODEL` | 模型名 | `qwen-plus` |
| `DATABASE_URL` | 数据库连接串 | `sqlite:///./medical.db` |
| `JWT_SECRET` | JWT 密钥 | 需自行修改 |
| `CORS_ORIGINS` | 允许的前端地址 | `http://localhost:5173` |

## 📡 主要 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/user/register` `/login` | 注册 / 登录 |
| POST | `/api/v1/consult/chat` | 发送问诊消息（非流式） |
| WS   | `/api/ws/chat?token=` | 流式问诊（前端默认使用） |
| GET  | `/api/v1/consult/sessions` | 问诊会话列表 |
| GET  | `/api/v1/consult/sessions/{id}` | 会话详情（含消息） |
| GET/POST | `/api/v1/knowledge` | 知识库浏览 / 新增 |
| GET  | `/api/v1/knowledge/search?q=` | 向量检索 |
## 🌿 知识库（中医经方方证）

当前知识库为**中医经方方证**，共 381 条，来源：

- `05_常用经方100首方证分析（病理辨证体系版）` —— 按方剂聚合（病机/症状/舌脉/方解/现代疾病），109 方
- `胡希恕李冠杰 方证解读汇总 202105` —— 每方一篇讲解全文，272 方

**重建知识库**（资料更新或更换目录后）：

```bash
cd backend
# 1. 从中医资料目录生成知识库 JSON（默认 D:\AI\ZY-Study\data，可用 --dir 指定）
python ingest_tcm.py --dir "D:\AI\ZY-Study\data"
# 2. 强制清空旧数据并重建数据库 + 向量索引
python -m app.seed --tcm
# 3. 重启后端使其生效
```

> 如需换回西医样例知识库：将 `app/config.py` 中 `knowledge_file` 指回 `medical_knowledge.json`，再执行 `python -m app.seed --force`。

## 🔧 切换为生产配置（可选）

- **PostgreSQL**：`pip install psycopg`，将 `DATABASE_URL` 改为 `postgresql+psycopg://user:pass@host:5432/db`。
- **线上 Embedding**：在 `services/embeddings.py` 中替换为调用 Embedding API，并重建向量库。
- **更换大模型**：修改 `.env` 中的 `OPENAI_API_BASE` / `OPENAI_CHAT_MODEL`（支持任何 OpenAI 兼容接口，如智谱 GLM、DeepSeek 等）。
