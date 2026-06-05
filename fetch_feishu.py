# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

keywords = [
    "doxcnV0o7WxFlPK0QMCH3OwddId",
    "doxcnsd5eVqEmQ4Km8WibPwscid",
    "临床定份四步法",
    "OQQ8dLSf",
    "DF2ld9lGko",
    "附：打分",
    "doxcnm9IwzWX",
]

for kw in keywords:
    print("=" * 60, kw)
    r = subprocess.run(
        [
            "lark-cli", "docs", "+fetch",
            "--api-version", "v2",
            "--doc", "GAXbdwucpoa1NpxsOscc2HHknle",
            "--as", "user",
            "--scope", "keyword",
            "--keyword", kw,
            "--context-before", "0",
            "--context-after", "2",
            "--format", "pretty",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    out = r.stdout or r.stderr
    print(out[:4000])
    print()
