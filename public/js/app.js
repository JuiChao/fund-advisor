/**
 * 主应用逻辑 - 调用 API 获取预计算结果
 */
const App = (() => {
    let FUND_DATA = [];
    let chartPool = {};
    const API_BASE = '';

    // ===== 明亮主题 Chart.js 默认配置 =====
    Chart.defaults.color = '#64748b';
    Chart.defaults.borderColor = '#e2e8f0';
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
        if (s.includes('暂停')) return '<span class="pill pr">' + s + '</span>';
        if (s.includes('限10元')) return '<span class="pill py">' + s + '</span>';
        return '<span class="pill pg">' + s + '</span>';
    }
    function feeC(f) {
        if (f <= 0.006) return 'color:#34d399;font-weight:700';
        if (f <= 0.007) return 'color:#34d399';
        if (f <= 0.01) return '';
        return 'color:#f87171';
    }

    // ===== 页面切换 =====
    function initNav() {
        document.querySelectorAll('#nav-links a').forEach(a => {
            a.addEventListener('click', e => {
                e.preventDefault();
                const page = a.dataset.page;
                document.querySelectorAll('#nav-links a').forEach(x => x.classList.remove('on'));
                a.classList.add('on');
                document.querySelectorAll('[id^="page-"]').forEach(p => p.style.display = 'none');
                const target = document.getElementById('page-' + page);
                target.style.display = '';
                target.classList.remove('fade-in');
                void target.offsetWidth;
                target.classList.add('fade-in');
                if (page === 'ranking') renderRanking();
                if (page === 'simulator') populateSimSelect();
                if (page === 'portfolio') computePortfolio();
            });
        });
    }

    // ===== 概览页 =====
    function renderHome() {
        const nq = FUND_DATA.filter(f => f.index_type === '纳斯达克100');
        const sp = FUND_DATA.filter(f => f.index_type === '标普500');
        const avail = FUND_DATA.filter(f => !(f.limit_status || '').includes('暂停'));
        const minFee = Math.min(...FUND_DATA.map(f => (f.mgmt_fee || 0) + (f.custody_fee || 0)));

        document.getElementById('home-stats').innerHTML = `
            <div class="stat"><div class="lb">基金总数</div><div class="vl">${FUND_DATA.length}</div><div class="sub">纳指 ${nq.length} · 标普 ${sp.length}</div></div>
            <div class="stat"><div class="lb">可购买</div><div class="vl">${avail.length}</div><div class="sub">未暂停申购</div></div>
            <div class="stat"><div class="lb">最低费率</div><div class="vl">${(minFee * 100).toFixed(2)}%</div><div class="sub">管理费 + 托管费</div></div>
            <div class="stat"><div class="lb">数据更新</div><div class="vl" style="font-size:1rem">${FUND_DATA[0]?.updated_at?.split('T')[0] || '-'}</div><div class="sub">每日自动抓取</div></div>
        `;

        // 费率分布图
        function feeChart(id, list) {
            const data = list.map(f => ({ code: f.code, fee: ((f.mgmt_fee || 0) + (f.custody_fee || 0)) * 100 })).sort((a, b) => a.fee - b.fee);
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
                    plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ctx.parsed.y.toFixed(2) + '%' } } },
                    scales: {
                        x: { grid: { display: false } },
                        y: { beginAtZero: true, ticks: { callback: v => v + '%' }, grid: { color: '#f1f5f9' } }
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
            const strategies = await apiGet('/api/portfolio?years=20&budget=2000');
            let html = '<div class="table-wrap"><table><thead><tr><th>策略</th><th>风格</th><th>子方案</th><th>预期年化</th><th>20年终值</th></tr></thead><tbody>';
            strategies.forEach(s => {
                ['ideal', 'practical'].forEach(vk => {
                    const v = s[vk];
                    const sim = v?.simulation || {};
                    const label = vk === 'ideal' ? '理论最优' : '实际可买';
                    html += `<tr>
                        <td style="font-weight:600;color:var(--accent2)">${s.icon || ''} ${s.name}</td>
                        <td style="font-size:.8125rem;color:var(--txt2)">${s.description || ''}</td>
                        <td><span class="pill ${vk === 'ideal' ? 'pb' : 'pg'}">${label}</span></td>
                        <td style="color:var(--ok);font-weight:600">${sim.annualReturn ? sim.annualReturn + '%' : '-'}</td>
                        <td style="font-weight:600">${sim.medianFinal ? money(sim.medianFinal) : '-'}</td>
                    </tr>`;
                });
            });
            html += '</tbody></table></div>';
            document.getElementById('home-strategies').innerHTML = html;
            document.getElementById('home-strategies').classList.remove('ld');
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

    // ===== 排名页 =====
    let rankData = [];
    const rankCols = [
        { key: 'rank', label: '#' },
        { key: 'code', label: '代码' },
        { key: 'name', label: '名称', render: r => '<strong style="color:var(--txt)">' + r.name + '</strong>' },
        { key: 'fee', label: '费率', render: r => { const f = (r.mgmt_fee || 0) + (r.custody_fee || 0); return '<span style="' + feeC(f) + '">' + fmt(f) + '</span>'; } },
        { key: 'tracking_error', label: '跟踪误差', render: r => fmt(r.tracking_error) },
        { key: 'scale', label: '规模', render: r => r.scale ? r.scale.toFixed(1) + '亿' : '-' },
        { key: 'return_3yr', label: '近3年', render: r => { const v = r.return_3yr; return v != null ? '<span style="color:var(--ok)">' + fmt(v) + '</span>' : '-'; } },
        { key: 'morningstar', label: '晨星', render: r => { const n = r.morningstar; return n > 0 ? '<span style="color:var(--warn)">' + '★'.repeat(n) + '</span>' : '-'; } },
        { key: 'limit_status', label: '限购', render: r => pill(r.limit_status) },
        { key: 'score', label: '评分', render: r => '<strong style="color:var(--accent2)">' + r.score + '</strong>' },
    ];

    function scoreFund(f) {
        const fee = (f.mgmt_fee || 0) + (f.custody_fee || 0);
        const te = f.tracking_error || 0.02;
        const scale = f.scale || 10;
        const y3 = f.return_3yr;
        const ms = f.morningstar || 0;
        const pur = f.purchase_fee || 0.0012;
        const feeS = Math.max(0, Math.min(100, 100 - (fee - 0.004) / 0.006 * 50));
        const teS = Math.max(0, Math.min(100, 100 - (te - 0.008) / 0.022 * 67));
        const scS = (scale >= 10 && scale <= 80) ? 100 : (scale < 5 ? 40 : (scale > 100 ? 70 : 80));
        const y3S = y3 != null ? Math.max(0, Math.min(100, (y3 - 0.3) / 0.6 * 100)) : 50;
        const msS = ms > 0 ? ms * 25 : 40;
        const purS = Math.max(0, Math.min(100, 100 - (pur - 0.0008) / 0.001 * 50));
        return +(feeS * 0.35 + teS * 0.25 + scS * 0.15 + y3S * 0.12 + msS * 0.08 + purS * 0.05).toFixed(1);
    }

    function renderRanking() {
        const type = document.getElementById('rank-filter').value;
        const funds = FUND_DATA.filter(f => f.index_type === type);
        rankData = funds.map(f => ({ ...f, score: scoreFund(f) })).sort((a, b) => b.score - a.score).map((f, i) => ({ ...f, rank: i + 1 }));

        const thead = document.querySelector('#rank-table thead');
        thead.innerHTML = '<tr>' + rankCols.map(c => `<th data-key="${c.key}">${c.label} <span class="arr">⇅</span></th>`).join('') + '</tr>';

        function draw() {
            const tbody = document.querySelector('#rank-table tbody');
            tbody.innerHTML = rankData.map((r, i) => {
                const cls = i < 3 ? ' class="hl"' : (r.limit_status || '').includes('暂停') ? ' class="wr"' : '';
                return '<tr' + cls + '>' + rankCols.map(c => '<td>' + (c.render ? c.render(r) : (r[c.key] ?? '-')) + '</td>').join('') + '</tr>';
            }).join('');
        }

        thead.querySelectorAll('th').forEach(th => {
            th.addEventListener('click', () => {
                const key = th.dataset.key;
                const isFee = key === 'fee';
                rankData.sort((a, b) => {
                    let va, vb;
                    if (isFee) { va = (a.mgmt_fee || 0) + (a.custody_fee || 0); vb = (b.mgmt_fee || 0) + (b.custody_fee || 0); }
                    else { va = a[key]; vb = b[key]; }
                    if (va == null) va = Infinity; if (vb == null) vb = Infinity;
                    return typeof va === 'string' ? va.localeCompare(vb) : va - vb;
                });
                draw();
            });
        });
        draw();
    }

    // ===== 模拟器 - 自定义多选 =====
    let msSelected = new Set();
    let msInited = false;

    function initMultiSelect() {
        if (msInited) return;
        msInited = true;
        const trigger = document.getElementById('sim-sel-trigger');
        const dropdown = document.getElementById('sim-sel-dropdown');
        const list = document.getElementById('sim-sel-list');
        const search = document.getElementById('sim-sel-search');
        const textEl = document.getElementById('sim-sel-text');

        function feeStr(f) { return (((f.mgmt_fee||0)+(f.custody_fee||0))*100).toFixed(2) + '%'; }
        function renderList(filter) {
            const q = (filter || '').toLowerCase();
            const items = FUND_DATA.filter(f => {
                if (!q) return true;
                return f.code.includes(q) || f.name.toLowerCase().includes(q);
            });
            list.innerHTML = items.map(f => {
                const sel = msSelected.has(f.code) ? ' selected' : '';
                return `<div class="ms-opt${sel}" data-code="${f.code}">
                    <div class="ms-cb"></div>
                    <div class="ms-opt-info">
                        <div class="ms-opt-name">${f.code} ${f.name}</div>
                        <div class="ms-opt-meta">费率 ${feeStr(f)} · ${f.index_type}</div>
                    </div>
                </div>`;
            }).join('');
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

        try {
            const monthly = +document.getElementById('sim-m').value;
            const years = +document.getElementById('sim-y').value;
            let result;
            if (codes.length === 1) {
                const data = await apiGet(`/api/simulate?code=${codes[0]}&years=${years}&budget=${monthly}`);
                result = data.simulation;
            } else {
                const strategies = await apiGet(`/api/portfolio?years=${years}&budget=${monthly}`);
                let best = null, bestOverlap = 0;
                strategies.forEach(s => {
                    const overlap = (s.allocations || []).filter(a => codes.includes(a.code)).length;
                    if (overlap > bestOverlap) { bestOverlap = overlap; best = s; }
                });
                result = best?.simulation;
            }

            if (!result) {
                document.getElementById('sim-result').innerHTML = '<p style="color:var(--err);text-align:center;padding:2rem">无法获取模拟结果</p>';
                btn.disabled = false; btn.textContent = '运行模拟';
                return;
            }

            const total = monthly * years * 12;
            document.getElementById('sim-result').innerHTML = `
                <div class="stats">
                    <div class="stat"><div class="lb">总投入</div><div class="vl" style="font-size:1.15rem">${money(total)}</div></div>
                    <div class="stat"><div class="lb">预期终值</div><div class="vl" style="font-size:1.15rem;color:var(--ok)">${money(result.medianFinal)}</div></div>
                    <div class="stat"><div class="lb">年化收益</div><div class="vl" style="font-size:1.15rem;color:var(--accent2)">${result.annualReturn || result.meanReturnPct}%</div></div>
                </div>
                <table style="margin-top:.75rem">
                    <tr><td style="color:var(--err)">5% 悲观</td><td><strong>${money(result.p5)}</strong></td></tr>
                    <tr><td>25%</td><td><strong>${money(result.p25)}</strong></td></tr>
                    <tr><td style="color:var(--accent2)">50% 中位</td><td><strong>${money(result.medianFinal)}</strong></td></tr>
                    <tr><td>75%</td><td><strong>${money(result.p75)}</strong></td></tr>
                    <tr><td style="color:var(--ok)">95% 乐观</td><td><strong>${money(result.p95)}</strong></td></tr>
                </table>`;

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
                        y: { title: { display: true, text: '万元' }, grid: { color: '#f1f5f9' } }
                    }
                }
            });
        } catch (e) {
            document.getElementById('sim-result').innerHTML = `<p style="color:var(--err);text-align:center;padding:2rem">模拟失败: ${e.message}</p>`;
        }
        btn.disabled = false; btn.textContent = '运行模拟';
    }

    // ===== 定投方案 =====
    let pfCharts = {};

    function renderVariantTable(variant, prefix) {
        if (!variant) return '';
        const allocs = variant.allocations || [];
        const rows = allocs.map(a => `<tr class="${a.exceeds_limit ? 'wr' : ''}">
            <td style="color:var(--txt2)">${a.code}</td>
            <td style="text-align:left;font-weight:500">${a.name}</td>
            <td style="${feeC(a.fee)}">${(a.fee*100).toFixed(2)}%</td>
            <td>${a.daily}元</td>
            <td style="font-weight:600">${a.monthly}元</td>
            <td>${(a.actual_weight*100).toFixed(0)}%</td>
            <td>${pill(a.limit_status)}</td>
        </tr>`).join('');
        return `<div class="table-wrap"><table><thead><tr><th>代码</th><th>名称</th><th>费率</th><th>每日</th><th>月合计</th><th>占比</th><th>限购</th></tr></thead><tbody>${rows}</tbody></table></div>`;
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

    async function computePortfolio() {
        const btn = document.getElementById('btn-pf');
        btn.disabled = true; btn.textContent = '计算中…';
        try {
            const monthly = +document.getElementById('pf-m').value;
            const years = +document.getElementById('pf-y').value;
            Object.values(pfCharts).forEach(c => c.destroy());
            pfCharts = {};

            const strategies = await apiGet(`/api/portfolio?years=${years}&budget=${monthly}`);
            const pieColors = ['#6366f1','#f59e0b','#64748b','#eab308','#818cf8','#22d3ee'];

            let html = '';
            strategies.forEach(s => {
                const idealAllocs = s.ideal?.allocations || [];
                const practicalAllocs = s.practical?.allocations || [];

                html += `<div class="card">
                    <h3>${s.icon || ''} ${s.name} <span class="tag">${Math.round((s.nq_pct||0)*100)}% 纳指 + ${Math.round((1-(s.nq_pct||0))*100)}% 标普</span></h3>
                    <p style="color:var(--txt2);font-size:.8125rem;margin-bottom:1rem">${s.description || ''}</p>

                    <div class="pf-tabs" data-strategy="${s.key}">
                        <button class="pf-tab on" data-variant="ideal">理论最优</button>
                        <button class="pf-tab" data-variant="practical">实际可买</button>
                    </div>

                    <div class="pf-panel" id="pf-${s.key}-ideal">
                        <p style="color:var(--txt3);font-size:.75rem;margin:.5rem 0">${s.ideal?.note || ''}</p>
                        <div class="g2">
                            <div>${renderVariantTable(s.ideal, s.key)}</div>
                            <div>
                                <div class="cht"><canvas id="ch-${s.key}-ideal"></canvas></div>
                                ${renderVariantSim(s.ideal, years)}
                            </div>
                        </div>
                    </div>

                    <div class="pf-panel" id="pf-${s.key}-practical" style="display:none">
                        <p style="color:var(--txt3);font-size:.75rem;margin:.5rem 0">${s.practical?.note || ''}</p>
                        <div class="g2">
                            <div>${renderVariantTable(s.practical, s.key)}</div>
                            <div>
                                <div class="cht"><canvas id="ch-${s.key}-practical"></canvas></div>
                                ${renderVariantSim(s.practical, years)}
                            </div>
                        </div>
                    </div>
                </div>`;
            });
            document.getElementById('pf-container').innerHTML = html;
            document.getElementById('pf-container').classList.remove('ld');

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
                                borderColor: 'var(--surface)',
                                borderWidth: 2,
                            }]
                        },
                        options: {
                            responsive: true,
                            cutout: '60%',
                            plugins: { legend: { position: 'bottom', labels: { padding: 12, usePointStyle: true, pointStyle: 'circle', font: { size: 11 } } } }
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

    // ===== 初始化 =====
    async function init() {
        initNav();
        try {
            const resp = await fetch('data/funds.json');
            FUND_DATA = await resp.json();
            renderHome();
        } catch (e) {
            document.getElementById('home-stats').innerHTML = '<div class="card"><p style="color:var(--err)">数据加载失败: ' + e.message + '</p></div>';
        }

        const fmtMoney = v => '¥' + Number(v).toLocaleString('zh-CN');
        document.getElementById('rank-filter').addEventListener('change', renderRanking);
        document.getElementById('sim-m').addEventListener('input', e => document.getElementById('sim-mv').textContent = fmtMoney(e.target.value));
        document.getElementById('sim-y').addEventListener('input', e => document.getElementById('sim-yv').textContent = e.target.value + '年');
        document.getElementById('pf-m').addEventListener('input', e => document.getElementById('pf-mv').textContent = fmtMoney(e.target.value));
        document.getElementById('pf-y').addEventListener('input', e => document.getElementById('pf-yv').textContent = e.target.value + '年');
        document.getElementById('btn-sim').addEventListener('click', runSimulation);
        document.getElementById('btn-pf').addEventListener('click', computePortfolio);
    }

    return { init };
})();

document.addEventListener('DOMContentLoaded', App.init);
