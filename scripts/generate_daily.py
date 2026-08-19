#!/usr/bin/env python3
"""每日生活科技日报生成器（v2 生活化版）
抓取微信科技爆款 → 生活化过滤 → DeepSeek 点评(带标签) → 生成日报页 → 更新首页板块 → 归档页 → sitemap
"""
import os, re, sys, json, html, datetime, urllib.request, urllib.parse, urllib.error

HOST = os.environ.get("CIMI_HOST", "https://www.cimidata.com/").rstrip("/")

def _load_local_creds():
    """本地兜底：从 ~/.openclaw/openclaw.json 自动读凭据（Actions 云端无此文件则返回 None）。"""
    import pathlib
    p = pathlib.Path.home() / ".openclaw" / "openclaw.json"
    if not p.exists():
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            cfg = json.load(f)
        mcp = (cfg.get("mcp") or {}).get("servers", {}).get("cimi-data", {}).get("env", {})
        ds = (cfg.get("models") or {}).get("providers", {}).get("deepseek", {})
        return {"app_id": mcp.get("app_id"), "app_secret": mcp.get("app_secret"),
                "ds_key": ds.get("apiKey")}
    except Exception:
        return {}

_creds = _load_local_creds()
APP_ID  = os.environ.get("CIMI_APP_ID") or _creds.get("app_id") or ""
APP_SEC = os.environ.get("CIMI_APP_SECRET") or _creds.get("app_secret") or ""
DS_KEY  = os.environ.get("DEEPSEEK_API_KEY") or _creds.get("ds_key") or ""
SITE    = os.environ.get("SITE_DIR", ".")          # 本地测试设为 D:\DS_Harnees\MyWeb
CATEGORY = "keji"
TOP_N    = 10
DAILY_URL_PREFIX = "https://www.ktcove.com/daily/"

# ---- 生活化过滤规则 v2 ----
WHITELIST = ["爱范儿","少数派","虎嗅APP","量子位","机器之心","IT之家","差评",
  "AppSo","科技每日推送","极客公园","新智元","数字尾巴","果壳","环球科学","电脑报",
  "雷科技","电手","黑马公社","什么值得买","好物研究院","家电研究所","丁香生活研究所",
  "手机中国","太平洋电脑网","中关村在线","微软科技"]
BLACK_KW = ["暴雨","预警","涨停","跌停","地震","台风","洪水","天气","股市","油价",
  "通报","纪委","中奖","彩票","征婚","养生","谜案","车祸","火灾","招聘","辟谣","停水","停电",
  "外交","军事","战争","导弹","制裁","宏观","政策解读","经济数据","GDP"]
BOOST_KW = ["免费","省钱","避坑","技巧","教程","设置","隐私","安全","诈骗","手机","电脑",
  "软件","App","充电","电池","屏幕","网速","会员","订阅","家电","冰箱","空调","洗衣机",
  "电视","摄像头","路由器","耳机","键盘","鼠标","健康","视力","睡眠","儿童","老人","家庭",
  "宠物","厨房","清洁","收纳","出行","旅行","学习","办公","学生","打工人"]
TAG_COLORS = {"省💰":"#eab308","避坑⚠️":"#ef4444","提效⚡":"#22c55e","隐私🔒":"#3b82f6","健康❤️":"#ec4899","科普📖":"#94a3b8"}

def http_json(url, method="GET", params=None, data=None, headers=None, timeout=30):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method=method, headers=headers or {})
    if data is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"HTTP {e.code} from {url}\n服务端返回: {body}") from e

def get_token():
    try:
        r = http_json(f"{HOST}/api/token", method="POST",
                      data={"app_id": APP_ID, "app_secret": APP_SEC})
    except Exception as e:
        raise RuntimeError(f"无法连接 cimi-data（检查网络/密钥是否为空）：{e}")
    if not r.get("data"):
        raise RuntimeError("cimi-data token 请求失败，完整返回：" + json.dumps(r, ensure_ascii=False))
    return r["data"]["access_token"]

def fetch_hot(token):
    """拉取微信爆款文章（不传 published_at，该参数会导致 400；日期在客户端过滤）。"""
    r = http_json(f"{HOST}/api/v2/hot/articles", method="POST",
                  params={"access_token": token},
                  data={"category": CATEGORY, "read_num": 10000})
    return r.get("data", {}).get("items", []), r.get("balance")

def keep(item):
    nick, title = item.get("nickname", ""), item.get("title", "")
    if nick in WHITELIST: return True
    if any(k in title for k in BLACK_KW): return False
    boost = sum(1 for k in BOOST_KW if k.lower() in title.lower())
    if boost >= 1: return True
    return item.get("read_num", 0) >= 30000

def dedupe(items):
    seen, out = {}, []
    for it in items:
        nick = it.get("nickname", "")
        if seen.get(nick, 0) >= 2: continue
        seen[nick] = seen.get(nick, 0) + 1
        out.append(it)
    return out

def summarize(items):
    if not DS_KEY:
        return [{"title": it["title"], "summary": "", "why": "", "tag": "科普📖"} for it in items]
    lines = "\n".join(f"{i+1}. {it['title']}（{it.get('nickname','')}，阅读 {it.get('read_num',0)}）"
                      for i, it in enumerate(items))
    prompt = ("你是生活科技编辑，读者是普通消费者（学生、打工人、家里长辈）。对下面每条新闻写三样："
              "1)summary：一句话人话概括（40字内，别用术语）；2)why：对普通人的实际用处——能不能省钱、避坑、"
              "省时间、保护隐私或健康？用大白话写（50字内），开头直接说\"对你的用处：\"；"
              "3)tag：从 省💰/避坑⚠️/提效⚡/隐私🔒/健康❤️/科普📖 中选最贴切的一个。"
              "严格按JSON数组输出，不要其他文字："
              '[{"title":"原标题","summary":"...","why":"...","tag":"省💰"}]\n\n'
              f"新闻列表：\n{lines}")
    r = http_json("https://api.deepseek.com/chat/completions", method="POST",
                  headers={"Authorization": f"Bearer {DS_KEY}"},
                  data={"model": "deepseek-chat", "max_tokens": 1500, "temperature": 0.7,
                        "messages": [{"role": "user", "content": prompt}]})
    text = r["choices"][0]["message"]["content"]
    m = re.search(r"\[.*\]", text, re.S)
    try:
        notes = json.loads(m.group(0)) if m else []
        for n in notes:
            n.setdefault("tag", "科普📖")
        return notes
    except Exception:
        return []

def fmt_read(n):
    if n >= 100000: return "10万+"
    if n >= 10000: return f"{n//10000}.{n%10000//1000}万"
    return str(n)

def render_html(items, notes, date_str, balance):
    today_cn = datetime.date.today().strftime("%Y年%m月%d日")
    cards = []
    for i, (it, note) in enumerate(zip(items, notes), 1):
        tag = note.get("tag", "科普📖")
        color = TAG_COLORS.get(tag, "#94a3b8")
        cards.append(f"""
    <article class="card">
      <p class="tag"><span style="color:{color}">{tag}</span></p>
      <a class="t" href="{html.escape(it['content_url'])}" target="_blank" rel="noopener">
        <span class="no">{i}</span> {html.escape(it['title'])}
      </a>
      <p class="src">📰 {html.escape(it.get('nickname',''))} · 👀 {fmt_read(it.get('read_num',0))} · 🔁 {it.get('share_num',0)}</p>
      {f'<p class="sum">📌 {html.escape(note.get("summary",""))}</p>' if note.get('summary') else ''}
      {f'<p class="why">💡 {html.escape(note.get("why",""))}</p>' if note.get('why') else ''}
    </article>""")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>生活科技日报 {date_str} - 今天跟你有关系的 10 条科技信息</title>
<meta name="description" content="每日 10 条贴近生活的科技信息：省钱、避坑、提效、护隐私，附大白话点评。">
<style>
  body{{margin:0;background:#0f172a;color:#e2e8f0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.7}}
  .wrap{{max-width:720px;margin:0 auto;padding:20px 16px 40px}}
  header{{text-align:center;padding:28px 0 8px}}
  header h1{{margin:0;font-size:22px;letter-spacing:1px}}
  header p{{color:#94a3b8;font-size:13px;margin:6px 0 0}}
  .card{{background:#1e293b;border-radius:12px;padding:14px 16px;margin:14px 0}}
  .tag{{margin:0;font-size:13px;font-weight:700}}
  .t{{color:#60a5fa;text-decoration:none;font-size:16px;font-weight:600;display:block;margin-top:2px}}
  .t:hover{{text-decoration:underline}}
  .no{{display:inline-block;background:#60a5fa;color:#0f172a;border-radius:6px;padding:0 7px;font-size:13px;font-weight:700;margin-right:6px}}
  .src{{color:#94a3b8;font-size:12px;margin:6px 0 0}}
  .sum{{margin:8px 0 0;font-size:14px}}
  .why{{margin:4px 0 0;font-size:14px;color:#fbbf24}}
  .follow{{text-align:center;background:#1e293b;border-radius:12px;padding:18px;margin-top:26px}}
  .follow b{{color:#60a5fa}}
  footer{{text-align:center;color:#64748b;font-size:12px;margin-top:22px}}
  a.back{{color:#94a3b8;font-size:13px;text-decoration:none}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>📡 KTcove 生活科技日报</h1>
    <p>{today_cn} · 今天跟你有关系的 {len(items)} 条科技信息</p>
  </header>
  {''.join(cards)}
  <div class="follow">
    <p><b>每天 17:40 自动推送</b>，关注公众号「KTCOVE宝藏小站」不迷路</p>
    <p style="color:#94a3b8;font-size:13px"><a class="back" href="https://www.ktcove.com/daily/">查看历史日报 →</a> · 完整评测与工具推荐，公众号回复「目录」</p>
  </div>
  <footer><a class="back" href="https://www.ktcove.com/">← 返回首页 KTcove 寻宝人</a> · 余额 {balance}</footer>
</div>
</body>
</html>"""

def update_index(daily_path, today_items, notes):
    """更新首页 #daily 板块的 Top3 卡片（含 tag 徽标）。"""
    idx = os.path.join(SITE, "index.html")
    with open(idx, encoding="utf-8") as f: src = f.read()
    start = src.find('id="daily"')
    if start == -1:
        print("[warn] 首页没有 #daily 板块，跳过首页更新")
        return
    grid_start = src.find('<div class="grid">', start)
    grid_end = src.find('</div>', grid_start)
    cards = []
    for it, note in zip(today_items[:3], notes[:3]):
        tag = note.get("tag", "科普📖")
        color = TAG_COLORS.get(tag, "#94a3b8")
        why = note.get("why", "").replace("对你的用处：", "").replace("对你的用处:", "")[:40]
        cards.append(f'''<a class="card project-card" href="{daily_path}">
  <div class="card-icon">📰</div>
  <h3>{html.escape(it["title"])}</h3>
  <p>📰 {html.escape(it.get("nickname",""))} · <span style="color:{color}">{tag}</span> · {html.escape(why)}</p>
  <span class="card-link">查看全文 →</span>
</a>''')
    new_grid = '<div class="grid">\n        ' + "\n        ".join(cards) + "\n      "
    src = src[:grid_start] + new_grid + src[grid_end:]
    with open(idx, "w", encoding="utf-8") as f: f.write(src)

def compute_hot_words(items, notes):
    """从当天标题+摘要统计生活热词，取前 5 个作为标签。"""
    text = " ".join(it.get("title", "") for it in items)
    text += " " + " ".join(n.get("summary", "") + n.get("why", "") for n in notes)
    counts = {}
    for kw in BOOST_KW:
        c = text.lower().count(kw.lower())
        if c:
            counts[kw] = c
    top = [k for k, _ in sorted(counts.items(), key=lambda x: -x[1])][:5]
    return top or ["免费", "省钱", "避坑", "AI", "手机"]

def update_data_json(daily_dir, date_str, items, notes, rel):
    """维护 daily/data.json：按日期归档所有文章，供归档页搜索使用。"""
    path = os.path.join(daily_dir, "data.json")
    store = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                store = json.load(f)
        except Exception:
            store = {}
    store[date_str] = [
        {
            "date": date_str,
            "title": it["title"],
            "nickname": it.get("nickname", ""),
            "summary": note.get("summary", ""),
            "why": note.get("why", ""),
            "tag": note.get("tag", "科普📖"),
            "url": f"{DAILY_URL_PREFIX}{date_str}.html",
            "article_url": it.get("content_url", ""),
        }
        for it, note in zip(items, notes)
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=1)

def update_archive(daily_dir, hot_words):
    """生成 daily/index.html：搜索框 + 5 个热词标签 + 日期列表（前端读 data.json 搜索）。"""
    days = []
    for name in os.listdir(daily_dir):
        if name.endswith(".html") and name != "index.html":
            d = name[:-5]
            try:
                datetime.date.fromisoformat(d)
                days.append(d)
            except ValueError:
                continue
    days.sort(reverse=True)
    links = "".join(f'<a class="day" href="{d}.html">{d} 日报 →</a>'
                    for d in days)
    chips = "".join(
        f'<button class="chip" data-kw="{html.escape(k)}">{html.escape(k)}</button>'
        for k in hot_words)
    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>历史日报归档与搜索 - KTcove 生活科技日报</title>
<meta name="description" content="KTcove 生活科技日报历史归档：搜索框 + 今日热词标签，按关键词或日期查找往期科技生活信息。">
<style>
  body{{margin:0;background:#0f172a;color:#e2e8f0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.7}}
  .wrap{{max-width:720px;margin:0 auto;padding:20px 16px 40px}}
  header{{text-align:center;padding:28px 0 8px}}
  header h1{{margin:0;font-size:22px}}
  header p{{color:#94a3b8;font-size:13px;margin:6px 0 0}}
  .searchbox{{display:block;width:100%;box-sizing:border-box;padding:12px 16px;border-radius:10px;border:1px solid #334155;background:#1e293b;color:#e2e8f0;font-size:15px;margin-top:18px}}
  .searchbox:focus{{outline:none;border-color:#60a5fa}}
  .chips{{margin:12px 0 4px;text-align:center}}
  .chip{{background:#1e293b;color:#60a5fa;border:1px solid #334155;border-radius:999px;padding:6px 14px;margin:4px;font-size:13px;cursor:pointer}}
  .chip:hover,.chip.active{{background:#60a5fa;color:#0f172a}}
  .hint{{color:#64748b;font-size:12px;text-align:center;margin:14px 0 4px}}
  .day{{display:block;background:#1e293b;border-radius:10px;padding:12px 16px;margin:10px 0;color:#60a5fa;text-decoration:none}}
  .day:hover{{background:#334155}}
  .res{{background:#1e293b;border-radius:10px;padding:12px 16px;margin:10px 0}}
  .res a{{color:#60a5fa;text-decoration:none;font-weight:600;font-size:15px}}
  .res .meta{{color:#94a3b8;font-size:12px;margin-top:4px}}
  .res .tagc{{font-size:12px;font-weight:700}}
  .none{{text-align:center;color:#64748b;padding:30px 0}}
  footer{{text-align:center;color:#64748b;font-size:12px;margin-top:22px}}
  a.back{{color:#94a3b8;font-size:13px;text-decoration:none}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>📚 历史日报归档</h1>
    <p>共 {len(days)} 期 · 搜索或点热词，快速找到往期内容</p>
  </header>
  <input class="searchbox" id="q" type="search" placeholder="🔍 搜索历史日报，如：电池、免费、隐私…">
  <div class="chips" id="chips">{chips}</div>
  <p class="hint" id="hint">▼ 按日期浏览</p>
  <div id="days">{links}</div>
  <div id="results" style="display:none"></div>
  <footer><a class="back" href="https://www.ktcove.com/">← 返回首页</a></footer>
</div>
<script>
const TAG_COLOR = {{"省💰":"#eab308","避坑⚠️":"#ef4444","提效⚡":"#22c55e","隐私🔒":"#3b82f6","健康❤️":"#ec4899","科普📖":"#94a3b8"}};
let ALL = [];
fetch('data.json').then(r => r.json()).then(store => {{
  for (const [d, arr] of Object.entries(store)) ALL = ALL.concat(arr);
  ALL.sort((a, b) => b.date.localeCompare(a.date));
}}).catch(() => {{}});
function esc(s) {{ return String(s).replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])); }}
function render(list) {{
  const box = document.getElementById('results');
  if (!list.length) {{ box.style.display='block'; box.innerHTML='<p class="none">没有找到相关内容，换个词试试～</p>'; return; }}
  box.innerHTML = list.map(e => {{
    const c = TAG_COLOR[e.tag] || '#94a3b8';
    return '<div class="res"><a href="' + esc(e.url) + '">' + esc(e.title) + '</a>' +
      '<div class="meta">📅 ' + esc(e.date) + ' · 📰 ' + esc(e.nickname) + ' · <span class="tagc" style="color:' + c + '">' + esc(e.tag) + '</span></div>' +
      '<div class="meta">' + esc(e.summary || '') + '</div></div>';
  }}).join('');
  box.style.display = 'block';
}}
function doSearch() {{
  const kw = document.getElementById('q').value.trim().toLowerCase();
  const days = document.getElementById('days');
  const hint = document.getElementById('hint');
  if (!kw) {{ days.style.display='block'; hint.style.display='block'; document.getElementById('results').style.display='none'; return; }}
  const list = ALL.filter(e => (e.title + e.summary + e.why + e.tag + e.nickname).toLowerCase().includes(kw));
  days.style.display = 'none'; hint.style.display = 'none';
  render(list);
}}
document.getElementById('q').addEventListener('input', doSearch);
document.querySelectorAll('.chip').forEach(ch => ch.addEventListener('click', () => {{
  document.getElementById('q').value = ch.dataset.kw;
  document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
  ch.classList.add('active');
  doSearch();
}}));
</script>
</body>
</html>"""
    with open(os.path.join(daily_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)

def update_sitemap(daily_url):
    sp = os.path.join(SITE, "sitemap.xml")
    with open(sp, encoding="utf-8") as f: src = f.read()
    if daily_url in src: return
    today = datetime.date.today().isoformat()
    entry = f'''<url>
  <loc>{daily_url}</loc>
  <lastmod>{today}</lastmod>
  <changefreq>daily</changefreq>
  <priority>0.9</priority>
</url>'''
    src = src.replace("</urlset>", entry + "\n</urlset>", 1)
    with open(sp, "w", encoding="utf-8") as f: f.write(src)

def main():
    date_str = datetime.date.today().isoformat()
    token = get_token()
    all_items, balance = fetch_hot(token)
    today = datetime.date.today().isoformat()
    items = [it for it in all_items if str(it.get("published_at", "")).startswith(today)]
    if len(items) < 5:
        print(f"[warn] 今天匹配 {len(items)} 条，回退使用最近数据（共 {len(all_items)} 条）")
        items = all_items
    items = [it for it in items if keep(it)]
    items = dedupe(items)
    items.sort(key=lambda x: x.get("read_num", 0), reverse=True)
    items = items[:TOP_N]
    if len(items) < 5:
        print(f"[warn] 过滤后有效文章仅 {len(items)} 条，检查过滤规则")
    notes = summarize(items)
    if len(notes) != len(items):
        notes = [{"title": it["title"], "summary": "", "why": "", "tag": "科普📖"} for it in items]

    daily_dir = os.path.join(SITE, "daily"); os.makedirs(daily_dir, exist_ok=True)
    rel = f"daily/{date_str}.html"
    with open(os.path.join(SITE, rel), "w", encoding="utf-8") as f:
        f.write(render_html(items, notes, date_str, balance))
    update_index(rel, items, notes)
    hot_words = compute_hot_words(items, notes)
    update_data_json(daily_dir, date_str, items, notes, rel)
    update_archive(daily_dir, hot_words)
    update_sitemap(f"{DAILY_URL_PREFIX}{date_str}.html")
    print(f"OK: {rel} 已生成（{len(items)} 条）；首页板块/归档页(含搜索与热词 {','.join(hot_words)})/sitemap 已更新；余额 {balance}")

if __name__ == "__main__":
    main()
