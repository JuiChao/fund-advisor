/**
 * 主应用逻辑 - 调用 API 获取预计算结果
 */
const App = (() => {
    let FUND_DATA = [];
    let ALGO_CONFIG = null;
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

        Object.values(chartPool).forEach(ch => {
            if (ch && typeof ch.update === 'function') ch.update();
        });
        Object.values(pfCharts).forEach(ch => {
            if (ch && typeof ch.update === 'function') ch.update();
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
        }
        if (pName === 'simulator') {
            populateSimSelect();
            syncSliderBadges();
        }
        if (pName === 'portfolio') {
            computePortfolio();
            syncSliderBadges();
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
            navToggle.addEventListener('click', () => {
                const isOpen = navLinks.classList.toggle('show');
                navToggle.classList.toggle('open', isOpen);
                navToggle.setAttribute('aria-expanded', isOpen);
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

        document.getElementById('home-stats').innerHTML = `
            <div class="stat"><div class="lb">收录份额</div><div class="vl">${FUND_DATA.length}</div><div class="sub">纳指 ${nq.length} · 标普 ${sp.length} (涵盖A/C/D/E/F/I)</div></div>
            <div class="stat"><div class="lb">可购份额</div><div class="vl">${availAgency.length}</div><div class="sub">代销可买 (直销可买${availDirect.length})</div></div>
            <div class="stat"><div class="lb">最低综合年费</div><div class="vl">${(minFee * 100).toFixed(2)}%</div><div class="sub">管理+托管+销售费</div></div>
            <div class="stat"><div class="lb">数据更新</div><div class="vl" style="font-size:1rem">${FUND_DATA[0]?.updated_at?.split('T')[0] || '-'}</div><div class="sub">每日自动抓取</div></div>
        `;

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
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                title: items => data[items[0].dataIndex].name,
                                label: ctx => `综合费率: ${ctx.parsed.y.toFixed(2)}%`,
                                afterLabel: ctx => data[ctx.dataIndex].status ? `状态: ${data[ctx.dataIndex].status}` : ''
                            }
                        }
                    },
                    scales: {
                        x: { grid: { display: false } },
                        y: { beginAtZero: true, ticks: { callback: v => v + '%' }, grid: { color: 'rgba(99, 102, 241, 0.08)' } }
                    }
                }
            });
            // 基金名称列表
            const listEl = document.getElementById(id + '-list');
            if (listEl) {
                listEl.innerHTML = data.map(d =>
                    `<span class="fund-tag" title="${d.name}">${d.code} ${d.name.length > 6 ? d.name.substring(0, 6) + '..' : d.name}</span>`
                ).join('');
            }
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
        const c = (sclass || 'A').toUpperCase();
        const map = {
            'A': 'badge-a',
            'C': 'badge-c',
            'D': 'badge-d',
            'E': 'badge-e',
            'F': 'badge-f',
            'I': 'badge-i'
        };
        const cls = map[c] || 'badge-a';
        return `<span class="badge-share ${cls}">${c}类</span>`;
    }

    // ===== 排名页 =====
    let rankData = [];
    let rankSortDir = {};
    const rankCols = [
        { key: 'rank', label: '#', render: r => {
            if (r.rank === 1) return '<span class="tbl-rank-badge rank-gold" title="综合排名第1">🥇 1</span>';
            if (r.rank === 2) return '<span class="tbl-rank-badge rank-silver" title="综合排名第2">🥈 2</span>';
            if (r.rank === 3) return '<span class="tbl-rank-badge rank-bronze" title="综合排名第3">🥉 3</span>';
            return `<span class="tbl-rank-badge">#${r.rank}</span>`;
        } },
        { key: 'code', label: '代码', render: r => `<div class="tbl-code-cell"><span class="code-mono">${r.code}</span><button type="button" class="btn-copy-code" data-code="${r.code}" title="复制基金代码">📋</button><a href="fund/${r.code}.html" target="_blank" class="code-ext-link" title="在新标签页打开独立专页">↗</a></div>` },
        { key: 'name', label: '名称', render: r => {
            const curType = document.querySelector('#rank-filter .seg-btn.on')?.dataset.value || '纳斯达克100';
            const idxBadge = curType === 'ALL'
                ? `<span class="badge-idx ${r.index_type === '纳斯达克100' ? 'badge-nq' : 'badge-sp'}">${r.index_type === '纳斯达克100' ? '纳指' : '标普'}</span>`
                : '';
            return `<div class="tbl-name-cell">${idxBadge}${shareBadge(r.share_class)}<a href="fund/${r.code}.html" class="fund-name-link" data-code="${r.code}" title="点击展开多因子详情看板">${r.name}</a><span class="tbl-row-expand-arrow" title="点击展开/收起详情">▾</span></div>`;
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
            let html = '<div style="display:flex;flex-direction:column;gap:2px;align-items:center">';
            html += '<div style="font-size:0.7rem;color:var(--txt3)">代销</div>' + pill(r.limit_status);
            if (r.direct_limit_status) {
                html += '<div style="font-size:0.7rem;color:var(--txt3);margin-top:2px">直销</div>' + pill(r.direct_limit_status);
            }
            if (r.quota_sharing === 'SHARED') {
                html += `<div style="margin-top:2px" title="${r.quota_shared_desc || '多类份额合并计算单日限额'}"><span class="badge-shared" style="font-size:0.65rem;padding:1px 4px;border-radius:4px;background:rgba(245,158,11,0.15);color:var(--warn);border:1px solid rgba(245,158,11,0.3);white-space:nowrap;cursor:help">🔗 共享额度</span></div>`;
            } else if (r.quota_sharing === 'INDEPENDENT') {
                html += `<div style="margin-top:2px" title="${r.quota_shared_desc || '各份额独立计算限额'}"><span class="badge-indep" style="font-size:0.65rem;padding:1px 4px;border-radius:4px;background:rgba(16,185,129,0.15);color:var(--ok);border:1px solid rgba(16,185,129,0.3);white-space:nowrap;cursor:help">独立额度</span></div>`;
            }
            html += '</div>';
            return html;
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

        // 清空搜索按钮显隐
        const clearBtn = document.getElementById('rank-search-clear');
        if (clearBtn) {
            clearBtn.style.display = kw !== '' ? 'flex' : 'none';
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
    let isMobileDevice = window.innerWidth <= 768;
    let savedRankView = null;
    try { savedRankView = localStorage.getItem('fa_rank_view'); } catch (e) {}
    let currentRankView = savedRankView || (isMobileDevice ? 'card' : 'table');

    function applyRankView(viewMode) {
        currentRankView = viewMode;
        try { localStorage.setItem('fa_rank_view', viewMode); } catch (e) {}

        const toggle = document.getElementById('rank-view-toggle');
        const cardList = document.getElementById('rank-card-list');
        const tableWrap = document.getElementById('rank-table-wrap') || document.querySelector('#page-ranking .table-wrap');
        const swipeHint = document.getElementById('rank-swipe-hint') || document.querySelector('#page-ranking .mobile-swipe-hint');
        const statusMsg = document.getElementById('rank-view-status-msg');

        if (toggle) {
            toggle.querySelectorAll('.view-btn').forEach(btn => {
                if (btn.dataset.view === viewMode) btn.classList.add('on');
                else btn.classList.remove('on');
            });
        }

        if (viewMode === 'card') {
            if (cardList) cardList.style.display = '';
            if (tableWrap) tableWrap.style.display = 'none';
            if (swipeHint) swipeHint.style.display = 'none';
            if (statusMsg) statusMsg.textContent = '当前为投研卡片网格 · 模块化呈现核心指标，点击任意卡片可展开深度看板';
        } else {
            if (cardList) cardList.style.display = 'none';
            if (tableWrap) tableWrap.style.display = '';
            if (swipeHint) swipeHint.style.display = isMobileDevice ? 'block' : 'none';
            if (statusMsg) statusMsg.textContent = '当前为全景对比表格 · 支持点击表头多维排序，点击标的名称可展开抽屉看板';
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
                        <a href="fund/${r.code}.html" class="fmc-title" data-code="${r.code}">${r.name}</a>
                        <a href="fund/${r.code}.html" target="_blank" class="fmc-page-link" title="在新标签打开独立专页">评测专页 ↗</a>
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
                                <a href="fund/${r.code}.html" target="_blank" class="fmc-btn-act fmc-btn-primary">
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
                    window.open(`fund/${sibCode}.html`, '_blank');
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

            const result = await simulateViaWorker(funds, weights, years, monthly, await getDynamicParams());

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
            <td style="color:var(--txt2)">${a.code}</td>
            <td style="text-align:left;font-weight:500">
                ${shareBadge(a.share_class)}${a.name}
                ${a.is_stacked ? '<span class="badge-stacked" title="额度用尽时自动补充的优质份额">额度叠加</span>' : ''}
                ${a.quota_sharing === 'SHARED' ? `<span class="badge-shared" style="font-size:0.65rem;margin-left:4px;padding:1px 4px;border-radius:4px;background:rgba(245,158,11,0.15);color:var(--warn);border:1px solid rgba(245,158,11,0.3);white-space:nowrap;cursor:help" title="${a.quota_shared_desc || '多类份额共享限额'}">🔗 共享额度</span>` : ''}
            </td>
            <td style="${feeC(a.fee)}">${(a.fee*100).toFixed(2)}%</td>
            <td>${a.daily}元</td>
            <td style="font-weight:600">${a.monthly}元</td>
            <td>${(a.actual_weight*100).toFixed(0)}%</td>
            <td>${pill(a.limit_status)}${a.direct_limit_status ? '<div style="margin-top:2px">' + pill(a.direct_limit_status) + '</div>' : ''}</td>
        </tr>`).join('');
        let html = `<div class="table-wrap"><table><thead><tr><th>代码</th><th>名称</th><th>综合费率</th><th>每日</th><th>月合计</th><th>占比</th><th>代销/直销</th></tr></thead><tbody>${rows}</tbody></table></div>`;
        if (hasShared) {
            html += `<div style="margin-top:0.6rem;padding:0.5rem 0.75rem;background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.22);border-radius:6px;font-size:0.75rem;color:var(--txt2);line-height:1.5">
                <span style="color:var(--warn);font-weight:600">💡 共享额度避坑提示：</span>
                标有 <span style="color:var(--warn);font-weight:600">🔗 共享额度</span> 的基金，其 A 类与 C 类（及定制份额）由基金公司合并控制单日申购限额。若您已在其他渠道定投同门份额，切勿重复定投，以免超过合并上限导致银行扣款失败。
            </div>`;
        }
        return html;
    }

    function renderVariantSim(variant, years) {
        const sim = variant?.simulation;
        if (!sim) return '';
        return `<div style="margin-top:1rem">
            <div class="stats">
                <div class="stat"><div class="lb">预期年化</div><div class="vl" style="font-size:1.05rem;color:var(--accent2)">${sim.annualReturn}%</div></div>
                <div class="stat"><div class="lb">${years}年终值</div><div class="vl" style="font-size:1.05rem;color:var(--ok)">${money(sim.medianFinal)}</div></div>
            </div>
            <div style="font-size:.75rem;color:var(--txt3);margin-top:.35rem">5%: ${money(sim.p5)} · 25%: ${money(sim.p25)} · 75%: ${money(sim.p75)} · 95%: ${money(sim.p95)}</div>
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
        const sharpe = ra.sharpe_ratio != null ? ra.sharpe_ratio.toFixed(2) : null;

        let statusTag = '';
        let note = '';
        if (s.key === 'risk_parity') {
            statusTag = '<span class="tag" style="background:rgba(16,185,129,0.15);color:#059669;font-weight:700">✅ 达成等风险贡献 (ERC)</span>';
            note = '💡 <strong>等风险贡献 (ERC) 达成：</strong>均衡纳指与标普的边际风险贡献各约 50%，消除单一市场暴跌对净值的非对称冲击。';
        } else if (s.key === 'max_sharpe') {
            statusTag = `<span class="tag" style="background:rgba(99,102,241,0.15);color:#4f46e5;font-weight:700">🎯 最优夏普组合 (SR ${sharpe || ''})</span>`;
            note = `🎯 <strong>最优风险收益比 (夏普 ${sharpe || ''})：</strong>基于 Ledoit-Wolf 收缩协方差优化，在控制波动率的同时最大化超额收益。`;
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
        <div style="margin-top:1.25rem;padding:0.85rem 1rem;background:var(--surface2, var(--bg2));border-radius:var(--radius-sm, 8px);border:1px solid var(--border)">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.6rem;flex-wrap:wrap;gap:6px">
                <div style="display:flex;align-items:center;gap:6px">
                    <span style="font-weight:600;font-size:0.825rem;color:var(--txt)">📊 资金配置 vs 实际波动风险贡献</span>
                    ${statusTag}
                </div>
                <span style="font-size:0.75rem;color:var(--txt3)">组合年化波动: <strong>${vol}%</strong>${sharpe ? ' · 夏普比率: <strong>' + sharpe + '</strong>' : ''}</span>
            </div>
            
            <div style="margin-bottom:0.5rem">
                <div style="display:flex;justify-content:space-between;font-size:0.72rem;color:var(--txt2);margin-bottom:3px">
                    <span>资金权重 (Capital Weight)</span>
                    <span>纳指 ${nqCapitalPct}% / 标普 ${spCapitalPct}%</span>
                </div>
                <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;background:var(--border)">
                    <div style="width:${nqCapitalPct}%;background:#3b82f6" title="纳指资金占比 ${nqCapitalPct}%"></div>
                    <div style="width:${spCapitalPct}%;background:#10b981" title="标普资金占比 ${spCapitalPct}%"></div>
                </div>
            </div>

            <div style="margin-bottom:0.6rem">
                <div style="display:flex;justify-content:space-between;font-size:0.72rem;color:var(--txt2);margin-bottom:3px">
                    <span>波动风险贡献 (Risk Contribution)</span>
                    <span style="font-weight:${s.key === 'risk_parity' ? '700;color:var(--ok)' : 'normal'}">纳指 ${nqRiskPct}% / 标普 ${spRiskPct}%</span>
                </div>
                <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;background:var(--border)">
                    <div style="width:${nqRiskPct}%;background:linear-gradient(90deg, #3b82f6, #6366f1)" title="纳指风险贡献 ${nqRiskPct}%"></div>
                    <div style="width:${spRiskPct}%;background:linear-gradient(90deg, #10b981, #059669)" title="标普风险贡献 ${spRiskPct}%"></div>
                </div>
            </div>

            <div style="font-size:0.75rem;color:var(--txt2);line-height:1.4">${note}</div>
        </div>`;
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

                    mHtml += `<tr class="quant-matrix-row">
                        <td style="font-weight:600;white-space:nowrap">${s.icon || ''} ${s.name}</td>
                        <td>${typeBadge}</td>
                        <td style="font-weight:600">${nqW}% : ${spW}%</td>
                        <td>${riskBadge}</td>
                        <td><strong>${vol}</strong></td>
                        <td style="font-weight:700;color:var(--accent2)">${sharpe}</td>
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
                        <div class="g2">
                            <div>${renderVariantTable(s.ideal, s.key)}</div>
                            <div>
                                <div class="cht"><canvas id="ch-${s.key}-ideal"></canvas></div>
                                ${renderVariantSim(s.ideal, years)}
                                ${renderRiskContribution(s.ideal, s)}
                            </div>
                        </div>
                        <div style="margin-top:1.25rem;padding-top:0.85rem;border-top:1px dashed var(--border);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
                            <span style="font-size:0.75rem;color:var(--txt3)">💡 想要自定义定投预算、年限或测试极端市场压力？</span>
                            <button class="btn-simulate-action btn-sim-from-strat" data-strategy="${s.key}" data-variant="ideal">🚀 以该理论配置启动蒙特卡洛推演 ➔</button>
                        </div>
                    </div>

                    <div class="pf-panel" id="pf-${s.key}-practical" style="display:none">
                        <p style="color:${(s.practical?.note || '').includes('额度叠加') ? 'var(--ok)' : 'var(--txt3)'};font-size:.78rem;font-weight:500;margin:.5rem 0">${s.practical?.note || ''}</p>
                        <div class="g2">
                            <div>${renderVariantTable(s.practical, s.key)}</div>
                            <div>
                                <div class="cht"><canvas id="ch-${s.key}-practical"></canvas></div>
                                ${renderVariantSim(s.practical, years)}
                                ${renderRiskContribution(s.practical, s)}
                            </div>
                        </div>
                        <div style="margin-top:1.25rem;padding-top:0.85rem;border-top:1px dashed var(--border);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
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
                            labels: allocs.map(a => a.name.substring(0, 8)),
                            datasets: [{
                                data: allocs.map(a => a.monthly),
                                backgroundColor: pieColors,
                                borderWidth: 0,
                                hoverOffset: 6,
                                borderRadius: 5,
                                spacing: 3
                            }]
                        },
                        options: {
                            responsive: true,
                            cutout: '72%',
                            layout: { padding: 8 },
                            plugins: { 
                                legend: { 
                                    position: 'bottom', 
                                    labels: { 
                                        padding: 16, 
                                        usePointStyle: true, 
                                        pointStyle: 'circle', 
                                        font: { size: 12, family: 'system-ui, -apple-system, sans-serif' },
                                        color: '#64748b'
                                    } 
                                },
                                tooltip: {
                                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                                    titleFont: { size: 13, family: 'system-ui, -apple-system, sans-serif', weight: 'normal' },
                                    bodyFont: { size: 13, family: 'system-ui, -apple-system, sans-serif', weight: 'bold' },
                                    padding: 12,
                                    cornerRadius: 8,
                                    boxPadding: 6,
                                    displayColors: true,
                                    usePointStyle: true
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

    function simulateViaWorker(funds, weights, years, budget, dynamicParams) {
        return new Promise((resolve) => {
            const worker = getSimWorker();
            const fallbackArgs = [funds, weights, years, budget, dynamicParams];
            if (!worker) {
                resolve(localSimulatePortfolio(...fallbackArgs));
                return;
            }
            const cfg = ALGO_CONFIG;
            const effectiveParams = dynamicParams || cfg.simulation.params;
            const effectiveConfig = { ...cfg, simulation: { ...cfg.simulation, params: effectiveParams } };
            const id = ++_msgId;
            _pendingPromises.set(id, { resolve, fallbackArgs });
            worker.postMessage({ id, funds, weights, years, budget, config: effectiveConfig });
        });
    }

    function localSimulatePortfolio(funds, weights, years, budget, dynamicParams) {
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
            const invest = fundBudget * (1 - (fund.purchase_fee || defaults.purchase_fee));
            
            const z_te = new Float64Array(N * months);
            for (let i = 0; i < N * months; i++) {
                z_te[i] = boxMuller();
            }
            
            for (let s = 0; s < N; s++) {
                let shares = 0;
                let nav = 1.0;
                
                for (let m = 0; m < months; m++) {
                    const idx = s * months + m;
                    
                    const z_index1 = z_idx1[idx];
                    const z_index2 = z_idx2[idx];
                    const z_idx_val = isSP ? (rho * z_index1 + Math.sqrt(1 - rho * rho) * z_index2) : z_index1;
                    
                    const idx_r = retM + volM * z_idx_val;
                    const te_r = teV * z_te[idx];
                    const fx_r = fxM + fxV * z_fx[idx];
                    
                    const fund_r = idx_r + te_r - feeM + divM + fx_r;
                    nav *= (1 + fund_r);
                    shares += invest / nav;
                }
                finalValues[s] += shares * nav;
            }
        });
        
        finalValues.sort((a, b) => a - b);
        const mean = finalValues.reduce((a, b) => a + b, 0) / N;
        const ret = totalInvested > 0 ? (mean / totalInvested - 1) * 100 : 0;
        
        return {
            totalInvested: Math.round(totalInvested),
            medianFinal: Math.round(finalValues[Math.floor(N * 0.5)]),
            p5: Math.round(finalValues[Math.floor(N * 0.05)]),
            p25: Math.round(finalValues[Math.floor(N * 0.25)]),
            p75: Math.round(finalValues[Math.floor(N * 0.75)]),
            p95: Math.round(finalValues[Math.floor(N * 0.95)]),
            annualReturn: +(ret / years).toFixed(2),
            meanReturnPct: +ret.toFixed(2),
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
            return {
                nq_weight: +w_nq.toFixed(4),
                sp_weight: +w_sp.toFixed(4),
                nq_risk_contrib: +rc_nq.toFixed(4),
                sp_risk_contrib: +rc_sp.toFixed(4),
                portfolio_vol: +port_vol.toFixed(4),
                sharpe_ratio: +sharpe.toFixed(4)
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
            const [fundsResp, algoResp] = await Promise.all([
                fetch('data/funds.json?v=' + t),
                fetch('data/algorithm.json?v=' + t)
            ]);
            FUND_DATA = await fundsResp.json();
            ALGO_CONFIG = await algoResp.json();

            renderHome();
            initNav();
            initPresetChips();
            initSimQuickPresets();
            syncSliderBadges();
        } catch (e) {
            document.getElementById('home-stats').innerHTML = '<div class="card"><p style="color:var(--err)">数据加载失败: ' + e.message + '</p></div>';
        }

        // 全局基金代码快速复制监听
        document.addEventListener('click', e => {
            const copyBtn = e.target.closest('.btn-copy-code, .btn-copy-code-action');
            if (copyBtn) {
                e.preventDefault();
                e.stopPropagation();
                const code = copyBtn.dataset.code;
                if (code) {
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
        applyRankView(currentRankView);
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
        });
        document.getElementById('pf-y').addEventListener('input', e => {
            document.getElementById('pf-yv').textContent = e.target.value + '年';
            const b = document.getElementById('pf-yv-badge');
            if (b) b.textContent = e.target.value + ' 年';
        });
        document.getElementById('btn-sim').addEventListener('click', runSimulation);
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
            });
        }

        // 基金详情展开（事件委托，只绑定一次）
        document.querySelector('#rank-table').addEventListener('click', e => {
            const link = e.target.closest('.fund-name-link');
            if (!link) return;
            e.preventDefault();
            const code = link.dataset.code;
            const tr = link.closest('tr');
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
                    <a href="fund/${f.code}.html" target="_blank" class="btn-fund-page-action" title="在新标签页中打开这只基金的独立评测专页">
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
