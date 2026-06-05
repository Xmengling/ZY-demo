---
name: jingfang-card-organizer
description: 整理经方方剂卡片并写入本地网页数据库。当用户要求整理方剂、整理经方卡片、补方剂数据库、写入 jingfang.sqlite3、制作方剂卡片、更新方剂的组成/条文/病理/辨证/医案时使用；适用于当前项目中 ai-medical-consultant/backend/data/jingfang.sqlite3 的 formulas 表。
---

# 经方卡片整理

## 目标

把单个或少量经方整理成可复习、可发卡片、可被本地网页读取的结构化方剂记录，并写入 `jingfang.sqlite3` 的 `formulas` 表。

默认遵循当前项目 `AGENTS.md` 中形成的方剂整理规则；如果项目里有更新的 `AGENTS.md`，以项目文件为准。

## 快速流程

1. **先读本地规则和已有样例**
   - 当前项目有 `AGENTS.md` 时必须先读。
   - 用 `rg -n "方剂名|<方剂名>|胡希恕|李冠杰" .` 查已有整理、讲稿和样例。
   - 优先使用本地资料：同级 `ZY-Study/note/方剂整理.txt`、`tcm_rag_demo/data`、`ai-medical-consultant/backend/data/tcm_knowledge.json`、已有 `jingfang.sqlite3` payload。

2. **收集资料**
   - 组成：只记录中药和剂量，不把煎服法、服用法、先煎后下等写进 `composition`。
   - 条文：整理《伤寒论》《金匮要略》《外台》《千金》等相关原文，尽量保留条文编号或出处。
   - 胡希恕、李冠杰：摘取关键讲稿表达，再总结方药病机、主治边界、常见误解和类方区别。
   - 医案：优先用本地医案。若本地没有，联网查找经方名家医案，如胡希恕、李冠杰、冯世纶、黄煌、矢数道明、刘渡舟、大塚敬节等；医案文字中注明来源或出处名。

3. **整理卡片内容**
   - 固定模块顺序见 [card-schema.md](references/card-schema.md)。
   - 对辨证抓手、病理证据、禁忌边界、主症、舌脉、疗效、类方鉴别点使用 `[[**...**]]` 标记。
   - 语言保持学习笔记风格：准确、简洁、能复习、以方证为核心。

4. **组装数据库 JSON**
   - 字段映射见 [card-schema.md](references/card-schema.md)。
   - 常用字段包括：`id`、`name`、`categories`、`composition`、`pathology`、`pathologySymptoms`、`mainSymptoms`、`clinicalSymptoms`、`modernDiseases`、`abdominalDiagnosis`、`huXishuAnalysis`、`liGuanjieAnalysis`、`diagnosisPoints`、`classicTexts`、`caseItems`、`cases`、`caution`，可选 `herbImages`。
   - `cases` 应等于 `caseItems` 用两个换行拼接后的结果。

5. **写入 SQLite**
   - 优先使用本 skill 自带脚本（在项目根目录执行）：
     ```bash
     python .cursor/skills/jingfang-card-organizer/scripts/upsert_formula.py \
       --db ai-medical-consultant/backend/data/jingfang.sqlite3 \
       --payload /path/to/formula.json
     ```
   - 如果当前项目数据库位置不同，用 `find . -path '*jingfang.sqlite3' -print` 查找，并结合应用配置确认真实数据库。

6. **轻量校验**
   - 查询数据库记录，至少确认方剂名、条文数量、医案数量和一个核心短语。
   - 如果本地网页服务已启动，调用 API 确认新方剂能返回。
   - 写入或更新数据库后，用 Google Chrome 打开本地网页预览。本项目优先 `http://127.0.0.1:5173/formulas`（前端）与 `http://127.0.0.1:8000/api/v1/formulas`（后端 API）；若使用 ZY-Study 独立站点则为 `http://127.0.0.1:5188`。
   - 单个或少量方剂整理后不要自动导出 PDF；等接近 100 个方剂再统一导出和检查。

## 固定内容模块

写学习笔记版内容时，使用以下标题和顺序：

```markdown
## 方剂名
### 组成：
### 相关条文
### 方剂名病理
### 辩证要点
### 临床症状：
### 现代疾病：
### 胡希恕
### 李冠杰
### 对比
### 医案
```

资料不足时，可缺少个别模块，但优先补齐 `组成`、`相关条文`、`病理`、`辩证要点`、`对比` 和 `医案十二字病理分析`。

## 十二字病理写法

使用用户的十二字病理体系。常用标签包括：

`半表`、`半热`、`半虚`、`里热`、`里寒`、`里虚`、`水实`、`血虚`、`气实`、`血实`、`水虚`、`水实`。

每条写成：

`标签：证据/含义`

示例：

- `里热：[[**舌上燥而渴、潮热、烦躁**]]，热结在里。`
- `水实：[[**水结在胸胁**]]，胸膈痞满、短气、但头微汗出。`

## 数据库说明

`formulas` 表把整张卡片作为 JSON 存在 `payload`：

```sql
create table formulas (
  id text primary key,
  payload text not null,
  updated_at integer not null
);
```

网页卡片直接读取 JSON 字段。普通卡片内容不要新增数据库列。

## 安全边界

- 整理内容是学习笔记，不是医疗建议。
- 不要把现代病名等同于方证，始终回到方证辨证。
- 峻剂、有毒药、急腹症、严重心肺或神经系统场景，要明确标出边界、禁忌和急重风险。
- 不要编造医案。若医案来自网络或书籍摘编，在医案文字中说明来源。
