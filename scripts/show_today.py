#!/usr/bin/env python3
import json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "daily", "data.json")
d = json.load(open(p, encoding="utf-8"))
k = sorted(d)[-1]
print("=== 日期", k, "共", len(d[k]), "条 ===\n")
for i, x in enumerate(d[k], 1):
    print(f"{i}. [{x.get('direction')}] {x.get('nickname')} | {x.get('title')}")
    print(f"   痛点: {x.get('pain')}")
    print(f"   切入点: {x.get('angle')}")
    print(f"   关键词: {'/'.join(x.get('keywords', []))}")
    print(f"   评价: {x.get('review')}")
    print()
