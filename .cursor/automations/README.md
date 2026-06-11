# Cursor Automations

在 **Cursor → Automations** 页面创建与管理定时任务，不要在本机用 launchd/cron 脚本替代。

## 每日经方卡片整理（09:00）

- **触发**：`0 9 * * *`
- **仓库**：`Xmengling/ZY-demo` / `main`
- **队列脚本**：`scripts/jingfang/pick_next_formula.py`
- **Prompt**：`scripts/jingfang/daily_automation_prompt.md`
- **产出路径**：`ai-medical-consultant/backend/data/formula_cards/<id>.json`（会进 git）
- **本机导入 sqlite**：`python scripts/jingfang/import_formula_cards.py`

### 常见报错：工作区为空 / 找不到 AGENTS.md

1. **自动化依赖的文件还没 push 到 GitHub**（`.cursor/skills/`、`scripts/jingfang/` 等）
2. **Cloud Agent 未配置仓库权限**（私有仓库需授权）
3. **Automation 未填写 git 仓库** `Xmengling/ZY-demo` / `main`

> `jingfang.sqlite3` 在 `.gitignore` 中，云端无法直接把数据库同步回本机；云端任务改为 **提交 JSON 卡片**，本机再 `import_formula_cards.py` 导入。

## 每日仓库同步到远程（20:00）

- **触发**：`0 20 * * *`
- **仓库**：`Xmengling/ZY-demo` / `main`
- **Prompt**：`scripts/git/daily_sync_automation_prompt.md`

Cloud Agent 在 GitHub 检出仓库后执行：检查改动 → 排除敏感文件 → commit → `pull --rebase` → `push`。

> 本机未 push 的改动不会自动进云端；日常开发完请先 push，或由 20:00 任务同步**云端/Agent 已产生的提交**。

## 手动触发经方整理（推荐本机）

在 **ZY-demo 项目** 的 **本地 Agent** 中发送：

```
按 scripts/jingfang/daily_automation_prompt.md 执行一次每日经方卡片整理（本机模式，直接写 sqlite）。
```
