# 基金定投智能分析平台

基于蒙特卡洛模拟的指数基金定投分析工具，支持纳斯达克100和标普500基金的量化分析。

## 功能

- **基金排名** — 按费率、跟踪误差、规模、业绩等多维度评分排序
- **蒙特卡洛模拟** — 可调参数（预算/年限），预计算+线性缩放，毫秒级响应
- **六种定投策略** — 无约束最优、实际可买、最大收益、风险平衡、稳健保守、无限制最优
- **数据自动更新** — GitHub Actions 每日抓取天天基金网，自动部署

## 技术架构

```
GitHub Actions (每日)
  ├── Python scraper → 更新 funds.json
  └── Python simulator → 更新 simulations.json (156组预计算)
       ↓ push
Cloudflare Pages (自动部署)
  ├── 静态文件: HTML/CSS/JS + JSON
  └── Pages Functions: /api/portfolio (查表+缩放, <1ms)
```

- 前端: 纯 HTML/CSS/JS + Chart.js（CDN）
- 计算: GitHub Actions 预计算（Python/NumPy），前端查表
- API: Cloudflare Pages Functions（轻量查表+缩放）
- 部署: Cloudflare Pages（静态托管 + 边缘函数）
- 数据: GitHub Actions 每日自动抓取天天基金网

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 生成预计算数据
python scraper/simulate.py

# 启动本地服务
python -m http.server 8080 -d public
# 访问 http://localhost:8080

# 本地测试 Pages Functions (需要 wrangler)
npx wrangler pages dev public --port 8788
```

## 部署

1. Push 到 GitHub 仓库
2. Cloudflare Dashboard → Pages → 连接 GitHub 仓库
3. 构建设置: Framework preset=None, Output directory=`public`
4. GitHub Actions 自动每日更新数据并重新部署

## 数据来源

东方财富天天基金网，数据仅供参考，不构成投资建议。
