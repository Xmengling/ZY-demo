# ZY-demo

中医经方学习与 AI 问诊实验仓库。与同级目录 [ZY-Study](../ZY-Study) 配合使用：方剂卡片主库、讲稿资料、笔记规范在 ZY-Study；本仓库侧重 **AI 问诊应用** 与 **RAG 实验**。

## 目录结构

```
ZY-demo/
├── ai-medical-consultant/   # 主应用：Vue3 + FastAPI 智能问诊（端口 5173 / 8000）
├── tcm_rag_demo/            # 独立 RAG Demo：Gradio 问答（端口 7860）
├── scripts/                 # 工具脚本
│   ├── docs/                # 生成 Word / Excel 整理表
│   ├── analysis/            # 临床定份等演算实验
│   └── feishu/              # 飞书文档抓取辅助
├── docs/                    # 文档与生成物
│   ├── product/             # 产品设计（智能问诊流程等）
│   ├── pathology/           # 病理症状整理表（docx / xlsx）
│   └── feishu/              # 飞书文档写入补丁（XML）与抓取缓存
├── scratch/                 # 调试输出（txt / json，可删）
├── assets/exports/          # 导出图片（小红书卡片等）
├── archive/                 # 已停用的一次性脚本
├── .cursor/skills/          # 项目级 Agent Skills（随仓库走）
│   └── jingfang-card-organizer/  # 经方卡片整理与数据库写入
└── AGENTS.md                # Agent 工作流规范（方剂整理、数据库写入等）
```

## 快速启动

### AI 问诊系统（推荐）

```bash
# 后端
cd ai-medical-consultant/backend
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8000

# 前端（另开终端）
cd ai-medical-consultant/frontend
npm install
npm run dev
```

- 前端：http://127.0.0.1:5173
- 方剂解读：http://127.0.0.1:5173/formulas
- API 文档：http://127.0.0.1:8000/docs
- 演示账号：`demo` / `demo123`

### RAG Demo

```bash
cd tcm_rag_demo
pip install -r requirements.txt
python build_kb.py    # 首次构建向量库
python app.py         # 启动 Gradio
```

## 与 ZY-Study 的关系

| 功能 | ZY-Study | ZY-demo |
|------|----------|---------|
| 方剂卡片编辑站（:5188） | `web/` | 嵌入版 `frontend/public/jingfang/` |
| 方剂数据库 | `web/db/jingfang.sqlite3` | 复制到 `backend/data/jingfang.sqlite3` |
| 讲稿 / docx 资料 | `data/` | `tcm_rag_demo/data/` 有一份副本 |
| 方剂整理规范 | `note/方剂整理.txt` | 见 `AGENTS.md` |

数据根目录（macOS）：`/Users/qingling/梦玲/ZY-Study`

## 每日定时整理（Cursor Automation）

每天早上 9:00 自动整理 1 个新方剂，需在 **Cursor → Automations** 中启用（Cloud Agent）。

| 项目 | 说明 |
|------|------|
| 触发 | 每天 9:00（`0 9 * * *`） |
| 队列脚本 | `python scripts/jingfang/pick_next_formula.py` |
| Prompt 模板 | `scripts/jingfang/daily_automation_prompt.md` |
| 进度记录 | `scratch/jingfang-daily-queue.json` |

### 每日仓库同步（20:00）

| 项目 | 说明 |
|------|------|
| 触发 | 每天 20:00（`0 20 * * *`） |
| 行为 | 检查改动 → commit → pull --rebase → push |
| Prompt 模板 | `scripts/git/daily_sync_automation_prompt.md` |

## Agent Skill：经方卡片整理

项目内 skill 路径：`.cursor/skills/jingfang-card-organizer/`

写入方剂 JSON 到数据库：

```bash
python .cursor/skills/jingfang-card-organizer/scripts/upsert_formula.py \
  --db ai-medical-consultant/backend/data/jingfang.sqlite3 \
  --payload /path/to/formula.json
```

## 批量导出方剂卡片 PDF

```bash
pip install -r scripts/jingfang/requirements-export.txt
playwright install chromium

# 推荐：与 ZY-Study 网页预览一致的可搜索 PDF
python scripts/jingfang/export_formula_cards_batch.py
```

输出：`docs/exports/formula_cards/`。详见 `scripts/jingfang/README.md`。

## 常用脚本

```bash
# 生成十二字病理症状归属 Word
python scripts/docs/build_pathology_symptom_doc.py

# 生成经方病理分类症状表（写入 tcm_rag_demo/data/）
python scripts/docs/build_corrected_pathology_symptom_doc.py

# 生成方剂组成与病理比例 Excel
python scripts/docs/build_formula_pathology_ratios.py

# 重建中医知识库 JSON（需 ZY-Study/data）
cd ai-medical-consultant/backend
python ingest_tcm.py --dir "/Users/qingling/梦玲/ZY-Study/data"
python -m app.seed --tcm
```

## 说明

- `scratch/`、`docs/feishu/dumps/` 为会话中间产物，不影响运行。
- `backend/data/jingfang.sqlite3`、`backend/data/herbs/` 为运行时数据，已在 `.gitignore` 中忽略。
- 部分 `ingest_*.py` 仍含 Windows 默认路径，在 Mac 上请用 `--dir` 参数或环境变量 `TCM_DATA_DIR` 指定 ZY-Study 数据目录。
