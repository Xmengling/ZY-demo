#!/usr/bin/env python3
"""统计每味中药在不同方剂中的使用次数"""

import json
import re
from collections import defaultdict

with open('/Users/xxm/Documents/AI/ZY-demo/tcm_rag_demo/data/formula_ingredients_raw.json', 'r', encoding='utf-8') as f:
    formulas = json.load(f)

# herb -> list of formula names
herb_formulas = defaultdict(list)

for formula in formulas:
    name = formula['name']
    text = formula['ingredients']
    # 只保留组成的第一行（主方），去掉用法说明等附注
    lines = text.split('\n')
    # 取第一个非空行作为主组成
    main_line = lines[0].strip()
    # 有些多行组成（如各3、半夏各半升），需要合并前几行直到遇到说明性文字
    # 合并所有看起来像药物组成的行
    composition_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 如果行以"《"或"三味"、"以"、"六味"、"水"等开头，说明是注释
        if line.startswith('《') or line.startswith('三味') or line.startswith('以') or \
           line.startswith('六味') or line.startswith('水') or line.startswith('上') or \
           line.startswith('煮') or line.startswith('方后') or line.startswith('煎药'):
            break
        composition_lines.append(line)

    full_composition = ' '.join(composition_lines)

    # 替换分隔符：中文逗号、英文逗号 -> 统一分隔
    full_composition = full_composition.replace('，', '、').replace(',', '、')

    # 按、分割
    parts = full_composition.split('、')

    # 提取药物名（去掉剂量数字、单位等）
    herbs_in_formula = set()

    for part in parts:
        part = part.strip()
        if not part:
            continue
        # 去掉前导数字和空格
        part = part.strip()
        # 匹配"各N"模式 - 如 "桂枝、芍药、生姜各3"
        # 先处理"XX各N"模式
        match_each = re.match(r'^(.+?)各\d', part)
        if match_each:
            each_herbs = match_each.group(1)
            # 可能有多个药名用 、 分隔
            for h in each_herbs.split('、'):
                h = h.strip()
                if h:
                    herbs_in_formula.add(h)
            continue

        # 普通模式：药物名 + 可选剂量
        # 去掉剂量部分（数字、两、升、合、枚、个、片、克、钱、分、匕、方寸匕）
        herb = re.sub(r'[\d.]+[两升合枚个片克钱分匕]*$', '', part)
        herb = herb.strip()
        # 去掉"各"字
        herb = herb.strip('各')
        # 去掉"炮"、"炙"、"酒"等修饰前缀中的炮制说明（但保留炙、炮作为药名一部分？）
        # 实际上 炙甘草、炮附子 等应视为不同药名
        # 去掉开头的量词
        herb = re.sub(r'^第[一二三四五六七八九十百千万\d]+$', '', herb)
        if herb and len(herb) >= 1:
            herbs_in_formula.add(herb)

    for herb in herbs_in_formula:
        herb_formulas[herb].append(name)

# 按使用次数排序
sorted_herbs = sorted(herb_formulas.items(), key=lambda x: -len(x[1]))

# 输出结果
print(f"共统计 {len(formulas)} 个方剂，涉及 {len(sorted_herbs)} 味中药\n")
print("排名 | 药名 | 使用次数 | 方剂列表")
print("-" * 80)
for i, (herb, f_list) in enumerate(sorted_herbs, 1):
    names = '、'.join(f_list)
    print(f"{i:3d} | {herb} | {len(f_list):3d} | {names}")

# 保存JSON结果
result = []
for herb, f_list in sorted_herbs:
    result.append({
        'rank': len(result) + 1,
        'herb': herb,
        'count': len(f_list),
        'formulas': f_list
    })

with open('/Users/xxm/Documents/AI/ZY-demo/tcm_rag_demo/data/herb_usage_stats.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n结果已保存到 herb_usage_stats.json")
