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
git init
git add .
git commit -m "我的个人网站"
git branch -M main
git remote add origin https://github.com/你的用户名/你的用户名.github.io.git
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
| CNAME Record | `www` | `你的用户名.github.io.` | Automatic |

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
2. **Custom domain** 填入 `www.你的域名.com`（或 `你的域名.com`）
3. 点击 **Save**，等待 GitHub 校验通过
4. 勾选 **Enforce HTTPS**（证书自动签发，可能需等待几分钟到几小时）

### 3. 完成

浏览器访问 `https://www.你的域名.com`，网站上线 🎉

## 常用域名注册商参考

- **Namecheap**（本教程采用）：支持支付宝，.com 首年约 $10.9，续费约 $13.9，老牌靠谱
- **Porkbun**：支持支付宝，.com 续费约 $12，界面友好
- **阿里云 / 腾讯云**：支付宝/微信支付方便，.com 首年促销约 55~85 元，需身份证实名认证（1~2 天审核），续费约 85 元/年
- **Cloudflare Registrar**：成本价约 $10.4/年，续费不涨价，但**不支持支付宝**，需外币信用卡或虚拟卡
- 便宜后缀（.top/.xyz/.site 等）首年可能很低，但**续费贵**，购买前务必查看续费价格
