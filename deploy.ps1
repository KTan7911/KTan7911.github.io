# ============================================================
#  KTcove 每日生活科技日报 · 一行命令部署（GCM 认证版）
#  运行：cd D:\DS_Harnees\MyWeb 然后  .\deploy.ps1
#  流程：生成日报 -> 检查产物 -> git提交 -> git push（GCM 自动认证）
#  说明：无需任何令牌！首次推送会弹出浏览器授权窗口，点授权后自动记住。
# ============================================================
$ErrorActionPreference = "Stop"
Set-Location "D:\DS_Harnees\MyWeb"

Write-Host ""
Write-Host "========== 1/4 运行日报生成器 ==========" -ForegroundColor Cyan
python scripts\generate_daily.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "生成失败，脚本已停止。请把上方报错原文发我，我先帮你修。" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========== 2/4 检查生成产物 ==========" -ForegroundColor Cyan
$today = Get-Date -Format "yyyy-MM-dd"
$ok = $true
foreach ($f in @("daily\$today.html", "daily\index.html", "daily\data.json", "index.html")) {
    if (-not (Test-Path $f)) { Write-Host "缺少文件: $f" -ForegroundColor Red; $ok = $false }
    else { Write-Host "OK $f" -ForegroundColor Green }
}
if (-not $ok) { exit 1 }

Write-Host ""
Write-Host "========== 3/4 提交并推送 ==========" -ForegroundColor Cyan
git add -A
$staged = git diff --cached --name-only
if ($staged) {
    git commit -m "每日生活科技日报 自动部署 $today"
} else {
    Write-Host "没有新文件需要提交（内容已是最新）"
}

Write-Host ""
Write-Host "同步远程（Actions 自动提交可能让本地落后，先拉取合并）..." -ForegroundColor Cyan
git pull --rebase origin main -X ours 2>&1 | Out-Host

Write-Host ""
Write-Host "正在推送（GCM 认证：首次会弹出浏览器授权窗口，请点击授权）..." -ForegroundColor Yellow
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "推送失败。若为认证问题，请执行：" -ForegroundColor Red
    Write-Host "  git credential-manager github login" -ForegroundColor Yellow
    Write-Host "  （会再次弹出浏览器授权，完成后重新运行 .\deploy.ps1）" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "========== 4/4 完成！剩下两步在浏览器操作 ==========" -ForegroundColor Green
Write-Host "  1) 加 Secrets：GitHub 仓库 -> Settings -> Secrets and variables -> Actions"
Write-Host "     添加 3 个：CIMI_APP_ID / CIMI_APP_SECRET / DEEPSEEK_API_KEY（值从 ~/.openclaw/openclaw.json 复制）"
Write-Host "  2) 手动触发：仓库 -> Actions -> Daily Hot News -> Run workflow，等 1-3 分钟变绿"
Write-Host ""
Write-Host "  验证网址："
Write-Host "    今日日报: https://www.ktcove.com/daily/$today.html"
Write-Host "    搜索归档: https://www.ktcove.com/daily/"
Write-Host "    首页板块: https://www.ktcove.com/"
Write-Host ""
Write-Host "完成后每天 17:40（北京时间）全自动，无需任何操作，也无需再管令牌。" -ForegroundColor Yellow
