# -*- coding: utf-8 -*-
P = {"表实": 1, "里热": 2, "半热": 2, "水实": 2, "气实": 1, "里实": 1, "里虚": 0.5}
P_total = sum(P.values())

formulas = {
    "四逆散": {"份": 2, "总量": 12, "病理": {"半热": 0.20, "里实": 0.40, "气实": 0.20, "血虚": 0.20}},
    "小柴胡汤": {"份": 3, "总量": 29, "病理": {"半热": 0.379, "里虚": 0.379, "水实": 0.24}},
    "半夏厚朴汤": {"份": 2, "总量": 22, "病理": {"水实": 0.772, "气实": 0.227}},
    "葶苈大枣泻肺汤": {"份": 5, "总量": 10, "病理": {"水实": 0.50, "半热": 0.50}},
    "麻杏石甘汤": {"份": 3, "总量": 16, "病理": {"表实": 0.375, "里热": 0.50}},
}

print("=== pathology total score:", P_total, "===")
print()

match_scores = {}
for name, f in formulas.items():
    match_scores[name] = sum(P.get(k, 0) * v for k, v in f["病理"].items())

print("[1] match score = sum(patient_score * formula_pathology_pct)")
for name, f in formulas.items():
    m = match_scores[name]
    w = f["份"] * f["总量"]
    print(f"  {name:14s} fen={f['份']} total={f['总量']:2d} weighted={w:3d}  match={m:.3f}  match/total={m/f['总量']:.4f}")

print()
total_weighted = sum(f["份"] * f["总量"] for f in formulas.values())
match_total = sum(match_scores.values())
print("[2] weighted % in combo vs match score %")
for name, f in formulas.items():
    w_pct = f["份"] * f["总量"] / total_weighted * 100
    m_pct = match_scores[name] / match_total * 100
    print(f"  {name:14s} actual_wt%={w_pct:5.1f}  match%={m_pct:5.1f}  fen={f['份']}")

print()
print("[3] per pathology dimension")
pathology_formulas = {}
for name, f in formulas.items():
    for k, v in f["病理"].items():
        if k in P:
            pathology_formulas.setdefault(k, []).append((name, v, f["份"], f["总量"]))

for path in sorted(P, key=lambda x: -P[x]):
    score = P[path]
    print(f"\n  {path}={score}:")
    items = pathology_formulas.get(path, [])
    for name, pct, fen, total in sorted(items, key=lambda x: -x[1]):
        supply = fen * pct * total
        print(f"    {name:14s} in-form%={pct*100:5.1f}  fen={fen}  supply_idx={supply:.1f}")

print()
import math
print("[4] fen vs match/sqrt(total)")
for name, f in formulas.items():
    m = match_scores[name]
    adj = m / math.sqrt(f["总量"])
    print(f"  {name:14s} fen={f['份']}  adj={adj:.3f}  fen/adj={f['份']/adj:.2f}")

print()
print("[5] try proportional fen from match/total, normalized to min fen=2 baseline")
raw = {n: match_scores[n] / f["总量"] for n, f in formulas.items()}
base = raw["四逆散"]
pred = {n: round(raw[n] / base * 2) for n in raw}
print("  predicted fen (round):", pred)
print("  actual fen:", {n: f["份"] for n, f in formulas.items()})

print()
print("[6] try: fen proportional to match_score, adjusted by 1/sqrt(total)")
raw2 = {n: match_scores[n] / math.sqrt(f["总量"]) for n, f in formulas.items()}
base2 = raw2["四逆散"]
pred2 = {n: max(1, round(raw2[n] / base2 * 2)) for n in raw2}
print("  predicted fen:", pred2)

print()
print("[7] pathology drug points from table (for coverage check)")
drug_pts = {
    "四逆散": {"半热": 3, "里实": 6, "气实": 3, "血虚": 3},
    "小柴胡汤": {"半热": 11, "里虚": 11, "水实": 7},
    "半夏厚朴汤": {"水实": 17, "气实": 5},
    "葶苈大枣泻肺汤": {"水实": 5, "半热": 5},
    "麻杏石甘汤": {"表实": 6, "里热": 8},
}
need = P  # patient need in same units? scale patient scores to comparable units
# scale patient to drug-point scale: multiply by ~3? 
print("  patient need (raw):", P)
print("  total drug pts per fen (single dose):")
for name, pts in drug_pts.items():
    total_pts = sum(pts.values())
    fen = formulas[name]["份"]
    print(f"    {name:14s} single={total_pts}  x{fen}={total_pts*fen}")

print()
print("[8] coverage: patient pathology need vs supplied (fen * drug_pts * pct overlap)")
# For each pathology, sum supply across formulas
for path in P:
    supply = 0
    for name, pts in drug_pts.items():
        if path in pts:
            supply += pts[path] * formulas[name]["份"]
    print(f"  {path}: need~{P[path]}  supplied(drug_pts*fen)={supply}")
