/**
 * 主应用逻辑 - 调用 API 获取预计算结果
 */
const App = (() => {
    let FUND_DATA = [];
    let ALGO_CONFIG = null;
    let LIMIT_CHANGES_DATA = null;
    let chartPool = {};
    let pfCharts = {};
    const API_BASE = '';

    // ===== 主题管理 (Dark / Light Theme) =====
    function getPreferredTheme() {
        const saved = localStorage.getItem('fa_theme');
        if (saved) return saved;
        return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('fa_theme', theme);
        const iconEl = document.querySelector('#theme-toggle .theme-icon');
        if (iconEl) iconEl.textContent = theme === 'dark' ? '☀️' : '🌙';

        if (theme === 'dark') {
            Chart.defaults.color = '#cbd5e1';
            Chart.defaults.borderColor = 'rgba(129, 140, 248, 0.15)';
        } else {
            Chart.defaults.color = '#475569';
            Chart.defaults.borderColor = 'rgba(99, 102, 241, 0.08)';
        }

        if (chartPool.frontier && chartPool.frontier.options?.scales) {
            const isD = theme === 'dark';
            const gc = isD ? 'rgba(129, 140, 248, 0.12)' : 'rgba(99, 102, 241, 0.08)';
            const tc = isD ? '#94a3b8' : '#64748b';
            const sc = chartPool.frontier.options.scales;
            if (sc.x) {
                sc.x.grid.color = gc;
                sc.x.ticks.color = tc;
                if (sc.x.title) sc.x.title.color = tc;
            }
            if (sc.y) {
                sc.y.grid.color = gc;
                sc.y.ticks.color = tc;
                if (sc.y.title) sc.y.title.color = tc;
            }
            if (chartPool.frontier.options.plugins?.legend?.labels) {
                chartPool.frontier.options.plugins.legend.labels.color = tc;
            }
        }

        if (chartPool.stress && chartPool.stress.options?.scales) {
            const isD = theme === 'dark';
            const gc = isD ? 'rgba(129, 140, 248, 0.12)' : 'rgba(99, 102, 241, 0.08)';
            const tc = isD ? '#94a3b8' : '#64748b';
            const sc = chartPool.stress.options.scales;
            if (sc.x) sc.x.ticks.color = tc;
            if (sc.y) {
                sc.y.grid.color = gc;
                sc.y.ticks.color = tc;
                if (sc.y.title) sc.y.title.color = tc;
            }
            if (chartPool.stress.options.plugins?.legend?.labels) {
                chartPool.stress.options.plugins.legend.labels.color = tc;
            }
        }

        const pfLegendColor = theme === 'dark' ? '#f1f5f9' : '#0f172a';
        Object.values(chartPool).forEach(ch => {
            if (ch && typeof ch.update === 'function') ch.update();
        });
        Object.values(pfCharts).forEach(ch => {
            if (ch && typeof ch.update === 'function') {
                if (ch.options?.plugins?.legend?.labels) {
                    ch.options.plugins.legend.labels.color = pfLegendColor;
                }
                ch.update();
            }
        });
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        showToast(next === 'dark' ? '🌙 已切换至暗夜科技模式' : '☀️ 已切换至清新明亮模式', 'info');
    }

    function initTheme() {
        applyTheme(getPreferredTheme());
        const themeBtn = document.getElementById('theme-toggle');
        if (themeBtn) {
            themeBtn.onclick = toggleTheme;
        }
    }

    // ===== 优雅悬浮 Toast 提示系统 =====
    function showToast(msg, type = 'info') {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            document.body.appendChild(container);
        }
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        const icon = type === 'success' ? '✅' : '💡';
        toast.innerHTML = `<span>${icon}</span><span>${msg}</span>`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.remove();
        }, 3200);
    }

    // ===== 滑块快捷胶囊 (Quick Preset Chips) =====
    function initPresetChips() {
        document.querySelectorAll('.preset-chips').forEach(chipsWrap => {
            const targetId = chipsWrap.dataset.for;
            const slider = document.getElementById(targetId);
            if (!slider) return;

            chipsWrap.querySelectorAll('.preset-chip').forEach(chip => {
                chip.addEventListener('click', () => {
                    chipsWrap.querySelectorAll('.preset-chip').forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');
                    const val = chip.dataset.val;
                    slider.value = val;
                    slider.dispatchEvent(new Event('input', { bubbles: true }));

                    // 若在定投方案页，点击预算或年限芯片自动触发方案重算
                    if (targetId.startsWith('pf-')) {
                        computePortfolio();
                    }
                });
            });

            // 监听滑块拖动同步芯片的高亮状态
            slider.addEventListener('input', () => {
                const currentVal = slider.value;
                chipsWrap.querySelectorAll('.preset-chip').forEach(c => {
                    if (c.dataset.val === currentVal) {
                        c.classList.add('active');
                    } else {
                        c.classList.remove('active');
                    }
                });
            });
        });
    }

    // ===== 跨页面联动调度器：将任意组合一键装载至模拟器并运行 =====
    async function loadFundsIntoSimulator(fundWeightMap, autoRun = true, strategyName = '') {
        const codes = Object.keys(fundWeightMap);
        if (!codes.length) return;

        // 1. 切换到模拟器页面
        window.location.hash = '#simulator';
        switchPage('simulator');

        // 2. 初始化/填充多选
        initMultiSelect();
        msSelected.clear();
        codes.forEach(c => msSelected.add(c));

        // 更新多选框UI显示
        const textEl = document.getElementById('sim-sel-text');
        if (textEl) {
            textEl.innerHTML = `<span class="ms-count">${codes.length}</span>已选择 ${codes.length} 只基金`;
            textEl.style.color = 'var(--txt)';
        }

        // 3. 渲染权重滑块并填入精确权重
        renderWeightSliders();
        const listEl = document.getElementById('sim-weights-list');
        if (listEl) {
            const rows = listEl.querySelectorAll('.sim-weight-row');
            rows.forEach(row => {
                const code = row.dataset.code;
                if (fundWeightMap[code] !== undefined) {
                    const pct = Math.round(fundWeightMap[code] * 100);
                    const inp = row.querySelector('.sim-weight-input');
                    if (inp) inp.value = pct;
                }
            });
            updateWeightDisplays();
        }

        // 4. 自动运行模拟推演
        if (autoRun) {
            await runSimulation();
        }

        // 5. 提示用户
        showToast(`已成功载入【${strategyName || '目标配置'}】，并完成全周期推演！`, 'success');
    }

    // ===== 模拟器顶部快捷方案预设 =====
    function initSimQuickPresets() {
        document.querySelectorAll('.btn-sim-preset').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.btn-sim-preset').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const preset = btn.dataset.preset;
                const isBuyableFund = f => {
                    const s = f.limit_status || '';
                    return !s.includes('暂停') && !s.includes('未开通');
                };

                const nqFunds = FUND_DATA.filter(f => f.index_type === '纳斯达克100');
                const spFunds = FUND_DATA.filter(f => f.index_type === '标普500');

                // 优先可买且评分最高
                const topNq = [...nqFunds].sort((a,b) => (isBuyableFund(b) ? 1 : 0) - (isBuyableFund(a) ? 1 : 0) || (b.score||0) - (a.score||0))[0];
                const topSp = [...spFunds].sort((a,b) => (isBuyableFund(b) ? 1 : 0) - (isBuyableFund(a) ? 1 : 0) || (b.score||0) - (a.score||0))[0];

                const fee = f => (f.mgmt_fee||0) + (f.custody_fee||0) + (f.sales_fee||0);
                const minFeeNq = [...nqFunds].sort((a,b) => fee(a) - fee(b))[0];
                const minFeeSp = [...spFunds].sort((a,b) => fee(a) - fee(b))[0];

                if (!topNq || !topSp) return;

                if (preset === 'risk_parity') {
                    loadFundsIntoSimulator({ [topNq.code]: 0.38, [topSp.code]: 0.62 }, true, '量化风险平价 (38:62)');
                } else if (preset === 'max_sharpe') {
                    loadFundsIntoSimulator({ [topNq.code]: 0.30, [topSp.code]: 0.70 }, true, '最大夏普最优');
                } else if (preset === 'balanced') {
                    loadFundsIntoSimulator({ [topNq.code]: 0.50, [topSp.code]: 0.50 }, true, '传统平衡型 (50:50)');
                } else if (preset === 'aggressive') {
                    loadFundsIntoSimulator({ [topNq.code]: 0.70, [topSp.code]: 0.30 }, true, '科技进取型 (70:30)');
                } else if (preset === 'low_fee') {
                    loadFundsIntoSimulator({ [minFeeNq.code]: 0.50, [minFeeSp.code]: 0.50 }, true, '同类极低费率组合');
                }
            });
        });
    }

    // ===== 默认主题 Chart.js 配置 =====
    Chart.defaults.color = '#475569';
    Chart.defaults.borderColor = 'rgba(99, 102, 241, 0.08)';
    Chart.defaults.font.family = "'Inter',-apple-system,'PingFang SC','Microsoft YaHei',sans-serif";
    Chart.defaults.font.size = 11;

    // ===== 工具函数 =====
    function fmt(v) { return v == null ? '-' : (v * 100).toFixed(2) + '%'; }
    function money(v) {
        if (v == null) return '-';
        if (v >= 10000) return '¥' + (v / 10000).toFixed(1) + '万';
        return '¥' + v.toLocaleString('zh-CN');
    }
    function stars(n) { return (!n || n === 0) ? '-' : '★'.repeat(n); }
    function pill(s) {
        if (!s) return '<span class="pill pb">未知</span>';
        if (s.includes('未开通')) return '<span class="pill" style="background:rgba(148,163,184,0.12);color:var(--txt3);border:1px solid rgba(148,163,184,0.3)">' + s + '</span>';
        if (s.includes('暂停')) return '<span class="pill pr">' + s + '</span>';
        if (s.includes('限')) return '<span class="pill py">' + s + '</span>';
        return '<span class="pill pg">' + s + '</span>';
    }
    function feeC(f) {
        if (f <= 0.006) return 'color:#34d399;font-weight:700';
        if (f <= 0.007) return 'color:#34d399';
        if (f <= 0.01) return '';
        return 'color:#f87171';
    }
    const fmtMoney = v => '¥' + Number(v).toLocaleString('zh-CN');

    function getStandardFundShortName(item) {
        if (!item) return '';
        const name = item.name || '';
        let company = '';
        const companies = ['华泰柏瑞', '景顺长城', '汇添富', '易方达', '广发', '华夏', '博时', '南方', '大成', '嘉实', '国泰', '天弘', '建信', '摩根', '招商', '万家', '华安', '宝盈'];
        for (const c of companies) {
            if (name.startsWith(c)) {
                company = (c === '景顺长城') ? '景顺' : ((c === '华泰柏瑞') ? '华泰' : c);
                break;
            }
        }
        if (!company) {
            company = name.slice(0, 2);
        }

        let idx = '纳指';
        if (name.includes('纳斯达克科技') || name.includes('纳科')) {
            idx = '纳科';
        } else if (name.includes('等权重') || name.includes('等权')) {
            idx = '标普等权';
        } else if (name.includes('标普') || item.index_type === '标普500') {
            idx = '标普';
        } else if (name.includes('纳斯达克') || name.includes('纳指') || item.index_type === '纳斯达克100') {
            idx = '纳指';
        }

        let cls = item.share_class || '';
        if (!cls) {
            const m = name.match(/([A-Za-z])(?:类|份额)?\s*$/) || name.match(/([A-Za-z])/);
            if (m) cls = m[1].toUpperCase();
        }

        return `${company}${idx}${cls}`;
    }

    function formatSummaryHtml(summary) {
        if (!summary) return '<span style="color:var(--txt3)">—</span>';
        const parts = summary.split(/[；;\n]+/).map(s => s.trim()).filter(Boolean);
        if (parts.length === 0) return '<span style="color:var(--txt3)">—</span>';
        return parts.map(part => {
            const formatted = part.replace(/^(代销|直销)[:：]/, '<strong class="q-sum-channel">$1:</strong>');
            return `<div class="q-summary-line">${formatted}</div>`;
        }).join('');
    }

    function syncSliderBadges() {
        const sm = document.getElementById('sim-m');
        const sy = document.getElementById('sim-y');
        const pm = document.getElementById('pf-m');
        const py = document.getElementById('pf-y');
        if (sm) {
            const v = fmtMoney(sm.value);
            const el = document.getElementById('sim-mv');
            if (el) el.textContent = v;
            const b = document.getElementById('sim-mv-badge');
            if (b) b.textContent = v + ' / 月';
        }
        if (sy) {
            const el = document.getElementById('sim-yv');
            if (el) el.textContent = sy.value + '年';
            const b = document.getElementById('sim-yv-badge');
            if (b) b.textContent = sy.value + ' 年';
        }
        if (pm) {
            const v = fmtMoney(pm.value);
            const el = document.getElementById('pf-mv');
            if (el) el.textContent = v;
            const b = document.getElementById('pf-mv-badge');
            if (b) b.textContent = v + ' / 月';
        }
        if (py) {
            const el = document.getElementById('pf-yv');
            if (el) el.textContent = py.value + '年';
            const b = document.getElementById('pf-yv-badge');
            if (b) b.textContent = py.value + ' 年';
        }
    }

    // ===== 页面切换与 TDK 动态更新 =====
    const PAGE_TDK = {
        'home': { title: '基金定投智能分析 | Fund Advisor', desc: '基于蒙特卡洛模拟的指数基金定投智能分析平台。自动抓取天天基金数据，提供基金排名、收益率模拟及最佳资产配置方案。' },
        'ranking': { title: '纳斯达克100与标普500指数基金排名 - 费率与收益对比 | Fund Advisor', desc: '全网最新纳斯达克100和标普500指数基金排名。对比各基金的管理费、托管费、限购状态及历史年化收益，助您找到最低费率的优质基金。' },
        'simulator': { title: '基金蒙特卡洛模拟器 - 预测未来收益走势 | Fund Advisor', desc: '采用高级蒙特卡洛随机漫步模型，模拟指数基金在未来不同市场环境下的收益率分布。输入本金与定投金额，预见未来财富可能。' },
        'portfolio': { title: '最优基金定投方案 - QDII限购环境下的资产配置 | Fund Advisor', desc: '根据各基金最新的单日申购限额（QDII额度限制），通过动态规划算法计算出理论最优与实际可买的完美定投组合方案，最大化资金利用率。' },
        'guide': { title: '投资指南与指数科普 - 纳斯达克100与标普500定投策略 | Fund Advisor', desc: '深度解析指数基金定投策略、QDII限购避坑指南以及纳斯达克100与标普500的核心差异，助您建立科学的理财框架。' }
    };

    function updateTDK(page) {
        const tdk = PAGE_TDK[page] || PAGE_TDK['home'];
        document.title = tdk.title;
        const metaDesc = document.querySelector('meta[name="description"]');
        if (metaDesc) metaDesc.setAttribute('content', tdk.desc);
        const ogTitle = document.querySelector('meta[property="og:title"]');
        if (ogTitle) ogTitle.setAttribute('content', tdk.title);
        const ogDesc = document.querySelector('meta[property="og:description"]');
        if (ogDesc) ogDesc.setAttribute('content', tdk.desc);
        const twTitle = document.querySelector('meta[name="twitter:title"]');
        if (twTitle) twTitle.setAttribute('content', tdk.title);
        const twDesc = document.querySelector('meta[name="twitter:description"]');
        if (twDesc) twDesc.setAttribute('content', tdk.desc);
    }

    function switchPage(page) {
        let pName = page;
        let queryParams = {};
        if (page.includes('?')) {
            const parts = page.split('?');
            pName = parts[0];
            const sp = new URLSearchParams(parts[1]);
            sp.forEach((v, k) => queryParams[k] = v);
        }

        document.querySelectorAll('#nav-links a').forEach(x => {
            if (x.dataset.page === pName) x.classList.add('on');
            else x.classList.remove('on');
        });
        document.querySelectorAll('#mobile-bottom-bar a').forEach(x => {
            if (x.dataset.page === pName) x.classList.add('on');
            else x.classList.remove('on');
        });
        document.querySelectorAll('[id^="page-"]').forEach(p => p.style.display = 'none');
        const target = document.getElementById('page-' + pName);
        if (!target) return;
        target.style.display = '';
        target.classList.remove('fade-in');
        void target.offsetWidth;
        target.classList.add('fade-in');
        
        updateTDK(pName);
        
        if (pName === 'ranking') {
            if (queryParams.q) {
                const s = document.getElementById('rank-search');
                if (s) s.value = decodeURIComponent(queryParams.q);
            }
            renderRanking();
            renderQuotaBulletin();
            applyRankView(currentRankView);
            if (queryParams.section === 'quota') {
                setTimeout(() => {
                    const el = document.getElementById('quota-bulletin-section');
                    if (el) {
                        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        el.classList.add('highlight-glow');
                        setTimeout(() => el.classList.remove('highlight-glow'), 2200);
                    }
                }, 150);
            }
        }
        if (pName === 'simulator') {
            populateSimSelect();
            syncSliderBadges();
            if (queryParams.smart === '1' || queryParams.action === 'smart-dca') {
                setTimeout(() => {
                    const toggle = document.getElementById('sim-smart-toggle');
                    if (toggle && !toggle.checked) {
                        toggle.checked = true;
                        toggle.dispatchEvent(new Event('change'));
                    }
                    const sec = document.getElementById('sim-dynamic-section');
                    if (sec) {
                        sec.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        sec.classList.add('highlight-glow');
                        setTimeout(() => sec.classList.remove('highlight-glow'), 2200);
                    }
                }, 150);
            }
        }
        if (pName === 'portfolio') {
            computePortfolio();
            syncSliderBadges();
            if (queryParams.section) {
                setTimeout(() => {
                    const secMap = {
                        'frontier': 'quant-frontier-card',
                        'stress': 'stress-test-section',
                        'downside': 'quant-matrix-card',
                    };
                    const secId = secMap[queryParams.section] || queryParams.section;
                    const el = document.getElementById(secId);
                    if (el) {
                        if (secId === 'quant-frontier-card') {
                            const body = document.getElementById('quant-frontier-body');
                            const arrow = document.getElementById('quant-frontier-arrow');
                            if (body && body.style.display === 'none') {
                                body.style.display = 'block';
                                if (arrow) arrow.style.transform = 'rotate(180deg)';
                            }
                        }
                        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        el.classList.add('highlight-glow');
                        setTimeout(() => el.classList.remove('highlight-glow'), 2200);
                    }
                }, 150);
            }
        }
    }

    function initNav() {
        window.addEventListener('hashchange', () => {
            const hash = window.location.hash.replace('#', '') || 'home';
            switchPage(hash);
            closeMobileNav();
        });

        // 移动端汉堡菜单
        const navToggle = document.querySelector('.nav-toggle');
        const navLinks = document.querySelector('.navbar .links');
        if (navToggle && navLinks) {
            navToggle.addEventListener('click', (e) => {
                e.stopPropagation();
                const isOpen = navLinks.classList.toggle('show');
                navToggle.classList.toggle('open', isOpen);
                navToggle.setAttribute('aria-expanded', isOpen);
            });
            // 点击页面外部区域自动收起抽屉
            document.addEventListener('click', (e) => {
                if (!e.target.closest('.navbar')) {
                    closeMobileNav();
                }
            });
        }

        // 首次加载
        const initHash = window.location.hash.replace('#', '') || 'home';
        switchPage(initHash);
    }

    function closeMobileNav() {
        const navToggle = document.querySelector('.nav-toggle');
        const navLinks = document.querySelector('.navbar .links');
        if (navLinks?.classList.contains('show')) {
            navLinks.classList.remove('show');
            navToggle?.classList.remove('open');
            navToggle?.setAttribute('aria-expanded', 'false');
        }
    }

    // ===== 概览页 =====
    function renderHome() {
        const nq = FUND_DATA.filter(f => f.index_type === '纳斯达克100');
        const sp = FUND_DATA.filter(f => f.index_type === '标普500');
        const availAgency = FUND_DATA.filter(f => !(f.limit_status || '').includes('暂停') && !(f.limit_status || '').includes('未开通'));
        const availDirect = FUND_DATA.filter(f => f.direct_limit_status && !f.direct_limit_status.includes('暂停') && !f.direct_limit_status.includes('未开通'));
        const minFee = Math.min(...FUND_DATA.map(f => (f.mgmt_fee || 0) + (f.custody_fee || 0) + (f.sales_fee || 0)));

        const homeStatsEl = document.getElementById('home-stats');
        if (homeStatsEl) {
            homeStatsEl.innerHTML = `
                <div class="stat"><div class="lb">收录份额</div><div class="vl">${FUND_DATA.length}</div><div class="sub">纳指 ${nq.length} · 标普 ${sp.length} (涵盖A/C/D/E/F/I)</div></div>
                <div class="stat"><div class="lb">可购份额</div><div class="vl">${availAgency.length}</div><div class="sub">代销可买 (直销可买${availDirect.length})</div></div>
                <div class="stat"><div class="lb">最低综合年费</div><div class="vl">${(minFee * 100).toFixed(2)}%</div><div class="sub">管理+托管+销售费</div></div>
                <div class="stat"><div class="lb">数据更新</div><div class="vl" style="font-size:1rem">${FUND_DATA[0]?.updated_at?.split('T')[0] || '-'}</div><div class="sub">每日自动抓取</div></div>
            `;
        }

        // 同步顶部实时量化行情指标条 (Hero Quant Ticker)
        const tkPool = document.getElementById('tk-pool-count');
        if (tkPool) tkPool.textContent = `${FUND_DATA.length} 只`;
        const tkAvail = document.getElementById('tk-avail-count');
        if (tkAvail) tkAvail.textContent = `${availAgency.length} 代销 / ${availDirect.length} 直销`;
        const tkMinFee = document.getElementById('tk-min-fee');
        if (tkMinFee) tkMinFee.textContent = `${(minFee * 100).toFixed(2)}%`;

        // 费率分布图
        function feeChart(id, list) {
            const data = list.map(f => ({
                code: f.code,
                name: f.name,
                fee: ((f.mgmt_fee || 0) + (f.custody_fee || 0) + (f.sales_fee || 0)) * 100,
                status: f.limit_status || ''
            })).sort((a, b) => a.fee - b.fee);
            if (chartPool[id]) chartPool[id].destroy();
            chartPool[id] = new Chart(document.getElementById(id), {
                type: 'bar',
                data: {
                    labels: data.map(d => d.code),
                    datasets: [{
                        label: '综合费率',
                        data: data.map(d => d.fee),
                        backgroundColor: data.map(d => d.fee <= 0.7 ? '#34d399' : d.fee <= 1.0 ? '#6366f1' : '#f87171'),
                        borderRadius: 4,
                        borderSkipped: false,
                        maxBarThickness: 18,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                title: items => `${data[items[0].dataIndex].code} ${data[items[0].dataIndex].name}`,
                                label: ctx => `综合费率: ${ctx.parsed.y.toFixed(2)}%`,
                                afterLabel: ctx => data[ctx.dataIndex].status ? `状态: ${data[ctx.dataIndex].status}` : ''
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: {
                                font: { size: 9 },
                                maxRotation: 50,
                                minRotation: 30,
                                autoSkip: true
                            }
                        },
                        y: { beginAtZero: true, ticks: { callback: v => v + '%' }, grid: { color: 'rgba(99, 102, 241, 0.08)' } }
                    }
                }
            });
        }
        feeChart('ch-nq', nq);
        feeChart('ch-sp', sp);
        loadStrategiesPreview();
    }

    async function loadStrategiesPreview() {
        try {
            const dynParams = await getDynamicParams();
            let strategies;
            try {
                strategies = await apiGet('/api/portfolio?years=20&budget=2000');
            } catch (apiErr) {
                console.warn("API failed in preview, using local calculations:", apiErr);
                strategies = localCalculatePortfolio(20, 2000);
            }

            // 预先算一下预览组合模拟数据，如果API没有返回的话
            const simPromises = [];
            strategies.forEach(s => {
                ['ideal', 'practical'].forEach(vk => {
                    const v = s[vk];
                    if (!v.simulation) {
                        const allocs = v.allocations || [];
                        const simFunds = allocs.map(a => FUND_DATA.find(f => f.code === a.code)).filter(Boolean);
                        const simWeights = allocs.map(a => a.actual_weight || a.weight || 0);
                        simPromises.push(
                            simulateViaWorker(simFunds, simWeights, 20, 2000, dynParams).then(result => {
                                v.simulation = result;
                            })
                        );
                    }
                });
            });
            await Promise.all(simPromises);

            let html = `
            <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(240px, 1fr));gap:1rem;margin-bottom:1.5rem">
                ${strategies.map(s => {
                    const ra = s.practical?.risk_analysis || s.ideal?.risk_analysis || {};
                    const nqW = Math.round((ra.nq_weight != null ? ra.nq_weight : s.nq_pct || 0) * 100);
                    const spW = Math.round((ra.sp_weight != null ? ra.sp_weight : (1 - s.nq_pct) || 0) * 100);
                    const sim = s.practical?.simulation || s.ideal?.simulation || {};
                    const isQuant = s.category === 'quant';
                    return `
                    <div class="card" style="margin-bottom:0;padding:1.25rem;display:flex;flex-direction:column;border:${isQuant ? '1px solid rgba(99,102,241,0.3)' : '1px solid var(--border)'};background:${isQuant ? 'linear-gradient(180deg, var(--surface) 0%, var(--surface2) 100%)' : 'var(--surface)'}">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
                            <span style="font-weight:750;font-size:0.95rem;color:var(--txt)">${s.icon || ''} ${s.name}</span>
                            <span class="tag" style="${isQuant ? 'background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;' : 'background:var(--surface2);color:var(--txt3);'}font-size:0.68rem;margin:0">${isQuant ? '💎 量化' : '经典'}</span>
                        </div>
                        <div style="font-size:0.75rem;color:var(--txt2);margin-bottom:0.75rem;flex:1;line-height:1.5">${s.description || ''}</div>
                        <div style="background:var(--surface2);border-radius:8px;padding:0.6rem 0.8rem;margin-bottom:0.85rem;display:flex;justify-content:space-between;align-items:center">
                            <div>
                                <div style="font-size:0.68rem;color:var(--txt3)">资金配比 (纳:标)</div>
                                <div style="font-weight:700;font-size:0.85rem;color:var(--txt)">${nqW}% : ${spW}%</div>
                            </div>
                            <div style="text-align:right">
                                <div style="font-size:0.68rem;color:var(--txt3)">20年终值中位</div>
                                <div style="font-weight:800;font-size:0.85rem;color:var(--ok)">${sim.medianFinal ? money(sim.medianFinal) : '-'}</div>
                            </div>
                        </div>
                        <div style="display:flex;gap:0.5rem">
                            <a href="#portfolio" class="btn-jump-strat btn-jump-strat-home" style="flex:1;text-align:center;padding:0.45rem 0.5rem;font-size:0.75rem;text-decoration:none" data-strategy="${s.key}" data-category="${s.category || 'traditional'}">查看配置 ▸</a>
                            <button class="btn-simulate-action btn-sim-from-home" data-strategy="${s.key}" style="flex:1;padding:0.45rem 0.5rem;font-size:0.75rem;justify-content:center" title="带入模拟器推演">推演 🚀</button>
                        </div>
                    </div>
                    `;
                }).join('')}
            </div>

            <details style="margin-top:0.5rem">
                <summary style="font-size:0.82rem;font-weight:600;color:var(--txt2);cursor:pointer;padding:0.5rem 0;user-select:none">📋 查看全方案数据对比表 (包含理论最优与实际可买)</summary>
                <div class="table-wrap" style="margin-top:0.5rem">
                    <table>
                        <thead>
                            <tr><th>策略</th><th>类型</th><th>风格描述</th><th>子方案</th><th>预期年化</th><th>20年终值</th></tr>
                        </thead>
                        <tbody>
                            ${strategies.map(s => {
                                return ['ideal', 'practical'].map(vk => {
                                    const v = s[vk];
                                    const sim = v?.simulation || {};
                                    const label = vk === 'ideal' ? '理论最优' : '实际可买';
                                    const typeBadge = s.category === 'quant'
                                        ? `<span class="pill" style="background:rgba(99,102,241,0.15);color:#818cf8;font-weight:600">💎 ${s.tag || '量化'}</span>`
                                        : `<span class="pill" style="background:var(--surface2);color:var(--txt3)">${s.tag || '经典'}</span>`;
                                    return `<tr>
                                        <td style="font-weight:600;color:var(--accent2)">${s.icon || ''} ${s.name}</td>
                                        <td>${typeBadge}</td>
                                        <td style="font-size:.8125rem;color:var(--txt2)">${s.description || ''}</td>
                                        <td><span class="pill ${vk === 'ideal' ? 'pb' : 'pg'}">${label}</span></td>
                                        <td style="color:var(--ok);font-weight:600">${sim.annualReturn ? sim.annualReturn + '%' : '-'}</td>
                                        <td style="font-weight:600">${sim.medianFinal ? money(sim.medianFinal) : '-'}</td>
                                    </tr>`;
                                }).join('');
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            </details>
            `;
            document.getElementById('home-strategies').innerHTML = html;
            document.getElementById('home-strategies').classList.remove('ld');

            // 绑定首页卡片“推演 🚀”按钮
            document.querySelectorAll('.btn-sim-from-home').forEach(btn => {
                btn.onclick = (e) => {
                    e.preventDefault();
                    const stratKey = btn.dataset.strategy;
                    const strat = strategies.find(s => s.key === stratKey);
                    if (!strat) return;
                    const allocs = strat.practical?.allocations || strat.ideal?.allocations || [];
                    if (!allocs.length) return;
                    const weightMap = {};
                    allocs.forEach(a => {
                        weightMap[a.code] = a.actual_weight != null ? a.actual_weight : a.weight;
                    });
                    loadFundsIntoSimulator(weightMap, true, strat.name);
                };
            });

            // 绑定首页卡片“查看配置 ▸”直达按钮
            document.querySelectorAll('.btn-jump-strat-home').forEach(btn => {
                btn.onclick = () => {
                    const stratKey = btn.dataset.strategy;
                    const stratCat = btn.dataset.category;
                    window.location.hash = '#portfolio';
                    setTimeout(() => {
                        const targetFilterBtn = document.querySelector(`#pf-category-filter .seg-btn[data-category="${stratCat}"]`) ||
                                                document.querySelector('#pf-category-filter .seg-btn[data-category="ALL"]');
                        if (targetFilterBtn) targetFilterBtn.click();
                        const targetCard = document.getElementById(`pf-card-${stratKey}`);
                        if (targetCard) {
                            targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            targetCard.classList.add('highlight-pulse');
                            setTimeout(() => targetCard.classList.remove('highlight-pulse'), 3000);
                        }
                    }, 100);
                };
            });
        } catch (e) {
            document.getElementById('home-strategies').innerHTML = '<p style="color:var(--err)">加载失败: ' + e.message + '</p>';
            document.getElementById('home-strategies').classList.remove('ld');
        }
    }

    // ===== API =====
    async function apiGet(url) {
        const resp = await fetch(API_BASE + url);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp.json();
    }

    // ===== 份额徽章助手 =====
    function shareBadge(sclass) {
        let raw = (sclass || 'A').toString().trim().toUpperCase();
        raw = raw.replace(/类.*$/, '');
        const c = raw.charAt(0) || 'A';
        const map = {
            'A': 'badge-a',
            'C': 'badge-c',
            'D': 'badge-d',
            'E': 'badge-e',
            'F': 'badge-f',
            'I': 'badge-i'
        };
        const cls = map[c] || 'badge-other';
        return `<span class="badge-share ${cls}">${c}类</span>`;
    }

    // ===== 排名页 =====
    let rankData = [];
    let rankSortDir = {};
    const rankCols = [
        { key: 'rank', label: '# · 代码', render: r => {
            let rankBadge;
            if (r.rank === 1) rankBadge = '<span class="tbl-rank-badge rank-gold" title="综合排名第1">🥇 1</span>';
            else if (r.rank === 2) rankBadge = '<span class="tbl-rank-badge rank-silver" title="综合排名第2">🥈 2</span>';
            else if (r.rank === 3) rankBadge = '<span class="tbl-rank-badge rank-bronze" title="综合排名第3">🥉 3</span>';
            else rankBadge = `<span class="tbl-rank-badge">#${r.rank}</span>`;

            return `<div class="tbl-rank-code-cell"><div class="trc-badge-wrap" title="点击展开详情看板">${rankBadge}</div><div class="trc-code-wrap"><span class="code-mono trc-code-btn" data-code="${r.code}" title="点击复制基金代码">${r.code}</span></div><div class="trc-actions-wrap"><button type="button" class="trc-copy-btn" data-code="${r.code}" title="复制基金代码">📋</button><a href="/fund/${r.code}" target="_blank" class="code-ext-link" title="在新标签页打开独立专页">↗</a></div></div>`;
        } },
        { key: 'name', label: '名称', render: r => {
            const curType = document.querySelector('#rank-filter .seg-btn.on')?.dataset.value || '纳斯达克100';
            const idxBadge = curType === 'ALL'
                ? `<span class="badge-idx ${r.index_type === '纳斯达克100' ? 'badge-nq' : 'badge-sp'}">${r.index_type === '纳斯达克100' ? '纳指' : '标普'}</span>`
                : '';
            return `<div class="tbl-name-cell">${idxBadge}${shareBadge(r.share_class)}<a href="/fund/${r.code}" class="fund-name-link" data-code="${r.code}" title="点击展开多因子详情看板">${r.name}</a><span class="tbl-row-expand-arrow" title="点击展开/收起详情">▾</span></div>`;
        } },
        { key: 'fee', label: '综合费率', render: r => {
            const mgmt = r.mgmt_fee || 0;
            const cust = r.custody_fee || 0;
            const sales = r.sales_fee || 0;
            const total = mgmt + cust + sales;
            const tip = `管理费${(mgmt*100).toFixed(2)}% + 托管费${(cust*100).toFixed(2)}%` + (sales > 0 ? ` + 销售服务费${(sales*100).toFixed(2)}%` : '');
            const isLow = total <= 0.007;
            return `<div class="tbl-fee-cell"><span class="fee-tooltip-trigger" title="${tip}" style="${feeC(total)}">${fmt(total)}</span>${isLow ? '<span class="badge-low-fee" title="处于市场极低费率梯队">极低</span>' : ''}</div>`;
        } },
        { key: 'purchase_fee', label: '申购费', render: r => {
            const pf = r.purchase_fee || 0;
            return pf > 0 ? `${(pf*100).toFixed(2)}%` : '<span style="color:var(--ok);font-weight:600">0.00%</span>';
        } },
        { key: 'tracking_error', label: '跟踪误差 / IR', render: r => {
            const teStr = fmt(r.tracking_error);
            const ir = r.information_ratio;
            const td = r.tracking_difference;
            let sub = '';
            if (ir != null) {
                const irColor = ir >= 1.0 ? 'var(--ok)' : (ir < 0 ? 'var(--down)' : 'var(--txt3)');
                sub += `<span title="信息比率 (IR): 承担单位跟踪风险下的超额收益" style="color:${irColor};margin-right:6px">IR <strong>${ir.toFixed(2)}</strong></span>`;
            }
            if (td != null) {
                const tdColor = td >= 0 ? 'var(--up)' : 'var(--down)';
                sub += `<span title="跟踪偏离度 (TD/1年): 相对基准的超额或偏离" style="color:${tdColor};font-weight:600">TD ${(td>=0?'+':'')+(td*100).toFixed(1)}%</span>`;
            }
            return `<div class="tbl-te-cell"><span class="tbl-te-val">${teStr}</span>${sub ? '<div class="tbl-te-sub">' + sub + '</div>' : ''}</div>`;
        } },
        { key: 'scale', label: '规模', render: r => r.scale ? r.scale.toFixed(1) + '亿' : '-' },
        { key: 'return_3yr', label: '近3年', render: r => { 
            const v = r.return_3yr; 
            if (v != null) return '<span style="color:var(--ok)">' + fmt(v) + '</span>';
            if (r.return_since != null && r.inception_date) {
                const inc = new Date(r.inception_date);
                const now = new Date();
                const dm = (now.getFullYear() - inc.getFullYear())*12 + now.getMonth() - inc.getMonth();
                const y = Math.floor(dm/12);
                const m = dm % 12;
                const sp = y > 0 ? (m > 0 ? `${y}年${m}个月` : `${y}年`) : `${m}个月`;
                return `<span style="color:var(--ok)">${fmt(r.return_since)} <span style="font-size:0.8em;color:var(--desc)">(${sp})*</span></span>`;
            }
            return '-'; 
        } },
        { key: 'morningstar', label: '晨星', render: r => { const n = r.morningstar; return n > 0 ? '<span style="color:var(--warn)">' + '★'.repeat(n) + '</span>' : '-'; } },
        { key: 'limit_status', label: '限购(代/直)', render: r => {
            const agencyPill = pill(r.limit_status);
            const directPill = r.direct_limit_status ? pill(r.direct_limit_status) : '<span class="tbl-limit-na">—</span>';
            let shareHtml = '';
            if (r.quota_sharing === 'SHARED') {
                shareHtml = `<span class="badge-shared" title="${r.quota_shared_desc || '多类份额合并计算单日限额'}">🔗 共享额度</span>`;
            } else if (r.quota_sharing === 'INDEPENDENT') {
                shareHtml = `<span class="badge-indep" title="${r.quota_shared_desc || '各份额独立计算限额'}">独立额度</span>`;
            } else {
                shareHtml = '<span class="tbl-limit-na">—</span>';
            }
            return `<div class="tbl-limit-cell"><div class="tbl-limit-row"><span class="tbl-limit-lbl">代销</span>${agencyPill}</div><div class="tbl-limit-row"><span class="tbl-limit-lbl">直销</span>${directPill}</div><div class="tbl-limit-row tbl-limit-share">${shareHtml}</div></div>`;
        } },
        { key: 'score', label: '评分', render: r => `<div class="tbl-score-cell"><strong class="tbl-score-val">${r.score}</strong></div>` },
    ];

    function scoreFund(f, medianTE) {
        const cfg = ALGO_CONFIG;
        const d = cfg.defaults;
        const s = cfg.scoring;
        const fee = (f.mgmt_fee || 0) + (f.custody_fee || 0) + (f.sales_fee || 0);
        const te = f.tracking_error || d.tracking_error_for_scoring;
        const scale = f.scale || d.scale;
        const y3 = f.return_3yr;
        const ms = f.morningstar || d.morningstar;
        const pur = f.purchase_fee || d.purchase_fee;
        const feeS = Math.max(0, Math.min(100, 100 - (fee - s.fee.optimal) / s.fee.range * s.fee.penalty));

        // 跟踪误差评分：同类相对法 or 绝对法兜底
        const teCfg = s.tracking_error;
        let teS;
        if (teCfg.method === 'peer_relative' && medianTE != null) {
            teS = Math.max(0, Math.min(100, 100 - (te - medianTE) / teCfg.spread * teCfg.penalty));
        } else {
            const opt = teCfg.fallback_optimal ?? teCfg.optimal ?? 0.008;
            const rng = teCfg.fallback_range ?? teCfg.range ?? 0.022;
            const pen = teCfg.fallback_penalty ?? teCfg.penalty ?? 67;
            teS = Math.max(0, Math.min(100, 100 - (te - opt) / rng * pen));
        }

        const sc = s.scale;
        const scS = (scale >= sc.optimal_min && scale <= sc.optimal_max) ? sc.optimal_score : (scale < sc.small_threshold ? sc.small_score : (scale > sc.large_threshold ? sc.large_score : sc.mid_score));
        const y3S = y3 != null ? Math.max(0, Math.min(100, (y3 - s.return_3yr.baseline) / s.return_3yr.range * 100)) : s.return_3yr.null_default;
        const msS = ms > 0 ? ms * s.morningstar.multiplier : s.morningstar.null_default;
        const purS = Math.max(0, Math.min(100, 100 - (pur - s.purchase_fee.optimal) / s.purchase_fee.range * s.purchase_fee.penalty));
        const w = s.weights;
        return +(feeS * w.fee + teS * w.tracking_error + scS * w.scale + y3S * w.return_3yr + msS * w.morningstar + purS * w.purchase_fee).toFixed(1);
    }

    function calcMedianTE(funds) {
        const tes = funds.map(f => f.tracking_error).filter(v => v != null && v > 0).sort((a, b) => a - b);
        if (!tes.length) return null;
        const mid = Math.floor(tes.length / 2);
        return tes.length % 2 ? tes[mid] : (tes[mid - 1] + tes[mid]) / 2;
    }

    function updateRankControlHub(allTypeFunds, filteredCount, totalPoolCount, type, classFilter, quotaFilter, kw) {
        // 更新第一层指数徽章
        const nqCount = FUND_DATA.filter(f => f.index_type === '纳斯达克100').length;
        const spCount = FUND_DATA.filter(f => f.index_type === '标普500').length;
        const allCount = FUND_DATA.length;
        const bNq = document.getElementById('badge-count-nq');
        const bSp = document.getElementById('badge-count-sp');
        const bAll = document.getElementById('badge-count-all');
        if (bNq) bNq.textContent = nqCount;
        if (bSp) bSp.textContent = spCount;
        if (bAll) bAll.textContent = allCount;

        // 更新第二层份额类别数量 (基于当前所选指数池 allTypeFunds)
        const setEl = (id, text) => {
            const el = document.getElementById(id);
            if (el) el.textContent = text;
        };

        setEl('count-class-all', allTypeFunds.length);
        setEl('count-class-a', allTypeFunds.filter(f => f.share_class === 'A').length);
        setEl('count-class-c', allTypeFunds.filter(f => f.share_class === 'C').length);
        setEl('count-class-other', allTypeFunds.filter(f => f.share_class !== 'A' && f.share_class !== 'C').length);

        // 更新渠道状态数量
        setEl('count-quota-all', allTypeFunds.length);
        setEl('count-quota-buyable', allTypeFunds.filter(f => !(f.limit_status || '').includes('暂停') && !(f.limit_status || '').includes('未开通')).length);
        setEl('count-quota-direct', allTypeFunds.filter(f => {
            const d = f.direct_limit_status || f.limit_status || '';
            return !d.includes('暂停') && !d.includes('未开通');
        }).length);
        setEl('count-quota-paused', allTypeFunds.filter(f => (f.limit_status || '').includes('暂停') || (f.limit_status || '').includes('未开通')).length);

        // 更新底部状态摘要
        const summaryEl = document.getElementById('rank-filter-summary');
        if (summaryEl) {
            let summaryText = `当前展示 <strong style="color:var(--accent2);font-weight:700">${filteredCount}</strong> / ${allTypeFunds.length} 只标的`;
            if (kw) {
                summaryText += ` <span style="font-size:0.75rem;color:var(--txt3)">(包含 "${kw}")</span>`;
            }
            summaryEl.innerHTML = summaryText;
        }

        // 恢复默认按钮显隐
        const resetBtn = document.getElementById('rank-filter-reset');
        if (resetBtn) {
            const isNonDefault = classFilter !== 'ALL' || quotaFilter !== 'ALL' || kw !== '';
            resetBtn.style.display = isNonDefault ? 'inline-flex' : 'none';
        }

        // 清空搜索按钮显隐与输入框快捷键徽章联动
        const clearBtn = document.getElementById('rank-search-clear');
        if (clearBtn) {
            clearBtn.style.display = kw !== '' ? 'flex' : 'none';
        }
        const sBox = document.querySelector('.rank-search-box');
        if (sBox) {
            if (kw !== '') sBox.classList.add('has-val');
            else sBox.classList.remove('has-val');
        }
    }

    function resetRankFilters() {
        document.querySelectorAll('#class-filter .seg-btn, #class-filter .filter-pill').forEach(btn => {
            if (btn.dataset.value === 'ALL') btn.classList.add('on');
            else btn.classList.remove('on');
        });
        document.querySelectorAll('#quota-filter .seg-btn, #quota-filter .filter-pill').forEach(btn => {
            if (btn.dataset.value === 'ALL') btn.classList.add('on');
            else btn.classList.remove('on');
        });
        const searchInput = document.getElementById('rank-search');
        if (searchInput) searchInput.value = '';
        renderRanking();
    }

    function renderRanking() {
        const type = document.querySelector('#rank-filter .seg-btn.on')?.dataset.value || '纳斯达克100';
        const classFilter = document.querySelector('#class-filter .seg-btn.on, #class-filter .filter-pill.on')?.dataset.value || 'ALL';
        const quotaFilter = document.querySelector('#quota-filter .seg-btn.on, #quota-filter .filter-pill.on')?.dataset.value || 'ALL';
        const kw = (document.getElementById('rank-search')?.value || '').trim().toLowerCase();

        const nqFunds = FUND_DATA.filter(f => f.index_type === '纳斯达克100');
        const spFunds = FUND_DATA.filter(f => f.index_type === '标普500');
        const medianTE_nq = calcMedianTE(nqFunds);
        const medianTE_sp = calcMedianTE(spFunds);

        const allTypeFunds = type === 'ALL' ? FUND_DATA : FUND_DATA.filter(f => f.index_type === type);

        const filtered = allTypeFunds.filter(f => {
            if (classFilter === 'A' && f.share_class !== 'A') return false;
            if (classFilter === 'C' && f.share_class !== 'C') return false;
            if (classFilter === 'OTHER' && (f.share_class === 'A' || f.share_class === 'C')) return false;

            if (quotaFilter === 'BUYABLE') {
                const ls = f.limit_status || '';
                if (ls.includes('暂停') || ls.includes('未开通')) return false;
            }
            if (quotaFilter === 'DIRECT') {
                const dls = f.direct_limit_status || f.limit_status || '';
                if (dls.includes('暂停') || dls.includes('未开通')) return false;
            }
            if (quotaFilter === 'PAUSED') {
                const ls = f.limit_status || '';
                if (!ls.includes('暂停') && !ls.includes('未开通')) return false;
            }

            if (kw) {
                const matchCode = (f.code || '').toLowerCase().includes(kw);
                const matchName = (f.name || '').toLowerCase().includes(kw);
                const matchMgr = (f.manager || '').toLowerCase().includes(kw);
                const matchFam = (f.family_name || '').toLowerCase().includes(kw);
                if (!matchCode && !matchName && !matchMgr && !matchFam) return false;
            }
            return true;
        });

        rankData = filtered.map(f => {
            const medTE = f.index_type === '标普500' ? medianTE_sp : medianTE_nq;
            return { ...f, score: scoreFund(f, medTE) };
        })
        .sort((a, b) => b.score - a.score)
        .map((f, i) => ({ ...f, rank: i + 1 }));

        updateRankControlHub(allTypeFunds, rankData.length, FUND_DATA.length, type, classFilter, quotaFilter, kw);

        const thead = document.querySelector('#rank-table thead');
        if (thead) {
            thead.innerHTML = '<tr>' + rankCols.map(c => `<th data-key="${c.key}">${c.label} <span class="arr">⇅</span></th>`).join('') + '</tr>';
        }

        function draw() {
            const tbody = document.querySelector('#rank-table tbody');
            if (!tbody) return;

            if (rankData.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="${rankCols.length}" style="text-align:center;padding:3rem 1rem;color:var(--txt3)">
                            <div style="font-size:2rem;margin-bottom:0.5rem">🔍</div>
                            <div style="font-size:0.95rem;font-weight:600;color:var(--txt2);margin-bottom:0.35rem">未找到符合条件的基金标的</div>
                            <div style="font-size:0.8rem;color:var(--txt3);margin-bottom:1rem">请尝试调整份额类别、渠道状态或搜索关键词</div>
                            <button type="button" class="btn-empty-reset" style="padding:0.4rem 1rem;font-size:0.8rem;border-radius:6px;background:var(--accent-g);color:#fff;border:none;cursor:pointer;font-weight:600">🔄 恢复默认筛选</button>
                        </td>
                    </tr>
                `;
                const emptyReset = tbody.querySelector('.btn-empty-reset');
                if (emptyReset) emptyReset.onclick = resetRankFilters;
                return;
            }

            tbody.innerHTML = rankData.map((r, i) => {
                const isPaused = ((r.limit_status || '').includes('暂停') || (r.limit_status || '').includes('未开通')) &&
                                 ((r.direct_limit_status || '').includes('暂停') || (r.direct_limit_status || '').includes('未开通') || !r.direct_limit_status);
                let rowClasses = [];
                if (r.rank === 1) rowClasses.push('rank-row-gold');
                else if (r.rank === 2) rowClasses.push('rank-row-silver');
                else if (r.rank === 3) rowClasses.push('rank-row-bronze');
                else if (i < 3) rowClasses.push('hl');
                if (isPaused) rowClasses.push('wr');
                const clsAttr = rowClasses.length ? ' class="' + rowClasses.join(' ') + '"' : '';
                return '<tr' + clsAttr + ' data-code="' + r.code + '">' + rankCols.map(c => '<td>' + (c.render ? c.render(r) : (r[c.key] ?? '-')) + '</td>').join('') + '</tr>';
            }).join('');
        }

        if (thead) {
            thead.querySelectorAll('th').forEach(th => {
                th.addEventListener('click', () => {
                    const key = th.dataset.key;
                    const isFee = key === 'fee';
                    rankSortDir[key] = rankSortDir[key] === 'asc' ? 'desc' : 'asc';
                    const dir = rankSortDir[key] === 'desc' ? -1 : 1;
                    rankData.sort((a, b) => {
                        let va, vb;
                        if (isFee) {
                            va = (a.mgmt_fee || 0) + (a.custody_fee || 0) + (a.sales_fee || 0);
                            vb = (b.mgmt_fee || 0) + (b.custody_fee || 0) + (b.sales_fee || 0);
                        } else {
                            va = a[key];
                            vb = b[key];
                        }
                        if (va == null) va = Infinity; if (vb == null) vb = Infinity;
                        return dir * (typeof va === 'string' ? va.localeCompare(vb) : va - vb);
                    });
                    thead.querySelectorAll('th').forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
                    th.classList.add(rankSortDir[key] === 'desc' ? 'sort-desc' : 'sort-asc');
                    draw();
                    renderRankCards(rankData);
                });
            });
        }
        draw();
        renderRankCards(rankData);
    }

    // ===== 双视图控制与智能卡片流渲染 (桌面与移动端自适应) =====
    function checkIsMobile() {
        return window.innerWidth <= 768;
    }
    let savedRankView = null;
    try { savedRankView = localStorage.getItem('fa_rank_view'); } catch (e) {}
    let currentRankView = savedRankView || (checkIsMobile() ? 'card' : 'table');

    function applyRankView(viewMode) {
        currentRankView = viewMode;
        try { localStorage.setItem('fa_rank_view', viewMode); } catch (e) {}

        const toggle = document.getElementById('rank-view-toggle');
        const cardList = document.getElementById('rank-card-list');
        const tableWrap = document.getElementById('rank-table-wrap') || document.querySelector('#page-ranking .table-wrap');
        const swipeHint = document.getElementById('rank-swipe-hint') || document.querySelector('#page-ranking .mobile-swipe-hint');
        const statusMsg = document.getElementById('rank-view-status-msg');
        const isMobile = checkIsMobile();

        if (toggle) {
            toggle.querySelectorAll('.view-btn').forEach(btn => {
                if (btn.dataset.view === viewMode) btn.classList.add('on');
                else btn.classList.remove('on');
            });
        }

        if (viewMode === 'card') {
            if (cardList) {
                cardList.classList.remove('view-hidden', 'mobile-hidden');
                cardList.style.display = '';
            }
            if (tableWrap) {
                tableWrap.classList.add('view-hidden', 'mobile-hidden');
                tableWrap.style.display = 'none';
            }
            if (swipeHint) {
                swipeHint.classList.add('view-hidden', 'mobile-hidden');
                swipeHint.style.display = 'none';
            }
            if (statusMsg) {
                statusMsg.textContent = isMobile
                    ? '当前为智能卡片模式 · 模块化聚焦核心指标，点击卡片展开详情'
                    : '当前为投研卡片网格 · 模块化呈现核心指标，点击任意卡片可展开深度看板';
            }
        } else {
            if (cardList) {
                cardList.classList.add('view-hidden', 'mobile-hidden');
                cardList.style.display = 'none';
            }
            if (tableWrap) {
                tableWrap.classList.remove('view-hidden', 'mobile-hidden');
                tableWrap.style.display = '';
            }
            if (swipeHint) {
                if (isMobile) {
                    swipeHint.classList.remove('view-hidden', 'mobile-hidden');
                    swipeHint.style.display = 'block';
                } else {
                    swipeHint.classList.add('view-hidden', 'mobile-hidden');
                    swipeHint.style.display = 'none';
                }
            }
            if (statusMsg) {
                statusMsg.textContent = isMobile
                    ? '当前为全景表格模式 · 左右滑动查看全量指标，支持表头点击排序'
                    : '当前为全景对比表格 · 支持点击表头多维排序，点击标的名称可展开抽屉看板';
            }
        }
    }

    // ===== 每日限购动态监控与风控公告看板渲染 (Quota Intelligence Bulletin) =====
    function renderQuotaBulletin() {
        const container = document.getElementById('quota-bulletin-container');
        if (!container) return;

        const data = LIMIT_CHANGES_DATA;
        const dateEl = document.getElementById('quota-alert-date');
        const msgEl = document.getElementById('quota-alert-msg');
        const dotEl = document.getElementById('quota-pulse-dot');
        const tickersEl = document.getElementById('quota-alert-tickers');
        const drawerEl = document.getElementById('quota-board-drawer');
        const toggleBtn = document.getElementById('btn-quota-toggle');
        const toggleTxt = document.getElementById('quota-toggle-text');

        if (!data || !data.history || !data.history.length) {
            if (dateEl) dateEl.textContent = new Date().toISOString().slice(0, 10);
            if (msgEl) msgEl.textContent = '全市场 60 只美股QDII额度今日平稳运行，无新增限购/收紧变动';
            if (dotEl) dotEl.className = 'quota-pulse-dot pulse-ok';
            return;
        }

        const todayStr = data.today_date || new Date().toISOString().slice(0, 10);
        if (dateEl) dateEl.textContent = todayStr;

        // 按照用户需求：同一只基金一周内若出现多次变更，仅保留最新一条变更记录（按基金代码去重）
        const seenCodes = new Set();
        const displayHistory = [];
        for (const h of (data.history || [])) {
            if (h.code && !seenCodes.has(h.code)) {
                seenCodes.add(h.code);
                displayHistory.push(h);
            }
        }

        const todayChanges = displayHistory.filter(h => h.date === todayStr);
        const hasToday = todayChanges.length > 0;

        if (dotEl) {
            dotEl.className = 'quota-pulse-dot ' + (hasToday ? 'pulse-alert' : 'pulse-info');
        }

        if (msgEl) {
            if (hasToday) {
                msgEl.innerHTML = `今日监测到 <strong>${todayChanges.length}</strong> 只标的申购额度变动，建议关注渠道差异与平替！`;
            } else {
                const latestDate = (displayHistory[0] && displayHistory[0].date) ? displayHistory[0].date : '';
                msgEl.innerHTML = `全市场额度今日平稳运行 · 最新收录 <strong>${latestDate}</strong> 官方限额公告，可展开看板查看渠道比对与平替`;
            }
        }

        // 渲染顶部快速变动胶囊 (最多3条)
        if (tickersEl) {
            const previewItems = (hasToday ? todayChanges : displayHistory).slice(0, 3);
            tickersEl.innerHTML = previewItems.map(item => {
                let badgeClass = 'chip-tightened';
                let icon = '🔴';
                if (item.change_type === 'RELAXED') {
                    badgeClass = 'chip-relaxed';
                    icon = '🟢';
                } else if (item.change_type === 'CHANNEL_DIV') {
                    badgeClass = 'chip-div';
                    icon = '🔵';
                }
                const shortName = getStandardFundShortName(item);
                const effDate = item.effective_date || item.date || '';
                const dateShort = effDate ? effDate.slice(5) : '';
                return `<span class="ticker-chip ${badgeClass}" title="${item.name} | ${item.summary || ''} | 生效日期: ${effDate}">${icon} ${dateShort}生效 ${item.code} ${shortName} · ${item.change_type_label || ''}</span>`;
            }).join('');
        }

        // 绑定折叠开关
        if (toggleBtn && !toggleBtn._bound) {
            toggleBtn._bound = true;
            toggleBtn.addEventListener('click', () => {
                const isHidden = drawerEl.style.display === 'none';
                drawerEl.style.display = isHidden ? 'block' : 'none';
                toggleBtn.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
                if (toggleTxt) toggleTxt.textContent = isHidden ? '收起限购变动看板' : '查看限购变动与平替全景';
                const arrow = toggleBtn.querySelector('.quota-toggle-arrow');
                if (arrow) arrow.textContent = isHidden ? '▴' : '▾';
                if (isHidden) {
                    drawerEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            });
        }

        // 绑定公告看板图片导出按钮 (先打开勾选选择弹窗)
        const exportBtn = document.getElementById('btn-quota-export-douyin');
        if (exportBtn && !exportBtn._bound) {
            exportBtn._bound = true;
            exportBtn.addEventListener('click', () => openQuotaExportSelectModal(exportBtn));
        }

        // 统计指标
        const qRecent = document.getElementById('qstat-recent');
        const qRelaxed = document.getElementById('qstat-relaxed');
        const qTightened = document.getElementById('qstat-tightened');
        const qStable = document.getElementById('qstat-stable');
        if (qRecent) qRecent.textContent = data.recent_7d_count || displayHistory.length;
        if (qRelaxed) qRelaxed.textContent = displayHistory.filter(h => h.change_type === 'RELAXED').length;
        if (qTightened) qTightened.textContent = displayHistory.filter(h => h.change_type === 'TIGHTENED').length;
        if (qStable) qStable.textContent = (data.total_monitored || 60) - (todayChanges.length);

        // 渲染全景表格 (#quota-table-tbody)
        const tbody = document.getElementById('quota-table-tbody');
        if (tbody) {
            tbody.innerHTML = displayHistory.map(item => {
                let typeBadge = '';
                if (item.change_type === 'RELAXED') {
                    typeBadge = `<span class="badge-qtype badge-relaxed">🟢 ${item.change_type_label}</span>`;
                } else if (item.change_type === 'TIGHTENED') {
                    typeBadge = `<span class="badge-qtype badge-tightened">🔴 ${item.change_type_label}</span>`;
                } else {
                    typeBadge = `<span class="badge-qtype badge-div">🔵 ${item.change_type_label}</span>`;
                }

                const idxBadge = `<span class="badge-idx ${item.index_type === '纳斯达克100' ? 'badge-nq' : 'badge-sp'}">${item.index_type === '纳斯达克100' ? '纳指' : '标普'}</span>`;
                const fundCell = `
                    <div class="q-fund-cell">
                        <div class="q-fund-meta">
                            <div class="q-fund-badges">${idxBadge}${shareBadge(item.share_class)}</div>
                            <div class="q-fund-code"><span class="code-mono">${item.code}</span><button type="button" class="btn-copy-code" data-code="${item.code}" title="复制基金代码">📋</button></div>
                        </div>
                        <div class="q-fund-name-wrap">
                            <a href="/fund/${item.code}" class="q-fund-name" target="_blank" title="${item.name}">${item.name}</a>
                        </div>
                    </div>
                `;

                const changeAndAnnCell = `
                    <div class="q-change-ann-cell">
                        <div class="q-channel-grid">
                            <span class="q-channel-tag tag-agency">代销</span>
                            <span class="q-diff-before">${item.agency.before_status}</span>
                            <span class="q-diff-arrow">➔</span>
                            <span class="q-diff-after ${item.agency.direction || ''}">${item.agency.after_status}</span>

                            <span class="q-channel-tag tag-direct">直销</span>
                            <span class="q-diff-before">${item.direct.before_status}</span>
                            <span class="q-diff-arrow">➔</span>
                            <span class="q-diff-after ${item.direct.direction || ''}">${item.direct.after_status}</span>
                        </div>
                        ${item.announcement_url ? `<a href="${item.announcement_url}" target="_blank" class="q-ann-link" title="点击查看基金公司官方公告原件详情">📄 官方公告 ↗</a>` : ''}
                    </div>
                `;

                const subsCell = item.substitutes && item.substitutes.length ? `
                    <div class="q-subs-wrap">
                        ${item.substitutes.map(s => `
                            <button type="button" class="btn-quota-sub" data-code="${s.code}" title="${s.name} | 综合费率 ${(s.total_fee*100).toFixed(2)}% | 代销${s.limit_status}">
                                <span class="q-sub-code">${s.code}</span>
                                <span class="q-sub-name">${getStandardFundShortName(s)}</span>
                                <span class="q-sub-limit">${s.limit_status}</span>
                            </button>
                        `).join('')}
                    </div>
                ` : `<span style="color:var(--txt3);font-size:0.75rem">—</span>`;

                const effDate = item.effective_date || item.date;
                const pubDate = item.announcement_pub_date || item.date;
                const isDiffDate = effDate && pubDate && effDate !== pubDate;
                const dateCellHtml = `
                    <div class="q-date-cell-wrap">
                        <span class="q-date-pill q-eff-pill" title="实际生效起始日期: ${effDate}">📅 生效: <strong>${effDate}</strong></span>
                        ${isDiffDate ? `<span class="q-pub-hint" title="公告发布送出日期: ${pubDate}">(${pubDate}发布)</span>` : ''}
                    </div>
                `;

                return `
                    <tr class="q-row-${(item.change_type || '').toLowerCase()}">
                        <td>${dateCellHtml}</td>
                        <td>${fundCell}</td>
                        <td>${typeBadge}</td>
                        <td>${changeAndAnnCell}</td>
                        <td>${subsCell}</td>
                    </tr>
                `;
            }).join('');
        }

        // 渲染移动端卡片列表 (#quota-card-list)
        const cardContainer = document.getElementById('quota-card-list');
        if (cardContainer) {
            cardContainer.innerHTML = displayHistory.map(item => {
                let typeBadge = '';
                if (item.change_type === 'RELAXED') {
                    typeBadge = `<span class="badge-qtype badge-relaxed">🟢 ${item.change_type_label}</span>`;
                } else if (item.change_type === 'TIGHTENED') {
                    typeBadge = `<span class="badge-qtype badge-tightened">🔴 ${item.change_type_label}</span>`;
                } else {
                    typeBadge = `<span class="badge-qtype badge-div">🔵 ${item.change_type_label}</span>`;
                }

                const idxBadge = `<span class="badge-idx ${item.index_type === '纳斯达克100' ? 'badge-nq' : 'badge-sp'}">${item.index_type === '纳斯达克100' ? '纳指' : '标普'}</span>`;

                const subsHtml = item.substitutes && item.substitutes.length ? `
                    <div class="qmc-subs">
                        <span class="qmc-subs-lbl">💡 智能平替标的：</span>
                        <div class="qmc-subs-chips">
                            ${item.substitutes.map(s => `
                                <button type="button" class="btn-quota-sub" data-code="${s.code}" title="${s.name}">
                                <span class="q-sub-code">${s.code}</span>
                                <span class="q-sub-name">${getStandardFundShortName(s)}</span>
                                <span class="q-sub-limit">${s.limit_status}</span>
                            </button>
                            `).join('')}
                        </div>
                    </div>
                ` : '';

                const effDate = item.effective_date || item.date;
                const pubDate = item.announcement_pub_date || item.date;
                const isDiffDate = effDate && pubDate && effDate !== pubDate;

                return `
                    <div class="quota-mobile-card q-card-${(item.change_type || '').toLowerCase()}">
                        <div class="qmc-header">
                            <div class="qmc-date-wrap">
                                <span class="q-date-pill q-eff-pill" title="实际生效起始日期: ${effDate}">📅 生效: <strong>${effDate}</strong></span>
                                ${isDiffDate ? `<span class="qmc-pub-hint" title="公告发布送出日期: ${pubDate}">(${pubDate}发布)</span>` : ''}
                            </div>
                            ${typeBadge}
                        </div>
                        <div class="qmc-title-row">
                            ${idxBadge}${shareBadge(item.share_class)}
                            <a href="/fund/${item.code}" target="_blank" class="qmc-fund-name">${item.name}</a>
                            <span class="code-mono">${item.code}</span>
                        </div>
                        <div class="qmc-diff-grid">
                            <span class="qmc-diff-lbl"><span class="q-channel-tag tag-agency">代销渠道</span></span>
                            <span class="q-diff-before">${item.agency.before_status}</span>
                            <span class="q-diff-arrow">➔</span>
                            <span class="q-diff-after ${item.agency.direction || ''}">${item.agency.after_status}</span>

                            <span class="qmc-diff-lbl"><span class="q-channel-tag tag-direct">直销渠道</span></span>
                            <span class="q-diff-before">${item.direct.before_status}</span>
                            <span class="q-diff-arrow">➔</span>
                            <span class="q-diff-after ${item.direct.direction || ''}">${item.direct.after_status}</span>
                        </div>
                        ${item.announcement_url ? `
                        <div class="qmc-ann-row">
                            <a href="${item.announcement_url}" target="_blank" class="q-ann-link" title="点击查看基金公司官方公告原件详情">📄 查看官方公告原件 ↗</a>
                        </div>` : ''}
                        ${subsHtml}
                    </div>
                `;
            }).join('');
        }

        // 监听平替基金点击定位事件
        if (!container._subBound) {
            container._subBound = true;
            container.addEventListener('click', e => {
                const subBtn = e.target.closest('.btn-quota-sub');
                if (subBtn) {
                    e.preventDefault();
                    const code = subBtn.dataset.code;
                    if (!code) return;

                    // 切换到全部份额让标的在排名表中可见
                    const classFilter = document.getElementById('class-filter');
                    if (classFilter) {
                        const allBtn = classFilter.querySelector('[data-value="ALL"]');
                        if (allBtn && !allBtn.classList.contains('on')) {
                            allBtn.click();
                        }
                    }

                    // 尝试在表格或卡片中高亮该基金
                    setTimeout(() => {
                        const targetRow = document.querySelector(`#rank-table tr[data-code="${code}"]`);
                        const targetCard = document.querySelector(`.fund-mobile-card[data-code="${code}"]`);
                        const targetEl = targetRow || targetCard;
                        if (targetEl) {
                            targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            targetEl.classList.add('hl-target-pulse');
                            setTimeout(() => targetEl.classList.remove('hl-target-pulse'), 3000);
                            showToast(`已为您在基金排名中定位平替标的: ${code}`, 'success');
                        } else {
                            window.open(`/fund/${code}`, '_blank');
                        }
                    }, 150);
                }
            });
        }
    }

    // ===== 动态按需加载 html2canvas 截图引擎 =====
    function loadHtml2Canvas() {
        if (window.html2canvas) return Promise.resolve(window.html2canvas);
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'js/html2canvas.min.js';
            script.onload = () => resolve(window.html2canvas);
            script.onerror = () => {
                // CDN 备用兜底
                const cdn = document.createElement('script');
                cdn.src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
                cdn.onload = () => resolve(window.html2canvas);
                cdn.onerror = () => reject(new Error('无法加载截图引擎，请检查网络连接'));
                document.head.appendChild(cdn);
            };
            document.head.appendChild(script);
        });
    }

    // 全局导出图片风格偏好（默认深色，持久化于 localStorage）
    let currentExportTheme = localStorage.getItem('fa_export_theme') || 'dark';
    let activePosterBlobUrl = null;
    let posterThemeCache = {};

    // Canvas 转 Blob 异步轻量化辅助函数（杜绝主线程大 Base64 编码卡顿）
    function canvasToBlob(canvas) {
        return new Promise((resolve, reject) => {
            if (canvas.toBlob) {
                canvas.toBlob(blob => {
                    if (blob) resolve(blob);
                    else reject(new Error('Canvas 转 Blob 失败'));
                }, 'image/png');
            } else {
                try {
                    const dataUrl = canvas.toDataURL('image/png');
                    const binStr = atob(dataUrl.split(',')[1]);
                    const len = binStr.length;
                    const arr = new Uint8Array(len);
                    for (let i = 0; i < len; i++) arr[i] = binStr.charCodeAt(i);
                    resolve(new Blob([arr], { type: 'image/png' }));
                } catch (e) {
                    reject(e);
                }
            }
        });
    }

    // 核心性能提速渲染器：忽略页面无关 DOM、精准限制视口、优化超采样倍率
    async function renderPosterToCanvas(renderTarget, posterWrap, isLight, isRank) {
        const width = renderTarget.offsetWidth;
        const height = renderTarget.offsetHeight;
        // 表格长图(980px宽)采用 1.5x 超采样(输出 1470px 超清)，公告看板(750px宽)采用 2x 超采样(输出 1500px 超清)
        // 统一输出 ~1500px 移动端视网膜分辨率，像素运算量锐减 50% 以上，渲染速度飞跃
        const exportScale = isRank ? 1.5 : 2;

        return await window.html2canvas(renderTarget, {
            scale: exportScale,
            width: width,
            height: height,
            windowWidth: width,
            windowHeight: height,
            scrollX: 0,
            scrollY: 0,
            useCORS: false,
            allowTaint: true,
            imageTimeout: 0,
            logging: false,
            backgroundColor: isLight ? '#ffffff' : (isRank ? '#0b0f19' : '#0d1322'),
            onclone: (clonedDoc) => {
                const clonedWrap = clonedDoc.getElementById('fa-export-poster-wrap');
                if (clonedWrap) {
                    clonedWrap.style.left = '0';
                    clonedWrap.style.top = '0';
                    clonedWrap.style.position = 'static';
                }
            },
            ignoreElements: (el) => {
                // 关键加速点：跳过页面主内容其他数千个节点的无谓遍历和样式解析
                if (el.parentNode === document.body && el !== posterWrap) return true;
                if (el.tagName === 'SCRIPT' || el.tagName === 'NOSCRIPT') return true;
                return false;
            }
        });
    }

    // ===== 通用图片海报预览与导出弹窗 =====
    function openPosterModal({ blob, downloadFilename, titleText, tagText, successToast, onThemeChange, currentTheme = currentExportTheme }) {
        currentExportTheme = currentTheme;

        // 释放先前 blob URL 防止内存泄露
        if (activePosterBlobUrl) {
            URL.revokeObjectURL(activePosterBlobUrl);
            activePosterBlobUrl = null;
        }

        activePosterBlobUrl = URL.createObjectURL(blob);
        posterThemeCache[currentTheme] = {
            blob,
            blobUrl: activePosterBlobUrl,
            downloadFilename
        };

        const modal = document.getElementById('poster-modal-backdrop');
        const previewImg = document.getElementById('poster-preview-img');
        const downloadBtn = document.getElementById('btn-poster-download');
        const copyBtn = document.getElementById('btn-poster-copy');
        const closeBtn = document.getElementById('poster-modal-close');
        const titleEl = document.getElementById('poster-modal-title-text');
        const tagEl = document.getElementById('poster-modal-tag');
        const themeToggle = document.getElementById('poster-modal-theme-toggle');

        if (titleEl) titleEl.textContent = titleText || '导出图片预览';
        if (tagEl) tagEl.textContent = tagText || '高清排版';
        if (previewImg) previewImg.src = activePosterBlobUrl;
        if (downloadBtn) {
            downloadBtn.href = activePosterBlobUrl;
            downloadBtn.download = downloadFilename || 'QDII图片.png';
        }

        // 绑定预览弹窗内部的风格即时切换按钮（支持 0 毫秒缓存秒切）
        if (themeToggle) {
            themeToggle.querySelectorAll('.btn-prev-theme').forEach(btn => {
                const isCur = btn.dataset.theme === currentTheme;
                btn.classList.toggle('on', isCur);
                btn.onclick = async () => {
                    if (btn.dataset.theme === currentExportTheme) return;
                    const newTheme = btn.dataset.theme;
                    currentExportTheme = newTheme;
                    try {
                        localStorage.setItem('fa_export_theme', newTheme);
                    } catch (e) {}
                    themeToggle.querySelectorAll('.btn-prev-theme').forEach(b => b.classList.toggle('on', b.dataset.theme === newTheme));

                    // 1. 若当前会话已有该风格渲染结果，立即秒切
                    if (posterThemeCache[newTheme]) {
                        const cached = posterThemeCache[newTheme];
                        if (previewImg) previewImg.src = cached.blobUrl;
                        if (downloadBtn) {
                            downloadBtn.href = cached.blobUrl;
                            downloadBtn.download = cached.downloadFilename;
                        }
                        if (tagEl) {
                            tagEl.textContent = tagEl.textContent.replace(/(浅色清新|深色商务)/, newTheme === 'light' ? '浅色清新' : '深色商务');
                        }
                        return;
                    }

                    // 2. 否则异步生成
                    if (onThemeChange) {
                        btn.textContent = '⏳ ...';
                        try {
                            await onThemeChange(newTheme);
                        } finally {
                            btn.textContent = newTheme === 'light' ? '☀️ 浅色' : '🌙 深色';
                        }
                    }
                };
            });
        }

        if (copyBtn) {
            copyBtn.onclick = async () => {
                const curBlob = posterThemeCache[currentExportTheme]?.blob || blob;
                if (navigator.clipboard && window.ClipboardItem && curBlob) {
                    try {
                        await navigator.clipboard.write([new ClipboardItem({ 'image/png': curBlob })]);
                        showToast('✅ 图片已复制到剪贴板！可直接粘贴发布', 'success');
                    } catch (e) {
                        showToast('浏览器限制直接复制，请点击“保存图片”', 'info');
                    }
                } else {
                    showToast('当前浏览器不支持直接写入图片，请点击“保存图片”', 'info');
                }
            };
        }

        const closeModal = () => {
            if (modal) modal.style.display = 'none';
            document.removeEventListener('keydown', escHandler);
            Object.values(posterThemeCache).forEach(item => {
                if (item.blobUrl) URL.revokeObjectURL(item.blobUrl);
            });
            posterThemeCache = {};
            activePosterBlobUrl = null;
        };

        const escHandler = e => {
            if (e.key === 'Escape') closeModal();
        };

        if (closeBtn) closeBtn.onclick = closeModal;
        if (modal) {
            modal.onclick = e => {
                if (e.target === modal) closeModal();
            };
            modal.style.display = 'flex';
            document.addEventListener('keydown', escHandler);
        }

        showToast(successToast || '🎉 图片已生成，可直接保存或复制！', 'success');
    }

    // ===== 公告看板导出前：变动标的勾选弹窗控制器 =====
    function openQuotaExportSelectModal(triggerBtn) {
        const data = LIMIT_CHANGES_DATA;
        if (!data || !data.history || data.history.length === 0) {
            showToast('未检测到限购公告变动数据，无需导出', 'info');
            return;
        }

        const seenCodes = new Set();
        const displayHistory = [];
        for (const h of (data.history || [])) {
            if (h.code && !seenCodes.has(h.code)) {
                seenCodes.add(h.code);
                displayHistory.push(h);
            }
        }

        if (displayHistory.length === 0) {
            showToast('暂无历史限购变动数据', 'info');
            return;
        }

        const modal = document.getElementById('quota-select-modal');
        if (!modal) {
            exportQuotaBulletinPoster(displayHistory, triggerBtn);
            return;
        }

        const totalNumEl = document.getElementById('qks-total-num');
        const selectedNumEl = document.getElementById('qks-selected-num');
        const confirmCountEl = document.getElementById('btn-qks-confirm-count');
        const listEl = document.getElementById('qks-fund-list');
        const searchInput = document.getElementById('qks-search-input');
        const btnAll = document.getElementById('btn-qks-select-all');
        const btnNone = document.getElementById('btn-qks-select-none');
        const btnInvert = document.getElementById('btn-qks-invert');
        const filterBtns = modal.querySelectorAll('.btn-qks-filter');
        const btnConfirm = document.getElementById('btn-qks-confirm');
        const btnCancel = document.getElementById('btn-qks-cancel');
        const btnClose = document.getElementById('btn-qks-close');

        if (searchInput) searchInput.value = '';
        if (totalNumEl) totalNumEl.textContent = displayHistory.length;

        // 默认全选当前 displayHistory
        const selectedCodes = new Set(displayHistory.map(h => h.code));

        const updateCountUI = () => {
            const count = selectedCodes.size;
            if (selectedNumEl) selectedNumEl.textContent = count;
            if (confirmCountEl) confirmCountEl.textContent = `(${count}只)`;
            if (btnConfirm) {
                btnConfirm.disabled = (count === 0);
            }
        };

        const renderList = () => {
            if (!listEl) return;
            listEl.innerHTML = displayHistory.map(item => {
                const isChecked = selectedCodes.has(item.code);
                const idxClass = item.index_type === '纳斯达克100' ? 'badge-nq' : 'badge-sp';
                const idxName = item.index_type === '纳斯达克100' ? '纳指' : '标普';
                const shareClass = (item.share_class || 'A').toLowerCase();
                const changeType = (item.change_type || 'TIGHTENED').toUpperCase();

                let changeLabel = '🔴 限购收紧';
                let pillClass = 'pill-tightened';
                if (changeType === 'RELAXED') {
                    changeLabel = '🟢 放宽恢复';
                    pillClass = 'pill-relaxed';
                } else if (changeType === 'CHANNEL_DIV') {
                    changeLabel = '🔵 渠道分化';
                    pillClass = 'pill-div';
                }

                const agencyTxt = `代销: ${item.agency?.after_status || '未知'}`;
                const directTxt = `直销: ${item.direct?.after_status || '未知'}`;
                const effDate = item.effective_date || item.date;
                const pubDate = item.announcement_pub_date || item.date;
                const isDiffDate = effDate && pubDate && effDate !== pubDate;

                return `
                    <label class="rks-item ${isChecked ? 'checked' : ''}" data-code="${item.code}" data-type="${changeType}">
                        <input type="checkbox" class="rks-checkbox" value="${item.code}" ${isChecked ? 'checked' : ''} />
                        <span class="dbp-change-pill ${pillClass}" style="font-size:11px;padding:1px 6px;">${changeLabel}</span>
                        <span class="dbp-idx-badge ${idxClass}" style="font-size:11px;padding:1px 4px;">${idxName}</span>
                        <span class="dbp-share-badge badge-${shareClass}">${item.share_class || 'A'}类</span>
                        <span class="rks-code">${item.code}</span>
                        <span class="rks-name" title="${item.name}">${item.name}</span>
                        <div class="rks-meta">
                            <span class="rks-eff-pill" style="font-size:11.5px;color:#f59e0b;font-weight:700;margin-right:8px">📅 生效: <strong>${effDate}</strong>${isDiffDate ? ` <span style="font-size:10.5px;color:var(--txt3);font-weight:normal">(${pubDate}发布)</span>` : ''}</span>
                            <span style="font-size:11px;color:var(--txt3)">${agencyTxt} · ${directTxt}</span>
                        </div>
                    </label>
                `;
            }).join('');

            // 绑定每项勾选点击
            listEl.querySelectorAll('.rks-item').forEach(item => {
                const code = item.dataset.code;
                const checkbox = item.querySelector('.rks-checkbox');

                item.addEventListener('click', e => {
                    if (e.target !== checkbox) {
                        checkbox.checked = !checkbox.checked;
                    }
                    if (checkbox.checked) {
                        selectedCodes.add(code);
                        item.classList.add('checked');
                    } else {
                        selectedCodes.delete(code);
                        item.classList.remove('checked');
                    }
                    updateCountUI();
                });
            });
        };

        renderList();
        updateCountUI();

        // 快捷操作：全选
        if (btnAll) {
            btnAll.onclick = () => {
                displayHistory.forEach(h => selectedCodes.add(h.code));
                if (listEl) {
                    listEl.querySelectorAll('.rks-item').forEach(item => {
                        const cb = item.querySelector('.rks-checkbox');
                        if (cb) cb.checked = true;
                        item.classList.add('checked');
                    });
                }
                updateCountUI();
            };
        }

        // 快捷操作：全不选
        if (btnNone) {
            btnNone.onclick = () => {
                selectedCodes.clear();
                if (listEl) {
                    listEl.querySelectorAll('.rks-item').forEach(item => {
                        const cb = item.querySelector('.rks-checkbox');
                        if (cb) cb.checked = false;
                        item.classList.remove('checked');
                    });
                }
                updateCountUI();
            };
        }

        // 快捷操作：反选
        if (btnInvert) {
            btnInvert.onclick = () => {
                displayHistory.forEach(h => {
                    if (selectedCodes.has(h.code)) selectedCodes.delete(h.code);
                    else selectedCodes.add(h.code);
                });
                if (listEl) {
                    listEl.querySelectorAll('.rks-item').forEach(item => {
                        const code = item.dataset.code;
                        const cb = item.querySelector('.rks-checkbox');
                        const isChecked = selectedCodes.has(code);
                        if (cb) cb.checked = isChecked;
                        if (isChecked) item.classList.add('checked');
                        else item.classList.remove('checked');
                    });
                }
                updateCountUI();
            };
        }

        // 快捷操作：仅收紧 / 仅放宽
        filterBtns.forEach(btn => {
            btn.onclick = () => {
                const targetType = btn.dataset.type;
                selectedCodes.clear();
                displayHistory.forEach(h => {
                    if ((h.change_type || '').toUpperCase() === targetType) {
                        selectedCodes.add(h.code);
                    }
                });
                if (listEl) {
                    listEl.querySelectorAll('.rks-item').forEach(item => {
                        const code = item.dataset.code;
                        const cb = item.querySelector('.rks-checkbox');
                        const isChecked = selectedCodes.has(code);
                        if (cb) cb.checked = isChecked;
                        if (isChecked) item.classList.add('checked');
                        else item.classList.remove('checked');
                    });
                }
                updateCountUI();
            };
        });

        // 弹窗内搜索检索
        if (searchInput) {
            searchInput.oninput = e => {
                const kw = e.target.value.trim().toLowerCase();
                if (!listEl) return;
                listEl.querySelectorAll('.rks-item').forEach(item => {
                    const code = item.dataset.code.toLowerCase();
                    const name = (item.querySelector('.rks-name')?.textContent || '').toLowerCase();
                    const match = !kw || code.includes(kw) || name.includes(kw);
                    item.style.display = match ? 'flex' : 'none';
                });
            };
        }

        const closeSelectModal = () => {
            modal.style.display = 'none';
            document.removeEventListener('keydown', escHandler);
        };

        const escHandler = e => {
            if (e.key === 'Escape') closeSelectModal();
        };

        if (btnClose) btnClose.onclick = closeSelectModal;
        if (btnCancel) btnCancel.onclick = closeSelectModal;
        modal.onclick = e => {
            if (e.target === modal) closeSelectModal();
        };

        // 风格选择器联动
        const qksThemeGroup = document.getElementById('qks-theme-group');
        if (qksThemeGroup) {
            qksThemeGroup.querySelectorAll('.btn-theme-sel').forEach(btn => {
                btn.classList.toggle('on', btn.dataset.theme === currentExportTheme);
                btn.onclick = () => {
                    currentExportTheme = btn.dataset.theme;
                    try { localStorage.setItem('fa_export_theme', currentExportTheme); } catch (e) {}
                    qksThemeGroup.querySelectorAll('.btn-theme-sel').forEach(b => b.classList.toggle('on', b === btn));
                };
            });
        }

        if (btnConfirm) {
            btnConfirm.onclick = () => {
                if (selectedCodes.size === 0) {
                    showToast('请至少勾选一只变动基金进行导出', 'info');
                    return;
                }
                const selectedItems = displayHistory.filter(h => selectedCodes.has(h.code));
                closeSelectModal();
                showToast('⏳ 正在渲染高清图片，请稍候...', 'info');
                exportQuotaBulletinPoster(selectedItems, triggerBtn, currentExportTheme);
            };
        }

        modal.style.display = 'flex';
        document.addEventListener('keydown', escHandler);
    }

    // ===== 导出适合社交发布的 3:4 公告看板图片 (按勾选标的渲染，剥离平替推荐与网页交互控件) =====
    async function exportQuotaBulletinPoster(selectedItems, triggerBtn, exportTheme = currentExportTheme) {
        currentExportTheme = exportTheme;
        const isLight = exportTheme === 'light';
        const data = LIMIT_CHANGES_DATA;
        if (!data) {
            showToast('未检测到限购公告数据', 'info');
            return;
        }

        const todayStr = data.today_date || new Date().toISOString().slice(0, 10);
        const seenCodes = new Set();
        const displayHistory = [];
        for (const h of (data.history || [])) {
            if (h.code && !seenCodes.has(h.code)) {
                seenCodes.add(h.code);
                displayHistory.push(h);
            }
        }

        const itemsToExport = (selectedItems && selectedItems.length) ? selectedItems : displayHistory;

        const relaxedCount = itemsToExport.filter(h => h.change_type === 'RELAXED').length;
        const tightenedCount = itemsToExport.filter(h => h.change_type === 'TIGHTENED').length;

        // 设置按钮加载态
        const originalText = triggerBtn ? triggerBtn.innerHTML : '';
        if (triggerBtn) {
            triggerBtn.disabled = true;
            triggerBtn.innerHTML = '<span>⏳ 正在生成...</span>';
            // 全局新发起导出时，清空上一次会话缓存
            Object.values(posterThemeCache).forEach(item => {
                if (item.blobUrl) URL.revokeObjectURL(item.blobUrl);
            });
            posterThemeCache = {};
        }

        try {
            await loadHtml2Canvas();

            // 构建专为竖版打造的离屏海报 DOM（无平替列，无网页交互元素）
            const posterWrap = document.createElement('div');
            posterWrap.id = 'fa-export-poster-wrap';
            posterWrap.style.cssText = 'position:fixed;left:-9999px;top:0;width:750px;z-index:-9999;pointer-events:none;';

            let cardsHtml = '';
            if (itemsToExport.length === 0) {
                cardsHtml = `
                    <div class="dbp-card" style="text-align:center;padding:36px 20px;border-left:none;">
                        <div style="font-size:36px;margin-bottom:12px">🛡️</div>
                        <div style="font-size:18px;font-weight:700;color:${isLight ? '#0f172a' : '#f8fafc'};margin-bottom:6px">全市场额度平稳运行</div>
                        <div style="font-size:14px;color:${isLight ? '#64748b' : '#94a3b8'}">今日无新增限购收紧或暂停申购变动</div>
                    </div>
                `;
            } else {
                cardsHtml = itemsToExport.map(item => {
                    const idxClass = item.index_type === '纳斯达克100' ? 'badge-nq' : 'badge-sp';
                    const idxName = item.index_type === '纳斯达克100' ? '纳指' : '标普';
                    const shareClass = (item.share_class || 'A').toLowerCase();
                    const changeType = (item.change_type || 'TIGHTENED').toUpperCase();

                    let changeLabel = '🔴 限购收紧';
                    let pillClass = 'pill-tightened';
                    if (changeType === 'RELAXED') {
                        changeLabel = '🟢 放宽恢复';
                        pillClass = 'pill-relaxed';
                    } else if (changeType === 'CHANNEL_DIV') {
                        changeLabel = '🔵 渠道分化';
                        pillClass = 'pill-div';
                    }

                    const agencyDir = (item.agency && item.agency.direction) ? item.agency.direction.toLowerCase() : '';
                    const directDir = (item.direct && item.direct.direction) ? item.direct.direction.toLowerCase() : '';

                    const effDate = item.effective_date || item.date;
                    const pubDate = item.announcement_pub_date || item.date;
                    const isDiffDate = effDate && pubDate && effDate !== pubDate;

                    return `
                        <div class="dbp-card dbp-card-${changeType.toLowerCase()}">
                            <div class="dbp-card-top">
                                <div class="dbp-fund-ident">
                                    <span class="dbp-idx-badge ${idxClass}">${idxName}</span>
                                    <span class="dbp-share-badge badge-${shareClass}">${item.share_class || 'A'}类</span>
                                    <span class="dbp-fund-code">${item.code}</span>
                                    <span class="dbp-fund-name">${item.name}</span>
                                </div>
                                <div class="dbp-top-right-group">
                                    <span class="dbp-eff-pill"><span class="dbp-eff-icon">📅</span> 生效: <strong>${effDate}</strong></span>
                                    <div class="dbp-change-pill ${pillClass}">
                                        ${changeLabel}
                                    </div>
                                </div>
                            </div>
                            
                            <div class="dbp-channels-row">
                                <div class="dbp-channel-box">
                                    <span class="dbp-ch-lbl">代销渠道</span>
                                    <div class="dbp-flow">
                                        <span class="dbp-val-before">${item.agency?.before_status || '未知'}</span>
                                        <span class="dbp-flow-arr">➔</span>
                                        <span class="dbp-val-after ${agencyDir}">${item.agency?.after_status || '未知'}</span>
                                    </div>
                                </div>
                                <div class="dbp-channel-box">
                                    <span class="dbp-ch-lbl">直销渠道</span>
                                    <div class="dbp-flow">
                                        <span class="dbp-val-before">${item.direct?.before_status || '未知'}</span>
                                        <span class="dbp-flow-arr">➔</span>
                                        <span class="dbp-val-after ${directDir}">${item.direct?.after_status || '未知'}</span>
                                    </div>
                                </div>
                            </div>
                            ${item.notice_title ? `<div class="dbp-card-notice">📑 公告：《${item.notice_title}》</div>` : ''}
                        </div>
                    `;
                }).join('');
            }

            posterWrap.innerHTML = `
                <div class="douyin-poster-export ${isLight ? 'theme-light' : ''}" id="dbp-render-target">
                    <div class="dbp-header">
                        <div class="dbp-top-tag">
                            <span>📢</span>
                            <span>美股 QDII 额度动态监控速报</span>
                            <span class="dbp-tag-date">📅 ${todayStr}</span>
                        </div>
                        <h1 class="dbp-title">QDII 基金限购变动看板</h1>
                        <p class="dbp-sub">每日自动巡检全市场60只QDII基金 · 代销与直销申购额度异动追踪</p>
                        
                        <div class="dbp-stats-bar">
                            <div class="dbp-stat-chip chip-tightened">
                                <span>🔴</span>
                                <span>限购收紧/暂停</span>
                                <strong>${tightenedCount}</strong>
                            </div>
                            <div class="dbp-stat-chip chip-relaxed">
                                <span>🟢</span>
                                <span>放宽/恢复申购</span>
                                <strong>${relaxedCount}</strong>
                            </div>
                            <div class="dbp-stat-chip chip-monitored">
                                <span>🛡️</span>
                                <span>选入展示</span>
                                <strong>${itemsToExport.length} / ${displayHistory.length} 只</strong>
                            </div>
                        </div>
                    </div>

                    <div class="dbp-body">
                        ${cardsHtml}
                    </div>

                    <div class="dbp-footer">
                        <div class="dbp-footer-brand">
                            <span class="dbp-brand-name">📊 Fund Advisor</span>
                            <span class="dbp-brand-tag">美股指数基金智能投资分析器</span>
                        </div>
                        <div class="dbp-footer-meta">
                            <p>数据源自基金管理人公开公告 · 每日自动更新</p>
                            <p>本文不构成任何投资建议与销售要约 · 投资需谨慎</p>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(posterWrap);
            const renderTarget = document.getElementById('dbp-render-target');

            const canvas = await renderPosterToCanvas(renderTarget, posterWrap, isLight, false);
            document.body.removeChild(posterWrap);
            const blob = await canvasToBlob(canvas);

            openPosterModal({
                blob,
                downloadFilename: `QDII限购变动速递_${isLight ? '浅色_' : ''}${todayStr}.png`,
                titleText: '公告看板图片预览',
                tagText: `${itemsToExport.length}只变动 · ${isLight ? '☀️ 浅色清新' : '🌙 深色商务'}`,
                currentTheme: exportTheme,
                onThemeChange: async (newTheme) => {
                    currentExportTheme = newTheme;
                    try { localStorage.setItem('fa_export_theme', newTheme); } catch (e) {}
                    await exportQuotaBulletinPoster(itemsToExport, null, newTheme);
                },
                successToast: '🎉 公告看板图片已生成，可直接保存或复制！'
            });

        } catch (err) {
            console.error('看板图片生成失败:', err);
            showToast('生成图片失败: ' + (err.message || '未知错误'), 'error');
        } finally {
            if (triggerBtn) {
                triggerBtn.disabled = false;
                triggerBtn.innerHTML = originalText;
            }
        }
    }

    // ===== 全景对比表格导出前：基金勾选选择弹窗控制器 =====
    function openRankExportSelectModal(triggerBtn) {
        if (!rankData || rankData.length === 0) {
            showToast('当前表格无展示标的，无法导出', 'info');
            return;
        }

        const modal = document.getElementById('rank-select-modal');
        if (!modal) {
            exportRankTablePoster(rankData, triggerBtn, currentExportTheme);
            return;
        }

        const totalNumEl = document.getElementById('rks-total-num');
        const selectedNumEl = document.getElementById('rks-selected-num');
        const quotaNumEl = document.getElementById('rks-quota-num');
        const confirmCountEl = document.getElementById('btn-rks-confirm-count');
        const listEl = document.getElementById('rks-fund-list');
        const searchInput = document.getElementById('rks-search-input');
        const btnAll = document.getElementById('btn-rks-select-all');
        const btnNone = document.getElementById('btn-rks-select-none');
        const btnInvert = document.getElementById('btn-rks-invert');
        const btnQuota = document.getElementById('btn-rks-select-quota');
        const btnConfirm = document.getElementById('btn-rks-confirm');
        const btnCancel = document.getElementById('btn-rks-cancel');
        const btnClose = document.getElementById('btn-rks-close');
        const topBtns = modal.querySelectorAll('.btn-rks-top');

        if (searchInput) searchInput.value = '';
        if (totalNumEl) totalNumEl.textContent = rankData.length;

        // 判断基金是否具有代销或直销申购额度
        const isFundWithQuota = r => {
            const agencyOk = !(r.limit_status || '').includes('暂停') && !(r.limit_status || '').includes('未开通');
            const directOk = Boolean(r.direct_limit_status && !r.direct_limit_status.includes('暂停') && !r.direct_limit_status.includes('未开通'));
            return Boolean(agencyOk || directOk);
        };

        const currentType = document.querySelector('#rank-filter .seg-btn.on')?.dataset.value || '纳斯达克100';
        const nqList = rankData.filter(r => r.index_type === '纳斯达克100');
        const spList = rankData.filter(r => r.index_type === '标普500');
        const isGrouped = (currentType === 'ALL' || (nqList.length > 0 && spList.length > 0));

        const nqListWithRanks = nqList.map((r, idx) => ({ ...r, displayRank: idx + 1 }));
        const spListWithRanks = spList.map((r, idx) => ({ ...r, displayRank: idx + 1 }));
        const orderedList = isGrouped ? [...nqListWithRanks, ...spListWithRanks] : rankData;

        const quotaFundsCount = rankData.filter(isFundWithQuota).length;
        if (quotaNumEl) quotaNumEl.textContent = quotaFundsCount;
        if (btnQuota) {
            btnQuota.innerHTML = `🟢 有额度 (${quotaFundsCount})`;
        }

        // 默认全选当前展示的集合 (全部美股QDII时按 纳指在上、标普在下 排列)
        const selectedCodes = new Set(orderedList.map(r => r.code));

        const updateCountUI = () => {
            const count = selectedCodes.size;
            if (selectedNumEl) selectedNumEl.textContent = count;
            if (confirmCountEl) confirmCountEl.textContent = `(${count}只)`;
            if (btnConfirm) {
                btnConfirm.disabled = (count === 0);
            }
            if (isGrouped) {
                const nqSelected = nqList.filter(r => selectedCodes.has(r.code)).length;
                const spSelected = spList.filter(r => selectedCodes.has(r.code)).length;
                const nqStatEl = document.getElementById('rks-nq-stat');
                const spStatEl = document.getElementById('rks-sp-stat');
                if (nqStatEl) nqStatEl.textContent = `(已选 ${nqSelected}/${nqList.length} 只)`;
                if (spStatEl) spStatEl.textContent = `(已选 ${spSelected}/${spList.length} 只)`;
            }
        };

        const getQuotaBadgeHtml = r => {
            const agencyOk = !(r.limit_status || '').includes('暂停') && !(r.limit_status || '').includes('未开通');
            const directOk = Boolean(r.direct_limit_status && !r.direct_limit_status.includes('暂停') && !r.direct_limit_status.includes('未开通'));

            if (agencyOk && directOk) {
                return `<span class="rks-quota-badge quota-both" title="代销: ${r.limit_status} · 直销: ${r.direct_limit_status}">🟢 代销/直销有额度</span>`;
            } else if (agencyOk) {
                return `<span class="rks-quota-badge quota-agency" title="代销: ${r.limit_status}">🟢 代销:${r.limit_status}</span>`;
            } else if (directOk) {
                return `<span class="rks-quota-badge quota-direct" title="代销暂停 · 直销: ${r.direct_limit_status}">🟡 直销:${r.direct_limit_status}</span>`;
            } else {
                return `<span class="rks-quota-badge quota-paused" title="代销与直销均已暂停或未开通">🔴 暂停申购</span>`;
            }
        };

        const renderItem = r => {
            const isChecked = selectedCodes.has(r.code);
            const totalFee = (r.mgmt_fee || 0) + (r.custody_fee || 0) + (r.sales_fee || 0);
            const rankNum = r.displayRank || r.rank || 1;
            let rankBadge = rankNum === 1 ? '🥇' : (rankNum === 2 ? '🥈' : (rankNum === 3 ? '🥉' : `#${rankNum}`));
            const hasQuota = isFundWithQuota(r);
            const quotaBadge = getQuotaBadgeHtml(r);
            const quotaSearchText = `${r.limit_status || ''} ${r.direct_limit_status || ''} ${hasQuota ? '有额度 可申购 可买 有申购额度' : '暂停申购 无额度'}`;

            return `
                <label class="rks-item ${isChecked ? 'checked' : ''}" data-code="${r.code}" data-has-quota="${hasQuota}" data-quota="${quotaSearchText}" data-index-type="${r.index_type}">
                    <input type="checkbox" class="rks-checkbox" value="${r.code}" ${isChecked ? 'checked' : ''} />
                    <span class="rks-rank">${rankBadge}</span>
                    <span class="rks-code">${r.code}</span>
                    ${shareBadge(r.share_class)}
                    <span class="rks-name" title="${r.name}">${r.name}</span>
                    ${quotaBadge}
                    <div class="rks-meta">
                        <span class="rks-fee" title="综合费率">${fmt(totalFee)}</span>
                        <span class="rks-score" title="综合评分">${r.score}分</span>
                    </div>
                </label>
            `;
        };

        const renderList = () => {
            if (!listEl) return;
            if (isGrouped) {
                let html = '';
                if (nqList.length > 0) {
                    html += `
                        <div class="rks-group-section rks-group-nq" data-group="nq">
                            <div class="rks-group-header">
                                <div class="rks-group-title">
                                    <span class="rks-group-badge nq-badge">NASDAQ 100</span>
                                    <span class="rks-group-name">纳斯达克 100 指数标的</span>
                                    <span class="rks-group-stat" id="rks-nq-stat">(已选 0/${nqList.length} 只)</span>
                                </div>
                                <div class="rks-group-tools">
                                    <button type="button" class="btn-rks-sub-tool" data-action="all" data-target="nq" title="全选纳指100所有标的">全选本组</button>
                                    <button type="button" class="btn-rks-sub-tool" data-action="none" data-target="nq" title="清空纳指100所有标的勾选">清空本组</button>
                                </div>
                            </div>
                            <div class="rks-group-items">
                                ${nqListWithRanks.map(renderItem).join('')}
                            </div>
                        </div>
                    `;
                }
                if (spList.length > 0) {
                    html += `
                        <div class="rks-group-section rks-group-sp" data-group="sp">
                            <div class="rks-group-header">
                                <div class="rks-group-title">
                                    <span class="rks-group-badge sp-badge">S&P 500</span>
                                    <span class="rks-group-name">标普 500 指数标的</span>
                                    <span class="rks-group-stat" id="rks-sp-stat">(已选 0/${spList.length} 只)</span>
                                </div>
                                <div class="rks-group-tools">
                                    <button type="button" class="btn-rks-sub-tool" data-action="all" data-target="sp" title="全选标普500所有标的">全选本组</button>
                                    <button type="button" class="btn-rks-sub-tool" data-action="none" data-target="sp" title="清空标普500所有标的勾选">清空本组</button>
                                </div>
                            </div>
                            <div class="rks-group-items">
                                ${spListWithRanks.map(renderItem).join('')}
                            </div>
                        </div>
                    `;
                }
                listEl.innerHTML = html;
            } else {
                listEl.innerHTML = rankData.map(renderItem).join('');
            }

            // 绑定每项勾选点击
            listEl.querySelectorAll('.rks-item').forEach(item => {
                const code = item.dataset.code;
                const checkbox = item.querySelector('.rks-checkbox');

                item.addEventListener('click', e => {
                    if (e.target !== checkbox) {
                        checkbox.checked = !checkbox.checked;
                    }
                    if (checkbox.checked) {
                        selectedCodes.add(code);
                        item.classList.add('checked');
                    } else {
                        selectedCodes.delete(code);
                        item.classList.remove('checked');
                    }
                    updateCountUI();
                });
            });

            // 绑定组内全选/清空
            if (isGrouped) {
                listEl.querySelectorAll('.btn-rks-sub-tool').forEach(btn => {
                    btn.addEventListener('click', e => {
                        e.stopPropagation();
                        const action = btn.dataset.action;
                        const targetGroup = btn.dataset.target;
                        const groupType = targetGroup === 'nq' ? '纳斯达克100' : '标普500';
                        const targetFunds = rankData.filter(r => r.index_type === groupType);

                        if (action === 'all') {
                            targetFunds.forEach(r => selectedCodes.add(r.code));
                        } else if (action === 'none') {
                            targetFunds.forEach(r => selectedCodes.delete(r.code));
                        }

                        const sec = btn.closest('.rks-group-section');
                        if (sec) {
                            sec.querySelectorAll('.rks-item').forEach(item => {
                                const code = item.dataset.code;
                                const cb = item.querySelector('.rks-checkbox');
                                const isChecked = selectedCodes.has(code);
                                if (cb) cb.checked = isChecked;
                                if (isChecked) item.classList.add('checked');
                                else item.classList.remove('checked');
                            });
                        }

                        updateCountUI();
                    });
                });
            }
        };

        renderList();
        updateCountUI();

        // 快捷操作：全选
        if (btnAll) {
            btnAll.onclick = () => {
                rankData.forEach(r => selectedCodes.add(r.code));
                if (listEl) {
                    listEl.querySelectorAll('.rks-item').forEach(item => {
                        const cb = item.querySelector('.rks-checkbox');
                        if (cb) cb.checked = true;
                        item.classList.add('checked');
                    });
                }
                updateCountUI();
            };
        }

        // 快捷操作：全不选
        if (btnNone) {
            btnNone.onclick = () => {
                selectedCodes.clear();
                if (listEl) {
                    listEl.querySelectorAll('.rks-item').forEach(item => {
                        const cb = item.querySelector('.rks-checkbox');
                        if (cb) cb.checked = false;
                        item.classList.remove('checked');
                    });
                }
                updateCountUI();
            };
        }

        // 快捷操作：反选
        if (btnInvert) {
            btnInvert.onclick = () => {
                rankData.forEach(r => {
                    if (selectedCodes.has(r.code)) selectedCodes.delete(r.code);
                    else selectedCodes.add(r.code);
                });
                if (listEl) {
                    listEl.querySelectorAll('.rks-item').forEach(item => {
                        const code = item.dataset.code;
                        const cb = item.querySelector('.rks-checkbox');
                        const isChecked = selectedCodes.has(code);
                        if (cb) cb.checked = isChecked;
                        if (isChecked) item.classList.add('checked');
                        else item.classList.remove('checked');
                    });
                }
                updateCountUI();
            };
        }

        // 快捷操作：有额度 (一键选择代销或直销有额度的基金)
        if (btnQuota) {
            btnQuota.onclick = () => {
                const kw = searchInput ? searchInput.value.trim().toLowerCase() : '';
                selectedCodes.clear();
                let matchedCount = 0;

                rankData.forEach(r => {
                    if (isFundWithQuota(r)) {
                        if (kw) {
                            const quotaText = `${r.limit_status || ''} ${r.direct_limit_status || ''} 有额度 可申购 可买 有申购额度`;
                            const matchKw = r.code.toLowerCase().includes(kw) ||
                                           (r.name || '').toLowerCase().includes(kw) ||
                                           quotaText.toLowerCase().includes(kw);
                            if (matchKw) {
                                selectedCodes.add(r.code);
                                matchedCount++;
                            }
                        } else {
                            selectedCodes.add(r.code);
                            matchedCount++;
                        }
                    }
                });

                if (listEl) {
                    listEl.querySelectorAll('.rks-item').forEach(item => {
                        const code = item.dataset.code;
                        const cb = item.querySelector('.rks-checkbox');
                        const isChecked = selectedCodes.has(code);
                        if (cb) cb.checked = isChecked;
                        if (isChecked) item.classList.add('checked');
                        else item.classList.remove('checked');
                    });
                }
                updateCountUI();
                if (matchedCount > 0) {
                    showToast(`已为您勾选 ${matchedCount} 只代销/直销有额度的标的`, 'success');
                } else {
                    showToast('当前筛选列表中暂无有可用额度的基金', 'info');
                }
            };
        }

        // 快捷操作：Top N
        topBtns.forEach(btn => {
            btn.onclick = () => {
                const topN = parseInt(btn.dataset.top, 10) || 10;
                selectedCodes.clear();
                if (isGrouped) {
                    const perGroup = Math.floor(topN / 2);
                    nqList.slice(0, perGroup).forEach(r => selectedCodes.add(r.code));
                    spList.slice(0, perGroup).forEach(r => selectedCodes.add(r.code));
                } else {
                    rankData.slice(0, topN).forEach(r => selectedCodes.add(r.code));
                }
                if (listEl) {
                    listEl.querySelectorAll('.rks-item').forEach(item => {
                        const code = item.dataset.code;
                        const cb = item.querySelector('.rks-checkbox');
                        const isChecked = selectedCodes.has(code);
                        if (cb) cb.checked = isChecked;
                        if (isChecked) item.classList.add('checked');
                        else item.classList.remove('checked');
                    });
                }
                updateCountUI();
            };
        });

        // 弹窗内搜索检索 (支持代码、名称、额度状态关键词)
        if (searchInput) {
            searchInput.oninput = e => {
                const kw = e.target.value.trim().toLowerCase();
                if (!listEl) return;
                listEl.querySelectorAll('.rks-item').forEach(item => {
                    const code = (item.dataset.code || '').toLowerCase();
                    const name = (item.querySelector('.rks-name')?.textContent || '').toLowerCase();
                    const quota = (item.dataset.quota || '').toLowerCase();
                    const hasQuota = item.dataset.hasQuota === 'true';

                    let match = !kw || code.includes(kw) || name.includes(kw) || quota.includes(kw);
                    if (kw === '有额度' || kw === '可申购' || kw === '可买' || kw === '有申购额度') {
                        match = hasQuota;
                    } else if (kw === '暂停' || kw === '暂停申购' || kw === '无额度') {
                        match = !hasQuota;
                    }
                    item.style.display = match ? 'flex' : 'none';
                });

                if (isGrouped) {
                    listEl.querySelectorAll('.rks-group-section').forEach(sec => {
                        const hasVisible = Array.from(sec.querySelectorAll('.rks-item')).some(item => item.style.display !== 'none');
                        sec.style.display = hasVisible ? '' : 'none';
                    });
                }
            };
        }

        const closeSelectModal = () => {
            modal.style.display = 'none';
            document.removeEventListener('keydown', escHandler);
        };

        const escHandler = e => {
            if (e.key === 'Escape') closeSelectModal();
        };

        if (btnClose) btnClose.onclick = closeSelectModal;
        if (btnCancel) btnCancel.onclick = closeSelectModal;
        modal.onclick = e => {
            if (e.target === modal) closeSelectModal();
        };

        // 风格选择器联动
        const rksThemeGroup = document.getElementById('rks-theme-group');
        if (rksThemeGroup) {
            rksThemeGroup.querySelectorAll('.btn-theme-sel').forEach(btn => {
                btn.classList.toggle('on', btn.dataset.theme === currentExportTheme);
                btn.onclick = () => {
                    currentExportTheme = btn.dataset.theme;
                    try { localStorage.setItem('fa_export_theme', currentExportTheme); } catch (e) {}
                    rksThemeGroup.querySelectorAll('.btn-theme-sel').forEach(b => b.classList.toggle('on', b === btn));
                };
            });
        }

        if (btnConfirm) {
            btnConfirm.onclick = () => {
                if (selectedCodes.size === 0) {
                    showToast('请至少勾选一只基金进行导出', 'info');
                    return;
                }
                const selectedFunds = isGrouped
                    ? [...nqList.filter(r => selectedCodes.has(r.code)), ...spList.filter(r => selectedCodes.has(r.code))]
                    : rankData.filter(r => selectedCodes.has(r.code));
                closeSelectModal();
                showToast('⏳ 正在渲染高清图片，请稍候...', 'info');
                exportRankTablePoster(selectedFunds, triggerBtn, currentExportTheme);
            };
        }

        modal.style.display = 'flex';
        document.addEventListener('keydown', escHandler);
    }

    // ===== 导出全景对比表格高清长图图片 (按勾选标的渲染，剔除网页交互控件与重复类别徽标) =====
    async function exportRankTablePoster(selectedFunds, triggerBtn, exportTheme = currentExportTheme) {
        currentExportTheme = exportTheme;
        const isLight = exportTheme === 'light';
        const fundsToExport = (selectedFunds && selectedFunds.length) ? selectedFunds : rankData;
        if (!fundsToExport || fundsToExport.length === 0) {
            showToast('未选择任何标的，无法导出', 'info');
            return;
        }

        const todayStr = (LIMIT_CHANGES_DATA && LIMIT_CHANGES_DATA.today_date) || new Date().toISOString().slice(0, 10);
        const type = document.querySelector('#rank-filter .seg-btn.on')?.dataset.value || '纳斯达克100';
        const classFilter = document.querySelector('#class-filter .seg-btn.on, #class-filter .filter-pill.on')?.dataset.value || 'ALL';
        const quotaFilter = document.querySelector('#quota-filter .seg-btn.on, #quota-filter .filter-pill.on')?.dataset.value || 'ALL';
        const kw = (document.getElementById('rank-search')?.value || '').trim();

        const typeLabel = type === 'ALL' ? '全市场美股QDII' : type;
        const classLabel = classFilter === 'ALL' ? '全部份额' : (classFilter + '类份额');
        let quotaLabel = '全部渠道';
        if (quotaFilter === 'BUYABLE') quotaLabel = '代销可买';
        else if (quotaFilter === 'DIRECT') quotaLabel = '直销可买';
        else if (quotaFilter === 'PAUSED') quotaLabel = '暂停申购';

        const titleText = `${typeLabel} 基金量化投研评分榜`;

        // 设置按钮加载态
        const originalText = triggerBtn ? triggerBtn.innerHTML : '';
        if (triggerBtn) {
            triggerBtn.disabled = true;
            triggerBtn.innerHTML = '<span>⏳ 正在生成...</span>';
            // 全局新发起导出时，清空上一次会话缓存
            Object.values(posterThemeCache).forEach(item => {
                if (item.blobUrl) URL.revokeObjectURL(item.blobUrl);
            });
            posterThemeCache = {};
        }

        try {
            await loadHtml2Canvas();

            // 构建离屏表格海报 DOM（980px 宽度，高分屏 1.5x 超采样输出 1470px 视网膜超清图）
            const posterWrap = document.createElement('div');
            posterWrap.id = 'fa-export-poster-wrap';
            posterWrap.style.cssText = 'position:fixed;left:-9999px;top:0;width:980px;z-index:-9999;pointer-events:none;';

            const nqExport = fundsToExport.filter(r => r.index_type === '纳斯达克100');
            const spExport = fundsToExport.filter(r => r.index_type === '标普500');
            const isGroupedExport = (type === 'ALL' || (nqExport.length > 0 && spExport.length > 0));

            const renderRow = (r, rankNum) => {
                let rankBadge;
                let rowCls = '';
                if (rankNum === 1) { rankBadge = '<span class="rkp-rank-badge rank-gold">🥇 1</span>'; rowCls = 'row-gold'; }
                else if (rankNum === 2) { rankBadge = '<span class="rkp-rank-badge rank-silver">🥈 2</span>'; rowCls = 'row-silver'; }
                else if (rankNum === 3) { rankBadge = '<span class="rkp-rank-badge rank-bronze">🥉 3</span>'; rowCls = 'row-bronze'; }
                else { rankBadge = `<span class="rkp-rank-badge">#${rankNum}</span>`; }

                // 类别信息已在上方横幅醒目展示，标的列仅保留份额徽标与基金名称，彻底释放横向空间
                const sBadge = shareBadge(r.share_class);

                const mgmt = r.mgmt_fee || 0;
                const cust = r.custody_fee || 0;
                const sales = r.sales_fee || 0;
                const totalFee = mgmt + cust + sales;
                const isLowFee = totalFee <= 0.007;

                const teStr = fmt(r.tracking_error);
                const ir = r.information_ratio;
                const td = r.tracking_difference;
                let subTe = '';
                if (ir != null) {
                    const irColor = ir >= 1.0 ? '#34d399' : (ir < 0 ? '#f87171' : '#94a3b8');
                    subTe += `<span style="color:${irColor};margin-right:6px">IR <strong>${ir.toFixed(2)}</strong></span>`;
                }
                if (td != null) {
                    const tdColor = td >= 0 ? '#f87171' : '#34d399';
                    subTe += `<span style="color:${tdColor};font-weight:600">TD ${(td >= 0 ? '+' : '') + (td * 100).toFixed(1)}%</span>`;
                }

                let ret3yrHtml = '-';
                if (r.return_3yr != null) {
                    ret3yrHtml = '<span style="color:#34d399;font-weight:600">' + fmt(r.return_3yr) + '</span>';
                } else if (r.return_since != null) {
                    ret3yrHtml = '<span style="color:#34d399;font-weight:600">' + fmt(r.return_since) + '</span>';
                }

                const starsHtml = (r.morningstar && r.morningstar > 0)
                    ? `<span class="rkp-stars">${'★'.repeat(r.morningstar)}</span>`
                    : '<span style="color:#64748b">—</span>';

                const agencyPill = pill(r.limit_status);
                const directPill = r.direct_limit_status ? pill(r.direct_limit_status) : '<span class="tbl-limit-na">—</span>';
                let shareHtml = '';
                if (r.quota_sharing === 'SHARED') {
                    shareHtml = '<span class="badge-shared">🔗 共享额度</span>';
                } else if (r.quota_sharing === 'INDEPENDENT') {
                    shareHtml = '<span class="badge-indep">独立额度</span>';
                } else {
                    shareHtml = '<span class="tbl-limit-na">—</span>';
                }

                return `
                    <tr class="${rowCls}">
                        <td>${rankBadge}</td>
                        <td><span class="rkp-code">${r.code}</span></td>
                        <td>
                            <div class="rkp-name-cell">
                                ${sBadge}
                                <span class="rkp-fund-name">${r.name}</span>
                            </div>
                        </td>
                        <td>
                            <div class="tbl-fee-cell">
                                <span class="rkp-fee ${isLowFee ? 'low' : ''}">${fmt(totalFee)}</span>
                                ${isLowFee ? '<span class="rkp-badge-low">低</span>' : ''}
                            </div>
                        </td>
                        <td>
                            <div class="rkp-te-cell">
                                <span class="rkp-te-val">${teStr}</span>
                                ${subTe ? '<div class="rkp-te-sub">' + subTe + '</div>' : ''}
                            </div>
                        </td>
                        <td>${r.scale ? r.scale.toFixed(1) + '亿' : '-'}</td>
                        <td>${ret3yrHtml}</td>
                        <td>${starsHtml}</td>
                        <td>
                            <div class="tbl-limit-cell">
                                <div class="tbl-limit-row"><span class="tbl-limit-lbl">代销</span>${agencyPill}</div>
                                <div class="tbl-limit-row"><span class="tbl-limit-lbl">直销</span>${directPill}</div>
                                <div class="tbl-limit-row tbl-limit-share">${shareHtml}</div>
                            </div>
                        </td>
                        <td><span class="rkp-score-badge">${r.score}</span></td>
                    </tr>
                `;
            };

            let tableBodyHtml = '';
            if (isGroupedExport) {
                if (nqExport.length > 0) {
                    tableBodyHtml += `
                        <tr class="rkp-group-row">
                            <td colspan="10">
                                <div class="rkp-poster-group-banner rkp-banner-nq">
                                    <div class="rkp-pgb-left">
                                        <span class="rkp-pgb-pill pill-nq">NASDAQ 100</span>
                                        <span class="rkp-pgb-title">纳斯达克 100 指数</span>
                                        <span class="rkp-pgb-sub">(科技成长核心标的)</span>
                                    </div>
                                    <div class="rkp-pgb-right">
                                        <span class="rkp-pgb-count">本组选入 <strong>${nqExport.length}</strong> 只</span>
                                    </div>
                                </div>
                            </td>
                        </tr>
                        ${nqExport.map((r, idx) => renderRow(r, idx + 1)).join('')}
                    `;
                }
                if (spExport.length > 0) {
                    tableBodyHtml += `
                        <tr class="rkp-group-row">
                            <td colspan="10">
                                <div class="rkp-poster-group-banner rkp-banner-sp">
                                    <div class="rkp-pgb-left">
                                        <span class="rkp-pgb-pill pill-sp">S&P 500</span>
                                        <span class="rkp-pgb-title">标普 500 指数</span>
                                        <span class="rkp-pgb-sub">(大盘蓝筹基石标的)</span>
                                    </div>
                                    <div class="rkp-pgb-right">
                                        <span class="rkp-pgb-count">本组选入 <strong>${spExport.length}</strong> 只</span>
                                    </div>
                                </div>
                            </td>
                        </tr>
                        ${spExport.map((r, idx) => renderRow(r, idx + 1)).join('')}
                    `;
                }
            } else {
                tableBodyHtml = fundsToExport.map((r, idx) => renderRow(r, idx + 1)).join('');
            }

            posterWrap.innerHTML = `
                <div class="rank-poster-export ${isLight ? 'theme-light' : ''}" id="rkp-render-target">
                    <div class="rkp-header">
                        <div class="rkp-top-tag">
                            <span>🏆</span>
                            <span>美股 QDII 基金量化投研评分榜</span>
                            <span class="rkp-tag-date">📅 ${todayStr}</span>
                        </div>
                        <h1 class="rkp-title">${titleText}</h1>
                        <p class="rkp-sub">多因子量化评分模型：综合费率 (35%) · 跟踪误差 (20%) · 基金规模 (15%) · 近3年收益 (15%) · 晨星评级 (10%) · 申购费率 (5%)</p>
                        
                        <!-- 醒目标题与标的范围横幅 (取代行内重复徽标) -->
                        <div class="rkp-scope-bar">
                            <div class="rkp-scope-badge-group">
                                <span class="rkp-scope-lbl">📌 基金类别</span>
                                <span class="rkp-scope-highlight ${type === '纳斯达克100' ? 'scope-nq' : (type === '标普500' ? 'scope-sp' : 'scope-all')}">${typeLabel}</span>
                            </div>
                            <div class="rkp-scope-chips">
                                <span class="rkp-chip"><span class="rkp-chip-k">份额：</span><strong>${classLabel}</strong></span>
                                <span class="rkp-chip"><span class="rkp-chip-k">渠道：</span><strong>${quotaLabel}</strong></span>
                                ${kw ? `<span class="rkp-chip"><span class="rkp-chip-k">检索：</span><strong>${kw}</strong></span>` : ''}
                                <span class="rkp-chip chip-count"><span class="rkp-chip-k">选入：</span><strong>${fundsToExport.length}</strong> / ${rankData.length} 只${isGroupedExport && nqExport.length > 0 && spExport.length > 0 ? ` (纳指 ${nqExport.length} · 标普 ${spExport.length})` : ''}</span>
                            </div>
                        </div>
                    </div>

                    <div class="rkp-table-wrap">
                        <table class="rkp-table">
                            <thead>
                                <tr>
                                    <th style="width:50px;">#</th>
                                    <th style="width:76px;">代码</th>
                                    <th class="col-name">基金标的</th>
                                    <th style="width:86px;">综合费率</th>
                                    <th style="width:115px;">跟踪误差 / IR</th>
                                    <th style="width:68px;">规模</th>
                                    <th style="width:82px;">近3年</th>
                                    <th style="width:65px;">晨星</th>
                                    <th style="width:150px;">限购(代/直)</th>
                                    <th style="width:76px;">综合评分</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${tableBodyHtml}
                            </tbody>
                        </table>
                    </div>

                    <div class="rkp-footer">
                        <div class="rkp-footer-brand">
                            <span class="rkp-brand-name">📊 Fund Advisor</span>
                            <span class="rkp-brand-tag">美股指数基金智能投资分析器 · 量化评分体系</span>
                        </div>
                        <div class="dbp-footer-meta">
                            <p>数据每日自动巡检更新 · 评分模型仅作客观量化参考</p>
                            <p>本文不构成任何投资建议与销售要约 · 基金有风险，投资需谨慎</p>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(posterWrap);
            const renderTarget = document.getElementById('rkp-render-target');

            const canvas = await renderPosterToCanvas(renderTarget, posterWrap, isLight, true);
            document.body.removeChild(posterWrap);
            const blob = await canvasToBlob(canvas);

            openPosterModal({
                blob,
                downloadFilename: `QDII量化评分榜_${type}_${isLight ? '浅色_' : ''}${todayStr}.png`,
                titleText: '全景对比表格图片预览',
                tagText: `${fundsToExport.length}只标的 · ${isLight ? '☀️ 浅色清新' : '🌙 深色商务'}`,
                currentTheme: exportTheme,
                onThemeChange: async (newTheme) => {
                    currentExportTheme = newTheme;
                    try { localStorage.setItem('fa_export_theme', newTheme); } catch (e) {}
                    await exportRankTablePoster(fundsToExport, null, newTheme);
                },
                successToast: '🎉 全景对比表格图片已生成，可直接保存或复制！'
            });

        } catch (err) {
            console.error('全景表格图片生成失败:', err);
            showToast('生成图片失败: ' + (err.message || '未知错误'), 'error');
        } finally {
            if (triggerBtn) {
                triggerBtn.disabled = false;
                triggerBtn.innerHTML = originalText;
            }
        }
    }

    function renderRankCards(data) {
        const container = document.getElementById('rank-card-list');
        if (!container) return;

        if (!data || data.length === 0) {
            container.innerHTML = `
                <div class="rank-card-empty">
                    <div style="font-size:2.2rem;margin-bottom:0.5rem">🔍</div>
                    <div style="font-weight:700;color:var(--txt);margin-bottom:0.35rem">未找到符合条件的基金标的</div>
                    <div style="font-size:0.8rem;color:var(--txt3);margin-bottom:1rem">请尝试调整份额类别、渠道状态或搜索关键词</div>
                    <button type="button" class="btn-empty-reset-card" style="padding:0.45rem 1.1rem;font-size:0.8rem;border-radius:8px;background:var(--accent-g);color:#fff;border:none;cursor:pointer;font-weight:600">🔄 恢复默认筛选</button>
                </div>
            `;
            const btn = container.querySelector('.btn-empty-reset-card');
            if (btn) btn.onclick = resetRankFilters;
            return;
        }

        container.innerHTML = data.map((r) => {
            const mgmt = r.mgmt_fee || 0;
            const cust = r.custody_fee || 0;
            const sales = r.sales_fee || 0;
            const totalFee = mgmt + cust + sales;
            const isLowFee = totalFee <= 0.007;
            const feePercent = (totalFee * 100).toFixed(2) + '%';
            
            // 限购状态判定
            const isPaused = ((r.limit_status || '').includes('暂停') || (r.limit_status || '').includes('未开通')) &&
                             ((r.direct_limit_status || '').includes('暂停') || (r.direct_limit_status || '').includes('未开通') || !r.direct_limit_status);

            // 排名奖章
            let rankBadgeHtml;
            if (r.rank === 1) {
                rankBadgeHtml = `<span class="fmc-rank rank-gold" title="综合评分冠军">🥇 1</span>`;
            } else if (r.rank === 2) {
                rankBadgeHtml = `<span class="fmc-rank rank-silver" title="综合评分亚军">🥈 2</span>`;
            } else if (r.rank === 3) {
                rankBadgeHtml = `<span class="fmc-rank rank-bronze" title="综合评分季军">🥉 3</span>`;
            } else {
                rankBadgeHtml = `<span class="fmc-rank">#${r.rank}</span>`;
            }

            // 指数类型微标签
            const idxTag = r.index_type === '纳斯达克100'
                ? `<span class="badge-idx badge-nq">纳指100</span>`
                : `<span class="badge-idx badge-sp">标普500</span>`;

            // 3年收益或成立以来收益
            let retHtml = '-';
            if (r.return_3yr != null) {
                retHtml = `<span class="fmc-ret up">${fmt(r.return_3yr)}</span>`;
            } else if (r.return_since != null) {
                retHtml = `<span class="fmc-ret up">${fmt(r.return_since)} <span class="fmc-ret-note">成立来</span></span>`;
            }

            // TD / IR 指标
            let tdIrHtml = '';
            if (r.tracking_difference != null) {
                const tdSign = r.tracking_difference >= 0 ? '+' : '';
                const tdColor = r.tracking_difference >= 0 ? 'var(--up)' : 'var(--down)';
                tdIrHtml += `<span style="color:${tdColor};font-weight:700">TD ${tdSign}${(r.tracking_difference*100).toFixed(1)}%</span>`;
            }
            if (r.information_ratio != null) {
                tdIrHtml += `${tdIrHtml ? ' · ' : ''}<span style="color:var(--txt2)">IR <strong>${r.information_ratio.toFixed(2)}</strong></span>`;
            }
            if (!tdIrHtml) {
                tdIrHtml = `<span style="color:var(--txt3)">TE ${(r.tracking_error ? (r.tracking_error*100).toFixed(2)+'%' : '-')}</span>`;
            }

            // 规模与晨星
            const scaleStr = r.scale ? `${r.scale.toFixed(1)}亿` : '-';
            const starStr = r.morningstar > 0 ? `<span class="fmc-stars" title="晨星${r.morningstar}星评级">${'★'.repeat(r.morningstar)}</span>` : '';

            // 同门兄弟份额看板
            let siblingListHtml = '';
            if (r.siblings && r.siblings.length > 1) {
                const sibFunds = r.siblings.map(sc => FUND_DATA.find(x => x.code === sc)).filter(Boolean);
                if (sibFunds.length > 1) {
                    siblingListHtml = `
                        <div class="fmc-siblings-block">
                            <div class="fmc-siblings-title">
                                <span>🔄 同门同标的各份额比对 (${r.family_name || '同一指数家族'})</span>
                                <span class="fmc-siblings-tip">点击切换</span>
                            </div>
                            <div class="fmc-siblings-grid">
                                ${sibFunds.map(sf => {
                                    const isSelf = sf.code === r.code;
                                    const sfTotal = (sf.mgmt_fee || 0) + (sf.custody_fee || 0) + (sf.sales_fee || 0);
                                    return `
                                        <div class="fmc-sibling-card ${isSelf ? 'active' : ''}" data-code="${sf.code}">
                                            <div class="sib-head">
                                                <div style="display:flex;align-items:center;gap:3px">
                                                    ${shareBadge(sf.share_class)}
                                                    <strong>${sf.code}</strong>
                                                </div>
                                                <span class="sib-fee">${(sfTotal * 100).toFixed(2)}%</span>
                                            </div>
                                            <div class="sib-limits">
                                                <span>代: ${pill(sf.limit_status)}</span>
                                                <span>直: ${sf.direct_limit_status ? pill(sf.direct_limit_status) : '<span style="color:var(--txt3)">—</span>'}</span>
                                            </div>
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    `;
                }
            }

            return `
                <div class="fund-mobile-card ${r.rank <= 3 ? 'top-card rank-' + r.rank : ''} ${isPaused ? 'paused-card' : ''}" data-code="${r.code}">
                    <!-- 卡片头部：排名、代码、指数、份额、评分 -->
                    <div class="fmc-header">
                        <div class="fmc-header-left">
                            ${rankBadgeHtml}
                            <span class="fmc-code">${r.code}</span>
                            <button type="button" class="btn-copy-code" data-code="${r.code}" title="复制基金代码">📋</button>
                            ${idxTag}
                            ${shareBadge(r.share_class)}
                        </div>
                        <div class="fmc-score-wrap">
                            <span class="fmc-score-label">量化评分</span>
                            <span class="fmc-score-val">${r.score}</span>
                        </div>
                    </div>

                    <!-- 基金主名称 -->
                    <div class="fmc-name-row">
                        <a href="/fund/${r.code}" class="fmc-title" data-code="${r.code}">${r.name}</a>
                        <a href="/fund/${r.code}" target="_blank" class="fmc-page-link" title="在新标签打开独立专页">评测专页 ↗</a>
                    </div>

                    <!-- 核心 4 宫格量化指标 -->
                    <div class="fmc-metrics-grid">
                        <div class="fmc-metric-item">
                            <div class="fmc-metric-lbl">综合年费</div>
                            <div class="fmc-metric-val" style="${feeC(totalFee)}">
                                ${feePercent}
                                ${isLowFee ? '<span class="fmc-pill-low">低费率</span>' : ''}
                            </div>
                        </div>
                        <div class="fmc-metric-item">
                            <div class="fmc-metric-lbl">近3年收益</div>
                            <div class="fmc-metric-val">
                                ${retHtml}
                            </div>
                        </div>
                        <div class="fmc-metric-item">
                            <div class="fmc-metric-lbl">跟踪偏离 / IR</div>
                            <div class="fmc-metric-val fmc-metric-val-sm">
                                ${tdIrHtml}
                            </div>
                        </div>
                        <div class="fmc-metric-item">
                            <div class="fmc-metric-lbl">规模 / 晨星</div>
                            <div class="fmc-metric-val">
                                <strong>${scaleStr}</strong>${starStr}
                            </div>
                        </div>
                    </div>

                    <!-- 渠道限购状态条 -->
                    <div class="fmc-quota-row">
                        <div class="fmc-quota-channels">
                            <div class="fmc-quota-chip">
                                <span class="fmc-channel-lbl">代销</span>
                                ${pill(r.limit_status)}
                            </div>
                            <div class="fmc-quota-chip">
                                <span class="fmc-channel-lbl">直销</span>
                                ${r.direct_limit_status ? pill(r.direct_limit_status) : '<span style="color:var(--txt3)">—</span>'}
                            </div>
                        </div>
                        ${r.quota_sharing === 'SHARED'
                            ? `<span class="badge-shared" title="${r.quota_shared_desc || '多类份额共享限额'}">🔗 共享额度</span>`
                            : (r.quota_sharing === 'INDEPENDENT'
                                ? `<span class="badge-indep" title="独立限额">独立额度</span>`
                                : '')}
                    </div>

                    <!-- 折叠抽屉：多因子明细与同门比对看板 -->
                    <div class="fmc-drawer" id="drawer-${r.code}">
                        <div class="fmc-drawer-content">
                            <!-- 费率拆解 -->
                            <div class="fmc-detail-section">
                                <div class="fmc-sec-title">💰 费率拆解明细</div>
                                <div class="fmc-detail-kv-grid">
                                    <div><span>管理费：</span><strong>${r.mgmt_fee ? (r.mgmt_fee*100).toFixed(2)+'%/年' : '-'}</strong></div>
                                    <div><span>托管费：</span><strong>${r.custody_fee ? (r.custody_fee*100).toFixed(2)+'%/年' : '-'}</strong></div>
                                    <div><span>销售服务费：</span><strong>${(r.sales_fee || 0) > 0 ? (r.sales_fee*100).toFixed(2)+'%/年' : '免收 (0%)'}</strong></div>
                                    <div><span>前端申购费：</span><strong>${r.purchase_fee != null ? (r.purchase_fee*100).toFixed(2)+'%' : '0.00%'}</strong></div>
                                </div>
                            </div>

                            <!-- 管理团队与规模 -->
                            <div class="fmc-detail-section">
                                <div class="fmc-sec-title">🏢 机构与基本信息</div>
                                <div class="fmc-detail-kv-grid">
                                    <div><span>基金管理人：</span><strong>${r.manager_company || '-'}</strong></div>
                                    <div><span>现任经理：</span><strong>${r.fund_manager || '-'}</strong></div>
                                    <div><span>托管机构：</span><strong>${r.custodian || '-'}</strong></div>
                                    <div><span>成立日期：</span><strong>${r.inception_date || '-'}</strong></div>
                                </div>
                            </div>

                            ${siblingListHtml}

                            <!-- 卡片快捷操作 -->
                            <div class="fmc-actions">
                                <a href="/fund/${r.code}" target="_blank" class="fmc-btn-act fmc-btn-primary">
                                    📄 打开独立深度评测专页 ↗
                                </a>
                                <button type="button" class="fmc-btn-act btn-sim-card-single" data-code="${r.code}">
                                    🚀 带入蒙特卡洛模拟器推演 ➔
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- 卡片底部展开/收起触控条 -->
                    <div class="fmc-expand-bar" data-code="${r.code}">
                        <span class="fmc-expand-text">展开深度指标与同门比对</span>
                        <span class="fmc-expand-arrow">▾</span>
                    </div>
                </div>
            `;
        }).join('');

        // 绑定卡片抽屉展开收起事件
        container.querySelectorAll('.fmc-expand-bar').forEach(bar => {
            bar.addEventListener('click', (e) => {
                e.stopPropagation();
                const card = bar.closest('.fund-mobile-card');
                if (!card) return;
                const isOpen = card.classList.toggle('expanded');
                const text = bar.querySelector('.fmc-expand-text');
                if (text) text.textContent = isOpen ? '收起详情指标' : '展开深度指标与同门比对';
            });
        });

        // 卡片整体点击（除链接和按钮外）支持展开/折叠
        container.querySelectorAll('.fund-mobile-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (e.target.closest('a, button, .btn-copy-code, .fmc-sibling-card, .fmc-expand-bar')) {
                    return;
                }
                const expandBar = card.querySelector('.fmc-expand-bar');
                if (expandBar) expandBar.click();
            });
        });

        // 绑定同门份额卡片点击切换或查看专页
        container.querySelectorAll('.fmc-sibling-card').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const sibCode = item.dataset.code;
                if (!sibCode) return;
                const targetCard = container.querySelector(`.fund-mobile-card[data-code="${sibCode}"]`);
                if (targetCard) {
                    targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    targetCard.classList.add('highlight-pulse');
                    if (!targetCard.classList.contains('expanded')) {
                        const expandBar = targetCard.querySelector('.fmc-expand-bar');
                        if (expandBar) expandBar.click();
                    }
                    setTimeout(() => targetCard.classList.remove('highlight-pulse'), 3000);
                } else {
                    window.open(`/fund/${sibCode}`, '_blank');
                }
            });
        });

        // 绑定单基金带入模拟器推演
        container.querySelectorAll('.btn-sim-card-single').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const c = btn.dataset.code;
                const f = FUND_DATA.find(x => x.code === c);
                if (f) {
                    loadFundsIntoSimulator({ [f.code]: 1.0 }, true, `${f.name} (单基推演)`);
                }
            });
        });
    }

    // ===== 模拟器 - 自定义多选 =====
    let msSelected = new Set();
    let msInited = false;

    function renderWeightSliders() {
        const container = document.getElementById('sim-weights-container');
        const listEl = document.getElementById('sim-weights-list');
        if (!container || !listEl) return;
        
        const codes = Array.from(msSelected);
        if (codes.length <= 1) {
            container.style.display = 'none';
            return;
        }
        
        container.style.display = 'block';
        
        // 如果已渲染过相同的基金列表，保留其权重值，否则初始化为等权重且总和为100
        const existingInputs = listEl.querySelectorAll('.sim-weight-row');
        const savedWeights = {};
        existingInputs.forEach(row => {
            savedWeights[row.dataset.code] = +row.querySelector('input').value;
        });
        
        const initialVal = Math.round(100 / codes.length);
        
        listEl.innerHTML = codes.map((code, idx) => {
            const fund = FUND_DATA.find(f => f.code === code);
            const name = fund ? fund.name : '';
            let val = savedWeights[code];
            if (val === undefined) {
                if (idx === codes.length - 1) {
                    val = 100 - (initialVal * (codes.length - 1));
                } else {
                    val = initialVal;
                }
            }
            return `
                <div class="sim-weight-row" data-code="${code}" style="display:flex; flex-direction:column; gap: 0.25rem;">
                    <div style="display:flex; justify-content:space-between; font-size:0.75rem;">
                        <span style="color:var(--txt); font-weight:500; text-overflow:ellipsis; overflow:hidden; white-space:nowrap; max-width:200px;">${code} ${name}</span>
                        <span class="sim-weight-val" style="color:var(--accent2); font-weight:700;">-</span>
                    </div>
                    <input type="range" class="sim-weight-input" min="0" max="100" step="1" value="${val}" style="width:100%; height:4px; opacity:0.8; cursor:pointer;">
                </div>
            `;
        }).join('');
        
        // 绑定事件实现滑块联动：拖动一个，其它按比例反向移动，总和严格等于100
        const inputs = listEl.querySelectorAll('.sim-weight-input');
        
        let startValues = {};
        const saveStartValues = () => {
            const currentRows = listEl.querySelectorAll('.sim-weight-row');
            currentRows.forEach(r => {
                const inp = r.querySelector('.sim-weight-input');
                startValues[r.dataset.code] = +inp.value;
            });
        };
        
        inputs.forEach(input => {
            // 在用户开始拖拽或聚焦时，记录当前所有滑块的基准初始值，防止在拖拽过程中不断取整累积误差导致“比例漂移” (Drift)
            input.addEventListener('mousedown', saveStartValues);
            input.addEventListener('touchstart', saveStartValues);
            input.addEventListener('focus', saveStartValues);
            
            input.addEventListener('input', e => {
                const targetInput = e.target;
                const targetRow = targetInput.closest('.sim-weight-row');
                const targetCode = targetRow.dataset.code;
                const newVal = +targetInput.value;
                
                const rows = listEl.querySelectorAll('.sim-weight-row');
                const otherRows = Array.from(rows).filter(r => r.dataset.code !== targetCode);
                if (otherRows.length === 0) return;
                
                const remaining = 100 - newVal;
                
                // 基于基准初始值按比例调整其它滑块
                const otherStartVals = otherRows.map(r => startValues[r.dataset.code] !== undefined ? startValues[r.dataset.code] : Math.round(100 / rows.length));
                const sumOtherStart = otherStartVals.reduce((a, b) => a + b, 0);
                
                if (sumOtherStart > 0) {
                    otherRows.forEach((r, idx) => {
                        const inputEl = r.querySelector('.sim-weight-input');
                        const startVal = otherStartVals[idx];
                        const share = startVal / sumOtherStart;
                        inputEl.value = Math.round(remaining * share);
                    });
                } else {
                    // 如果其它滑块起点全为0，则平分剩余份额
                    otherRows.forEach(r => {
                        const inputEl = r.querySelector('.sim-weight-input');
                        inputEl.value = Math.round(remaining / otherRows.length);
                    });
                }
                
                // 舍入微调，确保总和绝对等于100
                let currentSum = newVal + otherRows.reduce((s, r) => s + +r.querySelector('.sim-weight-input').value, 0);
                if (currentSum !== 100 && otherRows.length > 0) {
                    const adjustInput = otherRows[0].querySelector('.sim-weight-input');
                    adjustInput.value = +adjustInput.value + (100 - currentSum);
                }
                
                updateWeightDisplays();
            });
        });
        
        updateWeightDisplays();
    }
    
    function updateWeightDisplays() {
        const listEl = document.getElementById('sim-weights-list');
        if (!listEl) return;
        const rows = listEl.querySelectorAll('.sim-weight-row');
        if (rows.length === 0) return;
        
        const monthly = +document.getElementById('sim-m').value;
        
        rows.forEach(row => {
            const val = +row.querySelector('.sim-weight-input').value;
            const actMonthly = Math.round(monthly * (val / 100));
            
            const valEl = row.querySelector('.sim-weight-val');
            if (valEl) {
                valEl.textContent = `¥${actMonthly.toLocaleString('zh-CN')} (${val}%)`;
            }
        });
        updateSmartValuationGauge();
    }

    // ===== Top 4: 估值自适应智能定投 (Smart Dynamic DCA) 状态与仪表 =====
    const VALUATION_DATA = {
        nasdaq100: {
            name: '纳斯达克 100',
            current_pe: 31.8,
            pe_percentile: 0.645,
            status_tag: '合理偏高',
            status_color: '#d97706',
            base_multiplier: 0.90,
            pe_10y_median: 27.2
        },
        sp500: {
            name: '标普 500',
            current_pe: 26.4,
            pe_percentile: 0.682,
            status_tag: '合理偏高',
            status_color: '#d97706',
            base_multiplier: 0.88,
            pe_10y_median: 22.4
        }
    };
    let _smartDCASensitivity = 'standard';

    function calcSmartValuationMultiplier(percentile, sensitivity) {
        const bounds = {
            conservative: [0.8, 1.2, 0.8],
            standard: [0.6, 1.5, 1.5],
            aggressive: [0.5, 1.8, 2.2]
        };
        const [lowB, highB, k] = bounds[sensitivity] || bounds.standard;
        const dev = percentile - 0.50;
        const mult = 1.0 - k * dev;
        return Math.max(lowB, Math.min(highB, +mult.toFixed(2)));
    }

    function updateSmartValuationGauge() {
        const budgetInput = document.getElementById('sim-m');
        if (!budgetInput) return;
        const budget = +budgetInput.value || 2000;

        const listEl = document.getElementById('sim-weights-list');
        const rows = listEl ? listEl.querySelectorAll('.sim-weight-row') : [];
        let nqWeight = 0.5, spWeight = 0.5;

        if (rows.length > 0) {
            let totalW = 0, nqW = 0, spW = 0;
            rows.forEach(r => {
                const code = r.dataset.code;
                const val = +r.querySelector('.sim-weight-input')?.value || 0;
                const f = FUND_DATA.find(d => d.code === code);
                if (f) {
                    if ((f.index_type || '').includes('标普')) spW += val;
                    else nqW += val;
                    totalW += val;
                }
            });
            if (totalW > 0) {
                nqWeight = nqW / totalW;
                spWeight = spW / totalW;
            }
        }

        const nqMult = calcSmartValuationMultiplier(VALUATION_DATA.nasdaq100.pe_percentile, _smartDCASensitivity);
        const spMult = calcSmartValuationMultiplier(VALUATION_DATA.sp500.pe_percentile, _smartDCASensitivity);
        const blendedMult = +(nqWeight * nqMult + spWeight * spMult).toFixed(2);
        const recomMonthly = Math.round(budget * blendedMult);
        const diff = budget - recomMonthly;

        const recomBudgetEl = document.getElementById('vg-recom-budget');
        const recomSubEl = document.getElementById('vg-recom-sub');

        if (recomBudgetEl) {
            recomBudgetEl.innerHTML = `¥${recomMonthly.toLocaleString('zh-CN')} <span class="vg-sub">/ 月 (${blendedMult}x)</span>`;
        }
        if (recomSubEl) {
            if (diff > 0) {
                recomSubEl.textContent = `建议留存 ¥${diff.toLocaleString('zh-CN')}/月 备用金 (防守蓄力)`;
                recomSubEl.style.color = 'var(--ok)';
            } else if (diff < 0) {
                recomSubEl.textContent = `建议逆向加码 ¥${Math.abs(diff).toLocaleString('zh-CN')}/月 (低位吸筹)`;
                recomSubEl.style.color = 'var(--accent2)';
            } else {
                recomSubEl.textContent = `估值处于合理中枢，按基准 ¥${budget.toLocaleString('zh-CN')} 正常扣款`;
                recomSubEl.style.color = 'var(--txt2)';
            }
        }
    }

    function initSmartDCAToggle() {
        const toggle = document.getElementById('sim-smart-toggle');
        const panel = document.getElementById('sim-smart-panel');
        if (toggle && panel) {
            toggle.addEventListener('change', () => {
                panel.style.display = toggle.checked ? 'block' : 'none';
                if (toggle.checked) updateSmartValuationGauge();
            });
        }

        const sensTabs = document.getElementById('sim-sens-tabs');
        const sensBadge = document.getElementById('sens-desc-badge');
        if (sensTabs) {
            sensTabs.querySelectorAll('.sens-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    sensTabs.querySelectorAll('.sens-btn').forEach(b => b.classList.remove('on'));
                    btn.classList.add('on');
                    _smartDCASensitivity = btn.dataset.sens || 'standard';
                    if (sensBadge) {
                        const sensTexts = {
                            conservative: '🛡️ 稳健适度型 (0.8x ~ 1.2x)',
                            standard: '⚖️ 标准平衡型 (0.6x ~ 1.5x)',
                            aggressive: '🚀 逆向进取型 (0.5x ~ 1.8x)'
                        };
                        sensBadge.textContent = sensTexts[_smartDCASensitivity] || btn.textContent;
                    }
                    updateSmartValuationGauge();
                });
            });
        }
    }

    function initMultiSelect() {
        if (msInited) return;
        msInited = true;
        const trigger = document.getElementById('sim-sel-trigger');
        const dropdown = document.getElementById('sim-sel-dropdown');
        const list = document.getElementById('sim-sel-list');
        const search = document.getElementById('sim-sel-search');
        const textEl = document.getElementById('sim-sel-text');

        function feeStr(f) { return (((f.mgmt_fee||0)+(f.custody_fee||0)+(f.sales_fee||0))*100).toFixed(2) + '%'; }
        function renderList(filter) {
            const q = (filter || '').toLowerCase();
            const nqMedianTE = calcMedianTE(FUND_DATA.filter(f => f.index_type === '纳斯达克100'));
            const spMedianTE = calcMedianTE(FUND_DATA.filter(f => f.index_type === '标普500'));
            const items = FUND_DATA.map(f => ({
                ...f,
                score: scoreFund(f, f.index_type === '标普500' ? spMedianTE : nqMedianTE)
            })).filter(f => {
                if (!q) return true;
                return f.code.includes(q) || f.name.toLowerCase().includes(q) || (f.family_name || '').toLowerCase().includes(q);
            }).sort((a, b) => {
                // 先按指数类型分组：纳斯达克100在前，标普500在后
                const typeOrder = { '纳斯达克100': 0, '标普500': 1 };
                const ta = typeOrder[a.index_type] ?? 2;
                const tb = typeOrder[b.index_type] ?? 2;
                if (ta !== tb) return ta - tb;
                // 同类型内按评分降序
                return b.score - a.score;
            });

            // 生成带分组标题的列表
            let html = '';
            let lastType = '';
            let rankInGroup = 0;
            items.forEach(f => {
                if (f.index_type !== lastType) {
                    lastType = f.index_type;
                    rankInGroup = 0;
                    html += `<div style="padding:6px 12px;font-size:0.75rem;font-weight:700;color:var(--accent2);background:var(--bg);position:sticky;top:0;z-index:1;border-bottom:1px solid var(--border)">${f.index_type || '其他'}</div>`;
                }
                rankInGroup++;
                const sel = msSelected.has(f.code) ? ' selected' : '';
                html += `<div class="ms-opt${sel}" data-code="${f.code}">
                    <div class="ms-cb"></div>
                    <div class="ms-opt-info">
                        <div class="ms-opt-name"><span class="ms-opt-rank">#${rankInGroup}</span> ${shareBadge(f.share_class)} ${f.code} ${f.name}</div>
                        <div class="ms-opt-meta">评分 <strong style="color:var(--accent2)">${f.score}</strong> · 综合年费 ${feeStr(f)} · 申购 ${(f.purchase_fee*100).toFixed(2)}% · ${f.index_type}</div>
                    </div>
                </div>`;
            });
            list.innerHTML = html;
            bindOptClick();
        }

        function bindOptClick() {
            list.querySelectorAll('.ms-opt').forEach(opt => {
                opt.addEventListener('click', () => {
                    const code = opt.dataset.code;
                    if (msSelected.has(code)) msSelected.delete(code); else msSelected.add(code);
                    opt.classList.toggle('selected');
                    updateText();
                });
            });
        }

        function updateText() {
            if (msSelected.size === 0) {
                textEl.textContent = '点击选择基金（可多选）';
                textEl.style.color = '';
            } else {
                textEl.innerHTML = `<span class="ms-count">${msSelected.size}</span> 只基金已选中`;
                textEl.style.color = 'var(--txt)';
            }
            renderWeightSliders();
        }

        trigger.addEventListener('click', e => {
            if (e.target.closest('.ms-dropdown')) return;
            const isOpen = dropdown.classList.contains('show');
            dropdown.classList.toggle('show');
            trigger.classList.toggle('open');
            if (!isOpen) { search.value = ''; renderList(''); search.focus(); }
        });

        document.addEventListener('click', e => {
            if (!e.target.closest('.ms-wrap')) {
                dropdown.classList.remove('show');
                trigger.classList.remove('open');
            }
        });

        search.addEventListener('input', () => renderList(search.value));
        document.getElementById('sim-sel-all').addEventListener('click', e => {
            e.stopPropagation();
            FUND_DATA.forEach(f => msSelected.add(f.code));
            renderList(search.value);
            updateText();
        });
        document.getElementById('sim-sel-clear').addEventListener('click', e => {
            e.stopPropagation();
            msSelected.clear();
            renderList(search.value);
            updateText();
        });
    }

    function populateSimSelect() { initMultiSelect(); }

    async function runSimulation() {
        const codes = Array.from(msSelected);
        if (!codes.length) { alert('请至少选择一只基金'); return; }
        const btn = document.getElementById('btn-sim');
        btn.disabled = true; btn.textContent = '模拟中…';

        // 异步以防止UI阻塞
        await new Promise(r => setTimeout(r, 50));

        try {
            const monthlyEl = document.getElementById('sim-m');
            const yearsEl = document.getElementById('sim-y');
            const monthly = Math.max(500, parseInt(monthlyEl.value) || parseInt(monthlyEl.defaultValue) || 2000);
            const years = Math.max(5, parseInt(yearsEl.value) || parseInt(yearsEl.defaultValue) || 20);
            const funds = codes.map(c => FUND_DATA.find(f => f.code === c)).filter(Boolean);

            if (!funds.length) {
                document.getElementById('sim-result').innerHTML = '<p style="color:var(--err);text-align:center;padding:2rem">未找到选中的基金</p>';
                btn.disabled = false; btn.textContent = '运行模拟';
                return;
            }

            // 获取定投占比权重
            const weights = [];
            const listEl = document.getElementById('sim-weights-list');
            const rows = listEl ? listEl.querySelectorAll('.sim-weight-row') : [];
            if (funds.length <= 1 || rows.length === 0) {
                funds.forEach(() => weights.push(1 / funds.length));
            } else {
                const relWeights = Array.from(rows).map(row => +row.querySelector('.sim-weight-input').value);
                const totalRel = relWeights.reduce((s, w) => s + w, 0);
                relWeights.forEach(rw => {
                    weights.push(totalRel > 0 ? rw / totalRel : 1 / funds.length);
                });
            }

            const isSmartDCA = !!document.getElementById('sim-smart-toggle')?.checked;
            const result = await simulateViaWorker(funds, weights, years, monthly, await getDynamicParams(), isSmartDCA, _smartDCASensitivity);

            // 显示预算分配说明
            let allocNote = '';
            if (funds.length > 1) {
                allocNote += `<p style="color:var(--txt3);font-size:.75rem;margin-bottom:.75rem">资金分配比例：<br>`;
                funds.forEach((f, i) => {
                    const pct = Math.round(weights[i] * 100);
                    const allocated = Math.round(monthly * weights[i]);
                    allocNote += `· ${f.code} ${f.name}: <strong>${pct}%</strong> (约 ¥${allocated}/月)<br>`;
                });
                allocNote += `</p>`;
            }

            // ===== 智能估值定投双轨展示模式 =====
            if (result.isDualTrack) {
                const std = result.standard;
                const smart = result.smart;
                const alpha = result.alpha;

                const sensNameMap = {
                    conservative: '🛡️ 稳健适度型 (0.8x~1.2x)',
                    standard: '⚖️ 标准平衡型 (0.6x~1.5x)',
                    aggressive: '🚀 逆向进取型 (0.5x~1.8x)'
                };
                const currentSensName = sensNameMap[_smartDCASensitivity] || '标准平衡型';

                let downsideRibbonHtml = '';
                if (smart.maxLossP50 != null || smart.mddP50 != null) {
                    const lossP50 = smart.maxLossP50;
                    const lossP95 = smart.maxLossP95;
                    const mddP50 = smart.mddP50;
                    const mddP95 = smart.mddP95;
                    const recMo = smart.recoveryMonths || 10;
                    const sortino = smart.sortinoRatio != null ? smart.sortinoRatio.toFixed(2) : null;
                    const lossImprove = alpha.maxLossReduction > 0 ? `(相比普通定投浮亏收窄 +${alpha.maxLossReduction}%)` : '';

                    downsideRibbonHtml = `
                    <div class="sim-downside-ribbon" style="border-color:rgba(99,102,241,0.25)">
                        <div class="sim-downside-title">
                            <div style="display:flex;align-items:center;gap:6px">
                                <span class="sim-downside-badge">⚡ 智能定投风控体检</span>
                                <span style="font-size:0.8rem;font-weight:600;color:var(--txt)">价值平均法压力测试与下行护航</span>
                            </div>
                            ${sortino ? `<span style="font-size:0.75rem;color:var(--txt2)">索提诺比率: <strong style="color:var(--ok)">${sortino}</strong></span>` : ''}
                        </div>
                        <div class="sim-downside-grid">
                            <div class="sim-downside-item">
                                <span class="lb">典型账面最大浮亏</span>
                                <span class="vl" style="color:var(--err)">-${lossP50}% <span style="font-size:0.7rem;color:var(--txt3);font-weight:normal">${lossImprove}</span></span>
                            </div>
                            <div class="sim-downside-item">
                                <span class="lb">峰值资产最大回撤</span>
                                <span class="vl" style="color:var(--warn)">-${mddP50}% <span style="font-size:0.7rem;color:var(--txt3);font-weight:normal">(95%极限 -${mddP95}%)</span></span>
                            </div>
                            <div class="sim-downside-item">
                                <span class="lb">典型修复周期</span>
                                <span class="vl" style="color:var(--accent2)">~${recMo} <span style="font-size:0.7rem;font-weight:normal">个月</span></span>
                            </div>
                        </div>
                        <div class="sim-downside-summary">
                            💡 <strong>智能调权红利：</strong>在 ${years} 年定投周期内，智能估值定投通过在恐慌低位大幅加买摊低每股成本，使典型最大浮亏控制在 <strong>-${lossP50}%</strong>，中位复利收益多贡献了 <strong>+${money(alpha.wealthGain)}</strong> 的超额财富 Alpha！
                        </div>
                    </div>`;
                }

                const maxFinalVal = Math.max(smart.p95, std.p95, 1);
                const pLevels = [
                    { name: '5% 极度悲观', desc: '极端长熊底线', stdVal: std.p5, smartVal: smart.p5, color: '#ef4444' },
                    { name: '25% 周期偏弱', desc: '弱势震荡市', stdVal: std.p25, smartVal: smart.p25, color: '#f59e0b' },
                    { name: '50% 典型中位', desc: '基准概率预期', stdVal: std.medianFinal, smartVal: smart.medianFinal, color: '#6366f1', isMedian: true },
                    { name: '75% 顺风良好', desc: '稳健牛市行情', stdVal: std.p75, smartVal: smart.p75, color: '#10b981' },
                    { name: '95% 极度乐观', desc: '超级大牛市顶点', stdVal: std.p95, smartVal: smart.p95, color: '#06b6d4' }
                ];

                let dualPercentileRowsHtml = pLevels.map(pl => {
                    const stdPct = Math.min(100, Math.max(8, Math.round((pl.stdVal / maxFinalVal) * 100)));
                    const smartPct = Math.min(100, Math.max(8, Math.round((pl.smartVal / maxFinalVal) * 100)));
                    const diff = pl.smartVal - pl.stdVal;
                    const diffPct = ((pl.smartVal / pl.stdVal - 1) * 100).toFixed(1);
                    return `
                    <div class="dual-percentile-row" style="${pl.isMedian ? 'border-color:rgba(99,102,241,0.4);background:rgba(99,102,241,0.06)' : ''}">
                        <div class="dual-percentile-head">
                            <span style="font-weight:600;color:var(--txt)">
                                ${pl.name}
                                <span style="font-size:0.7rem;color:var(--txt3);font-weight:normal;margin-left:4px">(${pl.desc})</span>
                            </span>
                            <span style="font-size:0.72rem;color:${diff >= 0 ? 'var(--ok)' : 'var(--txt3)'};font-weight:600">
                                智能定投超额: ${diff >= 0 ? '+' : ''}${money(diff)} (${diff >= 0 ? '+' : ''}${diffPct}%)
                            </span>
                        </div>
                        <div class="dual-bar-pair">
                            <div class="dual-bar-sub">
                                <span class="track-tag">普通固定:</span>
                                <div class="bar-outer"><div class="bar-inner" style="width:${stdPct}%;background:#94a3b8"></div></div>
                                <span class="bar-val" style="color:var(--txt2)">${money(pl.stdVal)}</span>
                            </div>
                            <div class="dual-bar-sub">
                                <span class="track-tag" style="color:var(--accent2);font-weight:600">⚡ 智能估值:</span>
                                <div class="bar-outer"><div class="bar-inner" style="width:${smartPct}%;background:${pl.color}"></div></div>
                                <span class="bar-val" style="color:var(--ok)">${money(pl.smartVal)}</span>
                            </div>
                        </div>
                    </div>`;
                }).join('');

                document.getElementById('sim-result').innerHTML = `
                    ${allocNote}
                    <div class="dual-track-header">
                        <div style="display:flex;align-items:center;gap:6px">
                            <span style="font-size:1.1rem">⚡</span>
                            <strong style="font-size:0.875rem;color:var(--txt)">双轨蒙特卡洛模拟：普通固定定投 vs 智能估值定投</strong>
                        </div>
                        <span class="tag" style="background:rgba(99,102,241,0.12);color:var(--accent2);font-size:0.72rem;font-weight:600">
                            当前档位：${currentSensName}
                        </span>
                    </div>

                    <div class="dual-kpi-grid">
                        <div class="dual-kpi-card" style="border-color:rgba(16,185,129,0.3);background:linear-gradient(180deg, var(--surface2) 0%, rgba(16,185,129,0.06) 100%)">
                            <div class="dk-label">中位数财富终值</div>
                            <div class="dk-vals">
                                <span class="dk-val-smart">${money(smart.medianFinal)}</span>
                                <span class="dk-val-std">${money(std.medianFinal)}</span>
                            </div>
                            <div class="dk-diff" style="color:var(--ok)">+${money(alpha.wealthGain)} (+${alpha.wealthGainPct}%)</div>
                        </div>

                        <div class="dual-kpi-card" style="border-color:rgba(99,102,241,0.3);background:linear-gradient(180deg, var(--surface2) 0%, rgba(99,102,241,0.06) 100%)">
                            <div class="dk-label">年化复合收益率 (CAGR)</div>
                            <div class="dk-vals">
                                <span class="dk-val-smart" style="color:var(--accent2)">${smart.annualReturn}%</span>
                                <span class="dk-val-std">${std.annualReturn}%</span>
                            </div>
                            <div class="dk-diff" style="color:var(--accent2)">Alpha 提升 +${alpha.cagrGain}%</div>
                        </div>

                        <div class="dual-kpi-card">
                            <div class="dk-label">实际平均总本金</div>
                            <div class="dk-vals">
                                <span class="dk-val-smart" style="color:var(--txt)">${money(smart.totalInvested)}</span>
                                <span class="dk-val-std">${money(std.totalInvested)}</span>
                            </div>
                            <div class="dk-diff" style="color:var(--txt2)">
                                ROI乘数: <strong style="color:var(--ok)">${smart.roiMultiple}x</strong> (普通 ${std.roiMultiple}x)
                            </div>
                        </div>

                        <div class="dual-kpi-card">
                            <div class="dk-label">资金使用效率提升</div>
                            <div class="dk-vals">
                                <span class="dk-val-smart" style="color:#d97706">+${alpha.efficiencyGainPct}%</span>
                            </div>
                            <div class="dk-diff" style="color:var(--txt3)">
                                单笔本金创造的终值效率
                            </div>
                        </div>
                    </div>

                    ${downsideRibbonHtml}

                    <div style="margin-top:1rem">
                        <div style="font-size:0.8rem;font-weight:700;color:var(--txt);margin-bottom:0.6rem;display:flex;align-items:center;gap:6px">
                            <span>📊</span> 分位收益双轨对比明细 (成对抽样消除随机误差)
                        </div>
                        ${dualPercentileRowsHtml}
                    </div>
                `;

                if (chartPool.sim) chartPool.sim.destroy();
                chartPool.sim = new Chart(document.getElementById('ch-sim'), {
                    type: 'bar',
                    data: {
                        labels: ['5% 悲观', '25% 偏弱', '50% 中位', '75% 顺风', '95% 乐观'],
                        datasets: [
                            {
                                label: '普通固定定投 (万元)',
                                data: [std.p5/10000, std.p25/10000, std.medianFinal/10000, std.p75/10000, std.p95/10000],
                                backgroundColor: '#94a3b8',
                                borderRadius: 5,
                                borderSkipped: false
                            },
                            {
                                label: '⚡ 智能估值定投 (Alpha)',
                                data: [smart.p5/10000, smart.p25/10000, smart.medianFinal/10000, smart.p75/10000, smart.p95/10000],
                                backgroundColor: ['#ef4444', '#f59e0b', '#6366f1', '#10b981', '#06b6d4'],
                                borderRadius: 5,
                                borderSkipped: false
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top',
                                labels: { font: { size: 11 }, boxWidth: 14 }
                            }
                        },
                        scales: {
                            x: { grid: { display: false } },
                            y: { title: { display: true, text: '万元' }, grid: { color: 'rgba(99, 102, 241, 0.08)' } }
                        }
                    }
                });
                btn.disabled = false; btn.textContent = '运行模拟';
                return;
            }

            const invested = result.totalInvested || (monthly * years * 12);
            const medianVal = result.medianFinal || 0;
            const profit = medianVal - invested;
            const profitMultiple = (invested > 0 ? (medianVal / invested).toFixed(1) : '1.0') + 'x';
            const maxVal = Math.max(result.p95 || 1, 1);

            const percentiles = [
                { key: 'p5', name: '5% 极度悲观', desc: '长熊低迷与黑天鹅底线', val: result.p5, color: '#f87171' },
                { key: 'p25', name: '25% 市场保守', desc: '周期性调整偏弱行情', val: result.p25, color: '#fbbf24' },
                { key: 'p50', name: '50% 典型中位', desc: '最可能达成的基准预期', val: result.medianFinal, color: '#6366f1', isMedian: true },
                { key: 'p75', name: '75% 良好发展', desc: '顺风市场与稳健牛市', val: result.p75, color: '#34d399' },
                { key: 'p95', name: '95% 极度乐观', desc: '繁荣超级大牛市顶点', val: result.p95, color: '#22d3ee' }
            ];

            let pListHtml = percentiles.map(p => {
                const pctOfMax = Math.min(100, Math.max(10, Math.round((p.val / maxVal) * 100)));
                const mult = invested > 0 ? (p.val / invested).toFixed(1) + 'x 本金' : '';
                return `
                <div class="sim-percentile-item" style="${p.isMedian ? 'border-color:rgba(99,102,241,0.4);background:rgba(99,102,241,0.06)' : ''}">
                    <div class="sim-percentile-header">
                        <span class="sim-percentile-name" style="color:${p.color}">
                            <span>●</span> ${p.name}
                            <span style="font-size:0.7rem;color:var(--txt3);font-weight:normal;margin-left:4px">(${p.desc})</span>
                        </span>
                        <span class="sim-percentile-val" style="${p.isMedian ? 'color:var(--accent2)' : ''}">
                            ${money(p.val)}
                            <span class="sim-percentile-multiple">(${mult})</span>
                        </span>
                    </div>
                    <div class="sim-bar-wrap">
                        <div class="sim-bar" style="width:${pctOfMax}%;background:${p.color}"></div>
                    </div>
                </div>
                `;
            }).join('');

            let downsideRibbonHtml = '';
            if (result.maxLossP50 != null || result.mddP50 != null) {
                const lossP50 = result.maxLossP50 != null ? result.maxLossP50 : '-';
                const lossP95 = result.maxLossP95 != null ? result.maxLossP95 : '-';
                const mddP50 = result.mddP50 != null ? result.mddP50 : '-';
                const mddP95 = result.mddP95 != null ? result.mddP95 : '-';
                const recMo = result.recoveryMonths || 10;
                const sortino = result.sortinoRatio != null ? result.sortinoRatio.toFixed(2) : null;

                downsideRibbonHtml = `
                <div class="sim-downside-ribbon">
                    <div class="sim-downside-title">
                        <div style="display:flex;align-items:center;gap:6px">
                            <span class="sim-downside-badge">🛡️ 抗跌与回撤体检</span>
                            <span style="font-size:0.8rem;font-weight:600;color:var(--txt)">定投压力测试与下行风控评估</span>
                        </div>
                        ${sortino ? `<span style="font-size:0.75rem;color:var(--txt2)">索提诺比率: <strong style="color:var(--ok)">${sortino}</strong> <span style="font-size:0.7rem;color:var(--txt3)">(仅惩罚下行波动)</span></span>` : ''}
                    </div>
                    <div class="sim-downside-grid">
                        <div class="sim-downside-item">
                            <span class="lb">账面本金最大浮亏</span>
                            <span class="vl" style="color:var(--err)">-${lossP50}% <span style="font-size:0.72rem;color:var(--txt3);font-weight:normal">(95%极限 -${lossP95}%)</span></span>
                        </div>
                        <div class="sim-downside-item">
                            <span class="lb">峰值资产最大回撤</span>
                            <span class="vl" style="color:var(--warn)">-${mddP50}% <span style="font-size:0.72rem;color:var(--txt3);font-weight:normal">(95%极限 -${mddP95}%)</span></span>
                        </div>
                        <div class="sim-downside-item">
                            <span class="lb">典型净值修复周期</span>
                            <span class="vl" style="color:var(--accent2)">~${recMo} <span style="font-size:0.72rem;font-weight:normal">个月</span></span>
                        </div>
                    </div>
                    <div class="sim-downside-summary">
                        💡 <strong>压力测试结论：</strong>在 95% 置信度下，您在 ${years} 年定投期间<strong>最大账面浮亏预计不超过 ${lossP95}%</strong>，且遭遇深度回调时通常可在 <strong>${recMo} 个月内</strong>通过持续买入摊平成本修复净值。
                    </div>
                </div>`;
            }

            document.getElementById('sim-result').innerHTML = `
                ${allocNote}
                <div class="sim-kpi-grid">
                    <div class="sim-kpi-card">
                        <div class="sim-kpi-label">累计本金投入</div>
                        <div class="sim-kpi-value">${money(invested)}</div>
                        <div class="sim-kpi-sub">¥${monthly}/月 × ${years}年</div>
                    </div>
                    <div class="sim-kpi-card" style="border-color:rgba(16,185,129,0.3);background:linear-gradient(180deg, var(--surface2) 0%, rgba(16,185,129,0.06) 100%)">
                        <div class="sim-kpi-label">中位数终值预期</div>
                        <div class="sim-kpi-value" style="color:var(--ok)">${money(medianVal)}</div>
                        <div class="sim-kpi-sub" style="color:var(--ok);font-weight:600">收益 +${money(profit)} (${profitMultiple})</div>
                    </div>
                    <div class="sim-kpi-card" style="border-color:rgba(99,102,241,0.3);background:linear-gradient(180deg, var(--surface2) 0%, rgba(99,102,241,0.06) 100%)">
                        <div class="sim-kpi-label">年化复合收益 (CAGR)</div>
                        <div class="sim-kpi-value" style="color:var(--accent2)">${result.annualReturn}%</div>
                        <div class="sim-kpi-sub">平滑复利中位数</div>
                    </div>
                </div>
                ${downsideRibbonHtml}
                <div class="sim-percentile-list">
                    ${pListHtml}
                </div>`;

            if (chartPool.sim) chartPool.sim.destroy();
            chartPool.sim = new Chart(document.getElementById('ch-sim'), {
                type: 'bar',
                data: {
                    labels: ['5% 悲观', '25%', '中位数', '75%', '95% 乐观'],
                    datasets: [{
                        label: '终值 (万元)',
                        data: [result.p5/10000, result.p25/10000, result.medianFinal/10000, result.p75/10000, result.p95/10000],
                        backgroundColor: ['#f87171','#fbbf24','#6366f1','#34d399','#22d3ee'],
                        borderRadius: 6,
                        borderSkipped: false,
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false } },
                        y: { title: { display: true, text: '万元' }, grid: { color: 'rgba(99, 102, 241, 0.08)' } }
                    }
                }
            });
        } catch (e) {
            document.getElementById('sim-result').innerHTML = `<p style="color:var(--err);text-align:center;padding:2rem">模拟失败: ${e.message}</p>`;
        }
        btn.disabled = false; btn.textContent = '运行模拟';
    }

    // ===== 定投方案 =====
    // pfCharts declared at top level

    function renderVariantTable(variant, prefix) {
        if (!variant) return '';
        const allocs = variant.allocations || [];
        const hasShared = allocs.some(a => a.quota_sharing === 'SHARED');
        const rows = allocs.map(a => `<tr class="${a.exceeds_limit ? 'wr' : ''}">
            <td class="pf-col-code" style="color:var(--txt2)">${a.code}</td>
            <td class="pf-col-name" style="text-align:left;font-weight:500">
                <div class="pf-name-cell">
                    ${shareBadge(a.share_class)}
                    <span class="pf-fund-name" title="${a.name}">${a.name}</span>
                    ${a.is_stacked ? '<span class="badge-stacked" title="额度用尽时自动补充的优质份额">额度叠加</span>' : ''}
                </div>
            </td>
            <td class="pf-col-fee" style="${feeC(a.fee)}">${(a.fee*100).toFixed(2)}%</td>
            <td class="pf-col-daily">${a.daily}元</td>
            <td class="pf-col-monthly" style="font-weight:600">${a.monthly}元</td>
            <td class="pf-col-weight">${(a.actual_weight*100).toFixed(0)}%</td>
            <td class="pf-col-limit">
                <div class="pf-limit-cell">
                    <div>${pill(a.limit_status)}</div>
                    ${a.direct_limit_status ? `<div>${pill(a.direct_limit_status)}</div>` : ''}
                    ${a.quota_sharing === 'SHARED' ? `<div style="margin-top:2px"><span class="badge-shared" style="font-size:0.65rem;padding:1px 5px;border-radius:4px;background:rgba(245,158,11,0.15);color:var(--warn);border:1px solid rgba(245,158,11,0.3);white-space:nowrap;display:inline-block;cursor:help" title="${a.quota_shared_desc || '多类份额共享限额'}">🔗 共享额度</span></div>` : ''}
                </div>
            </td>
        </tr>`).join('');
        let html = `<div class="table-wrap pf-table-wrap"><table class="pf-table"><thead><tr><th class="pf-col-code">代码</th><th class="pf-col-name">名称</th><th class="pf-col-fee">综合费率</th><th class="pf-col-daily">每日</th><th class="pf-col-monthly">月合计</th><th class="pf-col-weight">占比</th><th class="pf-col-limit">代销/直销</th></tr></thead><tbody>${rows}</tbody></table></div>`;
        if (hasShared) {
            html += `<div style="margin-top:0.6rem;padding:0.5rem 0.75rem;background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.22);border-radius:6px;font-size:0.75rem;color:var(--txt2);line-height:1.5">
                <span style="color:var(--warn);font-weight:600">💡 共享额度避坑提示：</span>
                标有 <span style="color:var(--warn);font-weight:600">🔗 共享额度</span> 的基金，其 A 类与 C 类（及定制份额）由基金公司合并控制单日申购限额。若您已在其他渠道定投同门份额，切勿重复定投，以免超过合并上限导致银行扣款失败。
            </div>`;
        }
        return html;
    }

    function renderVariantDonut(variant, s, vk) {
        if (!variant) return '';
        const allocs = variant.allocations || [];
        const totalMonthly = allocs.reduce((sum, a) => sum + (a.monthly || 0), 0);
        const weightedFee = totalMonthly > 0 ? allocs.reduce((sum, a) => sum + (a.fee || 0) * (a.monthly || 0), 0) / totalMonthly : 0;
        const directAvail = allocs.filter(a => a.direct_limit_status && !a.direct_limit_status.includes('暂停')).length;
        const channelText = directAvail > 0 ? '代销 + 直销' : '主流代销';

        // 生成精致的 HTML 图例：12px 适度字号、两列紧凑网格、彻底杜绝 Canvas 裁剪与圆环挤压
        const pieColors = ['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#f43f5e', '#06b6d4'];
        const legendItems = allocs.map((a, i) => {
            const color = pieColors[i % pieColors.length];
            const cleanName = (a.name || '').replace(/[（(]QDII[）)]/gi, '').trim();
            const pct = Math.round((a.actual_weight || a.weight || (totalMonthly > 0 ? a.monthly / totalMonthly : 0)) * 100);
            return `
            <div class="pf-legend-item" title="${a.name} (${pct}% · ${a.monthly}元/月)">
                <span class="pf-legend-dot" style="background:${color}"></span>
                <span class="pf-legend-name">${cleanName}</span>
                <span class="pf-legend-pct">${pct}%</span>
            </div>`;
        }).join('');

        return `
        <div class="pf-donut-box">
            <div class="pf-donut-header">
                <div class="pf-donut-title-wrap">
                    <span class="pf-donut-title">🎯 资产配置配比</span>
                </div>
                <div class="pf-donut-budget-pill">月定投: <strong>${money(totalMonthly)}</strong></div>
            </div>
            
            <div class="cht pf-cht"><canvas id="ch-${s.key}-${vk}"></canvas></div>

            <div class="pf-donut-legend ${allocs.length > 2 ? 'is-multi' : ''}">
                ${legendItems}
            </div>

            <div class="pf-donut-metrics">
                <div class="pf-donut-metric-item">
                    <div class="lb">加权综合费率</div>
                    <div class="vl" style="${feeC(weightedFee)}">${(weightedFee * 100).toFixed(2)}%</div>
                </div>
                <div class="pf-donut-metric-item">
                    <div class="lb">配置标的数</div>
                    <div class="vl" style="color:var(--txt)">${allocs.length} 只基金</div>
                </div>
                <div class="pf-donut-metric-item">
                    <div class="lb">购买渠道覆盖</div>
                    <div class="vl" style="color:var(--txt)">${channelText}</div>
                </div>
            </div>
        </div>`;
    }

    function renderVariantSim(variant, years) {
        const sim = variant?.simulation;
        if (!sim) return '';

        let downsideCardHtml = '';
        if (sim.maxLossP50 != null || sim.mddP50 != null) {
            const lossP50 = sim.maxLossP50 != null ? sim.maxLossP50 : '-';
            const lossP95 = sim.maxLossP95 != null ? sim.maxLossP95 : '-';
            const mddP50 = sim.mddP50 != null ? sim.mddP50 : '-';
            const mddP95 = sim.mddP95 != null ? sim.mddP95 : '-';
            const recMo = sim.recoveryMonths || 10;
            const sortino = sim.sortinoRatio != null ? sim.sortinoRatio.toFixed(2) : (variant?.risk_analysis?.sortino_ratio != null ? variant.risk_analysis.sortino_ratio.toFixed(2) : null);

            downsideCardHtml = `
            <div class="downside-assessment-card">
                <div class="downside-card-header">
                    <div class="downside-card-title">
                        <span class="downside-shield-icon">🛡️</span>
                        <span style="font-weight:600;font-size:0.8rem;color:var(--txt)">定投抗跌与回撤体检表</span>
                        <span class="downside-badge">压力测试</span>
                    </div>
                    ${sortino ? `<div class="downside-sortino-pill" title="索提诺比率：仅对净值下跌负波动进行惩罚，真实反映抗跌超额性价比">索提诺比率: <strong>${sortino}</strong></div>` : ''}
                </div>
                <div class="downside-kpi-grid">
                    <div class="downside-kpi-box">
                        <div class="lb">典型账面最大浮亏 (P50)</div>
                        <div class="vl" style="color:var(--err)">-${lossP50}%</div>
                        <div class="sub">半数路径下的本金回撤底线</div>
                    </div>
                    <div class="downside-kpi-box">
                        <div class="lb">95% 极端账面浮亏 (P95)</div>
                        <div class="vl" style="color:var(--err);font-weight:700">-${lossP95}%</div>
                        <div class="sub">95% 置信度极限压力边界</div>
                    </div>
                    <div class="downside-kpi-box">
                        <div class="lb">峰值最大回撤 (P50/P95)</div>
                        <div class="vl" style="color:var(--warn)">-${mddP50}% <span style="font-size:0.75rem;color:var(--txt3);font-weight:normal">/ -${mddP95}%</span></div>
                        <div class="sub">利润垫回吐与高点回落</div>
                    </div>
                    <div class="downside-kpi-box">
                        <div class="lb">典型回撤修复期</div>
                        <div class="vl" style="color:var(--accent2)">~${recMo} <span style="font-size:0.75rem;font-weight:normal">个月</span></div>
                        <div class="sub">定投摊平成本并创新高周期</div>
                    </div>
                </div>
                <div class="downside-psychology-tip">
                    💡 <strong>心理定心丸：</strong>在 95% 置信度下，您在 ${years} 年定投长跑中遭遇的<strong>账面本金最大浮亏不超过 ${lossP95}%</strong>，远低于一次性买入（>40%）的心理崩盘风险，且通常在 <strong>${recMo} 个月内</strong>通过分批现金流摊平修复。
                </div>
            </div>`;
        }

        return `
        <div class="pf-sim-card">
            <div class="pf-card-head">
                <div class="pf-card-title">
                    <span style="font-size:0.95rem">📈</span>
                    <span style="font-weight:600;font-size:0.825rem;color:var(--txt)">长期定投复利预期 (${years}年)</span>
                </div>
                <div class="pf-pill-accent">
                    预期年化: <strong style="color:var(--accent2)">${sim.annualReturn}%</strong>
                </div>
            </div>
            
            <div class="pf-sim-summary-row">
                <div class="pf-sim-summary-item">
                    <span class="lb">${years}年终值中位数 (P50):</span>
                    <span class="vl" style="color:var(--ok);font-weight:700">${money(sim.medianFinal)}</span>
                </div>
                <div class="pf-sim-summary-item">
                    <span class="lb">5%~95% 区间:</span>
                    <span class="vl" style="color:var(--txt2)">${money(sim.p5)} ~ ${money(sim.p95)}</span>
                </div>
            </div>

            ${downsideCardHtml}
        </div>`;
    }

    function renderRiskContribution(variant, s) {
        const ra = variant?.risk_analysis;
        if (!ra) return '';
        const nqCapitalPct = Math.round((ra.nq_weight || 0) * 100);
        const spCapitalPct = Math.round((ra.sp_weight || 0) * 100);
        const nqRiskPct = Math.round((ra.nq_risk_contrib || 0) * 100);
        const spRiskPct = Math.round((ra.sp_risk_contrib || 0) * 100);
        const vol = ra.portfolio_vol != null ? (ra.portfolio_vol * 100).toFixed(1) : '-';
        const sharpe = ra.sharpe_ratio != null ? ra.sharpe_ratio.toFixed(2) : '-';
        const sortino = ra.sortino_ratio != null ? ra.sortino_ratio.toFixed(2) : (variant?.simulation?.sortinoRatio != null ? variant.simulation.sortinoRatio.toFixed(2) : '-');
        const downVol = ra.downside_vol != null ? (ra.downside_vol > 1 ? Number(ra.downside_vol).toFixed(1) : (ra.downside_vol * 100).toFixed(1)) : (ra.portfolio_vol != null ? ((ra.portfolio_vol * 0.68) * 100).toFixed(1) : '-');

        let statusTag = '';
        let note = '';
        if (s.key === 'risk_parity') {
            statusTag = '<span class="tag" style="background:rgba(16,185,129,0.15);color:#059669;font-weight:700">✅ 达成等风险贡献 (ERC)</span>';
            note = '💡 <strong>等风险贡献 (ERC) 达成：</strong>均衡纳指与标普的边际风险贡献各约 50%，消除单一市场暴跌对净值的非对称冲击。';
        } else if (s.key === 'max_sharpe') {
            statusTag = `<span class="tag" style="background:rgba(99,102,241,0.15);color:#4f46e5;font-weight:700">🎯 最优夏普组合 (SR ${sharpe})</span>`;
            note = `🎯 <strong>最优风险收益比 (夏普 ${sharpe})：</strong>基于 Ledoit-Wolf 收缩协方差优化，在控制波动率的同时最大化超额收益。`;
        } else if (s.key === 'balanced') {
            statusTag = `<span class="tag" style="background:rgba(239,68,68,0.12);color:#dc2626;font-weight:700">⚠️ 风险非对称 (纳指占 ${nqRiskPct}%)</span>`;
            note = `⚠️ <strong>风险非对称警示：</strong>虽然资金按 50/50 均分，但因纳指波动大，纳指实际承担了 <strong>${nqRiskPct}%</strong> 的组合风险。`;
        } else if (s.key === 'growth') {
            statusTag = `<span class="tag" style="background:rgba(59,130,246,0.15);color:#2563eb;font-weight:700">🚀 弹性进攻型 (纳指占 ${nqRiskPct}%)</span>`;
            note = `🚀 <strong>进取型进攻敞口：</strong>大幅超配纳斯达克100，纳指贡献了 <strong>${nqRiskPct}%</strong> 的波动风险，获取充沛牛市弹性。`;
        } else if (s.key === 'conservative') {
            statusTag = `<span class="tag" style="background:rgba(16,185,129,0.12);color:#059669;font-weight:700">🛡️ 低波防守型 (标普占 ${spRiskPct}%)</span>`;
            note = `🛡️ <strong>低波动压舱石：</strong>标普500主导组合 <strong>${spRiskPct}%</strong> 的风险与收益，组合年化波动率低至 <strong>${vol}%</strong>。`;
        }

        return `
        <div class="pf-risk-card">
            <div class="pf-card-head">
                <div class="pf-card-title">
                    <span style="font-size:0.95rem">⚖️</span>
                    <span style="font-weight:600;font-size:0.825rem;color:var(--txt)">资金配置 vs 波动风险贡献</span>
                    ${statusTag}
                </div>
            </div>
            
            <div class="pf-risk-bars">
                <div class="pf-bar-group">
                    <div class="pf-bar-label">
                        <span>资金权重 (Capital Weight)</span>
                        <span>纳指 ${nqCapitalPct}% / 标普 ${spCapitalPct}%</span>
                    </div>
                    <div class="pf-bar-track">
                        <div class="pf-bar-seg" style="width:${nqCapitalPct}%;background:#3b82f6" title="纳指资金占比 ${nqCapitalPct}%"></div>
                        <div class="pf-bar-seg" style="width:${spCapitalPct}%;background:#10b981" title="标普资金占比 ${spCapitalPct}%"></div>
                    </div>
                </div>

                <div class="pf-bar-group">
                    <div class="pf-bar-label">
                        <span>波动风险贡献 (Risk Contribution)</span>
                        <span style="font-weight:${s.key === 'risk_parity' ? '700;color:var(--ok)' : '600'}">纳指 ${nqRiskPct}% / 标普 ${spRiskPct}%</span>
                    </div>
                    <div class="pf-bar-track">
                        <div class="pf-bar-seg" style="width:${nqRiskPct}%;background:linear-gradient(90deg, #3b82f6, #6366f1)" title="纳指风险贡献 ${nqRiskPct}%"></div>
                        <div class="pf-bar-seg" style="width:${spRiskPct}%;background:linear-gradient(90deg, #10b981, #059669)" title="标普风险贡献 ${spRiskPct}%"></div>
                    </div>
                </div>
            </div>

            <div class="pf-risk-kpi-grid">
                <div class="pf-risk-kpi-box">
                    <div class="lb">组合年化波动率</div>
                    <div class="vl" style="color:var(--warn)">${vol}%</div>
                    <div class="sub">收益综合年化标准差</div>
                </div>
                <div class="pf-risk-kpi-box">
                    <div class="lb">夏普比率 (Sharpe)</div>
                    <div class="vl" style="color:var(--accent2)">${sharpe}</div>
                    <div class="sub">超额回报 / 总波动风险</div>
                </div>
                <div class="pf-risk-kpi-box">
                    <div class="lb">索提诺比率 (Sortino)</div>
                    <div class="vl" style="color:var(--ok)">${sortino}</div>
                    <div class="sub">超额回报 / 负向回撤波动</div>
                </div>
                <div class="pf-risk-kpi-box">
                    <div class="lb">下行波动率 (Downside)</div>
                    <div class="vl" style="color:var(--txt)">${downVol}%</div>
                    <div class="sub">仅统计净值下跌损失波动</div>
                </div>
            </div>

            <div class="pf-risk-note">${note}</div>
        </div>`;
    }

    // ===== 阶段4：马克维茨均值-方差有效前沿曲线 (Markowitz Efficient Frontier) =====
    function renderEfficientFrontier(strategies, dynParams) {
        const canvas = document.getElementById('chart-efficient-frontier');
        if (!canvas) return;

        const p = dynParams || _dynamicParams || ALGO_CONFIG?.simulation?.params || {
            nasdaq_return: 0.1979,
            nasdaq_vol: 0.1899,
            sp500_return: 0.1610,
            sp500_vol: 0.1220,
            correlation_nq_sp: 0.75
        };
        const rf = 0.025; // 2.5% 无风险利率基准

        // 更新顶部量化基准参数徽标
        const badgeEl = document.getElementById('frontier-params-badge');
        if (badgeEl) {
            badgeEl.innerHTML = `📊 基准: 纳指 μ ${(p.nasdaq_return * 100).toFixed(1)}% / σ ${(p.nasdaq_vol * 100).toFixed(1)}% · 标普 μ ${(p.sp500_return * 100).toFixed(1)}% / σ ${(p.sp500_vol * 100).toFixed(1)}% · ρ ${(p.correlation_nq_sp || 0.75).toFixed(2)} · Rf 2.5%`;
        }

        // 计算任意资产权重的量化前沿特征
        function calcFrontierPoint(w_nq) {
            w_nq = Math.max(0, Math.min(1, Number(w_nq)));
            const w_sp = 1 - w_nq;
            const s1_sq = p.nasdaq_vol ** 2;
            const s2_sq = p.sp500_vol ** 2;
            const rho = p.correlation_nq_sp || 0.75;
            const cov12 = rho * p.nasdaq_vol * p.sp500_vol;
            const port_var = (w_nq ** 2) * s1_sq + 2 * w_nq * w_sp * cov12 + (w_sp ** 2) * s2_sq;
            const port_vol = Math.sqrt(Math.max(1e-8, port_var));
            const exp_r = w_nq * p.nasdaq_return + w_sp * p.sp500_return;
            const sharpe = (exp_r - rf) / port_vol;

            const z = (rf - exp_r) / (port_vol || 1e-4);
            function erf(x) {
                const a1 = 0.254829592, a2 = -0.284496736, a3 = 1.421413741, a4 = -1.453152027, a5 = 1.061405429, p = 0.3275911;
                const sign = x < 0 ? -1 : 1;
                const absX = Math.abs(x);
                const t = 1.0 / (1.0 + p * absX);
                const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-absX * absX);
                return sign * y;
            }
            const cdf_z = 0.5 * (1 + erf(z / Math.SQRT2));
            const pdf_z = Math.exp(-0.5 * z * z) / Math.sqrt(2 * Math.PI);
            const downVar = (port_vol ** 2) * ((z * z + 1) * cdf_z + z * pdf_z);
            const downVol = Math.sqrt(Math.max(1e-8, downVar));
            const sortino = downVol > 0 ? (exp_r - rf) / downVol : 0;

            const mrc_nq = (w_nq * s1_sq + w_sp * cov12) / port_vol;
            const mrc_sp = (w_sp * s2_sq + w_nq * cov12) / port_vol;
            const trc_nq = w_nq * mrc_nq;
            const trc_sp = w_sp * mrc_sp;
            const total_trc = trc_nq + trc_sp;
            const rc_nq = total_trc > 0 ? (trc_nq / total_trc) * 100 : 50;
            const rc_sp = total_trc > 0 ? (trc_sp / total_trc) * 100 : 50;

            return {
                w_nq,
                w_sp,
                w_nq_pct: Math.round(w_nq * 100),
                w_sp_pct: Math.round(w_sp * 100),
                x: +(port_vol * 100).toFixed(2),
                y: +(exp_r * 100).toFixed(2),
                port_vol_pct: +(port_vol * 100).toFixed(2),
                exp_r_pct: +(exp_r * 100).toFixed(2),
                sharpe: +sharpe.toFixed(2),
                sortino: +sortino.toFixed(2),
                rc_nq: +rc_nq.toFixed(1),
                rc_sp: +rc_sp.toFixed(1)
            };
        }

        // 解析解析解：GMV (全局最小方差) 与 ERC (等风险贡献)
        const s1_sq = p.nasdaq_vol ** 2;
        const s2_sq = p.sp500_vol ** 2;
        const rho = p.correlation_nq_sp || 0.75;
        const cov12 = rho * p.nasdaq_vol * p.sp500_vol;
        const gmv_denom = s1_sq + s2_sq - 2 * cov12;
        const gmv_raw = gmv_denom !== 0 ? (s2_sq - cov12) / gmv_denom : 0;
        const w_gmv = Math.max(0, Math.min(1, gmv_raw));
        const w_erc = p.sp500_vol / (p.nasdaq_vol + p.sp500_vol);

        // 离散化 101 点前沿曲线采样 (w_nq 从 0 到 1，步长 0.01)
        const allCurvePoints = [];
        for (let i = 0; i <= 100; i++) {
            allCurvePoints.push(calcFrontierPoint(i / 100));
        }

        // 寻找最优夏普切线组合 Tangency Portfolio
        let maxSharpePt = allCurvePoints[0];
        allCurvePoints.forEach(pt => {
            if (pt.sharpe > maxSharpePt.sharpe) {
                maxSharpePt = pt;
            }
        });
        const w_sharpe = maxSharpePt.w_nq;

        // 拆分有效前沿（GMV上方）与无效下半支（GMV下方）
        const effPoints = [];
        const ineffPoints = [];
        allCurvePoints.forEach(pt => {
            if (pt.w_nq >= w_gmv - 0.0001) {
                effPoints.push(pt);
            } else {
                ineffPoints.push(pt);
            }
        });
        if (ineffPoints.length > 0 && w_gmv > 0.001) {
            ineffPoints.push(calcFrontierPoint(w_gmv));
        }

        // 资本配置线 (Capital Allocation Line - CAL)
        const tanPt = calcFrontierPoint(w_sharpe);
        const calSlope = (tanPt.exp_r_pct - (rf * 100)) / (tanPt.port_vol_pct || 1);
        const maxVolX = Math.max(24, Math.round(p.nasdaq_vol * 118));
        const calPoints = [
            { x: 0, y: +(rf * 100).toFixed(2), isCal: true },
            { x: tanPt.x, y: tanPt.y, isCal: true },
            { x: maxVolX, y: +((rf * 100) + calSlope * maxVolX).toFixed(2), isCal: true }
        ];

        // 关键量化里程碑组合定义
        const milestoneDefs = [
            { key: 'sp500_only', name: '100% 标普 500 (基石底仓)', icon: '⚓', w: 0.0, color: '#14b8a6', badge: '单一基石', desc: '纯标普500基准' },
            { key: 'gmv', name: '全局最小方差组合 (GMV)', icon: '🛡️', w: w_gmv, color: '#10b981', badge: '全市场最低波动', desc: '全市场方差风险绝对最低点' },
            { key: 'conservative', name: '稳健型 (30% 纳指 : 70% 标普)', icon: '🛡️', w: 0.30, color: '#0ea5e9', badge: '经典稳健', desc: '低波底仓防御' },
            { key: 'risk_parity', name: '等风险贡献 (ERC / 风险平价)', icon: '💎', w: w_erc, color: '#8b5cf6', badge: '风险中性 50:50', desc: '消除单一资产高波动主导，两资产风险各50%' },
            { key: 'balanced', name: '平衡型 (50% 纳指 : 50% 标普)', icon: '⚖️', w: 0.50, color: '#3b82f6', badge: '传统平分 (62%风险)', desc: '资金对半均分，但纳指主导 62% 以上方差风险' },
            { key: 'max_sharpe', name: '最优夏普组合 (Tangency / MVO)', icon: '🎯', w: w_sharpe, color: '#f59e0b', badge: '最高夏普切线点', desc: '在给定约束下获得单位波动最高超额回报' },
            { key: 'growth', name: '进取型 (70% 纳指 : 30% 标普)', icon: '🚀', w: 0.70, color: '#f43f5e', badge: '高贝塔进攻', desc: '高比例科技敞口，享受充沛牛市弹性' },
            { key: 'nasdaq_only', name: '100% 纳斯达克 100 (成长引擎)', icon: '⚡', w: 1.0, color: '#6366f1', badge: '单一成长', desc: '纯纳斯达克100基准' }
        ];

        const milestonePoints = milestoneDefs.map(m => {
            const pt = calcFrontierPoint(m.w);
            return {
                ...pt,
                key: m.key,
                name: m.name,
                icon: m.icon,
                color: m.color,
                badge: m.badge,
                desc: m.desc,
                isMilestone: true
            };
        });

        // 默认激活点：优先取风险平价组合 ERC
        let currentWeight = w_erc;
        let activePoint = calcFrontierPoint(currentWeight);

        // 主题色配置
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const gridColor = isDark ? 'rgba(129, 140, 248, 0.12)' : 'rgba(99, 102, 241, 0.08)';
        const textColor = isDark ? '#94a3b8' : '#64748b';

        // 销毁已有图表实例
        if (chartPool.frontier) {
            chartPool.frontier.destroy();
            chartPool.frontier = null;
        }

        // 创建 Chart.js 散点与折线图
        chartPool.frontier = new Chart(canvas, {
            type: 'scatter',
            data: {
                datasets: [
                    {
                        type: 'line',
                        label: '马克维茨有效前沿 (Efficient Frontier)',
                        data: effPoints,
                        borderColor: '#6366f1',
                        backgroundColor: isDark ? 'rgba(99, 102, 241, 0.12)' : 'rgba(99, 102, 241, 0.06)',
                        fill: false,
                        tension: 0.35,
                        borderWidth: 3.5,
                        pointRadius: 0,
                        pointHoverRadius: 6,
                        showLine: true,
                        order: 3
                    },
                    {
                        type: 'line',
                        label: '无效下半支 (Inefficient Frontier)',
                        data: ineffPoints,
                        borderColor: isDark ? 'rgba(148, 163, 184, 0.4)' : 'rgba(148, 163, 184, 0.55)',
                        borderDash: [5, 5],
                        tension: 0.35,
                        borderWidth: 2,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        fill: false,
                        showLine: true,
                        order: 4
                    },
                    {
                        type: 'line',
                        label: '资本配置线 (CAL 切线)',
                        data: calPoints,
                        borderColor: '#f59e0b',
                        borderDash: [6, 4],
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false,
                        showLine: true,
                        order: 5
                    },
                    {
                        type: 'scatter',
                        label: '关键量化里程碑',
                        data: milestonePoints,
                        pointBackgroundColor: ctx => ctx.raw?.color || '#6366f1',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: ctx => (ctx.raw?.key === 'risk_parity' || ctx.raw?.key === 'max_sharpe') ? 9 : 7,
                        pointHoverRadius: 12,
                        order: 2
                    },
                    {
                        type: 'scatter',
                        label: '当前探索点位 (Cursor)',
                        data: [activePoint],
                        pointBackgroundColor: '#ec4899',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 3,
                        pointRadius: 10,
                        pointHoverRadius: 14,
                        order: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 600
                },
                interaction: {
                    mode: 'nearest',
                    intersect: false
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: textColor,
                            font: { size: 11, weight: '500' },
                            usePointStyle: true,
                            filter: item => item.text !== '当前探索点位 (Cursor)'
                        }
                    },
                    tooltip: {
                        backgroundColor: isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.96)',
                        titleColor: isDark ? '#f8fafc' : '#0f172a',
                        bodyColor: isDark ? '#cbd5e1' : '#334155',
                        borderColor: isDark ? 'rgba(99, 102, 241, 0.4)' : 'rgba(99, 102, 241, 0.25)',
                        borderWidth: 1,
                        padding: 12,
                        boxPadding: 4,
                        usePointStyle: true,
                        callbacks: {
                            title: function(items) {
                                if (!items.length) return '';
                                const raw = items[0].raw;
                                if (raw.isCal) return '📐 资本配置线 (Capital Allocation Line)';
                                if (raw.name) return `${raw.icon || '📍'} ${raw.name}`;
                                return `组合配比: 纳指 ${raw.w_nq_pct}% : 标普 ${raw.w_sp_pct}%`;
                            },
                            label: function(item) {
                                const raw = item.raw;
                                if (raw.isCal) {
                                    return [
                                        `波动率: ${raw.x}%`,
                                        `预期回报: ${raw.y}%`,
                                        '说明: 连接无风险资产 Rf 与切线组合的高效借贷线'
                                    ];
                                }
                                const lines = [
                                    `预期年化回报 E[R]: ${raw.y}%`,
                                    `组合年化波动 σ: ${raw.x}%`,
                                    `夏普比率 (Sharpe): ${raw.sharpe} · 索提诺 (Sortino): ${raw.sortino}`,
                                    `资金配比: 纳指 ${raw.w_nq_pct}% : 标普 ${raw.w_sp_pct}%`,
                                    `风险贡献: 纳指 ${raw.rc_nq}% : 标普 ${raw.rc_sp}%`
                                ];
                                if (raw.desc) {
                                    lines.push(`💡 特征: ${raw.desc}`);
                                }
                                return lines;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'linear',
                        grid: { color: gridColor },
                        ticks: {
                            color: textColor,
                            font: { size: 11 },
                            callback: v => v + '%'
                        },
                        title: {
                            display: true,
                            text: '组合年化波动率 σ (风险维度)',
                            color: textColor,
                            font: { size: 11, weight: '600' }
                        }
                    },
                    y: {
                        type: 'linear',
                        grid: { color: gridColor },
                        ticks: {
                            color: textColor,
                            font: { size: 11 },
                            callback: v => v + '%'
                        },
                        title: {
                            display: true,
                            text: '预期年化收益率 E[R] (收益维度)',
                            color: textColor,
                            font: { size: 11, weight: '600' }
                        }
                    }
                },
                onClick: (e, elements) => {
                    if (elements.length > 0) {
                        const el = elements[0];
                        const dataset = chartPool.frontier.data.datasets[el.datasetIndex];
                        const pt = dataset.data[el.index];
                        if (pt && pt.w_nq != null) {
                            updateHUD(pt.w_nq);
                        }
                    }
                }
            }
        });

        // 更新探测器 HUD 状态
        function updateHUD(w_nq) {
            const pt = calcFrontierPoint(w_nq);
            currentWeight = pt.w_nq;

            // 查找是否靠近关键里程碑
            const matched = milestonePoints.find(m => Math.abs(m.w_nq - pt.w_nq) <= 0.015);

            const hudIcon = document.getElementById('f-hud-icon');
            const hudTitle = document.getElementById('f-hud-title');
            const hudBadge = document.getElementById('f-hud-badge');

            if (matched) {
                if (hudIcon) hudIcon.textContent = matched.icon;
                if (hudTitle) hudTitle.textContent = matched.name;
                if (hudBadge) {
                    hudBadge.textContent = matched.badge;
                    hudBadge.style.background = matched.color;
                }
            } else {
                if (hudIcon) hudIcon.textContent = '🧭';
                if (hudTitle) hudTitle.textContent = `自定义探索配比 (纳指 ${pt.w_nq_pct}% : 标普 ${pt.w_sp_pct}%)`;
                if (hudBadge) {
                    hudBadge.textContent = '自定义配置';
                    hudBadge.style.background = 'var(--accent)';
                }
            }

            const slider = document.getElementById('frontier-range-slider');
            if (slider && Number(slider.value) !== pt.w_nq_pct) {
                slider.value = pt.w_nq_pct;
            }

            const curLabel = document.getElementById('f-slider-current');
            if (curLabel) {
                curLabel.innerHTML = `当前资金配比: <strong>纳指 ${pt.w_nq_pct}% : 标普 ${pt.w_sp_pct}%</strong>`;
            }

            const retEl = document.getElementById('f-kpi-ret');
            if (retEl) retEl.textContent = `${pt.exp_r_pct}%`;

            const volEl = document.getElementById('f-kpi-vol');
            if (volEl) volEl.textContent = `${pt.port_vol_pct}%`;

            const sharpeEl = document.getElementById('f-kpi-sharpe');
            if (sharpeEl) sharpeEl.textContent = `${pt.sharpe}`;

            const sortinoEl = document.getElementById('f-kpi-sortino');
            if (sortinoEl) sortinoEl.textContent = `${pt.sortino}`;

            const volRankEl = document.getElementById('f-kpi-vol-rank');
            if (volRankEl) {
                if (Math.abs(pt.w_nq - w_gmv) < 0.02) {
                    volRankEl.textContent = '🛡️ 全局最小方差点 (防守最强)';
                } else if (Math.abs(pt.w_nq - w_sharpe) < 0.02) {
                    volRankEl.textContent = '🎯 切线最高夏普比率 (最优超额)';
                } else if (Math.abs(pt.rc_nq - 50) <= 2) {
                    volRankEl.textContent = '💎 风险中性 (两资产各承担50%风险)';
                } else {
                    volRankEl.textContent = `分散化降波: 降低单一指数极端波动`;
                }
            }

            // 资金配比条
            const capNq = document.getElementById('f-cap-nq');
            const capSp = document.getElementById('f-cap-sp');
            if (capNq && capSp) {
                capNq.style.width = `${pt.w_nq_pct}%`;
                capNq.textContent = pt.w_nq_pct > 8 ? `${pt.w_nq_pct}%` : '';
                capSp.style.width = `${pt.w_sp_pct}%`;
                capSp.textContent = pt.w_sp_pct > 8 ? `${pt.w_sp_pct}%` : '';
            }

            // 风险贡献条
            const riskNq = document.getElementById('f-risk-nq');
            const riskSp = document.getElementById('f-risk-sp');
            if (riskNq && riskSp) {
                riskNq.style.width = `${pt.rc_nq}%`;
                riskNq.textContent = pt.rc_nq > 10 ? `${pt.rc_nq}%` : '';
                riskSp.style.width = `${pt.rc_sp}%`;
                riskSp.textContent = pt.rc_sp > 10 ? `${pt.rc_sp}%` : '';
            }

            // 风险提示文案
            const noteEl = document.getElementById('f-bars-note');
            if (noteEl) {
                if (Math.abs(pt.rc_nq - 50) <= 2) {
                    noteEl.textContent = '✨ 达成绝对等风险中性 (各50%)';
                    noteEl.style.color = 'var(--ok)';
                } else if (pt.w_nq_pct === 50) {
                    noteEl.textContent = `⚠️ 传统平分: 纳指实际承担 ${pt.rc_nq}% 方差风险`;
                    noteEl.style.color = 'var(--down)';
                } else if (pt.rc_nq > 65) {
                    noteEl.textContent = `⚡ 纳指高贝塔主导 ${pt.rc_nq}% 风险`;
                    noteEl.style.color = 'var(--down)';
                } else {
                    noteEl.textContent = `标普防守主导 ${pt.rc_sp}% 风险`;
                    noteEl.style.color = 'var(--ok)';
                }
            }

            // 更新图表 Cursor 点
            if (chartPool.frontier) {
                chartPool.frontier.data.datasets[4].data = [pt];
                chartPool.frontier.update('none');
            }
        }

        // 初始化 HUD 显示
        updateHUD(currentWeight);

        // 绑定滑块拖动事件
        const slider = document.getElementById('frontier-range-slider');
        if (slider) {
            slider.oninput = (e) => {
                const w = Number(e.target.value) / 100;
                updateHUD(w);
                // 同步更新预设按钮状态
                const presetBtns = document.querySelectorAll('.frontier-preset-btn');
                presetBtns.forEach(btn => btn.classList.remove('on'));
            };
        }

        // 绑定预设锚点按钮事件
        const presetContainer = document.getElementById('frontier-presets');
        if (presetContainer) {
            presetContainer.querySelectorAll('.frontier-preset-btn').forEach(btn => {
                btn.onclick = () => {
                    presetContainer.querySelectorAll('.frontier-preset-btn').forEach(b => b.classList.remove('on'));
                    btn.classList.add('on');
                    const preset = btn.dataset.preset;
                    let targetW = w_erc;
                    if (preset === 'gmv') targetW = w_gmv;
                    else if (preset === 'risk_parity') targetW = w_erc;
                    else if (preset === 'max_sharpe') targetW = w_sharpe;
                    else if (preset === 'conservative') targetW = 0.30;
                    else if (preset === 'balanced') targetW = 0.50;
                    else if (preset === 'growth') targetW = 0.70;
                    else if (preset === 'all') targetW = w_erc;

                    updateHUD(targetW);

                    // 同步高亮下方矩阵表格中对应的策略
                    if (preset !== 'all') {
                        const targetRow = document.querySelector(`.quant-matrix-row[data-strategy="${preset}"]`);
                        if (targetRow) {
                            document.querySelectorAll('.quant-matrix-row').forEach(r => r.classList.remove('highlight-pulse'));
                            targetRow.classList.add('highlight-pulse');
                            setTimeout(() => targetRow.classList.remove('highlight-pulse'), 2500);
                        }
                    }
                };
            });
        }

        // 绑定 CAL 切线显示切换事件
        const calToggle = document.getElementById('toggle-frontier-cal');
        if (calToggle) {
            calToggle.onchange = () => {
                if (chartPool.frontier) {
                    chartPool.frontier.data.datasets[2].hidden = !calToggle.checked;
                    chartPool.frontier.update();
                }
            };
        }

        // 绑定下方策略矩阵行点击事件：点击行即在上方有效前沿高亮并定位
        const matrixRows = document.querySelectorAll('.quant-matrix-row');
        matrixRows.forEach(row => {
            row.style.cursor = 'pointer';
            row.onclick = (e) => {
                if (e.target.closest('.btn-jump-strat, .btn-sim-matrix')) return;
                const stratKey = row.dataset.strategy;
                if (!stratKey) return;
                const matchBtn = document.querySelector(`.frontier-preset-btn[data-preset="${stratKey}"]`);
                if (matchBtn) {
                    matchBtn.click();
                    const panel = document.getElementById('frontier-interactive-panel');
                    if (panel) {
                        panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }
            };
        });
    }

    // ===== Top 3: 历史极端危机压力测试 (Historical Crisis Stress Testing) =====
    const HISTORICAL_SCENARIOS = {
        gfc: {
            id: 'gfc',
            name: '2008 全球次贷金融海啸',
            period: '2007.10 - 2009.12 (共 27 个月)',
            bgDesc: '美国次贷危机演变为百年一遇的全球流动性冰封与信用崩塌，雷曼兄弟倒闭，标普500单月暴跌近17%，整体最大回撤超 -52%。但在定投纪律加持下，投资者在低谷贪婪收集极廉价筹码，2009年迎来暴力修复。',
            ndxDrop: '-50.5%',
            spxDrop: '-52.6%',
            troughPeriod: '2009年2-3月 (第17个月)',
            labels: [
                '07.10', '07.11', '07.12', '08.01', '08.02', '08.03', '08.04', '08.05', '08.06',
                '08.07', '08.08', '08.09', '08.10', '08.11', '08.12', '09.01', '09.02', '09.03',
                '09.04', '09.05', '09.06', '09.07', '09.08', '09.09', '09.10', '09.11', '09.12'
            ],
            nq: [0.048, -0.069, -0.004, -0.086, -0.048, 0.012, 0.057, 0.046, -0.073, 0.014, 0.018, -0.119, -0.168, -0.109, 0.035, -0.058, -0.046, 0.109, 0.123, 0.052, 0.034, 0.081, 0.018, 0.046, -0.012, 0.049, 0.056],
            sp: [0.015, -0.044, -0.009, -0.061, -0.035, -0.006, 0.048, 0.011, -0.086, -0.010, 0.012, -0.091, -0.169, -0.075, 0.008, -0.086, -0.110, 0.085, 0.094, 0.053, 0.000, 0.074, 0.034, 0.036, -0.020, 0.057, 0.018],
            takeaway: '🌊 <strong>压力测试启示：</strong>在次贷危机最黑暗的 2009 年初，一次性买入投资者账面深度腰斩（-52%），而定投策略的最大账面浮亏仅约 <strong>-29% ~ -32%</strong>。更关键的是：定投仅用 <strong>6~7 个月</strong> 便从谷底彻底抹平浮亏重回盈利，而一次性买入耗时近 4 年才解套！'
        },
        covid: {
            id: 'covid',
            name: '2020 新冠疫情极速熔断',
            period: '2020.01 - 2020.12 (共 12 个月)',
            bgDesc: '新冠病毒全球大流行引爆史诗级流动性危机，美股10天内遭遇 4 次熔断。然而随着美联储无限QE与零利率救市，全球科技巨头业绩逆势暴增，纳斯达克开启人类金融史上最迅猛的 V 型超级大反转。',
            ndxDrop: '-28.0%',
            spxDrop: '-33.9%',
            troughPeriod: '2020年3月 (第3个月)',
            labels: [
                '20.01', '20.02', '20.03', '20.04', '20.05', '20.06',
                '20.07', '20.08', '20.09', '20.10', '20.11', '20.12'
            ],
            nq: [0.030, -0.064, -0.076, 0.154, 0.067, 0.063, 0.073, 0.111, -0.057, -0.032, 0.110, 0.051],
            sp: [-0.002, -0.084, -0.125, 0.127, 0.045, 0.018, 0.055, 0.070, -0.039, -0.028, 0.108, 0.037],
            takeaway: '🦠 <strong>压力测试启示：</strong>极速暴跌（Flash Crash）是定投的最佳盟友。在 2020 年 3 月熔断中，定投浮亏仅约 <strong>-9%</strong>，随后 4 月即刻凭借反弹完成回本，全年收益率高达 <strong>+22% ~ +27%</strong>。任何在恐慌中暂停定投的人都错失了整轮复利主升浪。'
        },
        dotcom: {
            id: 'dotcom',
            name: '2000 互联网泡沫破裂',
            period: '2000.03 - 2002.10 (共 32 个月)',
            bgDesc: '人类科技史估值泡沫巅峰破裂，纳斯达克100指数累计暴跌超过 -82%，历时近3年才见底。这是科技股历史上最残酷的漫长熊市考验，也是资产多元配置（纳指+标普）价值凸显的终极试金石。',
            ndxDrop: '-82.9%',
            spxDrop: '-47.4%',
            troughPeriod: '2002年9-10月 (第31-32个月)',
            labels: [
                '00.03', '00.04', '00.05', '00.06', '00.07', '00.08', '00.09', '00.10', '00.11', '00.12',
                '01.01', '01.02', '01.03', '01.04', '01.05', '01.06', '01.07', '01.08', '01.09', '01.10', '01.11', '01.12',
                '02.01', '02.02', '02.03', '02.04', '02.05', '02.06', '02.07', '02.08', '02.09', '02.10'
            ],
            nq: [0.042, -0.136, -0.119, 0.166, -0.056, 0.118, -0.127, -0.083, -0.229, -0.036, 0.122, -0.224, -0.146, 0.145, -0.014, -0.033, -0.058, -0.109, -0.169, 0.155, 0.151, -0.005, -0.028, -0.124, 0.068, -0.165, -0.062, -0.128, -0.088, 0.014, -0.135, 0.131],
            sp: [0.097, -0.031, -0.022, 0.024, -0.016, 0.061, -0.054, -0.005, -0.080, 0.004, 0.035, -0.092, -0.064, 0.077, 0.005, -0.025, -0.011, -0.064, -0.082, 0.018, 0.075, 0.008, -0.016, -0.021, 0.037, -0.061, -0.009, -0.072, -0.079, 0.005, -0.110, 0.086],
            takeaway: '⚡ <strong>压力测试启示：</strong>在纳指纯单边下跌 -82% 的世纪崩盘中，纯纳指单边定投最大浮亏达 -48.7%；而采用【稳健型 30/70】或【风险平价 38/62】方案，最大浮亏被大幅压缩至 <strong>-27% ~ -32%</strong>，且跌幅远低于标普单边一次性下跌，展现了跨行业因子分散与风险平价配置的保命防御力！'
        },
        ratehike: {
            id: 'ratehike',
            name: '2022 激进加息高通胀熊市',
            period: '2022.01 - 2022.12 (共 12 个月)',
            bgDesc: '美联储遭遇40年来最严重通胀失控，以史无前例的连续4次75bp暴力加息打压需求。高估值成长股首当其冲，纳指全年深跌 -33%，标普跌近 -19%，是检验估值挤泡沫与逆周期布局韧性的最近期样本。',
            ndxDrop: '-32.4%',
            spxDrop: '-18.1%',
            troughPeriod: '2022年10月 (第10个月)',
            labels: [
                '22.01', '22.02', '22.03', '22.04', '22.05', '22.06',
                '22.07', '22.08', '22.09', '22.10', '22.11', '22.12'
            ],
            nq: [-0.085, -0.046, 0.042, -0.134, -0.016, -0.090, 0.126, -0.052, -0.106, 0.040, 0.055, -0.090],
            sp: [-0.053, -0.031, 0.036, -0.088, 0.000, -0.084, 0.091, -0.042, -0.093, 0.080, 0.054, -0.059],
            takeaway: '📈 <strong>压力测试启示：</strong>2022 年加息熊市中，虽然全年单边收跌，但定投策略由于分批平摊买入成本，年终账面浮亏仅 <strong>-9% ~ -13%</strong>，相比直接买入纳指 -33% 的亏损大幅减少。紧接着 2023 年纳指录得 +54% 暴涨，2022 年坚持定投积累的低成本份额全部转化为超额利润。'
        }
    };

    let _activeStressScenario = 'gfc';

    function renderStressTest(scenarioKey, budgetVal, dynParams) {
        const key = scenarioKey || _activeStressScenario || 'gfc';
        const sc = HISTORICAL_SCENARIOS[key];
        if (!sc) return;

        const budget = Number(budgetVal) || Number(document.getElementById('pf-m')?.value) || 2000;
        const feeM = 0.005 / 12.0;

        // 1. 更新背景档案与关键 KPI
        const descEl = document.getElementById('stress-profile-desc');
        if (descEl) {
            descEl.innerHTML = `<strong style="color:var(--txt);font-size:0.875rem">${sc.name}</strong> <span style="color:var(--accent2);margin-left:6px;font-size:0.75rem">${sc.period}</span><br>${sc.bgDesc}`;
        }
        const kpiEl = document.getElementById('stress-profile-kpis');
        if (kpiEl) {
            kpiEl.innerHTML = `
                <div class="stress-kpi-pill">
                    <span class="lb">纳指峰谷跌幅</span>
                    <span class="vl" style="color:var(--err)">${sc.ndxDrop}</span>
                </div>
                <div class="stress-kpi-pill">
                    <span class="lb">标普峰谷跌幅</span>
                    <span class="vl" style="color:var(--err)">${sc.spxDrop}</span>
                </div>
                <div class="stress-kpi-pill">
                    <span class="lb">大盘见底周期</span>
                    <span class="vl" style="color:var(--txt);font-size:0.78rem">${sc.troughPeriod}</span>
                </div>
            `;
        }

        const budgetNoteEl = document.getElementById('stress-budget-note');
        if (budgetNoteEl) {
            budgetNoteEl.textContent = `当前推演预算: ¥${budget.toLocaleString()} / 月`;
        }

        // 2. 准备参测策略定义
        const rpWeight = (dynParams?.risk_parity_w_nq != null) ? dynParams.risk_parity_w_nq : 0.38;
        const msWeight = (dynParams?.max_sharpe_w_nq != null) ? dynParams.max_sharpe_w_nq : 0.60;

        const stratList = [
            { id: 'rp', name: '💎 风险平价', w_nq: rpWeight, color: '#f59e0b', badge: '<span class="tag" style="background:rgba(245,158,11,0.12);color:#d97706;font-weight:600">💎 平滑抗震</span>' },
            { id: 'ms', name: '⚖️ 最优夏普', w_nq: msWeight, color: '#8b5cf6', badge: '<span class="tag" style="background:rgba(139,92,246,0.12);color:#7c3aed;font-weight:600">⚖️ 效率兼顾</span>' },
            { id: 'mod', name: '🛡️ 稳健型', w_nq: 0.30, color: '#10b981', badge: '<span class="tag" style="background:rgba(16,185,129,0.12);color:var(--ok);font-weight:600">🛡️ 极佳防守</span>' },
            { id: 'bal', name: '🔄 平衡型', w_nq: 0.50, color: '#0ea5e9', badge: '<span class="tag" style="background:rgba(14,165,233,0.12);color:#0284c7;font-weight:600">🔄 均衡抗跌</span>' },
            { id: 'agg', name: '🚀 进取型', w_nq: 0.70, color: '#6366f1', badge: '<span class="tag" style="background:rgba(99,102,241,0.12);color:var(--accent2);font-weight:600">🚀 弹性进攻</span>' },
            { id: 'b_nq', name: '100% 纳指基准', w_nq: 1.00, color: '#ec4899', isBenchmark: true, badge: '<span class="tag" style="background:rgba(239,68,68,0.12);color:var(--err);font-weight:600">🔥 极端进攻</span>' },
            { id: 'b_sp', name: '100% 标普基准', w_nq: 0.00, color: '#14b8a6', isBenchmark: true, badge: '<span class="tag" style="background:rgba(20,184,166,0.12);color:#0d9488;font-weight:600">🏛️ 传统基准</span>' },
        ];

        // 3. 通算各策略在当前危机中的月度定投资产曲线与指标
        const simResults = stratList.map(st => {
            const w_nq = st.w_nq;
            const w_sp = 1.0 - w_nq;
            let cumInvest = 0;
            let wealth = 0;
            let peak = 0;
            let minPl = 0;
            let troughM = 1;
            const wealthPath = [];
            const investPath = [];
            const plPath = [];

            for (let m = 0; m < sc.nq.length; m++) {
                cumInvest += budget;
                const rnq = sc.nq[m];
                const rsp = sc.sp[m];
                const rp = w_nq * rnq + w_sp * rsp - feeM;
                wealth = (wealth + budget) * (1.0 + rp);

                const pl = (wealth - cumInvest) / cumInvest;
                wealthPath.push(Math.round(wealth));
                investPath.push(cumInvest);
                plPath.push(pl);

                if (pl < minPl) {
                    minPl = pl;
                    troughM = m + 1;
                }
                if (wealth > peak) peak = wealth;
            }

            let recMonths = null;
            for (let m = troughM; m < plPath.length; m++) {
                if (plPath[m] >= 0) {
                    recMonths = (m + 1) - troughM;
                    break;
                }
            }

            const finalReturnPct = ((wealth / cumInvest) - 1.0) * 100.0;

            return {
                ...st,
                cumInvest,
                finalWealth: wealth,
                finalReturnPct,
                minPl,
                troughM,
                recMonths,
                wealthPath,
                investPath
            };
        });

        // 4. 渲染压力测试表格
        const tbodyEl = document.getElementById('stress-test-tbody');
        if (tbodyEl) {
            tbodyEl.innerHTML = simResults.map(r => {
                const retColor = r.finalReturnPct >= 0 ? 'var(--ok)' : 'var(--err)';
                const retPrefix = r.finalReturnPct > 0 ? '+' : '';
                const recHtml = r.recMonths != null
                    ? `<span style="color:var(--ok);font-weight:600">谷底后 ${r.recMonths} 个月</span>`
                    : `<span style="color:var(--txt3)">周期内未回本</span>`;

                return `
                    <tr style="${r.isBenchmark ? 'background:rgba(100,116,139,0.03);' : ''}">
                        <td><strong>${r.name}</strong></td>
                        <td style="font-variant-numeric:tabular-nums;color:var(--txt2)">${Math.round(r.w_nq * 100)}% : ${Math.round((1 - r.w_nq) * 100)}%</td>
                        <td style="font-variant-numeric:tabular-nums">¥${r.cumInvest.toLocaleString()}</td>
                        <td style="font-variant-numeric:tabular-nums;font-weight:700">¥${Math.round(r.finalWealth).toLocaleString()}</td>
                        <td style="font-variant-numeric:tabular-nums;font-weight:700;color:${retColor}">${retPrefix}${r.finalReturnPct.toFixed(1)}%</td>
                        <td style="font-variant-numeric:tabular-nums">
                            <span style="color:var(--err);font-weight:700">${(r.minPl * 100).toFixed(1)}%</span>
                            <span style="font-size:0.72rem;color:var(--txt3);margin-left:4px">(第${r.troughM}月)</span>
                        </td>
                        <td>${recHtml}</td>
                        <td>${r.badge}</td>
                    </tr>
                `;
            }).join('');
        }

        // 5. 渲染启示录说明
        const calloutEl = document.getElementById('stress-takeaway-callout');
        if (calloutEl) {
            calloutEl.innerHTML = sc.takeaway;
        }

        // 6. 渲染折线图表 (Chart.js)
        const canvas = document.getElementById('chart-stress-test');
        if (!canvas) return;

        if (chartPool.stress) {
            chartPool.stress.destroy();
            chartPool.stress = null;
        }

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const gridColor = isDark ? 'rgba(129, 140, 248, 0.12)' : 'rgba(99, 102, 241, 0.08)';
        const tickColor = isDark ? '#94a3b8' : '#64748b';

        // 基准本金线 (Dashed gray)
        const baseInvestPath = simResults[0].investPath;
        const datasets = [
            {
                label: '累计投入本金',
                data: baseInvestPath,
                borderColor: isDark ? '#64748b' : '#94a3b8',
                borderWidth: 2,
                borderDash: [5, 5],
                pointRadius: 0,
                pointHoverRadius: 3,
                fill: false,
                order: 10
            }
        ];

        simResults.forEach(r => {
            datasets.push({
                label: r.name.replace(/^[^\w\u4e00-\u9fa5]+/, ''), // 去除前置表情符号使图例更简洁
                data: r.wealthPath,
                borderColor: r.color,
                borderWidth: r.isBenchmark ? 1.5 : (r.id === 'rp' ? 2.8 : 2),
                borderDash: r.isBenchmark ? [3, 3] : undefined,
                pointRadius: 0,
                pointHoverRadius: 4,
                tension: 0.25,
                fill: false,
                order: r.id === 'rp' ? 1 : (r.id === 'ms' ? 2 : (r.isBenchmark ? 8 : 4))
            });
        });

        chartPool.stress = new Chart(canvas, {
            type: 'line',
            data: {
                labels: sc.labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: tickColor,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            padding: 12,
                            font: { size: 11, family: 'Inter, system-ui, sans-serif' }
                        }
                    },
                    tooltip: {
                        backgroundColor: isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)',
                        titleColor: isDark ? '#f8fafc' : '#0f172a',
                        bodyColor: isDark ? '#cbd5e1' : '#334155',
                        borderColor: isDark ? '#334155' : '#e2e8f0',
                        borderWidth: 1,
                        padding: 10,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(ctx) {
                                const val = ctx.parsed.y;
                                const dsLabel = ctx.dataset.label || '';
                                if (dsLabel === '累计投入本金') {
                                    return ` ${dsLabel}: ¥${val.toLocaleString()}`;
                                }
                                const investVal = baseInvestPath[ctx.dataIndex] || 1;
                                const plPct = ((val - investVal) / investVal) * 100;
                                const sign = plPct >= 0 ? '+' : '';
                                return ` ${dsLabel}: ¥${val.toLocaleString()} (${sign}${plPct.toFixed(1)}%)`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: {
                            color: tickColor,
                            font: { size: 11, family: 'Inter, system-ui, sans-serif' },
                            maxRotation: 0,
                            autoSkip: true,
                            maxTicksLimit: 14
                        }
                    },
                    y: {
                        grid: { color: gridColor },
                        ticks: {
                            color: tickColor,
                            font: { size: 11, family: 'Inter, system-ui, sans-serif' },
                            callback: function(v) {
                                if (v >= 10000) return '¥' + (v / 10000).toFixed(1) + '万';
                                return '¥' + v;
                            }
                        }
                    }
                }
            }
        });
    }

    function initStressTestTabs() {
        const tabsContainer = document.getElementById('stress-scenario-tabs');
        if (!tabsContainer) return;
        tabsContainer.querySelectorAll('.seg-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const scKey = btn.dataset.scenario;
                if (!scKey || scKey === _activeStressScenario) return;
                tabsContainer.querySelectorAll('.seg-btn').forEach(b => b.classList.remove('on'));
                btn.classList.add('on');
                _activeStressScenario = scKey;
                const monthly = +document.getElementById('pf-m')?.value || 2000;
                renderStressTest(_activeStressScenario, monthly, _dynamicParams);
            });
        });
    }

    function applyPortfolioCategoryFilter(targetCat) {
        const cat = targetCat || document.querySelector('#pf-category-filter .seg-btn.on')?.dataset?.category || 'ALL';
        let matchCount = 0;
        const allCards = document.querySelectorAll('#pf-container .pf-card');
        allCards.forEach(card => {
            if (cat === 'ALL' || card.dataset.category === cat) {
                card.style.display = '';
                matchCount++;
            } else {
                card.style.display = 'none';
            }
        });
        const summaryEl = document.getElementById('pf-summary-text');
        if (summaryEl) {
            summaryEl.innerHTML = `当前展示 <strong style="color:var(--accent2);font-weight:700">${matchCount}</strong> / ${allCards.length} 组配置方案`;
        }
    }

    async function computePortfolio() {
        const btn = document.getElementById('btn-pf');
        btn.disabled = true; btn.textContent = '计算中…';
        try {
            const monthly = +document.getElementById('pf-m').value;
            const years = +document.getElementById('pf-y').value;
            Object.values(pfCharts).forEach(c => c.destroy());
            pfCharts = {};

            const dynParams = await getDynamicParams();
            let strategies;
            try {
                strategies = await apiGet(`/api/portfolio?years=${years}&budget=${monthly}`);
            } catch (apiErr) {
                console.warn("API failed, falling back to local calculation:", apiErr);
                strategies = localCalculatePortfolio(years, monthly);
            }
            
            // 为 ideal 和 practical 方案提供蒙特卡洛组合模拟数据 (仅在 API 未返回模拟结果时执行本地计算)
            const simPromises = [];
            strategies.forEach(s => {
                const idealAllocs = s.ideal?.allocations || [];
                const practicalAllocs = s.practical?.allocations || [];
                
                if (idealAllocs.length && !s.ideal.simulation) {
                    const simFunds = idealAllocs.map(a => FUND_DATA.find(f => f.code === a.code)).filter(Boolean);
                    const simWeights = idealAllocs.map(a => a.actual_weight || a.weight || 0);
                    simPromises.push(
                        simulateViaWorker(simFunds, simWeights, years, monthly, dynParams).then(result => {
                            s.ideal.simulation = result;
                        })
                    );
                }
                
                if (practicalAllocs.length && !s.practical.simulation) {
                    const simFunds = practicalAllocs.map(a => FUND_DATA.find(f => f.code === a.code)).filter(Boolean);
                    const simWeights = practicalAllocs.map(a => a.actual_weight || a.weight || 0);
                    simPromises.push(
                        simulateViaWorker(simFunds, simWeights, years, monthly, dynParams).then(result => {
                            s.practical.simulation = result;
                        })
                    );
                }
            });
            await Promise.all(simPromises);
            const pieColors = ['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#f43f5e', '#06b6d4'];

            // 渲染现代组合理论 (MPT) 5大定投策略全景矩阵看板
            const matrixTbody = document.getElementById('quant-matrix-tbody');
            if (matrixTbody) {
                let mHtml = '';
                strategies.forEach(s => {
                    const ra = s.practical?.risk_analysis || s.ideal?.risk_analysis || {};
                    const nqW = Math.round((ra.nq_weight != null ? ra.nq_weight : s.nq_pct || 0) * 100);
                    const spW = Math.round((ra.sp_weight != null ? ra.sp_weight : (1 - s.nq_pct) || 0) * 100);
                    const nqRC = Math.round((ra.nq_risk_contrib || 0) * 100);
                    const spRC = Math.round((ra.sp_risk_contrib || 0) * 100);
                    const vol = ra.portfolio_vol != null ? (ra.portfolio_vol * 100).toFixed(1) + '%' : '-';
                    const sharpe = ra.sharpe_ratio != null ? ra.sharpe_ratio.toFixed(2) : '-';
                    const sortino = ra.sortino_ratio != null ? ra.sortino_ratio.toFixed(2) : (sim?.sortinoRatio != null ? sim.sortinoRatio.toFixed(2) : '-');
                    const sim = s.practical?.simulation || s.ideal?.simulation;
                    const retStr = sim?.annualReturn != null ? `<strong style="color:var(--accent2)">${sim.annualReturn}%</strong>` : '-';
                    const medFinal = sim?.medianFinal != null ? `<span style="color:var(--ok);font-weight:600">${money(sim.medianFinal)}</span>` : '-';

                    let typeBadge = '';
                    if (s.category === 'quant') {
                        typeBadge = `<span class="tag" style="background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;font-weight:600">💎 ${s.tag || '量化专区'}</span>`;
                    } else {
                        typeBadge = `<span class="tag" style="background:var(--surface2);color:var(--txt2)">${s.tag || '经典传统'}</span>`;
                    }

                    let riskBadge = '';
                    if (s.key === 'risk_parity') {
                        riskBadge = `<span style="color:var(--ok);font-weight:700" title="达成等风险贡献：纳指与标普风险各50%">50% : 50% ✨</span>`;
                    } else if (s.key === 'balanced') {
                        riskBadge = `<span style="color:var(--down);font-weight:600" title="纳指波动大导致风险显著主导">${nqRC}% : ${spRC}% ⚠️</span>`;
                    } else {
                        riskBadge = `<span>${nqRC}% : ${spRC}%</span>`;
                    }

                    let highlightLogic = '';
                    if (s.key === 'risk_parity') {
                        highlightLogic = '<strong>等风险贡献 (ERC)：</strong>平滑波动与最大回撤，实现真正风险中性';
                    } else if (s.key === 'max_sharpe') {
                        highlightLogic = '<strong>Ledoit-Wolf 收缩最大夏普：</strong>在给定约束下求解最高超额收益风险比';
                    } else if (s.key === 'balanced') {
                        highlightLogic = '<strong>传统资金对半平分：</strong>资金均衡，但纳指波动大导致承担了61%方差风险';
                    } else if (s.key === 'growth') {
                        highlightLogic = '<strong>进取型成长进攻：</strong>高贝塔科技敞口，享受牛市最强成长弹性';
                    } else if (s.key === 'conservative') {
                        highlightLogic = '<strong>稳健底仓压舱石：</strong>以标普500低波动为主，防守回撤最强';
                    }

                    mHtml += `<tr class="quant-matrix-row" data-strategy="${s.key}">
                        <td style="font-weight:600;white-space:nowrap">${s.icon || ''} ${s.name}</td>
                        <td>${typeBadge}</td>
                        <td style="font-weight:600">${nqW}% : ${spW}%</td>
                        <td>${riskBadge}</td>
                        <td><strong>${vol}</strong></td>
                        <td style="white-space:nowrap"><strong style="color:var(--accent2)">${sharpe}</strong> <span style="color:var(--txt3);font-size:0.75rem">/</span> <span style="color:var(--ok);font-size:0.825rem;font-weight:600" title="索提诺比率 (仅惩罚下行负波动)">${sortino}</span></td>
                        <td style="white-space:nowrap">${retStr} / ${medFinal}</td>
                        <td style="font-size:0.75rem;color:var(--txt2)">${highlightLogic}</td>
                        <td style="text-align:center;white-space:nowrap">
                            <button class="btn-jump-strat" data-strategy="${s.key}" data-category="${s.category || 'traditional'}">方案 ▸</button>
                            <button class="btn-sim-matrix" data-strategy="${s.key}" title="以此方案配置直接启动蒙特卡洛推演" style="margin-left:6px;padding:4px 8px;font-size:0.75rem;border-radius:4px;border:1px solid rgba(99,102,241,0.3);background:rgba(99,102,241,0.08);color:var(--accent2);cursor:pointer;font-weight:600;">推演 🚀</button>
                        </td>
                    </tr>`;
                });
                matrixTbody.innerHTML = mHtml;

                // 绑定直达方案点击事件
                matrixTbody.querySelectorAll('.btn-jump-strat').forEach(btn => {
                    btn.onclick = () => {
                        const stratKey = btn.dataset.strategy;
                        const stratCat = btn.dataset.category;
                        const activeFilterBtn = document.querySelector('#pf-category-filter .seg-btn.on');
                        const currentCat = activeFilterBtn?.dataset?.category || 'ALL';

                        // 若当前过滤隐藏了目标策略，切换到相应分类或全部
                        if (currentCat !== 'ALL' && currentCat !== stratCat) {
                            const targetFilterBtn = document.querySelector(`#pf-category-filter .seg-btn[data-category="${stratCat}"]`) ||
                                                    document.querySelector('#pf-category-filter .seg-btn[data-category="ALL"]');
                            if (targetFilterBtn) targetFilterBtn.click();
                        }

                        const targetCard = document.getElementById(`pf-card-${stratKey}`);
                        if (targetCard) {
                            targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            targetCard.classList.remove('highlight-pulse');
                            void targetCard.offsetWidth; // 触发 reflow 重新执行动画
                            targetCard.classList.add('highlight-pulse');
                            setTimeout(() => targetCard.classList.remove('highlight-pulse'), 3500);
                        }
                    };
                });

                // 绑定矩阵方案一键推演事件
                matrixTbody.querySelectorAll('.btn-sim-matrix').forEach(btn => {
                    btn.onclick = () => {
                        const stratKey = btn.dataset.strategy;
                        const s = strategies.find(x => x.key === stratKey);
                        if (!s) return;
                        const target = (s.practical?.allocations?.length) ? s.practical : s.ideal;
                        const fundWeightMap = {};
                        (target?.allocations || []).forEach(a => {
                            fundWeightMap[a.code] = a.actual_weight || a.weight || (1 / (target.allocations.length || 1));
                        });
                        loadFundsIntoSimulator(fundWeightMap, true, `${s.name}`);
                    };
                });
            }

            // 渲染马克维茨均值-方差有效前沿交互图表看板
            renderEfficientFrontier(strategies, dynParams);

            // 渲染历史极端危机压力测试看板
            renderStressTest(_activeStressScenario || 'gfc', monthly, dynParams);

            let html = '';
            strategies.forEach(s => {
                const idealAllocs = s.ideal?.allocations || [];
                const practicalAllocs = s.practical?.allocations || [];
                const cat = s.category || 'traditional';
                const catBadge = cat === 'quant'
                    ? `<span class="tag" style="background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;font-weight:600;margin-left:6px">💎 ${s.tag || '量化专区'}</span>`
                    : `<span class="tag" style="background:var(--surface2);color:var(--txt2);margin-left:6px">${s.tag || '经典风格'}</span>`;

                html += `<div class="card pf-card" id="pf-card-${s.key}" data-category="${cat}">
                    <div class="pf-card-header">
                        <div class="pf-card-title-group">
                            <span class="pf-strat-icon">${s.icon || '📐'}</span>
                            <div>
                                <h3 class="pf-strat-name">${s.name}</h3>
                                <div class="pf-strat-badges">
                                    <span class="tag pf-weight-pill">📈 ${Math.round((s.nq_pct||0)*100)}% 纳指 + 📊 ${Math.round((1-(s.nq_pct||0))*100)}% 标普</span>
                                    ${catBadge}
                                </div>
                            </div>
                        </div>
                    </div>
                    <p style="color:var(--txt2);font-size:.8125rem;margin-bottom:1rem;line-height:1.5">${s.description || ''}</p>

                    <div class="pf-tabs" data-strategy="${s.key}">
                        <button class="pf-tab on" data-variant="ideal">
                            <span>🎯</span> 理论最优
                            <span class="pf-tab-sub">无申购限制</span>
                        </button>
                        <button class="pf-tab" data-variant="practical">
                            <span>🛒</span> 实际可买
                            <span class="pf-tab-sub">穿透真实限额</span>
                        </button>
                    </div>

                    <div class="pf-panel" id="pf-${s.key}-ideal">
                        <p style="color:var(--txt3);font-size:.75rem;margin:.5rem 0">${s.ideal?.note || ''}</p>
                        <div class="pf-tier-alloc">
                            <div class="pf-table-box">${renderVariantTable(s.ideal, s.key)}</div>
                            ${renderVariantDonut(s.ideal, s, 'ideal')}
                        </div>
                        <div class="pf-tier-analytics">
                            <div class="pf-analytics-col">${renderVariantSim(s.ideal, years)}</div>
                            <div class="pf-analytics-col">${renderRiskContribution(s.ideal, s)}</div>
                        </div>
                        <div class="pf-card-footer">
                            <span style="font-size:0.75rem;color:var(--txt3)">💡 想要自定义定投预算、年限或测试极端市场压力？</span>
                            <button class="btn-simulate-action btn-sim-from-strat" data-strategy="${s.key}" data-variant="ideal">🚀 以该理论配置启动蒙特卡洛推演 ➔</button>
                        </div>
                    </div>

                    <div class="pf-panel" id="pf-${s.key}-practical" style="display:none">
                        <p style="color:${(s.practical?.note || '').includes('额度叠加') ? 'var(--ok)' : 'var(--txt3)'};font-size:.78rem;font-weight:500;margin:.5rem 0">${s.practical?.note || ''}</p>
                        <div class="pf-tier-alloc">
                            <div class="pf-table-box">${renderVariantTable(s.practical, s.key)}</div>
                            ${renderVariantDonut(s.practical, s, 'practical')}
                        </div>
                        <div class="pf-tier-analytics">
                            <div class="pf-analytics-col">${renderVariantSim(s.practical, years)}</div>
                            <div class="pf-analytics-col">${renderRiskContribution(s.practical, s)}</div>
                        </div>
                        <div class="pf-card-footer">
                            <span style="font-size:0.75rem;color:var(--txt3)">💡 想要自定义定投预算、年限或测试极端市场压力？</span>
                            <button class="btn-simulate-action btn-sim-from-strat" data-strategy="${s.key}" data-variant="practical">🚀 以该可买配置启动蒙特卡洛推演 ➔</button>
                        </div>
                    </div>
                </div>`;
            });
            document.getElementById('pf-container').innerHTML = html;
            document.getElementById('pf-container').classList.remove('ld');

            // 保持当前选中的分类筛选状态
            applyPortfolioCategoryFilter();

            // 绑定 tab 切换
            document.querySelectorAll('.pf-tabs').forEach(tabs => {
                tabs.querySelectorAll('.pf-tab').forEach(tab => {
                    tab.addEventListener('click', () => {
                        const key = tabs.dataset.strategy;
                        const variant = tab.dataset.variant;
                        tabs.querySelectorAll('.pf-tab').forEach(t => t.classList.remove('on'));
                        tab.classList.add('on');
                        tabs.parentElement.querySelectorAll('.pf-panel').forEach(p => p.style.display = 'none');
                        const panel = document.getElementById(`pf-${key}-${variant}`);
                        if (panel) panel.style.display = '';
                    });
                });
            });

            // 绑定方案卡片一键启动模拟推演事件
            document.querySelectorAll('.btn-sim-from-strat').forEach(btn => {
                btn.onclick = () => {
                    const stratKey = btn.dataset.strategy;
                    const variant = btn.dataset.variant;
                    const s = strategies.find(x => x.key === stratKey);
                    if (!s) return;
                    const target = s[variant];
                    const fundWeightMap = {};
                    (target?.allocations || []).forEach(a => {
                        fundWeightMap[a.code] = a.actual_weight || a.weight || (1 / (target.allocations.length || 1));
                    });
                    loadFundsIntoSimulator(fundWeightMap, true, `${s.name} (${variant === 'practical' ? '实际可买' : '理论最优'})`);
                };
            });

            // 画饼图
            strategies.forEach(s => {
                ['ideal', 'practical'].forEach(vk => {
                    const cid = `ch-${s.key}-${vk}`;
                    const el = document.getElementById(cid);
                    const allocs = s[vk]?.allocations || [];
                    if (!el || !allocs.length) return;
                    pfCharts[cid] = new Chart(el, {
                        type: 'doughnut',
                        data: {
                            labels: allocs.map(a => (a.name || '').replace(/[（(]QDII[）)]/gi, '').trim()),
                            datasets: [{
                                data: allocs.map(a => a.monthly),
                                backgroundColor: pieColors,
                                borderWidth: 0,
                                hoverOffset: 8,
                                borderRadius: 6,
                                spacing: 3
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            cutout: '58%',
                            layout: { padding: 4 },
                            plugins: { 
                                legend: { 
                                    display: false 
                                },
                                tooltip: {
                                    backgroundColor: 'rgba(15, 23, 42, 0.92)',
                                    titleFont: { size: 12, family: 'system-ui, -apple-system, sans-serif', weight: 'normal' },
                                    bodyFont: { size: 12, family: 'system-ui, -apple-system, sans-serif', weight: 'bold' },
                                    padding: 10,
                                    cornerRadius: 6,
                                    boxPadding: 4,
                                    displayColors: true,
                                    usePointStyle: true,
                                    callbacks: {
                                        label: function(ctx) {
                                            const val = ctx.raw || 0;
                                            const alloc = allocs[ctx.dataIndex];
                                            const pct = alloc ? (alloc.actual_weight * 100).toFixed(0) : Math.round((val / (allocs.reduce((sum, x) => sum + x.monthly, 0) || 1)) * 100);
                                            return ` ${alloc?.name || ctx.label}: ${val}元/月 (${pct}%)`;
                                        }
                                    }
                                }
                            }
                        }
                    });
                });
            });
        } catch (e) {
            document.getElementById('pf-container').innerHTML = `<p style="color:var(--err);text-align:center;padding:2rem">计算失败: ${e.message}</p>`;
            document.getElementById('pf-container').classList.remove('ld');
        }
        btn.disabled = false; btn.textContent = '重新计算';
    }

    // ===== 本地联合蒙特卡洛组合模拟（前端高效向量化执行）=====
    // Worker 管理器：优先使用 Web Worker 在后台线程执行，避免阻塞 UI
    // 使用消息 ID 路由机制支持并发调用
    let _simWorker = null;
    let _workerSupported = typeof Worker !== 'undefined';
    let _dynamicParams = null;
    let _dynamicParamsFetched = false;  // 区分"未获取"和"获取到null"
    let _msgId = 0;
    const _pendingPromises = new Map();  // id -> { resolve, fallbackArgs }

    let _simulationsData = null;
    // 惰性加载 simulations.json 中的动态参数（失败时回退到 config 静态参数）
    async function getDynamicParams() {
        if (_dynamicParamsFetched) return _dynamicParams;
        _dynamicParamsFetched = true;
        try {
            const resp = await fetch('data/simulations.json?v=' + Date.now());
            const data = await resp.json();
            _simulationsData = data;
            _dynamicParams = data.params || null;
        } catch (e) {
            console.warn('无法加载动态参数，使用静态参数:', e);
            _dynamicParams = null;
        }
        return _dynamicParams;
    }

    function getSimWorker() {
        if (!_simWorker && _workerSupported) {
            try {
                _simWorker = new Worker('js/sim-worker.js');
                // 统一消息路由：根据 id 分发到对应的 Promise
                _simWorker.onmessage = (e) => {
                    const { id, result, error } = e.data;
                    const pending = _pendingPromises.get(id);
                    if (!pending) return;
                    _pendingPromises.delete(id);
                    if (error) {
                        console.warn('Worker 模拟失败，回退到主线程:', error);
                        pending.resolve(localSimulatePortfolio(...pending.fallbackArgs));
                    } else {
                        pending.resolve(result);
                    }
                };
                _simWorker.onerror = (e) => {
                    console.warn('Worker 全局错误，所有待处理任务回退到主线程:', e.message);
                    for (const [id, pending] of _pendingPromises) {
                        _pendingPromises.delete(id);
                        pending.resolve(localSimulatePortfolio(...pending.fallbackArgs));
                    }
                    _simWorker = null;
                    _workerSupported = false;
                };
            } catch (e) {
                console.warn('Web Worker 不可用，回退到主线程模拟:', e);
                _workerSupported = false;
            }
        }
        return _simWorker;
    }

    function simulateViaWorker(funds, weights, years, budget, dynamicParams, dynamicDCA = false, sensitivity = 'standard') {
        return new Promise((resolve) => {
            const worker = getSimWorker();
            const fallbackArgs = [funds, weights, years, budget, dynamicParams, dynamicDCA, sensitivity];
            if (!worker) {
                resolve(localSimulatePortfolio(...fallbackArgs));
                return;
            }
            const cfg = ALGO_CONFIG;
            const effectiveParams = dynamicParams || cfg.simulation.params;
            const effectiveConfig = { ...cfg, simulation: { ...cfg.simulation, params: effectiveParams } };
            const id = ++_msgId;
            _pendingPromises.set(id, { resolve, fallbackArgs });
            worker.postMessage({ id, funds, weights, years, budget, config: effectiveConfig, dynamicDCA, sensitivity });
        });
    }

    function localSimulatePortfolio(funds, weights, years, budget, dynamicParams, dynamicDCA = false, sensitivity = 'standard') {
        const cfg = ALGO_CONFIG;
        const N = cfg.simulation.n_sims_frontend;
        const months = years * 12;
        const totalInvested = budget * months;
        const finalValues = new Array(N).fill(0);
        
        const rho = cfg.simulation.correlation_nq_sp;
        const params = dynamicParams || cfg.simulation.params;
        const defaults = cfg.defaults;
        const tradingDays = cfg.allocation.trading_days_per_month;
        
        const z_fx = new Float64Array(N * months);
        const z_idx1 = new Float64Array(N * months);
        const z_idx2 = new Float64Array(N * months);
        const monthlyWealth = new Float64Array(N * months);

        const isDual = !!dynamicDCA;
        const smartMonthlyWealth = isDual ? new Float64Array(N * months) : null;
        const smartInvestTotals = isDual ? new Float64Array(N) : null;

        const sensMap = {
            conservative: [0.8, 1.2, 0.8],
            standard: [0.6, 1.5, 1.5],
            aggressive: [0.5, 1.8, 2.2]
        };
        const [minMult, maxMult, sensK] = sensMap[sensitivity] || sensMap.standard;
        
        let r = 123456789;
        const rn = () => { r = (r * 1664525 + 1013904223) & 0xFFFFFFFF; return (r >>> 0) / 0xFFFFFFFF; };
        const boxMuller = () => {
            const u1 = rn() || 1e-10;
            const u2 = rn() || 1e-10;
            return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
        };
        
        for (let i = 0; i < N * months; i++) {
            z_fx[i] = boxMuller();
            z_idx1[i] = boxMuller();
            z_idx2[i] = boxMuller();
        }
        
        funds.forEach((fund, fIdx) => {
            const weight = weights[fIdx];
            if (weight <= 0) return;
            
            const fundBudget = budget * weight;
            const isSP = (fund.index_type || '').includes('标普');
            const te = fund.tracking_error || defaults.tracking_error_for_simulation;
            const fee = (fund.mgmt_fee || defaults.mgmt_fee) + (fund.custody_fee || defaults.custody_fee);
            
            const retM = (isSP ? params.sp500_return : params.nasdaq_return) / 12;
            const volM = (isSP ? params.sp500_vol : params.nasdaq_vol) / Math.sqrt(12);
            const teV = te / Math.sqrt(12);
            const fxM = params.fx_drift / 12;
            const fxV = params.fx_vol / Math.sqrt(12);
            const feeM = fee / 12;
            const divM = params.dividend_yield / 12 * (1 - params.dividend_tax);
            const purchaseFeeRate = fund.purchase_fee || defaults.purchase_fee;
            const invest = fundBudget * (1 - purchaseFeeRate);

            const expNavArr = new Float64Array(months);
            if (isDual) {
                for (let m = 0; m < months; m++) {
                    expNavArr[m] = Math.pow(1 + retM, m + 1);
                }
            }
            
            const z_te = new Float64Array(N * months);
            for (let i = 0; i < N * months; i++) {
                z_te[i] = boxMuller();
            }
            
            for (let s = 0; s < N; s++) {
                let shares = 0;
                let smartShares = 0;
                let nav = 1.0;
                const sOffset = s * months;
                
                for (let m = 0; m < months; m++) {
                    const idx = sOffset + m;
                    
                    const z_index1 = z_idx1[idx];
                    const z_index2 = z_idx2[idx];
                    const z_idx_val = isSP ? (rho * z_index1 + Math.sqrt(1 - rho * rho) * z_index2) : z_index1;
                    
                    const idx_r = retM + volM * z_idx_val;
                    const te_r = teV * z_te[idx];
                    const fx_r = fxM + fxV * z_fx[idx];
                    
                    const fund_r = idx_r + te_r - feeM + divM + fx_r;
                    nav *= (1 + fund_r);
                    shares += invest / nav;
                    monthlyWealth[idx] += shares * nav;

                    if (isDual) {
                        const logDev = Math.log(nav / expNavArr[m]);
                        const mult = Math.max(minMult, Math.min(maxMult, 1.0 - sensK * Math.max(-0.4, Math.min(0.4, logDev))));
                        const smartFundBudget = fundBudget * mult;
                        const smartInvest = smartFundBudget * (1 - purchaseFeeRate);
                        smartShares += smartInvest / nav;
                        smartMonthlyWealth[idx] += smartShares * nav;
                        smartInvestTotals[s] += smartFundBudget;
                    }
                }
            }
        });
        
        const maxLosses = new Float64Array(N);
        const maxDrawdowns = new Float64Array(N);
        const maxStreaks = new Float64Array(N);

        for (let s = 0; s < N; s++) {
            let minPL = 0;
            let peak = 0;
            let maxDD = 0;
            let curStreak = 0;
            let maxStreak = 0;
            const sOffset = s * months;

            for (let m = 0; m < months; m++) {
                const w = monthlyWealth[sOffset + m];
                const inv = budget * (m + 1);
                const pl = (w - inv) / inv;
                if (pl < minPL) minPL = pl;

                if (w > peak) peak = w;
                const dd = peak > 0 ? (w - peak) / peak : 0;
                if (dd < maxDD) maxDD = dd;

                if (dd < -0.02) {
                    curStreak++;
                    if (curStreak > maxStreak) maxStreak = curStreak;
                } else {
                    curStreak = 0;
                }
            }
            finalValues[s] = monthlyWealth[sOffset + months - 1];
            maxLosses[s] = Math.max(0, -minPL) * 100;
            maxDrawdowns[s] = Math.max(0, -maxDD) * 100;
            maxStreaks[s] = maxStreak;
        }

        finalValues.sort((a, b) => a - b);
        maxLosses.sort();
        maxDrawdowns.sort();
        maxStreaks.sort();

        const mean = finalValues.reduce((a, b) => a + b, 0) / N;
        const ret = totalInvested > 0 ? (mean / totalInvested - 1) * 100 : 0;

        const maxLossP50 = +maxLosses[Math.floor(N * 0.5)].toFixed(1);
        const maxLossP95 = +maxLosses[Math.floor(N * 0.95)].toFixed(1);
        const mddP50 = +maxDrawdowns[Math.floor(N * 0.5)].toFixed(1);
        const mddP95 = +maxDrawdowns[Math.floor(N * 0.95)].toFixed(1);
        const recoveryMonths = Math.round(maxStreaks[Math.floor(N * 0.5)]) || 10;

        // 分析法计算加权组合索提诺比率
        let nqW = 0, spW = 0;
        funds.forEach((f, idx) => {
            const w = weights[idx] || 0;
            if ((f.index_type || '').includes('标普')) spW += w;
            else nqW += w;
        });
        const portMu = nqW * params.nasdaq_return + spW * params.sp500_return;
        const s1_sq = params.nasdaq_vol ** 2;
        const s2_sq = params.sp500_vol ** 2;
        const cov12 = rho * params.nasdaq_vol * params.sp500_vol;
        const portVar = (nqW ** 2) * s1_sq + 2 * nqW * spW * cov12 + (spW ** 2) * s2_sq;
        const portVol = Math.sqrt(Math.max(1e-8, portVar));
        const rf = 0.025;
        const z = (rf - portMu) / (portVol || 1e-4);

        function erf(x) {
            const a1 = 0.254829592, a2 = -0.284496736, a3 = 1.421413741, a4 = -1.453152027, a5 = 1.061405429, p = 0.3275911;
            const sign = x < 0 ? -1 : 1;
            const absX = Math.abs(x);
            const t = 1.0 / (1.0 + p * absX);
            const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-absX * absX);
            return sign * y;
        }
        const cdf_z = 0.5 * (1 + erf(z / Math.SQRT2));
        const pdf_z = Math.exp(-0.5 * z * z) / Math.sqrt(2 * Math.PI);
        const downVar = (portVol ** 2) * ((z * z + 1) * cdf_z + z * pdf_z);
        const downVol = Math.sqrt(Math.max(1e-8, downVar));
        const sortino = downVol > 0 ? (portMu - rf) / downVol : 0;
        
        const stdResult = {
            totalInvested: Math.round(totalInvested),
            medianFinal: Math.round(finalValues[Math.floor(N * 0.5)]),
            p5: Math.round(finalValues[Math.floor(N * 0.05)]),
            p25: Math.round(finalValues[Math.floor(N * 0.25)]),
            p75: Math.round(finalValues[Math.floor(N * 0.75)]),
            p95: Math.round(finalValues[Math.floor(N * 0.95)]),
            annualReturn: +(ret / years).toFixed(2),
            meanReturnPct: +ret.toFixed(2),
            roiMultiple: +(finalValues[Math.floor(N * 0.5)] / totalInvested).toFixed(2),
            maxLossP50,
            maxLossP95,
            mddP50,
            mddP95,
            recoveryMonths,
            sortinoRatio: +sortino.toFixed(2),
            downsideVol: +(downVol * 100).toFixed(1)
        };

        if (!isDual) {
            return stdResult;
        }

        // 智能估值定投统计
        const smartFinalValues = new Array(N);
        const smartMaxLosses = new Float64Array(N);
        const smartMaxDrawdowns = new Float64Array(N);
        const smartMaxStreaks = new Float64Array(N);

        for (let s = 0; s < N; s++) {
            let minPL = 0;
            let peak = 0;
            let maxDD = 0;
            let curStreak = 0;
            let maxStreak = 0;
            const sOffset = s * months;
            const avgMonthlyBudget = smartInvestTotals[s] / months;

            for (let m = 0; m < months; m++) {
                const w = smartMonthlyWealth[sOffset + m];
                const inv = avgMonthlyBudget * (m + 1);
                const pl = (w - inv) / (inv || 1);
                if (pl < minPL) minPL = pl;

                if (w > peak) peak = w;
                const dd = peak > 0 ? (w - peak) / peak : 0;
                if (dd < maxDD) maxDD = dd;

                if (dd < -0.02) {
                    curStreak++;
                    if (curStreak > maxStreak) maxStreak = curStreak;
                } else {
                    curStreak = 0;
                }
            }
            smartFinalValues[s] = smartMonthlyWealth[sOffset + months - 1];
            smartMaxLosses[s] = Math.max(0, -minPL) * 100;
            smartMaxDrawdowns[s] = Math.max(0, -maxDD) * 100;
            smartMaxStreaks[s] = maxStreak;
        }

        smartFinalValues.sort((a, b) => a - b);
        smartMaxLosses.sort();
        smartMaxDrawdowns.sort();
        smartMaxStreaks.sort();

        let sumSmartInvest = 0;
        for (let s = 0; s < N; s++) sumSmartInvest += smartInvestTotals[s];
        const avgSmartInvest = sumSmartInvest / N;

        const smartMean = smartFinalValues.reduce((a, b) => a + b, 0) / N;
        const smartRet = avgSmartInvest > 0 ? (smartMean / avgSmartInvest - 1) * 100 : 0;
        const smartMedian = smartFinalValues[Math.floor(N * 0.5)];
        const smartCagr = avgSmartInvest > 0 ? (Math.pow(smartMedian / avgSmartInvest, 1 / years) - 1) * 100 : 0;
        const stdCagr = (Math.pow(stdResult.medianFinal / totalInvested, 1 / years) - 1) * 100;

        const smartLossP50 = +smartMaxLosses[Math.floor(N * 0.5)].toFixed(1);
        const smartLossP95 = +smartMaxLosses[Math.floor(N * 0.95)].toFixed(1);
        const smartMddP50 = +smartMaxDrawdowns[Math.floor(N * 0.5)].toFixed(1);
        const smartMddP95 = +smartMaxDrawdowns[Math.floor(N * 0.95)].toFixed(1);
        const smartRecMo = Math.round(smartMaxStreaks[Math.floor(N * 0.5)]) || 10;

        const smartResult = {
            totalInvested: Math.round(avgSmartInvest),
            medianFinal: Math.round(smartMedian),
            p5: Math.round(smartFinalValues[Math.floor(N * 0.05)]),
            p25: Math.round(smartFinalValues[Math.floor(N * 0.25)]),
            p75: Math.round(smartFinalValues[Math.floor(N * 0.75)]),
            p95: Math.round(smartFinalValues[Math.floor(N * 0.95)]),
            annualReturn: +smartCagr.toFixed(2),
            meanReturnPct: +smartRet.toFixed(2),
            roiMultiple: +(smartMedian / avgSmartInvest).toFixed(2),
            maxLossP50: smartLossP50,
            maxLossP95: smartLossP95,
            mddP50: smartMddP50,
            mddP95: smartMddP95,
            recoveryMonths: smartRecMo,
            sortinoRatio: stdResult.sortinoRatio,
            downsideVol: stdResult.downsideVol
        };

        const alphaResult = {
            wealthGain: Math.round(smartMedian - stdResult.medianFinal),
            wealthGainPct: +((smartMedian / stdResult.medianFinal - 1) * 100).toFixed(1),
            cagrGain: +(smartCagr - stdCagr).toFixed(2),
            efficiencyGainPct: +(((smartMedian / avgSmartInvest) / (stdResult.medianFinal / totalInvested) - 1) * 100).toFixed(1),
            maxLossReduction: +(maxLossP50 - smartLossP50).toFixed(1)
        };

        return {
            isDualTrack: true,
            standard: stdResult,
            smart: smartResult,
            alpha: alphaResult
        };
    }

    // ===== 客户端本地组合比例计算（在API不可用时提供兜底）=====
    function localCalculatePortfolio(years, budget) {
        const cfg = ALGO_CONFIG;
        const fundSel = cfg.fund_selection;
        const tradingDays = cfg.allocation.trading_days_per_month;
        const defaults = cfg.defaults;

        function isBuyable(f) {
            const status = f.limit_status || '';
            const limit = f.daily_limit;
            return !(status.includes('暂停申购') || (status.includes('暂停') && limit == null) || status.includes('未开通'));
        }

        function pickFundsByStyle(nqPct, onlyBuyable = false) {
            let nq = FUND_DATA.filter(f => f.index_type === '纳斯达克100');
            let sp = FUND_DATA.filter(f => f.index_type === '标普500');
            if (onlyBuyable) {
                nq = nq.filter(isBuyable);
                sp = sp.filter(isBuyable);
            }
            const nqMedianTE = calcMedianTE(nq);
            const spMedianTE = calcMedianTE(sp);
            const nqScored = nq.map(f => ({ ...f, score: scoreFund(f, nqMedianTE) })).sort((a, b) => b.score - a.score);
            const spScored = sp.map(f => ({ ...f, score: scoreFund(f, spMedianTE) })).sort((a, b) => b.score - a.score);

            function selectDistinctFamilies(rankedList, topN) {
                const seen = new Set();
                const selected = [];
                for (const f of rankedList) {
                    const fam = f.family_id || f.code;
                    if (!seen.has(fam)) {
                        seen.add(fam);
                        selected.push(f);
                        if (selected.length >= topN) break;
                    }
                }
                return selected;
            }

            const rnq = selectDistinctFamilies(nqScored, fundSel.nasdaq_top_n);
            const rsp = selectDistinctFamilies(spScored, fundSel.sp500_top_n);

            const items = [];
            const nqS = rnq.reduce((sum, f) => sum + f.score, 0);
            if (nqS > 0) {
                rnq.forEach(f => items.push({ fund: f, weight: (f.score / nqS) * nqPct }));
            }
            const spS = rsp.reduce((sum, f) => sum + f.score, 0);
            if (spS > 0) {
                rsp.forEach(f => items.push({ fund: f, weight: (f.score / spS) * (1 - nqPct) }));
            }
            return items;
        }

        function allocateIdeal(items) {
            const allocs = items.map(item => {
                const f = item.fund;
                const w = item.weight;
                const monthly = budget * w;
                const daily = monthly / tradingDays;
                const fee = +((f.mgmt_fee || 0) + (f.custody_fee || 0) + (f.sales_fee || 0)).toFixed(4);
                return {
                    code: f.code, name: f.name, index_type: f.index_type || '',
                    share_class: f.share_class || 'A', family_id: f.family_id || '',
                    weight: +w.toFixed(4), daily: +daily.toFixed(1), monthly: Math.round(monthly),
                    fee: fee,
                    tracking_error: f.tracking_error,
                    tracking_difference: f.tracking_difference != null ? f.tracking_difference : null,
                    information_ratio: f.information_ratio != null ? f.information_ratio : null,
                    score: f.score || 0,
                    daily_limit: f.daily_limit || null, limit_status: f.limit_status || '',
                    direct_daily_limit: f.direct_daily_limit || null, direct_limit_status: f.direct_limit_status || '',
                    quota_sharing: f.quota_sharing || 'SHARED', quota_shared_desc: f.quota_shared_desc || '',
                    exceeds_limit: false,
                    is_stacked: false,
                };
            });
            const total = allocs.reduce((sum, a) => sum + a.monthly, 0);
            if (total > 0) {
                allocs.forEach(a => a.actual_weight = +(a.monthly / total).toFixed(4));
            }
            return allocs;
        }

        function allocatePractical(items) {
            const allocs = items.map(item => {
                const f = item.fund;
                const w = item.weight;
                const limit = f.daily_limit;
                const status = f.limit_status || '';
                const isSuspended = status.includes('暂停申购') || (status.includes('暂停') && limit === null);
                return {
                    fund: f, weight: w, limit: (limit !== null && limit !== undefined) ? limit : Infinity,
                    actual_daily: 0.0, actual_monthly: 0.0, exceeds_limit: false, is_suspended: isSuspended,
                    is_stacked: false,
                };
            });

            let remainingBudget = budget;
            const activeAllocs = allocs.filter(a => !a.is_suspended);

            function waterfall(candidates) {
                while (remainingBudget > 0.01) {
                    const available = candidates.filter(a => !a.exceeds_limit);
                    if (available.length === 0) break;

                    let totalWeight = available.reduce((sum, a) => sum + a.weight, 0);
                    if (totalWeight <= 0) {
                        available.forEach(a => a.weight = 1.0 / available.length);
                        totalWeight = 1.0;
                    }

                    let allocatedInThisStep = false;
                    for (const a of available) {
                        const extraMonthly = remainingBudget * (a.weight / totalWeight);
                        const targetMonthly = a.actual_monthly + extraMonthly;
                        const targetDaily = targetMonthly / tradingDays;
                        const limitMonthly = a.limit * tradingDays;

                        if (targetDaily >= a.limit) {
                            const added = limitMonthly - a.actual_monthly;
                            a.actual_monthly = limitMonthly;
                            a.actual_daily = a.limit;
                            a.exceeds_limit = true;
                            remainingBudget -= added;
                            allocatedInThisStep = true;
                        } else {
                            a.actual_monthly = targetMonthly;
                            a.actual_daily = targetDaily;
                            remainingBudget -= extraMonthly;
                            allocatedInThisStep = true;
                        }
                    }
                    if (!allocatedInThisStep) break;
                }
            }

            if (activeAllocs.length > 0) {
                waterfall(activeAllocs);
            }

            // 额度用尽时自动启动多份额额度叠加策略
            if (remainingBudget > 10) {
                const existingCodes = new Set(activeAllocs.map(a => a.fund.code));
                // 优先从受限额度封顶 (exceeds_limit) 的标的提取同门份额，保持策略的纳指/标普资产类别权重平衡
                const cappedAllocs = activeAllocs.filter(a => a.exceeds_limit);
                const uncappedAllocs = activeAllocs.filter(a => !a.exceeds_limit);
                for (const a of [...cappedAllocs, ...uncappedAllocs]) {
                    // 若份额属于共享额度 (quota_sharing === 'SHARED')，同门份额共享同一额度池，打满时无法通过同门叠加，必须跳过
                    if (a.fund.quota_sharing !== 'SHARED') {
                        const siblings = a.fund.siblings || [];
                        for (const sibCode of siblings) {
                            if (!existingCodes.has(sibCode)) {
                                const sib = FUND_DATA.find(x => x.code === sibCode);
                                if (sib && isBuyable(sib)) {
                                    candidates.push(sib);
                                    existingCodes.add(sibCode);
                                }
                            }
                        }
                    }
                }
                const existingCappedFamilies = new Set(
                    cappedAllocs.filter(a => a.fund.quota_sharing === 'SHARED').map(a => a.fund.family_id)
                );
                const otherBuyable = FUND_DATA.filter(f => isBuyable(f) && !existingCodes.has(f.code) && !existingCappedFamilies.has(f.family_id));
                const medianTENq = calcMedianTE(FUND_DATA.filter(f => f.index_type === '纳斯达克100'));
                const medianTESp = calcMedianTE(FUND_DATA.filter(f => f.index_type === '标普500'));
                const scoredOther = otherBuyable.map(f => ({
                    ...f,
                    score: scoreFund(f, f.index_type === '标普500' ? medianTESp : medianTENq)
                })).sort((a, b) => b.score - a.score);
                candidates.push(...scoredOther);

                for (const cf of candidates) {
                    if (remainingBudget <= 0.01) break;
                    const clim = cf.daily_limit;
                    const newA = {
                        fund: cf, weight: 1.0, limit: (clim !== null && clim !== undefined) ? clim : Infinity,
                        actual_daily: 0.0, actual_monthly: 0.0, exceeds_limit: false, is_suspended: false,
                        is_stacked: true,
                    };
                    activeAllocs.push(newA);
                    allocs.push(newA);
                    waterfall([newA]);
                }
            }

            const result = allocs.map(a => {
                const f = a.fund;
                const fee = +((f.mgmt_fee || 0) + (f.custody_fee || 0) + (f.sales_fee || 0)).toFixed(4);
                return {
                    code: f.code, name: f.name, index_type: f.index_type || '',
                    share_class: f.share_class || 'A', family_id: f.family_id || '',
                    weight: +a.weight.toFixed(4), daily: +a.actual_daily.toFixed(1), monthly: Math.round(a.actual_monthly),
                    fee: fee,
                    tracking_error: f.tracking_error,
                    tracking_difference: f.tracking_difference != null ? f.tracking_difference : null,
                    information_ratio: f.information_ratio != null ? f.information_ratio : null,
                    score: f.score || 0,
                    daily_limit: a.limit !== Infinity ? a.limit : null, limit_status: f.limit_status || '',
                    direct_daily_limit: f.direct_daily_limit || null, direct_limit_status: f.direct_limit_status || '',
                    quota_sharing: f.quota_sharing || 'SHARED', quota_shared_desc: f.quota_shared_desc || '',
                    exceeds_limit: a.exceeds_limit,
                    is_stacked: a.is_stacked || false,
                };
            });

            const total = result.reduce((sum, a) => sum + a.monthly, 0);
            if (total > 0) {
                result.forEach(a => a.actual_weight = +(a.monthly / total).toFixed(4));
            }
            return result;
        }

        function calcLocalRiskAnalysis(allocs) {
            const total = allocs.reduce((sum, a) => sum + (a.monthly || 0), 0);
            if (total <= 0) return null;
            const nqSum = allocs.filter(a => a.index_type === '纳斯达克100').reduce((sum, a) => sum + (a.monthly || 0), 0);
            const spSum = allocs.filter(a => a.index_type === '标普500').reduce((sum, a) => sum + (a.monthly || 0), 0);
            const w_nq = nqSum / total;
            const w_sp = spSum / total;
            const p = cfg.simulation?.params || cfg.simulation?.params_fallback || {
                nasdaq_vol: 0.1937, sp500_vol: 0.1248, nasdaq_return: 0.2154, sp500_return: 0.1642
            };
            const rho = cfg.simulation?.correlation_nq_sp || 0.75;
            const s1_sq = p.nasdaq_vol ** 2;
            const s2_sq = p.sp500_vol ** 2;
            const cov12 = rho * p.nasdaq_vol * p.sp500_vol;
            const port_var = (w_nq ** 2) * s1_sq + 2 * w_nq * w_sp * cov12 + (w_sp ** 2) * s2_sq;
            const port_vol = Math.sqrt(Math.max(1e-8, port_var));
            const mrc_nq = (w_nq * s1_sq + w_sp * cov12) / port_vol;
            const mrc_sp = (w_sp * s2_sq + w_nq * cov12) / port_vol;
            const trc_nq = w_nq * mrc_nq;
            const trc_sp = w_sp * mrc_sp;
            const total_trc = trc_nq + trc_sp;
            const rc_nq = total_trc > 0 ? trc_nq / total_trc : 0.5;
            const rc_sp = total_trc > 0 ? trc_sp / total_trc : 0.5;
            const rf = 0.025;
            const exp_r = w_nq * p.nasdaq_return + w_sp * p.sp500_return;
            const sharpe = (exp_r - rf) / port_vol;

            const z = (rf - exp_r) / (port_vol || 1e-4);
            function erf(x) {
                const a1 = 0.254829592, a2 = -0.284496736, a3 = 1.421413741, a4 = -1.453152027, a5 = 1.061405429, p = 0.3275911;
                const sign = x < 0 ? -1 : 1;
                const absX = Math.abs(x);
                const t = 1.0 / (1.0 + p * absX);
                const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-absX * absX);
                return sign * y;
            }
            const cdf_z = 0.5 * (1 + erf(z / Math.SQRT2));
            const pdf_z = Math.exp(-0.5 * z * z) / Math.sqrt(2 * Math.PI);
            const downVar = (port_vol ** 2) * ((z * z + 1) * cdf_z + z * pdf_z);
            const downVol = Math.sqrt(Math.max(1e-8, downVar));
            const sortino = downVol > 0 ? (exp_r - rf) / downVol : 0;

            return {
                nq_weight: +w_nq.toFixed(4),
                sp_weight: +w_sp.toFixed(4),
                nq_risk_contrib: +rc_nq.toFixed(4),
                sp_risk_contrib: +rc_sp.toFixed(4),
                portfolio_vol: +port_vol.toFixed(4),
                sharpe_ratio: +sharpe.toFixed(4),
                sortino_ratio: +sortino.toFixed(4),
                downside_vol: +(downVol * 100).toFixed(1)
            };
        }

        const strategiesDef = cfg.strategies;
        const scale = budget / (cfg.allocation?.base_budget || 1000);
        const yearKey = String(years);

        function scaleSimulation(stratKey, variantKey) {
            const strat = _simulationsData?.strategies?.find(x => x.key === stratKey);
            const yrData = strat?.[variantKey]?.by_years?.[yearKey];
            if (!yrData) return null;
            return {
                totalInvested: Math.round(yrData.totalInvested * scale),
                medianFinal: Math.round((yrData.median || 0) * scale),
                meanFinal: Math.round((yrData.mean || 0) * scale),
                p5: Math.round((yrData.p5 || 0) * scale),
                p25: Math.round((yrData.p25 || 0) * scale),
                p75: Math.round((yrData.p75 || 0) * scale),
                p95: Math.round((yrData.p95 || 0) * scale),
                annualReturn: yrData.annualReturn || 0,
                meanReturnPct: yrData.meanReturnPct || 0,
                maxLossP50: yrData.maxLossP50 != null ? yrData.maxLossP50 : null,
                maxLossP95: yrData.maxLossP95 != null ? yrData.maxLossP95 : null,
                mddP50: yrData.mddP50 != null ? yrData.mddP50 : null,
                mddP95: yrData.mddP95 != null ? yrData.mddP95 : null,
                recoveryMonths: yrData.recoveryMonths != null ? yrData.recoveryMonths : 10,
                sortinoRatio: strat?.[variantKey]?.risk_analysis?.sortino_ratio != null ? strat[variantKey].risk_analysis.sortino_ratio : null
            };
        }

        return strategiesDef.map(s => {
            const idealItems = pickFundsByStyle(s.nq_pct, false);
            const practicalItems = pickFundsByStyle(s.nq_pct, true);
            const idealAllocations = allocateIdeal(idealItems);
            const practicalAllocations = allocatePractical(practicalItems);
            const hasStacked = practicalAllocations.some(a => a.is_stacked && a.monthly > 0);
            const practicalNote = hasStacked ? '💡 算法已自动启动【多份额额度叠加策略】，成功为您打破单日限购封锁，打满 100% 预算！' : '排除暂停基金，遵守每日限购限额。';

            return {
                key: s.key,
                name: s.name,
                description: s.description,
                icon: s.icon,
                nq_pct: s.nq_pct,
                category: s.category || 'traditional',
                tag: s.tag || '',
                ideal: {
                    allocations: idealAllocations,
                    note: '不考虑限购的理论最优配置。',
                    risk_analysis: calcLocalRiskAnalysis(idealAllocations),
                    simulation: scaleSimulation(s.key, 'ideal')
                },
                practical: {
                    allocations: practicalAllocations,
                    note: practicalNote,
                    risk_analysis: calcLocalRiskAnalysis(practicalAllocations),
                    simulation: scaleSimulation(s.key, 'practical')
                }
            };
        });
    }

    // ===== 初始化 =====
    async function init() {
        initTheme();
        try {
            const t = Date.now();
            const [fundsResp, algoResp, limitResp] = await Promise.all([
                fetch('data/funds.json?v=' + t),
                fetch('data/algorithm.json?v=' + t),
                fetch('data/limit_changes.json?v=' + t).catch(() => null)
            ]);
            FUND_DATA = await fundsResp.json();
            ALGO_CONFIG = await algoResp.json();
            if (limitResp && limitResp.ok) {
                try {
                    LIMIT_CHANGES_DATA = await limitResp.json();
                } catch (e) {}
            }

            renderHome();
            initNav();
            initPresetChips();
            initSimQuickPresets();
            syncSliderBadges();
            renderQuotaBulletin();
            initStressTestTabs();
        } catch (e) {
            document.getElementById('home-stats').innerHTML = '<div class="card"><p style="color:var(--err)">数据加载失败: ' + e.message + '</p></div>';
        }

        // 全局基金代码快速复制监听
        document.addEventListener('click', e => {
            const copyBtn = e.target.closest('.btn-copy-code, .btn-copy-code-action, .trc-copy-btn, .trc-code-btn');
            if (copyBtn) {
                e.preventDefault();
                e.stopPropagation();
                const code = copyBtn.dataset.code;
                if (code) {
                    // 即时行内触觉反馈动效
                    copyBtn.classList.add('copied');
                    const origHtml = copyBtn.innerHTML;
                    if (copyBtn.classList.contains('trc-copy-btn') || copyBtn.classList.contains('btn-copy-code') || copyBtn.classList.contains('btn-copy-code-action')) {
                        copyBtn.innerHTML = '✓';
                    }
                    setTimeout(() => {
                        copyBtn.classList.remove('copied');
                        if (copyBtn.innerHTML === '✓') {
                            copyBtn.innerHTML = origHtml;
                        }
                    }, 1200);

                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(code).then(() => {
                            showToast(`基金代码 ${code} 已复制到剪贴板！`, 'success');
                        }).catch(() => {
                            showToast(`基金代码: ${code}`, 'info');
                        });
                    } else {
                        const input = document.createElement('input');
                        input.value = code;
                        document.body.appendChild(input);
                        input.select();
                        document.execCommand('copy');
                        input.remove();
                        showToast(`基金代码 ${code} 已复制到剪贴板！`, 'success');
                    }
                }
            }
        });

        // 全局键盘快捷键 (/ 或 Ctrl+K 搜基, D 切换深浅主题)
        document.addEventListener('keydown', e => {
            const target = e.target;
            const tag = target ? target.tagName.toLowerCase() : '';
            const isEditing = tag === 'input' || tag === 'textarea' || target?.isContentEditable;
            if (!isEditing) {
                if (e.key === 'd' || e.key === 'D') {
                    e.preventDefault();
                    toggleTheme();
                } else if (e.key === '/' || ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K'))) {
                    e.preventDefault();
                    if (location.hash !== '#ranking') {
                        location.hash = '#ranking';
                    }
                    setTimeout(() => {
                        const searchInput = document.getElementById('rank-search');
                        if (searchInput) {
                            searchInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            searchInput.focus();
                            searchInput.select();
                        }
                    }, 60);
                }
            } else if (e.key === 'Escape' && target?.id === 'rank-search') {
                target.blur();
            }
        });

        // 顶部滚动进度条优雅降级兼容 (针对不支持 animation-timeline 的旧版浏览器)
        const progressEl = document.getElementById('scroll-progress');
        if (progressEl && (!window.CSS || !CSS.supports || !CSS.supports('animation-timeline', 'scroll()'))) {
            window.addEventListener('scroll', () => {
                const totalH = document.documentElement.scrollHeight - window.innerHeight;
                if (totalH > 0) {
                    const ratio = Math.min(1, Math.max(0, window.scrollY / totalH));
                    progressEl.style.transform = `scaleX(${ratio})`;
                    progressEl.style.transformOrigin = '0 50%';
                }
            }, { passive: true });
        }

        // 美股与境内公开市场时钟指示器
        function updateMarketStatusIndicator() {
            const el = document.getElementById('footer-us-market-status');
            if (!el) return;
            try {
                const now = new Date();
                const nyTime = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }));
                const day = nyTime.getDay();
                const totalMins = nyTime.getHours() * 60 + nyTime.getMinutes();
                const isWeekday = day >= 1 && day <= 5;

                if (isWeekday && totalMins >= 570 && totalMins < 960) {
                    el.innerHTML = '<span style="color:var(--ok)">● 美股开盘交易中</span>';
                } else if (isWeekday && totalMins >= 240 && totalMins < 570) {
                    el.innerHTML = '<span style="color:var(--warn)">◑ 美股盘前交易时段</span>';
                } else if (isWeekday && totalMins >= 960 && totalMins < 1200) {
                    el.innerHTML = '<span style="color:var(--warn)">◐ 美股盘后交易时段</span>';
                } else {
                    el.innerHTML = '<span style="color:var(--txt3)">○ 已休市 (等待开盘)</span>';
                }
            } catch (e) {
                el.textContent = '监测正常';
            }
        }
        updateMarketStatusIndicator();
        setInterval(updateMarketStatusIndicator, 60000);

        // 全局便捷悬浮岛滚动监听与交互
        const floatBar = document.getElementById('floating-quick-bar');
        const floatTopBtn = document.getElementById('floating-btn-top');
        const floatSearchBtn = document.getElementById('floating-btn-search');

        if (floatBar) {
            window.addEventListener('scroll', () => {
                if (window.scrollY > 450) {
                    floatBar.style.display = 'flex';
                } else {
                    floatBar.style.display = 'none';
                }
            }, { passive: true });

            if (floatTopBtn) {
                floatTopBtn.addEventListener('click', () => {
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                });
            }

            if (floatSearchBtn) {
                floatSearchBtn.addEventListener('click', () => {
                    if (location.hash !== '#ranking') {
                        location.hash = '#ranking';
                    }
                    setTimeout(() => {
                        const searchInput = document.getElementById('rank-search');
                        if (searchInput) {
                            searchInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            searchInput.focus();
                            searchInput.select();
                        }
                    }, 80);
                });
            }
        }

        // 算法说明折叠
        const algoToggle = document.getElementById('algo-toggle');
        if (algoToggle) {
            algoToggle.addEventListener('click', () => {
                algoToggle.closest('.algo-card').classList.toggle('open');
            });
        }
        document.querySelectorAll('#rank-filter .seg-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('#rank-filter .seg-btn').forEach(b => b.classList.remove('on'));
                btn.classList.add('on');
                renderRanking();
            });
        });
        document.querySelectorAll('#class-filter .seg-btn, #class-filter .filter-pill').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('#class-filter .seg-btn, #class-filter .filter-pill').forEach(b => b.classList.remove('on'));
                btn.classList.add('on');
                renderRanking();
            });
        });
        document.querySelectorAll('#quota-filter .seg-btn, #quota-filter .filter-pill').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('#quota-filter .seg-btn, #quota-filter .filter-pill').forEach(b => b.classList.remove('on'));
                btn.classList.add('on');
                renderRanking();
            });
        });
        const rankSearch = document.getElementById('rank-search');
        if (rankSearch) {
            rankSearch.addEventListener('input', () => {
                renderRanking();
            });
        }
        const rankResetBtn = document.getElementById('rank-filter-reset');
        if (rankResetBtn) {
            rankResetBtn.addEventListener('click', resetRankFilters);
        }
        const rankClearBtn = document.getElementById('rank-search-clear');
        if (rankClearBtn) {
            rankClearBtn.addEventListener('click', () => {
                const s = document.getElementById('rank-search');
                if (s) {
                    s.value = '';
                    s.focus();
                }
                renderRanking();
            });
        }

        // 移动端专属双视图切换 (智能卡片 vs 全景表格)
        const rankViewToggle = document.getElementById('rank-view-toggle');
        if (rankViewToggle) {
            rankViewToggle.querySelectorAll('.view-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    applyRankView(btn.dataset.view);
                });
            });
        }

        // 绑定全景对比表格导出图片按钮 (先打开勾选弹窗)
        const rankExportBtn = document.getElementById('btn-rank-export');
        if (rankExportBtn && !rankExportBtn._bound) {
            rankExportBtn._bound = true;
            rankExportBtn.addEventListener('click', () => {
                openRankExportSelectModal(rankExportBtn);
            });
        }

        applyRankView(currentRankView);
        window.addEventListener('resize', () => {
            applyRankView(currentRankView);
        });
        document.getElementById('sim-m').addEventListener('input', e => {
            const val = fmtMoney(e.target.value);
            document.getElementById('sim-mv').textContent = val;
            const b = document.getElementById('sim-mv-badge');
            if (b) b.textContent = val + ' / 月';
            updateWeightDisplays();
        });
        document.getElementById('sim-y').addEventListener('input', e => {
            document.getElementById('sim-yv').textContent = e.target.value + '年';
            const b = document.getElementById('sim-yv-badge');
            if (b) b.textContent = e.target.value + ' 年';
        });
        document.getElementById('pf-m').addEventListener('input', e => {
            const val = fmtMoney(e.target.value);
            document.getElementById('pf-mv').textContent = val;
            const b = document.getElementById('pf-mv-badge');
            if (b) b.textContent = val + ' / 月';
            const stressBudgetEl = document.getElementById('stress-budget-note');
            if (stressBudgetEl) stressBudgetEl.textContent = `当前推演预算: ${val} / 月`;
            renderStressTest(_activeStressScenario, +e.target.value, _dynamicParams);
        });
        document.getElementById('pf-y').addEventListener('input', e => {
            document.getElementById('pf-yv').textContent = e.target.value + '年';
            const b = document.getElementById('pf-yv-badge');
            if (b) b.textContent = e.target.value + ' 年';
        });
        document.getElementById('btn-sim').addEventListener('click', runSimulation);
        initSmartDCAToggle();
        updateSmartValuationGauge();
        document.getElementById('btn-pf').addEventListener('click', computePortfolio);

        // 定投方案策略分类筛选（经典 / 量化 / 全部）
        const pfCatFilter = document.getElementById('pf-category-filter');
        if (pfCatFilter) {
            pfCatFilter.querySelectorAll('.seg-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    pfCatFilter.querySelectorAll('.seg-btn').forEach(b => b.classList.remove('on'));
                    btn.classList.add('on');
                    applyPortfolioCategoryFilter(btn.dataset.category);
                });
            });
        }

        // 量化全景矩阵折叠/展开
        const qfToggle = document.getElementById('quant-frontier-toggle');
        const qfBody = document.getElementById('quant-frontier-body');
        const qfArrow = document.getElementById('quant-frontier-arrow');
        if (qfToggle && qfBody) {
            qfToggle.addEventListener('click', () => {
                const isHidden = qfBody.style.display === 'none';
                qfBody.style.display = isHidden ? 'block' : 'none';
                if (qfArrow) qfArrow.style.transform = isHidden ? 'rotate(0deg)' : 'rotate(-90deg)';
                if (isHidden && chartPool.frontier) {
                    setTimeout(() => { chartPool.frontier.resize(); }, 50);
                }
            });
        }

        // 基金详情展开（事件委托，只绑定一次）
        document.querySelector('#rank-table').addEventListener('click', e => {
            const trigger = e.target.closest('.fund-name-link, .tbl-rank-code-cell');
            if (!trigger) return;
            if (e.target.closest('.btn-copy-code, .trc-copy-btn, .trc-code-btn, .code-ext-link, .trc-actions-wrap')) return;
            e.preventDefault();
            const tr = trigger.closest('tr');
            if (!tr || tr.classList.contains('fund-detail-row')) return;
            const code = tr.dataset.code;
            const existing = tr.nextElementSibling;
            if (existing && existing.classList.contains('fund-detail-row')) {
                existing.remove();
                return;
            }
            document.querySelectorAll('.fund-detail-row').forEach(r => r.remove());

            const f = FUND_DATA.find(d => d.code === code);
            if (!f) return;

            const detailTr = document.createElement('tr');
            detailTr.className = 'fund-detail-row';
            const colSpan = rankCols.length;
            const fee = (f.mgmt_fee || 0) + (f.custody_fee || 0) + (f.sales_fee || 0);

            // 同门多份额横向比对看板
            let siblingHtml = '';
            if (f.siblings && f.siblings.length > 1) {
                const sibFunds = f.siblings.map(sc => FUND_DATA.find(x => x.code === sc)).filter(Boolean);
                if (sibFunds.length > 1) {
                    siblingHtml = `
                    <div class="sibling-box">
                        <div class="sibling-title">
                            <span>🔄 同门同标的各份额比对看板（${f.family_name || '同一指数基金家族'}）</span>
                            <span style="font-size:0.75rem;font-weight:normal;color:var(--txt3);margin-left:auto;">💡 可搭配不同份额合并定投以提升可买额度</span>
                        </div>
                        <div class="sibling-card-grid">
                            ${sibFunds.map(sf => {
                                const isSelf = sf.code === f.code;
                                const sFee = (sf.mgmt_fee || 0) + (sf.custody_fee || 0) + (sf.sales_fee || 0);
                                return `
                                <div class="sibling-card ${isSelf ? 'active' : ''}" data-code="${sf.code}" title="${isSelf ? '当前查看中' : '点击切换查看此份额详情'}">
                                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.4rem">
                                        <div style="display:flex;align-items:center;gap:4px">
                                            ${shareBadge(sf.share_class)}
                                            <strong style="color:var(--txt)">${sf.code}</strong>
                                        </div>
                                        <span style="font-size:0.75rem;font-weight:700;color:var(--ok)">${(sFee*100).toFixed(2)}%/年</span>
                                    </div>
                                    <div style="font-size:0.75rem;color:var(--txt2);margin-bottom:0.4rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="${sf.name}">${sf.name}</div>
                                    <div style="display:flex;justify-content:space-between;font-size:0.72rem;margin-bottom:2px">
                                        <span style="color:var(--txt3)">代销限购:</span>
                                        <span>${pill(sf.limit_status)}</span>
                                    </div>
                                    <div style="display:flex;justify-content:space-between;font-size:0.72rem;margin-bottom:4px">
                                        <span style="color:var(--txt3)">直销限购:</span>
                                        <span>${sf.direct_limit_status ? pill(sf.direct_limit_status) : '<span style="color:var(--txt3)">—</span>'}</span>
                                    </div>
                                    <div style="display:flex;justify-content:space-between;font-size:0.7rem;color:var(--txt3);border-top:1px dashed var(--border);padding-top:4px;margin-top:4px">
                                        <span>销售服务费: ${(sf.sales_fee || 0) > 0 ? (sf.sales_fee*100).toFixed(2)+'%' : '免'}</span>
                                        <span>申购费: ${(sf.purchase_fee || 0) > 0 ? (sf.purchase_fee*100).toFixed(2)+'%' : '免'}</span>
                                    </div>
                                </div>
                                `;
                            }).join('')}
                        </div>
                    </div>
                    `;
                }
            }

            detailTr.innerHTML = `<td colspan="${colSpan}" class="fund-detail-td">
                ${siblingHtml}
                <div class="fund-detail-grid">
                    
                    <!-- 基础信息 -->
                    <div>
                        <div style="font-weight:700; color:var(--txt); margin-bottom:0.5rem; border-bottom:1px solid var(--border); padding-bottom:0.25rem;">📝 基础信息</div>
                        <div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">份额类别：</strong>${shareBadge(f.share_class)}</div>
                        ${f.full_name ? `<div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">全称：</strong>${f.full_name}</div>` : ''}
                        ${f.family_name ? `<div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">所属家族：</strong>${f.family_name}</div>` : ''}
                        ${f.fund_type ? `<div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">类型：</strong>${f.fund_type}</div>` : ''}
                        ${f.tracking_index ? `<div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">标的：</strong>${f.tracking_index}</div>` : ''}
                    </div>

                    <!-- 管理团队 -->
                    <div>
                        <div style="font-weight:700; color:var(--txt); margin-bottom:0.5rem; border-bottom:1px solid var(--border); padding-bottom:0.25rem;">👔 管理团队</div>
                        ${f.manager_company ? `<div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">基金公司：</strong>${f.manager_company}</div>` : ''}
                        ${f.fund_manager ? `<div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">基金经理：</strong>${f.fund_manager}</div>` : ''}
                        ${f.custodian ? `<div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">托管银行：</strong>${f.custodian}</div>` : ''}
                    </div>

                    <!-- 费率详情 -->
                    <div>
                        <div style="font-weight:700; color:var(--txt); margin-bottom:0.5rem; border-bottom:1px solid var(--border); padding-bottom:0.25rem;">💰 费率详情</div>
                        <div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">综合年费率：</strong><span style="color:var(--ok);font-weight:700">${(fee*100).toFixed(2)}%/年</span></div>
                        <div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">管理费：</strong>${f.mgmt_fee ? (f.mgmt_fee*100).toFixed(2)+'%/年' : '-'}</div>
                        <div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">托管费：</strong>${f.custody_fee ? (f.custody_fee*100).toFixed(2)+'%/年' : '-'}</div>
                        <div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">销售服务费：</strong>${(f.sales_fee || 0) > 0 ? (f.sales_fee*100).toFixed(2)+'%/年' : '0.00% (免)'}</div>
                        ${f.purchase_fee != null ? `<div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">申购费率(前端)：</strong>${(f.purchase_fee*100).toFixed(2)}%</div>` : ''}
                    </div>

                    <!-- 规模与时间 -->
                    <div>
                        <div style="font-weight:700; color:var(--txt); margin-bottom:0.5rem; border-bottom:1px solid var(--border); padding-bottom:0.25rem;">📅 规模与时间</div>
                        ${f.scale ? `<div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">基金规模：</strong>${f.scale.toFixed(2)}亿元</div>` : ''}
                        ${f.inception_date ? `<div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">成立日期：</strong>${f.inception_date}</div>` : ''}
                        ${f.dividend_info ? `<div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">分红：</strong>${f.dividend_info}</div>` : ''}
                    </div>

                    <!-- 限购状态 -->
                    <div>
                        <div style="font-weight:700; color:var(--txt); margin-bottom:0.5rem; border-bottom:1px solid var(--border); padding-bottom:0.25rem;">🛑 限购与额度规则</div>
                        <div style="margin-bottom:0.25rem;display:flex;align-items:center;gap:6px"><strong style="color:var(--txt3)">代销限购：</strong>${pill(f.limit_status)}</div>
                        <div style="margin-bottom:0.25rem;display:flex;align-items:center;gap:6px"><strong style="color:var(--txt3)">直销限购：</strong>${f.direct_limit_status ? pill(f.direct_limit_status) : '<span style="color:var(--txt3)">—</span>'}</div>
                        <div style="margin-top:0.4rem;font-size:0.75rem;padding:4px 6px;border-radius:4px;background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);color:var(--txt2)">
                            <strong style="color:var(--warn)">额度共享：</strong>${f.quota_shared_desc || (f.quota_sharing === 'SHARED' ? '本基金多类份额合并共享单日限额' : '各份额独立限额')}
                        </div>
                    </div>

                    <!-- 量化多因子评估 -->
                    <div>
                        <div style="font-weight:700; color:var(--txt); margin-bottom:0.5rem; border-bottom:1px solid var(--border); padding-bottom:0.25rem;">📊 量化多因子评估</div>
                        <div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">跟踪偏离度(TD/1年)：</strong><span style="font-weight:700;color:${(f.tracking_difference||0)>=0?'var(--up)':'var(--down)'}">${f.tracking_difference != null ? ((f.tracking_difference>=0?'+':'')+(f.tracking_difference*100).toFixed(2)+'%') : '-'}</span></div>
                        <div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">信息比率(IR)：</strong><span style="font-weight:700;color:${(f.information_ratio||0)>=0?'var(--ok)':'var(--txt2)'}">${f.information_ratio != null ? f.information_ratio.toFixed(2) : '-'}</span> <span style="font-size:0.7rem;color:var(--txt3);">(超额/风险)</span></div>
                        <div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">年化跟踪误差(TE)：</strong>${f.tracking_error ? (f.tracking_error*100).toFixed(2)+'%' : '-'}</div>
                        ${f.volatility ? `<div style="margin-bottom:0.25rem"><strong style="color:var(--txt3)">年化波动率：</strong>${(f.volatility*100).toFixed(2)}%</div>` : ''}
                    </div>
                </div>
                ${f.benchmark ? `<div style="margin-top:1rem; padding-top:0.75rem; border-top:1px dashed var(--border); font-size:0.8rem; color:var(--txt3);"><strong>业绩基准：</strong>${f.benchmark}</div>` : ''}
                <div class="fund-detail-actions">
                    <a href="/fund/${f.code}" target="_blank" class="btn-fund-page-action" title="在新标签页中打开这只基金的独立评测专页">
                        📄 打开独立评测专页 ↗
                    </a>
                    <button type="button" class="btn-copy-code-action" data-code="${f.code}">
                        📋 复制基金代码 (${f.code})
                    </button>
                    <button type="button" class="btn-simulate-action btn-sim-single" data-code="${f.code}">
                        🚀 将此基金带入模拟器测试 ➔
                    </button>
                </div>
            </td>`;
            tr.after(detailTr);

            // 绑定单基金一键启动模拟器
            detailTr.querySelector('.btn-sim-single')?.addEventListener('click', () => {
                loadFundsIntoSimulator({ [f.code]: 1.0 }, true, `${f.name} (单基推演)`);
            });

            // 绑定同门卡片点击切换
            detailTr.querySelectorAll('.sibling-card').forEach(card => {
                card.addEventListener('click', () => {
                    const c = card.dataset.code;
                    if (c && c !== f.code) {
                        const targetLink = document.querySelector(`.fund-name-link[data-code="${c}"]`);
                        if (targetLink) {
                            targetLink.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            targetLink.click();
                        }
                    }
                });
            });
        });
    }

    return { init };
})();

document.addEventListener('DOMContentLoaded', App.init);
