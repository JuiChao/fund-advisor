# 基金定投智能分析平台 (Fund Advisor Quantitative Terminal)

基于现代资产组合理论 (MPT) 与蒙特卡洛随机漫步模拟的指数基金量化定投分析工具，面向纳斯达克100与标普500 QDII基金的量化评测与配置决策。

[![Live Web Terminal](https://img.shields.io/badge/Live_Terminal-858000.xyz-0969da.svg?style=flat-square&logo=google-chrome)](https://858000.xyz/)
[![Website Status](https://img.shields.io/badge/Status-Online_24%2F7-brightgreen.svg?style=flat-square&logo=cloudflare)](https://858000.xyz/)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776ab.svg?style=flat-square&logo=python)](https://www.python.org/)
[![Cloudflare Pages](https://img.shields.io/badge/Platform-Cloudflare_Pages-f38020.svg?style=flat-square&logo=cloudflarepages)](https://858000.xyz/)
[![Data Pipeline](https://img.shields.io/badge/Data_Pipeline-Daily_Automated-success.svg?style=flat-square&logo=githubactions)](https://858000.xyz/)

---

> 🌐 **Official Quantitative Web Terminal**: [https://858000.xyz](https://858000.xyz/)  
> **生产级 Web 终端现已在线稳定运行，无需配置本地环境，直接在浏览器中体验 QDII 基金量化分析与蒙特卡洛定投模拟。**

---

## 旗舰核心功能与在线直达 (Flagship Modules)

- 📈 [QDII 标杆基金量化透视表 (Ranking Table)](https://858000.xyz/#ranking) — 全市场 QDII 基金多因子综合评分矩阵：按费率 (35%)、跟踪误差 (20%)、规模 (15%)、超额收益 (15%)、晨星评级 (10%) 和申购费率 (5%) 科学加权排位。
- 🛡️ [全市场 QDII 限购穿透雷达 (Quota Warning Radar)](https://858000.xyz/#quota-warning) — 穿透监控外汇额度紧缩、暂停大额申购及恢复申购状态，防范定投断流，提供同指数可买平替选项。
- 🎲 [蒙特卡洛 5,000 次随机漫步定投模拟器 (Simulator)](https://858000.xyz/#simulator) — 基于几何布朗运动 (GBM)，推演 1~30 年投资周期的五分位数概率收益分布（95% 乐观、75% 良好、50% 中位、25% 谨慎、5% 保守），支持多资产自选组合权重回测。
- 📊 [Markowitz 现代资产组合理论有效前沿 (MPT Portfolio)](https://858000.xyz/#portfolio) — 均值-方差优化计算，提供 6 种量化定投配置范式（无约束最优、实际可买、最大收益、风险平衡、稳健保守、无限制最优）及黑天鹅极端行情压力测试。
- 📚 [QDII 指数基金量化投研百科 (Research Articles)](https://858000.xyz/articles/) — 全景收录 18 篇万字级深度投研长文，涵盖宽基指数、金融工程、外汇限额穿透与行为金融学实操：
  - 📖 [纳斯达克100指数投资完全指南 (Nasdaq 100 Guide)](https://858000.xyz/articles/nasdaq-100-investment-guide)
  - 📖 [标普500指数投资完全指南 (S&P 500 Guide)](https://858000.xyz/articles/sp500-investment-guide)
  - 📖 [QDII 基金限购穿透与外汇额度套利防范 (Quota Restrictions)](https://858000.xyz/articles/penetrating-qdii-purchase-quota-restrictions)
  - 📖 [蒙特卡洛模拟在基金定投中的金融工程实现 (Monte Carlo Financial Engineering)](https://858000.xyz/articles/monte-carlo-simulation-financial-engineering)
  - 📖 [现代资产组合理论 (MPT) 在定投中的应用 (MPT Portfolio Optimization)](https://858000.xyz/articles/mpt-modern-portfolio-theory-in-dca)
- 📋 [内容审校与事实核查方针 (Editorial & Fact-Checking Policy)](https://858000.xyz/editorial-policy) — 遵循金融与财富 (YMYL) 事实核查标准，透明公开数据清洗管线、参数校准与客观分析规范。

---

## 技术架构

```
GitHub Actions (每日定时任务)
  ├── Python Pipeline (天天基金网/东方财富数据同步与清洗) → 更新 funds.json
  └── Python Simulator (NumPy 5,000 次蒙特卡洛预计算) → 更新 simulations.json (156 组基准)
       ↓ Git Push 触发
Cloudflare Pages 全球边缘托管 (自动部署)
  ├── 纯原生静态层: HTML5 / CSS3 Tokens / Vanilla ES6+ / Chart.js CDN (零构建依赖)
  ├── 边缘函数 (Pages Functions): /api/portfolio (毫秒级查表与线性缩放，TTFB < 1ms)
  └── 生产终端入口: https://858000.xyz
```

- **前端架构**: 纯原生 HTML/CSS/JS + Chart.js CDN，无打包构建负担，加载迅速
- **科学计算**: GitHub Actions 预计算（Python / NumPy），前端查表与 Web Worker 异步计算双轨制
- **边缘接口**: Cloudflare Pages Functions（轻量查表与线性缩放）
- **数据自动化**: GitHub Actions 每日凌晨自动更新全市场公募基金净值与限购公告

---

## 本地开发

```bash
# 1. 安装科学计算依赖
pip install -r requirements.txt

# 2. 生成预计算数据
python scraper/simulate.py

# 3. 启动本地静态服务器
python -m http.server 8080 -d public
# 浏览器访问 http://localhost:8080

# 4. 本地测试 Pages Functions (需要 wrangler)
npx wrangler pages dev public --port 8788
```

---

## 自动化测试

```bash
# 运行基线单元测试 (94 项量化算法与数据校验)
python -m unittest discover tests

# 运行合规性测试 (AdSense, 爬虫与 YMYL 规范)
python -m unittest discover tests_compliance

# 运行 4 级端到端测试套件 (309 项全场景与边界校验)
python tests_e2e/run_all_e2e.py
```

---

## 生产部署

1. 代码推送至 GitHub 仓库 `master` 分支
2. Cloudflare Dashboard → Pages → 连接 GitHub 仓库
3. 构建配置: Framework preset=`None`, Output directory=`public`
4. GitHub Actions 每日自动同步更新数据并触发自动部署

---

## 投研指南与合规规范

- 🌐 [官方量化终端 (Live Web Terminal)](https://858000.xyz/)
- 📖 [关于平台与研究方法 (About Fund Advisor)](https://858000.xyz/about)
- 📋 [事实核查与审校方针 (Editorial & Fact-Checking Policy)](https://858000.xyz/editorial-policy)
- 🔒 [隐私保护政策 (Privacy Policy)](https://858000.xyz/privacy-policy)
- 📜 [用户服务协议 (Terms of Service)](https://858000.xyz/terms-of-service)

---

## 数据来源与免责声明

数据来源于公开公募基金信息与东方财富天天基金网。本平台所有量化模型、评分排序与模拟推演结论仅用于学术交流与量化工程展示，不构成任何投资建议或资产购买保证。市场有风险，投资需谨慎。
