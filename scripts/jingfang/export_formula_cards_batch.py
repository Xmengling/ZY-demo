#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量导出全部方剂卡片 PDF（默认：ZY-Study 网页可搜索版，与线上一致）。"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["searchable", "web-hd", "pil-legacy"],
        default="searchable",
        help="searchable=可搜索网页版(推荐); web-hd=3x截图高清; pil-legacy=旧版PIL直绘(糊)",
    )
    args = parser.parse_args()

    targets = {
        "searchable": SCRIPTS / "export_formula_cards_searchable_pdf_from_web.py",
        "web-hd": SCRIPTS / "export_formula_cards_pdf_from_web.py",
        "pil-legacy": SCRIPTS / "export_formula_cards_pdf_pil_legacy.py",
    }
    script = targets[args.mode]
    return subprocess.call([sys.executable, str(script)])


if __name__ == "__main__":
    raise SystemExit(main())
