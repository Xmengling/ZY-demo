#!/usr/bin/env python3
"""
Count herbal medicine usage across TCM formulas.

Reads formula_ingredients_raw.json, extracts herb names using a whitelist approach,
normalizes names, counts occurrences per formula, and outputs sorted stats.
"""

import json
import re
from collections import defaultdict, Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent
INPUT_FILE = DATA_DIR / "formula_ingredients_raw.json"
OUTPUT_FILE = DATA_DIR / "herb_usage_stats.json"

# =============================================================================
# Comprehensive whitelist of TCM herb names from 伤寒论/金匮要略
# Deduplicated, sorted by length descending for longest-match-first.
# =============================================================================

_RAW_WHITELIST = [
    # 5-char
    "甘李根白皮", "桑东南根白皮",

    # 4-char
    "生梓白皮", "蒴藋细叶", "王不留行", "紫石英",
    "木防己", "天门冬", "麦门冬", "山茱萸", "五味子",
    "酸枣仁", "吴茱萸", "旋覆花", "牡丹皮", "代赭石",
    "瓜蒌根", "栝蒌根", "天花粉", "瓜蒌实", "栝蒌实",
    "土瓜根", "白头翁", "败酱草", "赤小豆", "薏苡仁",
    "鸡子黄", "猪胆汁", "紫苏叶", "干苏叶", "冬瓜仁",
    "寒水石", "赤石脂", "白石脂", "豆黄卷", "灶心土",
    "蔓荆子", "款冬花", "射干",

    # 3-char
    "炙甘草", "炮附子", "生附子", "大附子",
    "炙枳实", "炙厚朴", "干地黄", "生地黄",
    "麻子仁", "胶饴",
    "赤硝", "蜣螂", "蜂窠", "鼠妇", "石韦",
    "瞿麦", "紫葳", "乌扇", "蛴螬", "蜀椒",
    "蜀漆", "乌头", "防己", "防风",
    "桔梗", "白前", "紫参", "皂荚",
    "连轺", "柏叶", "艾叶", "竹茹", "竹叶",
    "橘皮", "薤白", "白酒", "茵陈", "栀子",
    "通草", "黄柏", "乌梅", "雄黄", "矾石",
    "苦参", "秦皮", "芒硝", "石膏", "知母",
    "粳米", "柴胡", "黄芩", "黄连", "人参",
    "茯苓", "白术", "猪苓", "泽泻", "阿胶",
    "桃仁", "牡蛎", "龙骨", "黄芪", "当归",
    "川芎", "干姜", "半夏", "麻黄", "葛根",
    "杏仁", "厚朴", "附子", "大黄", "枳实",
    "桂枝", "芍药", "甘草", "生姜", "大枣",
    "水蛭", "虻虫", "蟅虫", "干漆", "鳖甲",
    "升麻", "天雄", "薯蓣", "神曲", "白敛",
    "白薇", "菊花", "铅丹", "瓜子", "滑石",
    "葶苈子", "白鱼", "乱发", "蒲灰", "戎盐",
    "葵子", "新绛", "葱白", "人尿", "败酱",
    "旋复花", "白蜜", "硝石", "椒目",
    "栀子", "香豉", "豉",
    "白芍", "独活",

    # 2-char (most common)
    "桂枝", "芍药", "甘草", "生姜", "大枣",
    "麻黄", "葛根", "半夏", "细辛", "干姜",
    "杏仁", "厚朴", "附子", "大黄", "芒硝",
    "枳实", "柴胡", "黄芩", "人参", "黄连",
    "茯苓", "白术", "猪苓", "泽泻", "阿胶",
    "当归", "川芎", "石膏", "知母", "粳米",
    "桃仁", "牡蛎", "龙骨", "黄芪", "防风",
    "防己", "通草", "栀子", "茵陈", "矾石",
    "雄黄", "苦参", "秦皮", "艾叶", "薤白",
    "白酒", "水蛭", "虻虫", "蟅虫", "蛴螬",
    "干漆", "竹叶", "竹茹", "橘皮", "连轺",
    "皂荚", "紫参", "白前", "桔梗", "鼠妇",
    "石韦", "瞿麦", "紫葳", "蜂窠", "赤硝",
    "蜣螂", "天雄", "薯蓣", "神曲", "白敛",
    "白薇", "菊花", "铅丹", "瓜子", "滑石",
    "葶苈", "白鱼", "乱发", "蒲灰", "戎盐",
    "葵子", "新绛", "葱白", "人尿", "败酱",
    "旋复花", "白蜜", "饴糖",
    "乌头", "鳖甲", "升麻",
    "蜀椒", "蜀漆",
    "小麦", "瓜蒌", "白芍", "独活",
    "粉", "蜜", "盐", "葱",

    # Single-char (keep minimal to avoid false positives)
]

# Deduplicate and sort by length descending
HERB_WHITELIST = sorted(set(_RAW_WHITELIST), key=lambda x: -len(x))
HERB_SET = set(HERB_WHITELIST)

# =============================================================================
# Normalization: variant name -> canonical name
# =============================================================================
NORMALIZE_MAP = {
    # 瓜蒌/栝蒌 variants
    "栝蒌根": "瓜蒌根",
    "栝蒌实": "瓜蒌实",
    "栝楼根": "瓜蒌根",
    "栝楼实": "瓜蒌实",
    "栝蒌": "瓜蒌",
    "栝楼": "瓜蒌",
    "天花粉": "瓜蒌根",

    # 川芎/芎藭
    "芎藭": "川芎",

    # 黄柏/黄檗
    "黄檗": "黄柏",

    # 旋覆花/旋复花
    "旋复花": "旋覆花",

    # 香豉/豆豉
    "香豉": "豆豉",
    "豉": "豆豉",

    # 薯蓣/山药
    "薯蕷": "山药",
    "薯蓣": "山药",

    # OCR variants
    "枙子": "栀子",
    "乌挴": "乌梅",

    # 败酱 variants
    "败酱草": "败酱",

    # 五味/五味子
    "五味": "五味子",

    # 梗米 -> 粳米
    "梗米": "粳米",

    # 艾 -> 艾叶
    "艾": "艾叶",

    # 生葛 -> 葛根
    "生葛": "葛根",

    # 干苏叶 -> 紫苏叶
    "干苏叶": "紫苏叶",

    # 葶苈 -> 葶苈子 (same herb)
    "葶苈": "葶苈子",

    # 生姜汁 -> 生姜
    "生姜汁": "生姜",
}


def normalize_text(text: str) -> str:
    """Normalize ingredient text: remove annotations, clean up whitespace."""
    # Remove 《...》 annotations and following text
    text = re.sub(r'《[^》]*》[^《\n]*', '', text)
    # Remove lines starting with 《
    lines = text.split('\n')
    lines = [l for l in lines if not re.match(r'^\s*《', l)]
    text = '\n'.join(lines)

    # Remove parenthetical notes (炙), (炮), (一作菖蒲), etc.
    text = re.sub(r'[（(][^）)]*[）)]', '', text)

    # Replace newlines with 、
    text = re.sub(r'\n+', '、', text)

    # Normalize spaces around 、
    text = re.sub(r'\s*、\s*', '、', text)

    # Remove spaces between CJK characters (e.g., "炙甘 草" -> "炙甘草")
    text = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', text)

    return text


def extract_herbs(text: str) -> set:
    """Extract herb names from normalized text using whitelist substring matching.
    Iterates whitelist (longest first) and checks if each herb appears in text."""
    herbs = set()
    norm = normalize_text(text)

    for herb in HERB_WHITELIST:
        if herb in norm:
            herbs.add(herb)

    return herbs


def apply_normalization(herbs: set) -> set:
    """Map variant herb names to canonical forms."""
    return {NORMALIZE_MAP.get(h, h) for h in herbs}


# Compound herb prefixes: if "炙甘草" is found, don't also count "甘草"
# Maps compound herb -> base herb to remove
COMPOUND_OVERRIDES = {
    "炙甘草": "甘草",
    "炮附子": "附子",
    "生附子": "附子",
    "大附子": "附子",
    "炙枳实": "枳实",
    "炙厚朴": "厚朴",
    "生姜汁": "生姜",
}


def remove_substring_herbs(herbs: set) -> set:
    """When a compound herb (e.g. 炙甘草) is present, remove the base
    herb (甘草) that was matched as a substring."""
    to_remove = set()
    for compound, base in COMPOUND_OVERRIDES.items():
        if compound in herbs and base in herbs:
            to_remove.add(base)
    return herbs - to_remove


def parse_formula(formula: dict) -> dict:
    """Parse one formula: extract herbs, normalize, return result."""
    name = formula["name"]
    ingredients = formula["ingredients"]

    raw_herbs = extract_herbs(ingredients)
    norm_herbs = apply_normalization(raw_herbs)
    norm_herbs = remove_substring_herbs(norm_herbs)

    return {
        "name": name,
        "raw_ingredients": ingredients,
        "herbs_raw": sorted(raw_herbs),
        "herbs_normalized": sorted(norm_herbs),
    }


def main():
    print(f"Reading formulas from: {INPUT_FILE}")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        formulas = json.load(f)
    print(f"Found {len(formulas)} formulas")

    herb_counter = Counter()
    herb_formulas = defaultdict(list)

    for formula in formulas:
        result = parse_formula(formula)
        for herb in result["herbs_normalized"]:
            herb_counter[herb] += 1
            herb_formulas[herb].append(result["name"])

    sorted_herbs = sorted(herb_counter.items(), key=lambda x: -x[1])

    # Build output
    output = {
        "total_formulas": len(formulas),
        "total_unique_herbs": len(sorted_herbs),
        "herb_usage": []
    }
    for rank, (herb, count) in enumerate(sorted_herbs, 1):
        output["herb_usage"].append({
            "rank": rank,
            "herb": herb,
            "count": count,
            "formulas": sorted(herb_formulas[herb]),
        })

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nOutput written to: {OUTPUT_FILE}")
    print(f"\n{'='*70}")
    print(f"HERB USAGE STATISTICS (Top 60)")
    print(f"{'='*70}")
    print(f"{'Rank':<6}{'Herb':<14}{'Count':<8}{'Sample Formulas'}")
    print(f"{'-'*70}")

    for rank, (herb, count) in enumerate(sorted_herbs[:60], 1):
        flist = sorted(herb_formulas[herb])[:4]
        extra = len(herb_formulas[herb]) - 4
        suffix = f" (+{extra} more)" if extra > 0 else ""
        print(f"{rank:<6}{herb:<14}{count:<8}{', '.join(flist)}{suffix}")

    print(f"\n{'='*70}")
    print(f"Total: {len(sorted_herbs)} unique herbs across {len(formulas)} formulas")
    print(f"{'='*70}")

    print(f"\n\nFULL LIST (all {len(sorted_herbs)} herbs):")
    print(f"{'='*70}")
    for rank, (herb, count) in enumerate(sorted_herbs, 1):
        print(f"{rank:>3}. {herb}: {count}")


if __name__ == "__main__":
    main()
