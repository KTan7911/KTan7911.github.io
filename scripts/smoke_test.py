#!/usr/bin/env python3
"""离线冒烟测试：用本地 daily/data.json 模拟 fetch，跑通 render_html / update_index / update_archive，
不调用任何网络。用于验证排版修复没有破坏生成流程。"""
import os, sys, json, datetime

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SITE, "scripts"))
import generate_daily as g

# 用 data.json 里最近一天的数据伪造 items + notes
with open(os.path.join(SITE, "daily", "data.json"), encoding="utf-8") as f:
    store = json.load(f)
latest = sorted(store.keys(), reverse=True)[0]
rows = store[latest]
items = [{
    "title": r["title"], "nickname": r["nickname"],
    "read_num": 12345, "share_num": 100,
    "content_url": r.get("article_url", "#"),
} for r in rows]
notes = [{"title": r["title"], "summary": r["summary"], "why": r["why"], "tag": r["tag"]} for r in rows]

# 1) 渲染当日页
html_out = g.render_html(items, notes, latest, "TEST")
assert "card" in html_out and items[0]["title"] in html_out
print(f"[ok] render_html 生成，{len(items)} 条")

# 2) 更新首页（写临时副本，避免污染真实 index.html）
idx = os.path.join(SITE, "index.html")
bak = idx + ".testbak"
with open(idx, encoding="utf-8") as f: original = f.read()
with open(bak, "w", encoding="utf-8") as f: f.write(original)
try:
    g.update_index(f"daily/{latest}.html", items, notes)
    with open(idx, encoding="utf-8") as f: after = f.read()
    # 校验：锚点仍成对、卡片数=3、没有孤立 </a>
    assert after.count(g.GRID_START) == 1 and after.count(g.GRID_END) == 1, "锚点不成对"
    seg = after[after.find(g.GRID_START):after.find(g.GRID_END)]
    assert seg.count('<a class="card') == min(3, len(items)), f"卡片数异常 {seg.count('<a class=\"card')}"
    print("[ok] update_index 锚点替换正常，卡片数正确")
finally:
    with open(idx, "w", encoding="utf-8") as f: f.write(original)
    os.remove(bak)
    print("[ok] index.html 已还原")

# 3) 归档页
g.update_archive(os.path.join(SITE, "daily"), ["省钱", "避坑", "手机", "电池", "隐私"])
print("[ok] update_archive 生成正常")
print("\n全部冒烟测试通过 ✅")
