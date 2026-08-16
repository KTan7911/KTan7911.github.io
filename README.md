# 个人网站

一个零依赖的现代简洁个人网站模板（HTML / CSS / JS），适合个人介绍、简历、作品集。

## 本地预览

直接用浏览器打开 `index.html` 即可，或者启动一个本地静态服务器：

```bash
# 方式一：Python
python -m http.server 8000

# 方式二：Node.js（需要 npx）
npx serve .
```

然后访问 http://localhost:8000

## 自定义修改

打开 `index.html`，把以下内容换成你自己的：

| 位置 | 修改内容 |
|---|---|
| `<title>` 和 hero 区域 | 你的名字、介绍 |
| `#about` | 关于我的介绍 |
| `#skills` | 技能卡片 |
| `#projects` | 项目作品（含链接） |
| `#contact` | 邮箱、GitHub、微信 |

## 部署到 GitHub Pages（免费，无需服务器）

### 1. 创建 GitHub 仓库

1. 注册/登录 [GitHub](https://github.com)
2. 点击右上角 **+ → New repository**
3. 仓库名填 `你的用户名.github.io`（例如 `zhangsan.github.io`）
4. 选择 **Public**，创建仓库

### 2. 上传代码

在本目录执行（需要先安装 [Git](https://git-scm.com/downloads)）：

```bash
git push -u origin main
```

### 3. 开启 Pages

1. 在 GitHub 仓库页面进入 **Settings → Pages**
2. Source 选择 **Deploy from a branch**，Branch 选 `main`，目录选 `/ (root)`
3. 保存后等 1~2 分钟，访问 `https://你的用户名.github.io` 即可看到网站

## 在 Namecheap 购买域名（约 $10~11 ≈ 70~80 元，支持支付宝）

### 1. 注册/登录 Namecheap

1. 打开 [namecheap.com](https://www.namecheap.com)，点击右上角 **Sign Up / Login**
2. 用邮箱注册（或用 Google 账号登录），完成邮箱验证
3. 账户信息（Address）用拼音填真实地址即可，手机号填 `+86` 开头的国内号码

### 2. 搜索并购买域名

1. 首页搜索框输入你想要的域名（例如 `zhangsan`），点 **Search**
2. 在结果列表选 `.com`（首年约 $10.9，续费约 $13.9），点 **Add to cart**
   - 小心勾选框！结算页会默认勾选 **WhoisGuard**（隐私保护）和 **自动续费**，建议保留 WhoisGuard（防信息泄露，部分后缀含在价格里），自动续费可自行决定
3. 购物车确认后点 **Checkout**

### 3. 用支付宝付款

1. 付款方式选 **Alipay（支付宝）**
2. 填写账单信息（Billing Address 用拼音填国内地址）
3. 确认金额后提交订单，页面会跳转出**支付宝二维码**
4. 用手机支付宝扫码付款，付款成功后域名即时生效（通常 1~10 分钟）

### 4. 确认域名到手

1. 登录 Namecheap 后台，左侧 **Domain List** 能看到你的域名 ✅
2. 状态为 **Active** 即注册成功
3. 点域名进入 **Manage**，可以设置域名转发等（绑定 GitHub Pages 时用「Advanced DNS」）

---

## 绑定自己的域名（花几十块买的域名）

> 前提：域名已注册成功，且托管平台是 GitHub Pages 这类**国外服务**——**不需要 ICP 备案**。

### 1. 在 Namecheap 添加 DNS 记录

进入 Namecheap 后台 **Domain List → 点域名 → Advanced DNS**，在 **Host Records** 区域添加：

| Type | Host | Value | TTL |
|---|---|---|---|
| A Record | `@` | `185.199.108.153` | Automatic |
| A Record | `@` | `185.199.109.153` | Automatic |
| A Record | `@` | `185.199.110.153` | Automatic |
| A Record | `@` | `185.199.111.153` | Automatic |
| CNAME Record | `www` | `KTan7911.github.io.` | Automatic |

> 注意：
> - Namecheap 的 `@` 填 **`@`**（或留空，代表根域名）
> - CNAME 的 Value 末尾**一定要带点**：`你的用户名.github.io.`
> - 如果有默认的 `www` 记录，先删掉再添加新的

| 类型 | 主机记录 | 值 |
|---|---|---|
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `你的用户名.github.io` |

### 2. 在 GitHub 配置自定义域名

1. 进入仓库 **Settings → Pages**
2. **Custom domain** 填入 `www.ktcove.com`（或 `ktcove.com`）
3. 点击 **Save**，等待 GitHub 校验通过
4. 勾选 **Enforce HTTPS**（证书自动签发，可能需等待几分钟到几小时）

### 3. 完成

浏览器访问 `https://www.ktcove.com`，网站上线 🎉

## 常用域名注册商参考

- **Namecheap**（本教程采用）：支持支付宝，.com 首年约 $10.9，续费约 $13.9，老牌靠谱
- **Porkbun**：支持支付宝，.com 续费约 $12，界面友好
- **阿里云 / 腾讯云**：支付宝/微信支付方便，.com 首年促销约 55~85 元，需身份证实名认证（1~2 天审核），续费约 85 元/年
- **Cloudflare Registrar**：成本价约 $10.4/年，续费不涨价，但**不支持支付宝**，需外币信用卡或虚拟卡
- 便宜后缀（.top/.xyz/.site 等）首年可能很低，但**续费贵**，购买前务必查看续费价格

---

# 📝 发布新文章指南（SEO 版）

每次发布新文章，按下面 4 步走，搜索引擎会自动收录。

## 第 1 步：复制文章模板

1. 复制 `article-localsend.html`，重命名为新文章（如 `article-xxx.html`）
2. 修改以下**必须改**的部分：

| 位置 | 改成什么 |
|---|---|
| `<title>` | 新文章标题（含关键词，如「XXX：开源神器深度评测」） |
| `<meta name="description">` | 一句话描述文章，含 2~3 个关键词 |
| `<meta name="keywords">` | 3~5 个相关关键词，逗号分隔 |
| `<link rel="canonical">` | `https://www.ktcove.com/article-xxx.html` |
| `og:url` / `twitter:*` | 同上，改成新页面地址 |
| `JSON-LD` 里的 `headline` / `description` / `datePublished` | 新文章的标题、描述、日期 |
| `<article>` 正文 | 替换成新内容 |

> ⚠️ **JSON-LD 的 `datePublished`** 记得改成当天的日期（格式 `YYYY-MM-DD`）。

## 第 2 步：首页加卡片

在 `index.html` 的「宝藏推荐」区块（`id="treasures"`）里，复制一张现有卡片：

```html
<a class="card project-card" href="article-xxx.html">
  <div class="card-icon">📡</div>
  <h3>文章标题</h3>
  <p>一句话简介（含关键词）</p>
  <span class="card-link">阅读全文 →</span>
</a>
```

## 第 3 步：更新 sitemap.xml

在 `sitemap.xml` 的 `<urlset>` 里加一条（`lastmod` 填当天）：

```xml
<url>
  <loc>https://www.ktcove.com/article-xxx.html</loc>
  <lastmod>2026-08-16</lastmod>
  <changefreq>monthly</changefreq>
  <priority>0.8</priority>
</url>
```

## 第 4 步：推送上线

```powershell
cd D:\DS_Harnees\MyWeb
git add -A
git commit -m "新增文章：文章标题"
# 推送需要 GitHub 令牌（Contents: Read and write 权限，用完即删）
git push https://KTan7911:<令牌>@github.com/KTan7911/KTan7911.github.io.git main
```

推送后等 1~2 分钟，访问 `https://www.ktcove.com/article-xxx.html` 验证。

## 发布后（可选，加速收录）

- **Google**：[Search Console](https://search.google.com/search-console) → 顶部 URL 检查 → 输入新页面地址 → 「请求编制索引」
- **百度**：百度平台 → 普通收录 → 链接提交（有配额时手动提交；无配额则等蜘蛛自然抓取）
- 在公众号文章里附上网站链接，也能加速收录

## 日常维护备忘

| 事项 | 说明 |
|---|---|
| 域名续费 | Dynadot 每年续费一次，建议开启自动续费 |
| 令牌安全 | GitHub 令牌用完即删，别长期保留 |
| 账号安全 | Dynadot / GitHub 建议开启双重验证（2FA） |
| 桌面敏感截图 | 含账号密码的截图建议删除或加密保存 |
