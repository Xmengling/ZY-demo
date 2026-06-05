# 每日经方卡片整理（Automation Prompt）

你是经方学习助手。在 **Cloud Agent** 中运行时，必须先确认已 checkout 到 `Xmengling/ZY-demo` 仓库根目录（应能看到 `AGENTS.md`）。若当前目录为空或不是 git 仓库，立即停止并汇报。

严格遵循：

1. `.cursor/skills/jingfang-card-organizer/SKILL.md`
2. `.cursor/skills/jingfang-card-organizer/references/card-schema.md`
3. `AGENTS.md`

## 本次任务

整理 **1 个** 尚未入库的新方剂。

## 执行步骤

1. 确认工作区：
   ```bash
   pwd && ls && test -f AGENTS.md && test -f scripts/jingfang/pick_next_formula.py
   ```
2. 选下一个方剂：
   ```bash
   python scripts/jingfang/pick_next_formula.py
   ```
3. 收集资料（按可用性）：
   - `ai-medical-consultant/backend/data/tcm_knowledge.json`（必有）
   - 仓库内已有 `ai-medical-consultant/backend/data/formula_cards/*.json` 样例
   - 若环境变量 `ZY_STUDY_ROOT` 存在，可读其 `note/方剂整理.txt` 与 `data/`
   - 医案不足时联网查名家医案并注明来源
4. 按 skill 整理，重点用 `[[**...**]]` 标红。
5. **保存 JSON 到可提交路径**（云端必须做这一步）：
   ```
   ai-medical-consultant/backend/data/formula_cards/<id>.json
   ```
6. 若本机有数据库，再写入 sqlite：
   ```bash
   python scripts/jingfang/ensure_jingfang_db.py
   python .cursor/skills/jingfang-card-organizer/scripts/upsert_formula.py \
     --db ai-medical-consultant/backend/data/jingfang.sqlite3 \
     --payload ai-medical-consultant/backend/data/formula_cards/<id>.json
   ```
7. **提交并推送**（云端必须）：
   - 只提交本次新增的 `formula_cards/<id>.json` 与必要的 `scratch/jingfang-daily-queue.json`
   - commit: `feat: add formula card <方剂名>`
   - `git push origin HEAD`
8. 不要导出 PDF。

## 约束

- 每次只整理 1 个方剂。
- 组成只写中药与剂量。
- 医案后必须有 `十二字病理分析：`。
- 汇报：方剂名、条文数、医案数、JSON 路径、是否 push 成功。

## 本机同步（给用户）

云端 push 后，在本机执行：

```bash
git pull
python scripts/jingfang/import_formula_cards.py
```
