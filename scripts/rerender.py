#!/usr/bin/env python3
"""从 daily/data.json 重新渲染当日页 + 首页板块（不调 API），用于调整样式后快速预览。"""
import os, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SITE, "scripts"))
import generate_daily as g

date_str = sorted(json.load(open(os.path.join(SITE, "daily", "data.json"), encoding="utf-8")))[-1]
store = json.load(open(os.path.join(SITE, "daily", "data.json"), encoding="utf-8"))
rows = store[date_str]

items = [{"title": r["title"], "nickname": r.get("nickname", ""), "read_num": 0,
          "share_num": 0, "content_url": r.get("article_url", "#")} for r in rows]
notes = [{"title": r["title"], "direction": r.get("direction", "提效"),
          "pain": r.get("pain", ""), "angle": r.get("angle", ""),
          "keywords": r.get("keywords", []), "review": r.get("review", "")} for r in rows]

# 重新交错排序（方向轮转）
DIRECTIONS = g.DIRECTIONS
by_d = {d: [p for p in zip(items, notes) if p[1]["direction"] == d] for d in DIRECTIONS}
inter, idx = [], 0
while len(inter) < len(items):
    for d in DIRECTIONS:
        if idx < len(by_d[d]):
            inter.append(by_d[d][idx])
    idx += 1
items = [p[0] for p in inter]; notes = [p[1] for p in inter]

rel = f"daily/{date_str}.html"
open(os.path.join(SITE, rel), "w", encoding="utf-8").write(g.render_html(items, notes, date_str, "preview"))
g.update_index(rel, items, notes)
print(f"OK 重渲染 {rel}（{len(items)} 条，顺序：" + "→".join(n["direction"] for n in notes) + "）")
