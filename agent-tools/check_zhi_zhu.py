import sqlite3
c = sqlite3.connect(r"d:\AI\demo\ai-medical-consultant\backend\data\jingfang.sqlite3")
r = c.execute("select id from formulas where json_extract(payload,'$.name')='枳术汤'").fetchone()
print("exists:", r)
print("total:", c.execute("select count(*) from formulas").fetchone()[0])
