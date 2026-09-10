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
  "外交","军事","战争","导弹","制裁","宏观","政策解读","经济数据","GDP",
  "逝世","悼念","讣告","追思","缅怀","暖心","正能量","感动","致敬","表彰","慰问","座谈",
  "印发","通知公告","学习贯彻","领导调研","参观考察","峰会论坛","白皮书"]
LIFE_KW = ["免费","省钱","避坑","技巧","教程","设置","隐私","安全","诈骗","手机","电脑",
  "软件","App","充电","电池","屏幕","网速","会员","订阅","家电","冰箱","空调","洗衣机",
  "电视","摄像头","路由器","耳机","键盘","鼠标","健康","视力","睡眠","儿童","老人","家庭",
  "宠物","厨房","清洁","收纳","出行","旅行","学习","办公","学生","打工人",
  "清理","加速","下载","备份","找回","删除","恢复","提醒","清单","攻略","测评","实测"]
FAR_KW = ["光刻机","大模型","芯片","财报","季度","融资","IPO","股价","市值","发布会",
  "行业报告","专利","巨头","格局","战略","生态","资本","投融资","供应链","量产","制程",
  "纳米","架构师","开发者","半导体","新能源车","销量","同比","增长","破纪录","估值",
  "白皮书","峰会","论坛","人工智能大会","产业联盟","出海","全球化"]
LIFE_ACCOUNTS = ["什么值得买","果壳","雷科技","电手","黑马公社","手机中国","好物研究院",
  "家电研究所","丁香生活研究所","太平洋电脑网","中关村在线"]
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

# 热榜渠道（cimi-data get_hot_ranking 接口）
HOT_CHANNELS = {1: "微博", 2: "知乎", 3: "百度", 4: "抖音", 5: "头条"}

def fetch_hot_ranking(token, channel_id):
    """拉取单一热榜渠道的条目，统一成 wx-hot 相同的 item 结构。

    接口：GET /api/v3/hotrank?access_token=..&channel_id=N
    返回 list[{title, nickname(=平台名), read_num(=热度), share_num, content_url, _channel}]。
    接口异常时返回空列表，不影响主流程。
    """
    try:
        r = http_json(f"{HOST}/api/v3/hotrank", method="GET",
                      params={"access_token": token, "channel_id": channel_id})
    except Exception as e:
        print(f"[warn] 热榜渠道 {HOT_CHANNELS.get(channel_id, channel_id)} 拉取失败：{e}")
        return []
    d = r.get("data")
    if isinstance(d, dict):
        items = d.get("items") or d.get("list") or []
    elif isinstance(d, list):
        items = d
    else:
        items = []
    out = []
    for it in items:
        if isinstance(it, str):
            it = {"title": it}
        title = it.get("title") or it.get("word") or it.get("name") or it.get("keyword") or ""
        if not title:
            continue
        hot = it.get("hot") or it.get("hot_value") or it.get("read_num") or it.get("num") or it.get("rank") or 0
        try:
            hot = int(hot)
        except Exception:
            hot = 0
        out.append({
            "title": title,
            "nickname": HOT_CHANNELS.get(channel_id, f"渠道{channel_id}"),
            "read_num": hot,
            "share_num": 0,
            "content_url": it.get("url") or it.get("link") or f"https://www.baidu.com/s?wd={urllib.parse.quote(title)}",
            "_channel": HOT_CHANNELS.get(channel_id, str(channel_id)),
        })
    return out

def life_score(item):
    """生活化评分：命中生活词 +2/个，命中高大上词 -3/个，生活类账号 +2。"""
    t = item.get("title", "")
    s = 0
    for kw in LIFE_KW:
        if kw in t: s += 2
    for kw in FAR_KW:
        if kw in t: s -= 3
    if item.get("nickname", "") in LIFE_ACCOUNTS: s += 2
    return s

def keep(item):
    title = item.get("title", "")
    if any(k in title for k in BLACK_KW): return False
    if item.get("_channel"):                 # 热榜条目：单独用宽松规则
        return keep_hot(item)
    s = life_score(item)
    if s >= 2: return True                     # 明显生活向
    if item.get("nickname", "") in WHITELIST and s >= 0: return True  # 科技媒体且不扣分
    return item.get("nickname", "") in LIFE_ACCOUNTS

# ---- 热榜专用过滤 ----
# 硬噪声：直接剔除（悲剧/政治军事/体育赛事/娱乐八卦/讣告等，与生活科技无关）
HOT_BLACK = ["遇难","身亡","死亡","去世","逝世","讣告","悼念","报警","刑拘","被抓",
  "酒驾","诈骗","缅北","坠亡","跳楼","车祸","碰撞","火灾","爆炸",
  "战争","导弹","军演","冲突","制裁","外交","特朗普","普京","以色列","哈马斯",
  "女篮","男篮","国足","中超","英超","NBA","世界杯","奥运","金牌","夺冠","止步","无缘",
  "欧冠","联赛","球队","球迷","进球","停赛","乒乓","乒乓","运动员",
  "音乐节","演唱会","综艺","花少","明星","艺人","剧组","剧透","票房","热播",
  "恋情","出轨","离婚","结婚","婚礼","生子","怀孕","恋爱","分手","复婚",
  "梅姨","凶手","嫌犯","案","暴发","疫情","病毒","地震","台风","暴雨","洪水"]
# 生活/科技相关提升词（命中任一即纳入）
HOT_GOOD = ["手机","苹果","iPhone","安卓","华为","小米","折叠","屏幕","充电","电池","芯片","处理器",
  "电脑","笔记本","平板","耳机","手表","WiFi","网络","宽带","流量","套餐","5G","6G",
  "App","软件","应用","系统","升级","更新","下载","安装","清理","备份","数据","隐私",
  "AI","人工智能","大模型","机器人","GPT","算法","智能",
  "健康","睡眠","视力","减肥","瘦","饮食","运动","跑步","走路","养生","医生","体检",
  "涨","降","降价","优惠","免费","省钱","折扣","价格","块钱","元",
  "技巧","教程","攻略","方法","妙招","科普","揭秘","避坑","提醒","注意","建议",
  "家","冰箱","空调","洗衣机","厨","清洁","收纳","家电","出行","旅行","驾驶","车",
  "学生","学习","老师","教育","考试","高考","大学","考研","考公",
  "就业","招聘","职场","打工","工资","养老金","退休","医保","社保"]

def keep_hot(item):
    """热榜条目过滤：先剔除硬噪声，再要求命中生活/科技关键词。"""
    t = item.get("title", "")
    if any(k in t for k in HOT_BLACK):
        return False
    if any(k in t for k in LIFE_KW) or any(k in t for k in HOT_GOOD):
        return True
    return False

def hot_score(item):
    """热榜条目排序分：相关性 + 热度。强科技/消费话题加权。"""
    t = item.get("title", "")
    s = 0
    for kw in HOT_GOOD:
        if kw in t: s += 2
    # 强消费科技词额外加权，优先上日报
    STRONG = ["手机","iPhone","苹果","华为","小米","折叠","降价","价格","便宜","省钱","免费",
              "App","软件","AI","人工智能","机器人","健康","睡眠","减肥","技巧","教程","攻略"]
    for kw in STRONG:
        if kw in t: s += 3
    return s

def dedupe(items):
    """去重：微信源每个公众号最多 2 条；热榜源不限单平台数（避免单平台霸屏，但不卡太死）。"""
    seen, hot_seen, out = {}, {}, []
    for it in items:
        if it.get("_channel"):
            # 热榜：每个平台最多 4 条
            ch = it["_channel"]
            if hot_seen.get(ch, 0) >= 4:
                continue
            hot_seen[ch] = hot_seen.get(ch, 0) + 1
            out.append(it)
        else:
            nick = it.get("nickname", "")
            if seen.get(nick, 0) >= 2:
                continue
            seen[nick] = seen.get(nick, 0) + 1
            out.append(it)
    # 标题去重
    tseen, uniq = set(), []
    for it in out:
        t = it.get("title", "")
        if t in tseen:
            continue
        tseen.add(t)
        uniq.append(it)
    return uniq

# ---- 四大方向（主页板块宗旨：省钱/避坑/提效/护隐私）----
DIRECTIONS = ["省钱", "避坑", "提效", "护隐私"]
DIR_ICON = {"省钱": "省💰", "避坑": "避坑⚠️", "提效": "提效⚡", "护隐私": "隐私🔒"}
DIR_COLOR = {"省钱": "#eab308", "避坑": "#ef4444", "提效": "#22c55e", "护隐私": "#3b82f6"}
# 各方向目标条数（尽量 3+3+2+2）
DIR_QUOTA = {"省钱": 3, "避坑": 3, "提效": 2, "护隐私": 2}
# 各方向关键词（用于预筛 + 排序）
DIR_KW = {
    "省钱": ["省钱", "免费", "降价", "减价", "优惠", "折扣", "平替", "便宜", "性价比", "囤", "券", "会员", "续费", "扣费", "薅", "消费降级", "价格", "涨", "涨了", "块钱", "元"],
    "避坑": ["避坑", "陷阱", "套路", "智商税", "维权", "退钱", "退款", "骗局", "诈骗", "虚假", "坑", "上当", "投诉", "12315", "黑幕", "翻车", "踩雷", "被宰"],
    "提效": ["提效", "效率", "AI", "工具", "自动化", "技巧", "教程", "攻略", "快捷", "模板", "办公", "效率提升", "一键", "插件", "App", "软件", "提示词", "省时", "减负", "时间管理"],
    "护隐私": ["隐私", "权限", "信息泄露", "数据安全", "防骗", "追踪", "定位", "麦克风", "摄像头", "个人信息", "合规", "新规", "实名", "人脸", "验证码", "账号", "加密"],
}

def summarize(items):
    """用 DeepSeek 将条目改写为生活优化 10 条日报（四方向，每条 6 字段）。

    输出字段：title(标题)/direction(方向)/pain(核心痛点)/angle(文章切入点)/keywords(关键词)/review(深度评价)。
    保留原始 it，便于渲染时取来源/链接。
    """
    if not DS_KEY:
        return [{"title": it["title"], "direction": "提效", "pain": "", "angle": "",
                 "keywords": [], "review": ""} for it in items]
    lines = "\n".join(
        f"{i+1}. [{it.get('_channel') or it.get('nickname','')}] {it['title']}"
        for i, it in enumerate(items))
    prompt = (
        "你是一名专注\"现代人生活优化\"的内容主编，请为下面每条热点内容写一份日报条目。四个方向："
        "1省钱（消费降级/平替/薅羊毛/隐性支出/自动续费）2避坑（消费陷阱/合同套路/智商税/维权/新型骗局）"
        "3提效（AI工具/办公技巧/时间管理/自动化/信息减负）4护隐私（数据安全/App权限/防诈骗/个人信息保护/监管新规）。"
        "对每条输出 6 个字段：\n"
        "1)title：标题（15-25字，带钩子，不夸大）；\n"
        "2)direction：从 省钱/避坑/提效/护隐私 中选最贴切的一个；\n"
        "3)pain：核心痛点（1句话）；\n"
        "4)angle：文章切入点（2-3句，说清讲什么、怎么讲）；\n"
        "5)keywords：关键词标签（3-5个，字符串数组）；\n"
        "6)review：深度评价（30字左右）——点出这篇文章\"真正解决了什么\"而非复述标题，可有一点反差或提醒，"
        "像朋友推荐不像广告文案；允许指出局限性；禁止夸大（不用震惊/必看/史上最全/彻底/绝对），"
        "禁止编造数据、案例、专家名、机构名。\n"
        "严格按 JSON 数组输出，不要其他文字："
        '[{"title":"...","direction":"省钱","pain":"...","angle":"...","keywords":["..."],"review":"..."}]\n'
        "注意：四个方向尽量均衡，优先覆盖 省钱/避坑/提效/护隐私 各至少 2 条。\n\n"
        f"候选内容：\n{lines}")
    r = http_json("https://api.deepseek.com/chat/completions", method="POST",
                  headers={"Authorization": f"Bearer {DS_KEY}"},
                  data={"model": "deepseek-chat", "max_tokens": 4000, "temperature": 0.7,
                        "messages": [{"role": "user", "content": prompt}]})
    text = r["choices"][0]["message"]["content"]
    m = re.search(r"\[.*\]", text, re.S)
    try:
        notes = json.loads(m.group(0)) if m else []
        for n in notes:
            if n.get("direction") not in DIRECTIONS:
                n["direction"] = "提效"
            if not isinstance(n.get("keywords"), list):
                n["keywords"] = [str(n.get("keywords", ""))] if n.get("keywords") else []
        return notes
    except Exception:
        return []

def balance_by_direction(items, notes):
    """按 3+3+2+2 配额挑出最终 10 条（notes 已带 direction）。

    策略：先按方向归类，各方向优先取 life/hot 分高的；不足配额从其他方向按分补，"
    最终保证 10 条。
    """
    scored = list(zip(items, notes))
    def score(pair):
        it = pair[0]
        return hot_score(it) if it.get("_channel") else life_score(it)
    buckets = {d: [] for d in DIRECTIONS}
    for pair in scored:
        d = pair[1].get("direction")
        if d in buckets:
            buckets[d].append(pair)
    for d in buckets:
        buckets[d].sort(key=score, reverse=True)
    picked, used = [], set()
    for d in DIRECTIONS:
        for pair in buckets[d][:DIR_QUOTA[d]]:
            picked.append(pair); used.add(id(pair))
    # 补足到 10 条
    rest = [p for p in sorted(scored, key=score, reverse=True) if id(p) not in used]
    for pair in rest:
        if len(picked) >= 10:
            break
        picked.append(pair)
    picked = picked[:10]
    # 交错排序：让四个方向轮流出现，首页不会一屏全是同一方向
    by_d = {d: [p for p in picked if p[1].get("direction") == d] for d in DIRECTIONS}
    interleaved, idx = [], 0
    while len(interleaved) < len(picked):
        for d in DIRECTIONS:
            if idx < len(by_d[d]):
                interleaved.append(by_d[d][idx])
        idx += 1
    picked = interleaved
    return [p[0] for p in picked], [p[1] for p in picked]

def fmt_read(n):
    if n >= 100000: return "10万+"
    if n >= 10000: return f"{n//10000}.{n%10000//1000}万"
    return str(n)

def render_html(items, notes, date_str, balance):
    """详情页：展示 10 条日报的完整 6 字段（方向/来源/痛点/切入点/关键词/评价）。"""
    today_cn = datetime.date.today().strftime("%Y年%m月%d日")
    rows = []
    for i, (it, note) in enumerate(zip(items, notes), 1):
        d = note.get("direction", "提效")
        color = DIR_COLOR.get(d, "#94a3b8")
        kws = note.get("keywords") or []
        kw_html = "".join(f'<span class="kw">{html.escape(str(k))}</span>' for k in kws)
        rows.append(f"""
    <div class="item">
      <div class="ihead">
        <span class="no">{i}</span>
        <span class="dir" style="color:{color};border-color:{color}">{html.escape(d)}</span>
        <span class="src">📰 {html.escape(it.get('nickname',''))}</span>
      </div>
      <a class="t" href="{html.escape(it['content_url'])}" target="_blank" rel="noopener">{html.escape(note.get('title') or it['title'])}</a>
      {f'<div class="fld"><b>痛点</b>{html.escape(note.get("pain",""))}</div>' if note.get('pain') else ''}
      {f'<div class="fld"><b>切入点</b>{html.escape(note.get("angle",""))}</div>' if note.get('angle') else ''}
      {f'<div class="kws">{kw_html}</div>' if kw_html else ''}
      {f'<div class="review">💬 {html.escape(note.get("review",""))}</div>' if note.get('review') else ''}
    </div>""")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>今日生活科技 {date_str} - 省钱·避坑·提效·护隐私 10 条</title>
<meta name="description" content="每天 10 条跟你有关系的科技信息：省钱、避坑、提效、护隐私，每条附痛点、切入点与深度评价。">
<style>
  body{{margin:0;background:#0f172a;color:#e2e8f0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.7}}
  .wrap{{max-width:760px;margin:0 auto;padding:20px 16px 40px}}
  header{{text-align:center;padding:28px 0 14px}}
  header h1{{margin:0;font-size:22px;letter-spacing:1px}}
  header p{{color:#94a3b8;font-size:13px;margin:6px 0 0}}
  .list{{background:#1e293b;border-radius:14px;padding:6px 20px;margin-top:6px}}
  .item{{padding:20px 0;border-top:1px solid #334155}}
  .item:first-child{{border-top:none}}
  .ihead{{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap}}
  .no{{flex:0 0 24px;height:24px;line-height:24px;text-align:center;background:#60a5fa;color:#0f172a;border-radius:7px;font-size:13px;font-weight:700}}
  .dir{{font-size:12px;font-weight:700;border:1px solid;border-radius:10px;padding:1px 9px}}
  .src{{font-size:12px;color:#94a3b8}}
  .t{{color:#e2e8f0;text-decoration:none;font-size:17px;font-weight:700;display:block;line-height:1.5}}
  .t:hover{{color:#60a5fa}}
  .fld{{margin:8px 0 0;font-size:14px;color:#cbd5e1}}
  .fld b{{display:inline-block;color:#60a5fa;font-size:12px;font-weight:700;margin-right:8px;border:1px solid #334155;border-radius:6px;padding:0 6px}}
  .kws{{margin:9px 0 0}}
  .kw{{display:inline-block;font-size:12px;color:#94a3b8;border:1px solid #334155;border-radius:10px;padding:1px 9px;margin:0 6px 6px 0}}
  .review{{margin:9px 0 0;font-size:14px;color:#fbbf24}}
  .follow{{text-align:center;background:#1e293b;border-radius:12px;padding:18px;margin-top:26px}}
  .follow b{{color:#60a5fa}}
  footer{{text-align:center;color:#64748b;font-size:12px;margin-top:22px}}
  a.back{{color:#94a3b8;font-size:13px;text-decoration:none}}
  @media(max-width:560px){{.list{{padding:2px 13px}}.t{{font-size:15.5px}}}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>📡 KTcove 今日生活科技</h1>
    <p>{today_cn} · 省钱 · 避坑 · 提效 · 护隐私 ，共 {len(items)} 条</p>
  </header>
  <div class="list">{''.join(rows)}
  </div>
  <div class="follow">
    <p><b>每天 17:40 自动更新</b>，关注公众号「KTCOVE宝藏小站」不迷路</p>
    <p style="color:#94a3b8;font-size:13px"><a class="back" href="https://www.ktcove.com/daily/">查看历史日报 →</a></p>
  </div>
  <footer><a class="back" href="https://www.ktcove.com/">← 返回首页 KTcove 寻宝人</a></footer>
</div>
</body>
</html>"""

GRID_START = "<!--DAILY_LIST_START-->"
GRID_END = "<!--DAILY_LIST_END-->"

def update_index(daily_path, today_items, notes):
    """更新首页 #daily 板块为「10 条清单」布局（标题 + 一句点评）。

    用锚点注释精确替换列表区，避免旧版靠 find('</div>') 误伤卡片内部 div 导致的 HTML 破坏。
    """
    idx = os.path.join(SITE, "index.html")
    with open(idx, encoding="utf-8") as f: src = f.read()
    gs = src.find(GRID_START)
    ge = src.find(GRID_END)
    if gs == -1 or ge == -1 or ge < gs:
        print("[warn] 首页缺少 DAILY_LIST 锚点，跳过首页更新（请先运行 fix_daily_section.py）")
        return
    rows = []
    for i, (it, note) in enumerate(zip(today_items, notes), 1):
        d = note.get("direction", "提效")
        color = DIR_COLOR.get(d, "#94a3b8")
        review = (note.get("review", "") or "").strip()
        rows.append(
            f'        <div class="ditem">\n'
            f'          <div class="dno">{i}</div>\n'
            f'          <div class="dmain">\n'
            f'            <a class="dtitle" href="{daily_path}">{html.escape(note.get("title") or it["title"])}</a>\n'
            f'            <div class="dmeta"><span class="dtag" style="color:{color}">{html.escape(d)}</span>{html.escape(review)}</div>\n'
            f'          </div>\n'
            f'        </div>'
        )
    block = GRID_START + "\n" + "\n".join(rows) + "\n        " + GRID_END
    src = src[:gs] + block + src[ge + len(GRID_END):]
    with open(idx, "w", encoding="utf-8") as f: f.write(src)

def compute_hot_words(items, notes):
    """从当天标题+评价统计热词，取前 5 个作为归档页标签。"""
    text = " ".join(it.get("title", "") for it in items)
    text += " " + " ".join((n.get("review", "") + " " + n.get("pain", "")) for n in notes)
    counts = {}
    for kw in LIFE_KW:
        c = text.lower().count(kw.lower())
        if c:
            counts[kw] = c
    top = [k for k, _ in sorted(counts.items(), key=lambda x: -x[1])][:5]
    return top or ["省钱", "避坑", "提效", "护隐私", "手机"]

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
            "title": note.get("title") or it["title"],
            "nickname": it.get("nickname", ""),
            "direction": note.get("direction", "提效"),
            "pain": note.get("pain", ""),
            "angle": note.get("angle", ""),
            "keywords": note.get("keywords", []),
            "review": note.get("review", ""),
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
const DIR_COLOR = {{"省钱":"#eab308","避坑":"#ef4444","提效":"#22c55e","护隐私":"#3b82f6"}};
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
    const c = DIR_COLOR[e.direction] || '#94a3b8';
    const kws = (e.keywords || []).slice(0, 3).map(k => '#' + esc(k)).join(' ');
    return '<div class="res"><a href="' + esc(e.url) + '">' + esc(e.title) + '</a>' +
      '<div class="meta">📅 ' + esc(e.date) + ' · 📰 ' + esc(e.nickname) + ' · <span class="tagc" style="color:' + c + '">' + esc(e.direction) + '</span></div>' +
      '<div class="meta">' + esc(e.review || '') + '</div>' +
      (kws ? '<div class="meta">' + kws + '</div>' : '') + '</div>';
  }}).join('');
  box.style.display = 'block';
}}
function doSearch() {{
  const kw = document.getElementById('q').value.trim().toLowerCase();
  const days = document.getElementById('days');
  const hint = document.getElementById('hint');
  if (!kw) {{ days.style.display='block'; hint.style.display='block'; document.getElementById('results').style.display='none'; return; }}
  const list = ALL.filter(e => (e.title + ' ' + (e.review||'') + ' ' + (e.pain||'') + ' ' + (e.angle||'') + ' ' + ((e.keywords||[]).join(' ')) + ' ' + (e.direction||'') + ' ' + e.nickname).toLowerCase().includes(kw));
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

def collect_items(token):
    """多源采集：微信爆款（keji+caijing）+ 热榜（微博/知乎/百度/抖音/头条）。

    返回 (all_items, balance)。任一源失败不影响其它源。
    """
    all_items, balance = [], None
    # 1) 微信爆款（科技类，不足时补财经）
    try:
        wx_items, balance = fetch_hot(token)
        all_items.extend(wx_items)
        print(f"[info] 微信科技类 {len(wx_items)} 条")
        if len(wx_items) < 20:
            global CATEGORY
            old = CATEGORY
            CATEGORY = "caijing"
            try:
                cj_items, balance = fetch_hot(token)
                all_items.extend(cj_items)
                print(f"[info] 微信财经类补充 {len(cj_items)} 条")
            finally:
                CATEGORY = old
    except Exception as e:
        print(f"[warn] 微信爆款拉取失败：{e}")
    # 2) 热榜五渠道
    for cid in HOT_CHANNELS:
        rk = fetch_hot_ranking(token, cid)
        all_items.extend(rk)
        print(f"[info] 热榜 {HOT_CHANNELS[cid]} {len(rk)} 条")
    return all_items, balance

def main():
    date_str = datetime.date.today().isoformat()
    token = get_token()
    all_items, balance = collect_items(token)
    print(f"[info] 共采集 {len(all_items)} 条原始条目，余额 {balance}")
    today = datetime.date.today().isoformat()
    # 微信源带 published_at，热榜源不带：分开处理。
    wx_dated = [it for it in all_items if not it.get("_channel") and str(it.get("published_at", "")).startswith(today)]
    hot_items = [it for it in all_items if it.get("_channel")]
    if not wx_dated:
        # 微信当日无数据时，退回全部微信条目（避免空）
        wx_dated = [it for it in all_items if not it.get("_channel")]
    items = wx_dated + hot_items
    print(f"[info] 当日微信 {len(wx_dated)} 条 + 热榜 {len(hot_items)} 条")
    items = [it for it in items if keep(it)]
    if len(items) < 5:
        print(f"[warn] 生活化过滤后仅 {len(items)} 条，放宽为按热度取（剔除黑名单词后）") 
        items = [it for it in all_items if not any(k in it.get("title", "") for k in BLACK_KW)]
    items = dedupe(items)
    items.sort(key=lambda x: ((hot_score(x) if x.get("_channel") else life_score(x)), x.get("read_num", 0)), reverse=True)
    # 方向感知预筛：每个方向至少保底若干条候选，保证 DeepSeek 有料可分
    def dir_of(it):
        t = it.get("title", "")
        best, bestc = None, 0
        for d, kws in DIR_KW.items():
            c = sum(1 for k in kws if k in t)
            if c > bestc:
                best, bestc = d, c
        return best
    by_dir = {d: [] for d in DIRECTIONS}
    others = []
    for it in items:
        d = dir_of(it)
        (by_dir[d] if d in by_dir else others).append(it)
    pool, picked_ids = [], set()
    for d in DIRECTIONS:            # 每方向先取前 5 条
        for it in by_dir[d][:5]:
            pool.append(it); picked_ids.add(id(it))
    for it in (by_dir.get(None, []) + others):
        if len(pool) >= 20:
            break
        if id(it) not in picked_ids:
            pool.append(it); picked_ids.add(id(it))
    pool.sort(key=lambda x: ((hot_score(x) if x.get("_channel") else life_score(x)), x.get("read_num", 0)), reverse=True)
    items = pool[:18]
    if len(items) < 5:
        print(f"[warn] 有效文章仅 {len(items)} 条，检查过滤规则")
    if not items:
        print("[err] 本次采集/过滤后无有效条目，跳过本次生成（常见原因：cimi-data 余额不足 6020 或接口异常）。")
        print("[err] 未生成任何文件，不提交，等待下次运行。")
        return
    notes = summarize(items)
    if not notes:
        print("[warn] DeepSeek 未返回有效内容，使用占位（保留标题）")
        notes = [{"title": it["title"], "direction": "提效", "pain": "", "angle": "",
                  "keywords": [], "review": ""} for it in items]
    # DeepSeek 会自行精选/改写，条数可能少于输入：按标题对齐回原始 it（保链接/来源）
    used = set()
    aligned = []
    for n in notes:
        t = (n.get("title") or "").strip()
        match = None
        for it in items:
            if id(it) in used:
                continue
            if t and (t == it["title"].strip() or t[:8] in it["title"] or it["title"][:8] in t):
                match = it; break
        if match is None:
            # 按顺序补位
            for it in items:
                if id(it) not in used:
                    match = it; break
        if match is not None:
            used.add(id(match))
            aligned.append((match, n))
    if not aligned:
        aligned = list(zip(items, notes))
    items = [p[0] for p in aligned]
    notes = [p[1] for p in aligned]
    # 按 3+3+2+2 配额挑出最终 10 条
    items, notes = balance_by_direction(items, notes)
    print(f"[info] 最终 {len(items)} 条，方向分布：" +
          ", ".join(f"{d}{sum(1 for n in notes if n.get('direction')==d)}" for d in DIRECTIONS))

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
