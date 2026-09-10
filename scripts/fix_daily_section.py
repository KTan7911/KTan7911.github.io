#!/usr/bin/env python3
"""一次性修复首页 #daily 板块被 generate_daily.py 旧版 update_index() 破坏的 HTML。

做法：
1. 找到 <!-- 今日生活科技 --> 段起始的 <section ... id="daily"> 到它的 </section>
2. 用干净的、带锚点注释的板块替换（锚点供新版 update_index() 精确替换卡片区）
3. 从 daily/data.json 取最近一天的 Top 3 重建成整齐网格卡片
"""
import os, re, json, html

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG_COLORS = {"省💰": "#eab308", "避坑⚠️": "#ef4444", "提效⚡": "#22c55e",
              "隐私🔒": "#3b82f6", "健康❤️": "#ec4899", "科普📖": "#94a3b8"}

GRID_START = "<!--DAILY_GRID_START-->"
GRID_END = "<!--DAILY_GRID_END-->"


def load_latest_items():
    p = os.path.join(SITE, "daily", "data.json")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        store = json.load(f)
    if not store:
        return []
    latest = sorted(store.keys(), reverse=True)[0]
    return latest, store[latest][:3]


def card(it):
    tag = it.get("tag", "科普📖")
    color = TAG_COLORS.get(tag, "#94a3b8")
    why = it.get("why", "").replace("对你的用处：", "").replace("对你的用处:", "")[:46]
    return f'''<a class="card project-card" href="{html.escape(it.get('url', '#'))}">
          <div class="card-icon">📰</div>
          <h3>{html.escape(it.get('title', ''))}</h3>
          <p>📰 {html.escape(it.get('nickname', ''))} · <span style="color:{color}">{tag}</span> · {html.escape(why)}</p>
          <span class="card-link">查看全文 →</span>
        </a>'''


def build_section(latest_date, items):
    cards = "\n        ".join(card(it) for it in items)
    return f'''<!-- 今日生活科技（每日自动更新） -->
  <section class="section section-alt" id="daily">
    <div class="container">
      <h2 class="section-title">📰 今日生活科技</h2>
      <p class="section-desc">每天 10 条跟你有关系的科技信息：省钱、避坑、提效、护隐私，每条附一句「对你有啥用」。不聊宏大命题，只说生活里用得上。</p>
      <div class="grid">
        {GRID_START}
        {cards}
        {GRID_END}
      </div>
      <p style="text-align:center;margin-top:26px"><a class="card-link" href="daily/{latest_date}.html">查看完整日报（10 条）→</a></p>
    </div>
  </section>'''


def main():
    idx = os.path.join(SITE, "index.html")
    with open(idx, encoding="utf-8") as f:
        src = f.read()

    # 定位损坏的 section：从「今日生活科技」注释起到其后第一个 </section>
    m = re.search(r"<!--\s*今日生活科技[^>]*-->\s*<section[^>]*id=\"daily\"", src)
    if not m:
        # 兜底：直接找 id="daily"
        m = re.search(r'<section[^>]*id="daily"', src)
    if not m:
        print("[err] 找不到 #daily 板块")
        return
    start = m.start()
    sec_end = src.find("</section>", m.end())
    if sec_end == -1:
        print("[err] 找不到 </section>")
        return
    sec_end += len("</section>")

    latest_date, items = load_latest_items()
    if not items:
        print("[err] daily/data.json 为空，用占位")
        latest_date, items = "2026-08-24", []
    new_sec = build_section(latest_date, items)

    src = src[:start] + new_sec + src[sec_end:]
    with open(idx, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"OK: #daily 板块已重建（{len(items)} 张卡片，日期 {latest_date}）")


if __name__ == "__main__":
    main()
