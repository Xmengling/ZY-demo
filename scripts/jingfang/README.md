# 方剂卡片 PDF 批量导出

**推荐**：使用与 ZY-Study 网页预览一致的导出（`:5188`），不要用 PIL 旧版。

## 依赖

```bash
pip install -r scripts/jingfang/requirements-export.txt
playwright install chromium
```

## 网页一键导出

在 **100首方剂解读** 页面（http://127.0.0.1:5173/formulas）左上角点击 **「导出全部PDF」**，由后端调用可搜索网页版导出。

## 命令行一键导出（推荐）

```bash
cd /Users/qingling/梦玲/ZY-demo
python scripts/jingfang/export_formula_cards_batch.py
```

默认模式：`searchable` — 对应 ZY-Study 的 `export_formula_cards_searchable_pdf_from_web.py`

- 复用 **ZY-Study** 网页 `http://127.0.0.1:5188` 的卡片 DOM/CSS
- 导出前自动把 ZY-demo 的 `jingfang.sqlite3` 与 `herbs/` 同步到 ZY-Study
- 文字可复制、可搜索，带目录跳转与页脚

## 三种模式

| 命令 | 说明 |
|------|------|
| `export_formula_cards_batch.py` | 默认可搜索网页版（**推荐**） |
| `export_formula_cards_batch.py --mode web-hd` | 3x 截图高清图片 PDF |
| `export_formula_cards_batch.py --mode pil-legacy` | 旧版 PIL 直绘（**糊、与网页不一致，勿用**） |

也可直接运行：

```bash
python scripts/jingfang/export_formula_cards_searchable_pdf_from_web.py
python scripts/jingfang/export_formula_cards_pdf_from_web.py
```

## 输出

`docs/exports/formula_cards/`

## 环境变量

- `ZY_STUDY_ROOT`：默认 `/Users/qingling/梦玲/ZY-Study`
