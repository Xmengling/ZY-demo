#!/usr/bin/env python3
"""生成飞书文档表格XML"""
import json

with open('/Users/xxm/Documents/AI/ZY-demo/tcm_rag_demo/data/herb_usage_stats.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

herbs = data['herb_usage']

lines = []
lines.append('<table>')
lines.append('<colgroup><col width="80"/><col width="520"/><col width="80"/></colgroup>')
lines.append('<thead><tr>')
lines.append('<th background-color="light-gray"><p>排名</p></th>')
lines.append('<th background-color="light-gray"><p>中药名</p></th>')
lines.append('<th background-color="light-gray"><p>使用方剂数</p></th>')
lines.append('<th background-color="light-gray"><p>使用的方剂</p></th>')
lines.append('</tr></thead>')
lines.append('<tbody>')

for h in herbs:
    rank = h['rank']
    herb = h['herb']
    count = h['count']
    formula_list = '、'.join(h['formulas'])

    # Escape XML special chars
    herb_escaped = herb.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    formula_list_escaped = formula_list.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    lines.append('<tr>')
    lines.append(f'<td><p>{rank}</p></td>')
    lines.append(f'<td><p><b>{herb_escaped}</b></p></td>')
    lines.append(f'<td><p>{count}</p></td>')
    lines.append(f'<td><p><b><span text-color="rgb(46,161,33)">{formula_list_escaped}</span></b></p></td>')
    lines.append('</tr>')

lines.append('</tbody>')
lines.append('</table>')

xml = '\n'.join(lines)

# Write to file for use
with open('/Users/xxm/Documents/AI/ZY-demo/tcm_rag_demo/data/table_xml.txt', 'w', encoding='utf-8') as f:
    f.write(xml)

print(f"Generated table with {len(herbs)} rows")
print(f"XML length: {len(xml)} chars")
