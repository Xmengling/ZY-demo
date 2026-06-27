import json
from pathlib import Path

data = json.loads(Path(r"d:\AI\demo\ai-medical-consultant\backend\data\tcm_knowledge.json").read_text(encoding="utf-8"))
item = next(x for x in data if x.get("title") == "枳术汤")
Path(r"d:\AI\demo\agent-tools\zhi-zhu-tang-source.txt").write_text(item["content"], encoding="utf-8")
print(item["content"])
