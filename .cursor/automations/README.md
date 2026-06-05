# Cursor Automations

## 每日经方卡片整理（09:00）

- **触发**：`0 9 * * *`
- **队列脚本**：`scripts/jingfang/pick_next_formula.py`
- **Prompt**：`scripts/jingfang/daily_automation_prompt.md`
- **产出路径**：`ai-medical-consultant/backend/data/formula_cards/<id>.json`（会进 git）
- **本机导入 sqlite**：`python scripts/jingfang/import_formula_cards.py`

### 常见报错：工作区为空 / 找不到 AGENTS.md

原因通常是：

1. **自动化依赖的文件还没 push 到 GitHub**（`.cursor/skills/`、`scripts/jingfang/` 等）
2. **Cloud Agent 未配置仓库权限**（私有仓库需授权）
3. **Automation 未填写 git 仓库** `Xmengling/ZY-demo` / `main`

修复：先把本仓库改动 commit + push，再在 Automations 里确认 Cloud Agent 与仓库配置，然后重新 Run。

> `jingfang.sqlite3` 在 `.gitignore` 中，云端无法直接把数据库同步回本机；因此云端任务改为 **提交 JSON 卡片**，本机再 `import_formula_cards.py` 导入。

## 每日仓库同步到远程（20:00）

- **触发**：`0 20 * * *`
- **Prompt**：`scripts/git/daily_sync_automation_prompt.md`

## 手动触发经方整理（推荐本机）

在 **ZY-demo 项目** 的 **本地 Agent** 中发送：

```
按 scripts/jingfang/daily_automation_prompt.md 执行一次每日经方卡片整理（本机模式，直接写 sqlite）。
```

云端 Automations 适合：生成 JSON → commit → push；本机 Agent 适合：直接写本地 `jingfang.sqlite3` 并预览网页。
