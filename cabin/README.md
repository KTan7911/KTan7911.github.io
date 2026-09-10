# 小屋 🏠

> 一个只属于两个人的私密情绪空间

- 访问地址：https://www.ktcove.com/cabin/
- 需求文档：[`docs/需求文档.md`](docs/需求文档.md)

## 目录结构

```
cabin/
├── index.html              主页面
├── css/style.css           样式（奶油白 + 珊瑚粉）
├── js/
│   ├── config.js           ⚙️ 配置（Supabase 地址、心情、标签）
│   ├── api.js              Supabase 轻量客户端（纯 fetch，无 CDN）
│   └── app.js              主逻辑（登录、聊天流、输入、树洞）
└── docs/
    ├── 需求文档.md
    └── 建表SQL.sql         ⚙️ 数据库初始化脚本
```

## 部署

跟随现有流程，在 `D:\DS_Harnees\MyWeb` 下运行：

```powershell
.\deploy.ps1
```

或手动：

```powershell
cd D:\DS_Harnees\MyWeb
git add cabin
git commit -m "小屋 v1"
git pull --rebase origin main -X ours
git push origin main
```

## 首次配置（已完成）

- [x] 建 Supabase 项目（ap-southeast-1 新加坡）
- [x] 关闭邮箱验证（Confirm email）
- [x] 在 `js/config.js` 填入 URL 和 anon key
- [ ] 执行 `docs/建表SQL.sql` 建表
- [ ] 注册两个账号（你 + 她）

## 当前状态

**一期**
- [x] 登录 / 注册
- [x] 聊天流界面
- [x] 文字输入
- [x] 语音录入（存条目，音频上传待二期）
- [x] 心情 + 标签
- [x] 不可修改 / 不可删除（数据库层强制）
- [x] 树洞页
- [ ] 云端同步（已就绪，待建表后生效）
- [ ] 小屋 AI 对话（二期）

## 隐私说明

- 数据存 Supabase，**RLS 强制隔离**：只能读到自己那一行
- 数据库**不存在** UPDATE / DELETE 策略 → 记录写下去就改不了、删不掉
- `js/config.js` 里的 key 是**公开安全**的（anon / publishable），安全性由 RLS 保证
- ⚠️ **service_role key 永远不要写进这个目录**
