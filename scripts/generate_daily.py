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
# 微信爆款分类（多分类拉取，加宽软件/工具类内容来源）
WX_CATEGORIES = ["keji", "caijing"]
TOP_N    = 10
MIN_ITEMS = 3      # 固定条数（少而精）
MAX_ITEMS = 3      # 固定条数
DAILY_URL_PREFIX = "https://www.ktcove.com/daily/"

# ---- 软件/工具/技巧导向过滤规则 v3 ----
# 主播定位：软件（Windows/安卓/iOS/鸿蒙）、插件、知识、技巧、方法分享
# 目标：只留「能装、能用、能学」的东西；剔除医疗、汽车、奢侈品、消费纠纷等无关话题

# 优质来源账号（多为软件/数码/效率类）
WHITELIST = [
  # 软件/效率/App
  "少数派", "AppSo", "爱范儿", "电脑报", "IT之家", "微软科技", "Softpedia",
  "效率工具指南", "MacTalk", "苏生不惑", "好用App推荐", "小众软件", "异次元软件世界",
  "一沟祥云", "阮一峰的网络日志", "Linux中国", "开源中国", "GitHubDaily", "Python开发者",
  # 数码/硬件/测评
  "差评", "数字尾巴", "雷科技", "电手", "黑马公社", "手机中国", "锋潮评测",
  "太平洋电脑网", "中关村在线", "科技美学", "小白测评", "WHYLAB", "IT之家",
  # 科技媒体/大厂
  "虎嗅APP", "量子位", "机器之心", "极客公园", "新智元", "环球科学", "果壳",
  # 消费/生活科技
  "什么值得买", "好物研究院", "家电研究所", "丁香生活研究所",
  # 知识/学习
  "得到", "知乎日报", "利维坦", "三联生活周刊", "看理想"]

# 硬黑名单：标题命中直接剔除（跟软件/技巧完全无关的领域）
BLACK_KW = [
  # 天气灾害/突发事件
  "暴雨","预警","地震","台风","洪水","天气","停水","停电","火灾","车祸",
  # 财经股市
  "涨停","跌停","股市","油价","GDP","宏观","政策解读","经济数据",
  # 政治军事
  "外交","军事","战争","导弹","制裁","通报","纪委",
  # 政务通稿
  "逝世","悼念","讣告","追思","缅怀","暖心","正能量","感动","致敬","表彰",
  "慰问","座谈","印发","通知公告","学习贯彻","领导调研","参观考察","峰会论坛","白皮书",
  # 娱乐八卦
  "恋情","出轨","离婚","结婚","婚礼","生子","怀孕","恋爱","分手","复婚",
  "明星","艺人","剧组","剧透","票房","热播","综艺","演唱会","音乐节",
  # 体育
  "女篮","男篮","国足","中超","英超","NBA","世界杯","奥运","金牌","夺冠",
  # 医疗健康（主播不做这块）
  "养生","体检","医生","看病","医院","病症","吃药","中药","偏方","减肥","瘦身","近视","颈椎病",
  # 汽车（不做）
  "买车","车市","4S店","汽修","维修保养","油价","新能源车","燃油车","车主","驾驶","试驾","提车",
  # 奢侈品/消费纠纷（不做）
  "奢侈品","爱马仕","LV","香奈儿","名牌包","智商税","维权","投诉","退货","索赔","起诉","被告",
  # 情感/家庭
  "征婚","谜案","中奖","彩票","婆媳","彩礼","亲子关系"]

# 软件/工具/数码/效率 —— 命中即高度相关（核心保留词）
LIFE_KW = [
  # 系统与平台
  "Windows","windows","Win11","Win10","macOS","Mac","iOS","iPadOS","安卓","Android",
  "鸿蒙","HarmonyOS","Linux","Ubuntu","系统","系统更新","升级","补丁","版本",
  # 软件与应用
  "软件","App","应用","工具","插件","扩展","脚本","小程序","客户端","安装包","下载",
  "开源","免费软件","神器","宝藏","推荐","盘点","合集",
  # 技巧与方法
  "技巧","教程","攻略","方法","妙招","设置","配置","快捷键","玩法","使用技巧",
  "操作","步骤","一键","批量","自动化","效率","提效","摸鱼","办公",
  # 数据与安全
  "数据","备份","恢复","找回","删除","清理","隐私","安全","密码","账号","防骗","防诈",
  "权限","设置项","广告","弹窗","骚扰",
  # 设备与硬件（偏数码工具）
  "手机","电脑","笔记本","平板","耳机","键盘","鼠标","显示器","路由器","硬盘","U盘",
  "充电","电池","屏幕","芯片","处理器","摄像头","智能家居","智能手表","NAS","主机",
  # AI 工具
  "AI","人工智能","大模型","GPT","ChatGPT","DeepSeek","Copilot","机器人","算法","提示词",
  # 学习与知识
  "学习","知识","读书","笔记","考研","考公","考证","英语","网课","课程",
  # 网络与通信
  "WiFi","网络","宽带","流量","套餐","5G","6G","VPN","浏览器",
  # 消费（仅数码软件相关）
  "免费","省钱","优惠","折扣","会员","订阅","薅羊毛","平替","性价比","值得买"]

# 减分词：命中扣分（偏产业/资本/宏大叙事，非实操内容）
FAR_KW = ["光刻机","大模型","芯片","财报","季度","融资","IPO","股价","市值","发布会",
  "行业报告","专利","巨头","格局","战略","生态","资本","投融资","供应链","量产","制程",
  "纳米","架构师","开发者","半导体","销量","同比","增长","破纪录","估值",
  "白皮书","峰会","论坛","人工智能大会","产业联盟","出海","全球化"]

# 优质软件/效率/数码类账号（加分）
LIFE_ACCOUNTS = ["少数派", "AppSo", "爱范儿", "IT之家", "电脑报", "电手", "黑马公社",
  "小众软件", "异次元软件世界", "MacTalk", "苏生不惑", "效率工具指南", "少数派",
  "雷科技", "锋潮评测", "科技美学", "小白测评", "WHYLAB", "差评", "数字尾巴",
  "什么值得买", "果壳", "手机中国", "好物研究院", "家电研究所", "太平洋电脑网", "中关村在线"]
TAG_COLORS = {"软件📦":"#eab308","工具🔧":"#22c55e","技巧💡":"#3b82f6","隐私🔒":"#ef4444","科普📖":"#94a3b8"}

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

# 定向公众号（软件/数码/效率类）——这是最精准的内容来源
TARGET_ACCOUNTS = [
    "少数派",      # 软件/效率/App 测评，质量最高
    "AppSo",       # 应用推荐
    "爱范儿",      # 数码科技
    "IT之家",      # 科技资讯
    "小众软件",    # 小众软件推荐
    "电手",        # 数码技巧
    "差评",        # 数码评测
    "数字尾巴",    # 数码生活
    # 纯软件推荐号（搜一搜验证过，高频更新）
    "木子淇",      # 神仙App推荐，更新频率极高
    "效率君",      # 五星好评软件推荐
    "软件资源局",  # 宝藏APP
    "软件大侠",    # 本命软件分享
    "京灵智创",    # 免费实用软件
]
# 搜索关键词：用于发现往期高质量干货文章（不限日期）
SEARCH_KEYWORDS = [
    "Windows 技巧",     # 电脑技巧
    "软件推荐",         # 软件合集
    "App推荐",          # 应用推荐
    "效率工具",         # 效率工具
    "隐藏功能",         # 隐藏功能
    "开源软件",         # 开源
    "电脑小技巧",       # 电脑技巧
    "安卓技巧",         # 手机技巧
]

# 「常青干货」特征词（标题命中则优先，因为这类不看时效、收藏价值高）
EVERGREEN_KW = [
    "收藏", "合集", "盘点", "个技巧", "个小技巧", "招", "必会", "必装", "必备",
    "神器", "宝藏", "值得", "推荐", "好用", "效率翻倍", "干货", "一篇够", "够用",
    "告别", "小白", "新手", "秘籍", "大全", "排行榜", "好用不火", "冷门",
]


def fetch_account(token, name):
    """定向拉取指定公众号的历史文章（天然精准，无需过滤）。"""
    try:
        r = http_json(f"{HOST}/api/v2/articles/history", method="POST",
                      params={"access_token": token}, data={"id": name})
    except Exception as e:
        print(f"[warn] 公众号[{name}] 拉取失败：{str(e)[:80]}")
        return [], None
    items = (r.get("data") or {}).get("items") or []
    for it in items:
        it["_mp"] = name          # 标记来源公众号
        it["_channel"] = "公众号"  # 当作独立渠道，复用热榜的宽松过滤
        if it.get("source_url"):
            it["content_url"] = it["source_url"]
        # 公众号文章不叫 read_num，统一给个默认值
        it.setdefault("read_num", 0)
        it.setdefault("nickname", name)
    return items, r.get("balance")

def fetch_search(token, keyword, page=1):
    """微信搜一搜：按关键词搜集文章（不限日期，能捞到往期干货）。

    返回的标题带 <em> 高亮标签，需清洗。
    """
    try:
        r = http_json(f"{HOST}/api/v3/articles/search", method="POST",
                      params={"access_token": token},
                      data={"keyword": keyword, "page": page})
    except Exception as e:
        print(f"[warn] 搜索[{keyword}] 失败：{str(e)[:80]}")
        return [], None
    items = (r.get("data") or {}).get("items") or []
    out = []
    for it in items:
        title = re.sub(r"<[^>]+>", "", it.get("title", "") or "")
        if not title:
            continue
        out.append({
            "title": title,
            "nickname": it.get("nickname", ""),
            "content_url": it.get("content_url", ""),
            "published_at": it.get("published_at", ""),
            "read_num": 0,
            "_search": keyword,     # 标记来源搜索
        })
    return out, r.get("balance")

def evergreen_score(item):
    """往期干货评分：标题命中「常青」特征词加分。"""
    t = item.get("title", "")
    s = 0
    for kw in EVERGREEN_KW:
        if kw in t: s += 3
    # 含数字（如「21个」「30个」）通常代表清单式干货
    if re.search(r"\d+\s*[个招款种]", t):
        s += 4
    return s

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
    # 搜一搜来的：已是精准关键词结果，只要不中黑名单就放行
    if item.get("_search"):
        if any(k in title for k in BLACK_KW):
            return False
        return True
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
  "梅姨","凶手","嫌犯","案","暴发","疫情","病毒","地震","台风","暴雨","洪水",
  # ===== 主播不做的领域（新增）=====
  # 医疗健康
  "养生","体检","医生","医院","看病","病症","吃药","中药","偏方","诊室","临床",
  "减肥","瘦身","减脂","健身","瑜伽","膝盖","颈椎","腰椎","骨质","血压","血糖",
  # 汽车
  "买车","车市","4S店","汽修","维修保养","新能源车","燃油车","车主","驾驶","试驾","提车",
  "轿车","SUV","发动机","变速箱","油耗","轮胎","驾照","交管",
  # 奢侈品/消费维权
  "奢侈品","爱马仕","LV","香奈儿","名牌包","拾便袋",
  "维权","起诉","被告","索赔","消费者协会",
  # 房产/情感
  "房价","二手房","楼盘","房贷","彩礼","婆媳","征婚","相亲","脱单",
  # 硬件爆料/拉踩/段子（对软件技巧主播无用）
  "爆料","曝光","预测","前瞻","概念图","渲染图","上手","开箱","拆机",
  "起售价","预订价","预约量","代购","黄牛","涨价","维修费","工艺倒退",
  "A18","A19","骁龙","天玑","跑分","安兔兔","DXO",
  # 游戏/抽卡/娱乐向
  "攻略组","抽卡","氪金","副本","开黑","段位","皮肤","英雄","赛季",
  # 无关公众人物/八卦
  "宋祖德","网红","博主","主播","直播带货"]
# 软件/工具/技巧相关提升词（命中任一即纳入）——核心保留白名单
HOT_GOOD = [
  # 系统与平台
  "Windows","windows","Win11","Win10","macOS","iOS","iPadOS","安卓","Android",
  "鸿蒙","HarmonyOS","Linux","系统更新","系统升级",
  # 软件/应用/插件
  "软件","App","应用","插件","扩展","脚本","小程序","客户端","开源","神器","宝藏",
  "浏览器","输入法","播放器","下载器","工具箱",
  # AI 工具
  "AI","人工智能","大模型","GPT","ChatGPT","DeepSeek","Copilot","智能体","提示词","算法",
  # 设备与硬件
  "手机","苹果","iPhone","华为","小米","荣耀","OPPO","vivo","三星","折叠屏",
  "电脑","笔记本","台式机","平板","iPad","耳机","手表","键盘","鼠标","显示器","硬盘","NAS",
  "充电","电池","芯片","处理器","屏幕","摄像头","路由器","WiFi","网络","宽带","流量",
  # 技巧与方法
  "技巧","教程","攻略","方法","妙招","设置","配置","快捷键","操作","一键","批量","自动化",
  "提效","效率","办公","摸鱼","隐藏功能","冷知识","科普","盘点","实测","测评",
  # 数据/安全/隐私
  "隐私","数据","备份","恢复","找回","清理","加速","密码","账号","权限","防骗","防诈",
  "广告","弹窗","骚扰","卸载","升级","更新","下载","安装",
  # 学习知识
  "学习","知识","笔记","读书","课程","网课","考研","考证","英语","效率工具",
  # 消费（数码相关）
  "免费","省钱","优惠","折扣","降价","价格","会员","订阅","平替","性价比","薅羊毛"]

def keep_hot(item):
    """热榜/公众号条目过滤：先剔除硬噪声，再要求命中软件/工具/技巧关键词。"""
    t = item.get("title", "")
    # 定向公众号来的：来源本身够精准，只要不中黑名单就放行
    if item.get("_mp"):
        if any(k in t for k in BLACK_KW):
            return False
        # 公众号内也有广告/荐物/活动类，过滤掉
        NOISE = ["最后一波", "限时优惠", "复制口令", "文中链接", "广告", "抽奖",
                 "开奖", "签售", "招募", "招聘", "投稿", "征稿", "合作"]
        if any(k in t for k in NOISE):
            return False
        return True
    # 1. 黑名单优先（医疗/汽车/娱乐/体育/奢侈品一律不要）
    if any(k in t for k in BLACK_KW) or any(k in t for k in HOT_BLACK):
        return False
    # 2. 必须命中软件/工具/技巧相关词
    if not (any(k in t for k in LIFE_KW) or any(k in t for k in HOT_GOOD)):
        return False
    # 3. 产业/宏大叙事类（只谈趋势不谈怎么用）也会被剔除
    #    除非同时命中实操词（软件/工具/技巧/怎么做）
    industry = ["AGI", "通用人工智能", "大模型", "AI取代", "行业格局", "产业", "芯片",
                "算力", "估值", "融资", "上市", "财报", "发布会", "巨头", "战略"]
    hands_on = ["工具", "软件", "App", "插件", "技巧", "教程", "设置", "方法", "步骤",
                "一键", "怎么", "如何", "用法", "功能", "快捷键", "下载", "安装", "演示", "实测"]
    if any(k in t for k in industry) and not any(k in t for k in hands_on):
        return False
    return True

def hot_score(item):
    """排序分：定向公众号 > 搜一搜干货 > 强关键词；硬件爆料降权。"""
    t = item.get("title", "")
    s = 0
    # 定向公众号内容天然精准
    if item.get("_mp"):
        s += 6
    # 搜一搜来的往期干货：常青程度越高越优先
    if item.get("_search"):
        s += 4 + evergreen_score(item)
    for kw in HOT_GOOD:
        if kw in t: s += 2
    # 强相关词（主播核心内容）额外加权，优先上日报
    # 注：硬件品牌不算强词（避免 iPhone/手机爆料刷屏），软件/工具/技巧才算
    STRONG = ["Windows","Win11","macOS","iOS","安卓","Android","鸿蒙","HarmonyOS",
              "软件","App","插件","扩展","开源","神器","工具箱","教程","技巧","攻略",
              "AI","GPT","ChatGPT","DeepSeek","Copilot","提示词",
              "快捷键","设置","隐私","备份","自动化","效率","批量","一键","隐藏功能",
              "怎么用","如何","免费","省钱","权限"]
    for kw in STRONG:
        if kw in t: s += 3
    # 硬件爆料类降权（纯爆料/降价/预约/发布会不会教你用东西）
    HYPE = ["爆料","曝光","上手","开箱","预订","预约","起售价","售价","元起",
            "史上最低","降价","涨价","代购","黄牛","抢购","售罄",
            "上手体验","外观","配色","手感","续航","充电速度","跑分","排行"]
    for kw in HYPE:
        if kw in t: s -= 4
    return s

def dedupe(items):
    """去重：定向公众号每个最多 3 条；微信爆款每个号最多 2 条；热榜每平台最多 4 条。"""
    seen, hot_seen, out = {}, {}, []
    for it in items:
        if it.get("_mp"):
            # 定向公众号：每个号最多 3 条
            key = "mp:" + it["_mp"]
            if seen.get(key, 0) >= 3:
                continue
            seen[key] = seen.get(key, 0) + 1
            out.append(it)
            continue
        if it.get("_search"):
            # 搜一搜：同关键词最多 3 条
            key = "sk:" + it["_search"]
            if seen.get(key, 0) >= 3:
                continue
            seen[key] = seen.get(key, 0) + 1
            out.append(it)
            continue
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

# ---- 四大方向（主页板块宗旨：新软件/实用工具/技巧攻略/隐私安全）----
# 主播定位：软件（Windows/安卓/iOS/鸿蒙）、插件、知识、技巧、方法分享
DIRECTIONS = ["新软件", "实用工具", "技巧攻略", "隐私安全"]
DIR_ICON = {"新软件": "软件📦", "实用工具": "工具🔧", "技巧攻略": "技巧💡", "隐私安全": "隐私🔒"}
DIR_COLOR = {"新软件": "#eab308", "实用工具": "#22c55e", "技巧攻略": "#3b82f6", "隐私安全": "#ef4444"}
# 各方向目标条数（尽量 3+3+2+2）
DIR_QUOTA = {"新软件": 3, "实用工具": 3, "技巧攻略": 2, "隐私安全": 2}
# 各方向关键词（用于预筛 + 排序）
DIR_KW = {
    "新软件": ["软件", "App", "应用", "上线", "发布", "更新", "版本", "开源", "客户端", "插件", "扩展", "小程序", "下载", "安装", "Windows", "macOS", "iOS", "安卓", "鸿蒙", "Linux"],
    "实用工具": ["工具", "神器", "宝藏", "效率", "批量", "自动化", "脚本", "插件", "一键", "快捷键", "效率工具", "AI", "GPT", "Copilot", "提示词", "NAS", "备份"],
    "技巧攻略": ["技巧", "教程", "攻略", "方法", "妙招", "设置", "配置", "隐藏功能", "冷知识", "玩法", "操作", "盘点", "科普", "学习", "笔记", "键盘", "鼠标", "实测", "测评"],
    "隐私安全": ["隐私", "权限", "信息泄露", "数据安全", "防骗", "防诈", "追踪", "定位", "麦克风", "摄像头", "个人信息", "密码", "账号", "加密", "广告", "弹窗", "骚扰", "卸载"],
}

def summarize(items):
    """用 DeepSeek 将条目改写为软件/工具日报（四方向，每条 6 字段）。

    输出字段：title(标题)/direction(方向)/pain(核心痛点)/angle(文章切入点)/keywords(关键词)/review(深度评价)。
    保留原始 it，便于渲染时取来源/链接。
    """
    if not DS_KEY:
        return [{"title": it["title"], "direction": "技巧攻略", "pain": "", "angle": "",
                 "keywords": [], "review": ""} for it in items]
    lines = "\n".join(
        f"{i+1}. [{it.get('_mp') or it.get('_search') or it.get('_channel') or it.get('nickname','')}] {it['title']}"
        for i, it in enumerate(items))
    prompt = (
        "你是一名专注\"软件/工具/技巧\"分享的内容主编，读者是想学新东西、找好用的工具的人。"
        "四个方向："
        "1新软件（新出的App/软件/插件/开源项目/系统更新/鸿蒙安卓iOS Windows动态）"
        "2实用工具（效率工具/自动化/脚本/快捷键/AI工具/NAS/备份/一键操作）"
        "3技巧攻略（使用方法/设置/隐藏功能/教程/攻略/冷知识/学习技巧）"
        "4隐私安全（权限管理/数据安全/防骗防诈/广告弹窗/账号密码/卸载流氓软件）。"
        "❗重要：严格筛选，宁少勿滥。只写软件/工具/数码/技巧类内容。"
        "如果某条新闻跟这些完全无关（医疗健康、汽车、奢侈品、情感、房产、体育、娱乐八卦），"
        "直接跳过不写。\n"
        "【最终只输出 3 条】从候选里挑出 3 条最适合软件/工具/技巧受众的。"
        "注意：候选中可能混有“往期干货”（经典文章），这类只要内容好、值得收藏，"
        "跟新的内容一样可以选，不必因为是旧的就不用。\n"
        "质量比数量重要，宁缺毋滥。\n"
        "对每条输出 6 个字段：\n"
        "1)title：标题（15-25字，带钩子，不夸大）；\n"
        "2)direction：从 新软件/实用工具/技巧攻略/隐私安全 中选最贴切的一个；\n"
        "3)pain：核心痛点（1句话）——用大白话说出读者遇到这事时的真实困境或纠结，"
        "要让人一看就觉得\"说的就是我\"，别用行业黑话；\n"
        "4)angle：这一步是全文最重要的部分，不要写\"文章切入点\"这种编辑术语，"
        "而是要写给读者看的\"这东西/这个方法是什么 + 怎么用\"，具体要求：\n"
        "   （a）先一句话说清楚这是什么、能解决什么问题（软件叫什么名字、支持什么平台、干什么用的），"
        "读者看完能\"哦，原来是这么一个东西\"；\n"
        "   （b）再给出 2-3 条具体、能照着做的步骤（在哪下、怎么装、哪个按钮、怎么设置、有什么坑），"
        "要具体到动作，不要泛泛说\"可以试试\"\"值得一看\"；\n"
        "   （c）语言平实口语化，像朋友在饭桌上给你讲明白，不用术语，不喊口号，总长 60-90 字；\n"
        "5)keywords：关键词标签（3-5个，字符串数组）；\n"
        "6)review：我的观点（30-45字）——要有人味、有温度，像朋友替你想了一步。"
        "口吻可以带点共情（比如\"这功能藏得挺深\"\"找了好久终于有了\"），也可以温柔地提醒一句，"
        "但不要煽情、不要说教、不要用\"值得注意的是\"这类书面语，也不要点评文章本身写得好不好。"
        "重点是帮读者看到这个工具/方法对他有什么用。\n"
        "禁止夸大（不用震惊/必看/史上最全/彻底/绝对），禁止编造数据、案例、专家名、机构名。\n"
        "严格按 JSON 数组输出，不要其他文字："
        '[{"title":"...","direction":"实用工具","pain":"...","angle":"...","keywords":["..."],"review":"..."}]\n'
        "注意：三个方向尽量不同，优先从 新软件/实用工具/技巧攻略/隐私安全 中覆盖不同角度。\n\n"
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
                n["direction"] = "技巧攻略"
            if not isinstance(n.get("keywords"), list):
                n["keywords"] = [str(n.get("keywords", ""))] if n.get("keywords") else []
        return notes
    except Exception:
        return []

def balance_by_direction(items, notes):
    """按方向配额挑最终条目（质量优先，3-10 条都行）。

    策略：先按方向归类，各方向优先取 life/hot 分高的；从其他方向按分补，
    但**最多补到 10 条，最少 3 条即可**。AI 已经筛过的条目不额外凑数。
    """
    scored = list(zip(items, notes))
    def score(pair):
        it = pair[0]
        return hot_score(it) if (it.get("_channel") or it.get("_search") or it.get("_mp")) else life_score(it)
    buckets = {d: [] for d in DIRECTIONS}
    for pair in scored:
        d = pair[1].get("direction")
        if d in buckets:
            buckets[d].append(pair)
    for d in buckets:
        buckets[d].sort(key=score, reverse=True)
    picked, used = [], set()
    # 质量门槛：候选充足时按配额取
    total = len(scored)
    quota = DIR_QUOTA if total >= 8 else {d: 99 for d in DIRECTIONS}
    for d in DIRECTIONS:
        for pair in buckets[d][:quota[d]]:
            picked.append(pair); used.add(id(pair))
    # 补足到 MIN_ITEMS（但不超过 MAX_ITEMS，也不超过 AI 实际给出的条数）
    rest = [p for p in sorted(scored, key=score, reverse=True) if id(p) not in used]
    for pair in rest:
        if len(picked) >= MAX_ITEMS:
            break
        picked.append(pair)
    picked = picked[:MAX_ITEMS]
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
    """详情页：展示日报的完整 6 字段（方向/来源/怎么回事/怎么办/关键词/我的观点）。"""
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
      {f'<div class="fld"><b>怎么回事</b>{html.escape(note.get("pain",""))}</div>' if note.get('pain') else ''}
      {f'<div class="fld"><b>怎么办</b>{html.escape(note.get("angle",""))}</div>' if note.get('angle') else ''}
      {f'<div class="kws">{kw_html}</div>' if kw_html else ''}
      {f'<div class="review">💬 我的观点：{html.escape(note.get("review",""))}</div>' if note.get('review') else ''}
    </div>""")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>今日软件工具 {date_str} - 新软件·实用工具·技巧攻略·隐私安全</title>
<meta name="description" content="每天精选跟你有关系的软件工具信息：新软件、实用工具、技巧攻略、隐私安全，每条附怎么回事、怎么用与我的观点。">
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
    <h1>📡 KTcove 今日软件工具</h1>
    <p>{today_cn} · 新软件 · 实用工具 · 技巧攻略 · 隐私安全 ，共 {len(items)} 条</p>
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
    """更新首页 #daily 板块为「清单」布局（标题 + 一句点评）。

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
    return top or ["新软件", "实用工具", "技巧攻略", "隐私安全", "软件"]

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
            "direction": note.get("direction", "技巧攻略"),
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
const DIR_COLOR = {{"新软件":"#eab308","实用工具":"#22c55e","技巧攻略":"#3b82f6","隐私安全":"#ef4444"}};
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
    """多源采集：微信爆款（科技类多分类）+ 热榜（微博/知乎/百度/抖音/头条）。

    返回 (all_items, balance)。任一源失败不影响其它源。
    """
    all_items, balance = [], None

    # 0) 定向公众号（最精准的来源，优先）
    for name in TARGET_ACCOUNTS:
        acc_items, bal = fetch_account(token, name)
        if bal is not None:
            balance = bal
        all_items.extend(acc_items)
        print(f"[info] 公众号[{name}] {len(acc_items)} 条")

    # 1) 微信爆款：多分类拉取，补足软件/工具类内容
    #    keji=科技，caijing=财经，it=互联网数码（若接口支持）
    global CATEGORY
    _old_cat = CATEGORY
    for cat in WX_CATEGORIES:
        try:
            CATEGORY = cat
            wx_items, balance = fetch_hot(token)
            all_items.extend(wx_items)
            print(f"[info] 微信[{cat}] {len(wx_items)} 条")
        except Exception as e:
            print(f"[warn] 微信[{cat}] 拉取失败：{e}")
        finally:
            CATEGORY = _old_cat
    # 2) 热榜五渠道
    for cid in HOT_CHANNELS:
        rk = fetch_hot_ranking(token, cid)
        all_items.extend(rk)
        print(f"[info] 热榜 {HOT_CHANNELS[cid]} {len(rk)} 条")

    # 3) 搜一搜：捞往期干货（不限日期）
    for kw in SEARCH_KEYWORDS:
        found, bal = fetch_search(token, kw)
        if bal is not None:
            balance = bal
        all_items.extend(found)
        print(f"[info] 搜索[{kw}] {len(found)} 条")

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
    if len(items) < MIN_ITEMS:
        print(f"[warn] 过滤后仅 {len(items)} 条（低于最少 {MIN_ITEMS} 条）")
        print(f"[warn] 放宽为按热度取（仅剔除硬黑名单词）")
        items = [it for it in all_items if not any(k in it.get("title", "") for k in BLACK_KW)]
    items = dedupe(items)
    items.sort(key=lambda x: ((hot_score(x) if (x.get("_channel") or x.get("_search") or x.get("_mp")) else life_score(x)), x.get("read_num", 0)), reverse=True)
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
    pool.sort(key=lambda x: ((hot_score(x) if (x.get("_channel") or x.get("_search") or x.get("_mp")) else life_score(x)), x.get("read_num", 0)), reverse=True)
    items = pool[:18]
    if len(items) < MIN_ITEMS:
        print(f"[warn] 候选不足 {MIN_ITEMS} 条，本次不生成（宁缺勿滥）")
    if not items:
        print("[err] 本次采集/过滤后无有效条目，跳过本次生成（常见原因：cimi-data 余额不足 6020 或接口异常）。")
        print("[err] 未生成任何文件，不提交，等待下次运行。")
        return
    notes = summarize(items)
    if not notes:
        print("[warn] DeepSeek 未返回有效内容，使用占位（保留标题）")
        notes = [{"title": it["title"], "direction": "技巧攻略", "pain": "", "angle": "",
                  "keywords": [], "review": ""} for it in items]
    # AI 可能筛掉不相关条目：只要还有至少 MIN_ITEMS 条就照常发布（质量优先）
    if len(notes) < MIN_ITEMS:
        print(f"[warn] AI 筛选后仅 {len(notes)} 条（少于 {MIN_ITEMS} 条），本次跳过生成，等下次运行")
        print("[warn] 这说明今天适合的软件/工具类内容确实太少。")
        return
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
    # 按方向配额挑出最终条目（3-10 条）
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
