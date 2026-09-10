#!/usr/bin/env python3
"""重建首页 #daily 板块：改为「10 条清单」布局（标题 + 一句点评），一眼扫完。

- 用 <!--DAILY_LIST_START--> / <!--DAILY_LIST_END--> 锚点
- 从 daily/data.json 取最近一天的 10 条
"""
import os, re, json, html

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG_COLORS = {"省钱": "#eab308", "避坑": "#ef4444", "提效": "#22c55e", "护隐私": "#3b82f6"}

LIST_START = "<!--DAILY_LIST_START-->"
LIST_END = "<!--DAILY_LIST_END-->"

LIST_CSS = """  <style>
    .dlist{margin-top:8px;border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;background:var(--card-bg)}
    .ditem{display:flex;gap:12px;padding:14px 18px;border-top:1px solid var(--border);align-items:flex-start;transition:background .18s}
    .ditem:first-child{border-top:none}
    .ditem:hover{background:rgba(99,102,241,.06)}
    .dno{flex:0 0 26px;height:26px;line-height:26px;text-align:center;border-radius:7px;background:var(--primary);color:#fff;font-size:13px;font-weight:700;margin-top:1px}
    .dmain{flex:1;min-width:0}
    .dtitle{font-size:15.5px;font-weight:600;color:var(--text);text-decoration:none;display:block}
    .dtitle:hover{color:var(--primary)}
    .dmeta{margin-top:4px;font-size:13px;color:var(--text-light);line-height:1.55}
    .dtag{display:inline-block;font-size:12px;padding:1px 8px;border-radius:9px;background:rgba(148,163,184,.16);margin-right:6px;white-space:nowrap}
    @media(max-width:560px){.ditem{padding:12px 12px}.dtitle{font-size:14.5px}}
  </style>"""


def load_items():
    p = os.path.join(SITE, "daily", "data.json")
    if not os.path.exists(p):
        return None, []
    with open(p, encoding="utf-8") as f:
        store = json.load(f)
    if not store:
        return None, []
    latest = sorted(store.keys(), reverse=True)[0]
    return latest, store[latest]


def render_list(items):
    rows = []
    for i, it in enumerate(items, 1):
        d = it.get("direction", "提效")
        color = TAG_COLORS.get(d, "#94a3b8")
        review = (it.get("review", "") or "").strip()
        url = html.escape(it.get("url", "#"))
        rows.append(
            f'        <div class="ditem">\n'
            f'          <div class="dno">{i}</div>\n'
            f'          <div class="dmain">\n'
            f'            <a class="dtitle" href="{url}">{html.escape(it.get("title",""))}</a>\n'
            f'            <div class="dmeta"><span class="dtag" style="color:{color}">{html.escape(d)}</span>{html.escape(review)}</div>\n'
            f'          </div>\n'
            f'        </div>'
        )
    return "\n".join(rows)


def build_section(latest_date, items):
    lst = render_list(items)
    return f'''<!-- 今日生活科技（每日自动更新） -->
  <section class="section section-alt" id="daily">
    <div class="container">
      <h2 class="section-title">📰 今日生活科技</h2>
      <p class="section-desc">每天 10 条跟你有关系的科技信息：省钱、避坑、提效、护隐私，每条附一句「对你有啥用」。不聊宏大命题，只说生活里用得上。</p>
{LIST_CSS}
      <div class="dlist">
        {LIST_START}
{lst}
        {LIST_END}
      </div>
      <p style="text-align:center;margin-top:22px"><a class="card-link" href="daily/{latest_date}.html">查看完整日报（10 条）→</a></p>
    </div>
  </section>'''


def main():
    idx = os.path.join(SITE, "index.html")
    with open(idx, encoding="utf-8") as f:
        src = f.read()

    m = re.search(r"<!--\s*今日生活科技[^>]*-->\s*<section[^>]*id=\"daily\"", src)
    if not m:
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

    latest_date, items = load_items()
    if not items:
        print("[err] daily/data.json 为空")
        return
    new_sec = build_section(latest_date, items)
    src = src[:start] + new_sec + src[sec_end:]
    with open(idx, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"OK: #daily 已改为 {len(items)} 条清单布局（日期 {latest_date}）")


if __name__ == "__main__":
    main()
