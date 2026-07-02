/**
 * 主应用逻辑 - 调用 API 获取预计算结果
 */
const App = (() => {
    let FUND_DATA = [];
    let chartPool = {};
    const API_BASE = '';

    // ===== 明亮主题 Chart.js 默认配置 =====
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = 'rgba(99, 102, 241, 0.15)';
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
            const data = list.map(f => ({
                code: f.code,
                name: f.name,
                fee: ((f.mgmt_fee || 0) + (f.custody_fee || 0)) * 100,
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
                        y: { beginAtZero: true, ticks: { callback: v => v + '%' }, grid: { color: 'rgba(99, 102, 241, 0.15)' } }
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
            let strategies;
            try {
                strategies = await apiGet('/api/portfolio?years=20&budget=2000');
            } catch (apiErr) {
                console.warn("API failed in preview, using local calculations:", apiErr);
                strategies = localCalculatePortfolio(20, 2000);
            }

            // 预先算一下预览组合模拟数据，如果API没有返回的话
            strategies.forEach(s => {
                ['ideal', 'practical'].forEach(vk => {
                    const v = s[vk];
                    if (!v.simulation) {
                        const allocs = v.allocations || [];
                        const simFunds = allocs.map(a => FUND_DATA.find(f => f.code === a.code)).filter(Boolean);
                        const simWeights = allocs.map(a => a.actual_weight || a.weight || 0);
                        v.simulation = localSimulatePortfolio(simFunds, simWeights, 20, 2000);
                    }
                });
            });

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
        const type = document.querySelector('#rank-filter .seg-btn.on')?.dataset.value || '纳斯达克100';
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
            const items = FUND_DATA.map(f => ({
                ...f,
                score: scoreFund(f)
            })).filter(f => {
                if (!q) return true;
                return f.code.includes(q) || f.name.toLowerCase().includes(q);
            }).sort((a, b) => b.score - a.score);

            list.innerHTML = items.map((f, idx) => {
                const sel = msSelected.has(f.code) ? ' selected' : '';
                return `<div class="ms-opt${sel}" data-code="${f.code}">
                    <div class="ms-cb"></div>
                    <div class="ms-opt-info">
                        <div class="ms-opt-name"><span class="ms-opt-rank">#${idx + 1}</span> ${f.code} ${f.name}</div>
                        <div class="ms-opt-meta">评分 <strong style="color:var(--accent2)">${f.score}</strong> · 费率 ${feeStr(f)} · ${f.index_type}</div>
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

            // 对多基金组合进行高精度的联合蒙特卡洛模拟
            const weights = new Array(funds.length).fill(1 / funds.length);
            const result = localSimulatePortfolio(funds, weights, years, monthly);

            // 显示预算分配说明
            const perFundBudget = Math.round(monthly / codes.length);
            const allocNote = codes.length > 1
                ? `<p style="color:var(--txt3);font-size:.75rem;margin-bottom:.75rem">每月 ¥${monthly} 平均分配给 ${codes.length} 只基金，每只 ¥${perFundBudget}/月</p>`
                : '';

            document.getElementById('sim-result').innerHTML = `
                ${allocNote}
                <div class="stats">
                    <div class="stat"><div class="lb">总投入</div><div class="vl" style="font-size:1.15rem">${money(result.totalInvested)}</div></div>
                    <div class="stat"><div class="lb">预期终值</div><div class="vl" style="font-size:1.15rem;color:var(--ok)">${money(result.medianFinal)}</div></div>
                    <div class="stat"><div class="lb">年化收益</div><div class="vl" style="font-size:1.15rem;color:var(--accent2)">${result.annualReturn}%</div></div>
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
                        y: { title: { display: true, text: '万元' }, grid: { color: 'rgba(99, 102, 241, 0.15)' } }
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

            let strategies;
            try {
                strategies = await apiGet(`/api/portfolio?years=${years}&budget=${monthly}`);
            } catch (apiErr) {
                console.warn("API failed, falling back to local calculation:", apiErr);
                strategies = localCalculatePortfolio(years, monthly);
            }
            
            // 为 ideal 和 practical 方案动态运行精准的前端蒙特卡洛组合模拟
            strategies.forEach(s => {
                const idealAllocs = s.ideal?.allocations || [];
                const practicalAllocs = s.practical?.allocations || [];
                
                if (idealAllocs.length) {
                    const simFunds = idealAllocs.map(a => FUND_DATA.find(f => f.code === a.code)).filter(Boolean);
                    const simWeights = idealAllocs.map(a => a.actual_weight || a.weight || 0);
                    s.ideal.simulation = localSimulatePortfolio(simFunds, simWeights, years, monthly);
                }
                
                if (practicalAllocs.length) {
                    const simFunds = practicalAllocs.map(a => FUND_DATA.find(f => f.code === a.code)).filter(Boolean);
                    const simWeights = practicalAllocs.map(a => a.actual_weight || a.weight || 0);
                    s.practical.simulation = localSimulatePortfolio(simFunds, simWeights, years, monthly);
                }
            });

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

    // ===== 本地联合蒙特卡洛组合模拟（前端高效向量化执行）=====
    function localSimulatePortfolio(funds, weights, years, budget) {
        const N = 3000;
        const months = years * 12;
        const totalInvested = budget * months;
        const finalValues = new Array(N).fill(0);
        
        const rho = 0.75;
        const params = {
            nasdaq_return: 0.14, nasdaq_vol: 0.22,
            sp500_return: 0.11, sp500_vol: 0.18,
            fx_drift: 0.005, fx_vol: 0.03,
            dividend_yield: 0.008, dividend_tax: 0.10,
        };
        
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
            const te = fund.tracking_error || 0.015;
            const fee = (fund.mgmt_fee || 0.008) + (fund.custody_fee || 0.002);
            
            const retM = (isSP ? params.sp500_return : params.nasdaq_return) / 12;
            const volM = (isSP ? params.sp500_vol : params.nasdaq_vol) / Math.sqrt(12);
            const teV = te / Math.sqrt(12);
            const fxM = params.fx_drift / 12;
            const fxV = params.fx_vol / Math.sqrt(12);
            const feeM = fee / 12;
            const divM = params.dividend_yield / 12 * (1 - params.dividend_tax);
            const invest = fundBudget * (1 - (fund.purchase_fee || 0.0012));
            
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
        function isBuyable(f) {
            const status = f.limit_status || '';
            return !status.includes('暂停');
        }

        function pickFundsByStyle(nqPct, onlyBuyable = false) {
            let nq = FUND_DATA.filter(f => f.index_type === '纳斯达克100');
            let sp = FUND_DATA.filter(f => f.index_type === '标普500');
            if (onlyBuyable) {
                nq = nq.filter(isBuyable);
                sp = sp.filter(isBuyable);
            }
            const nqScored = nq.map(f => ({ ...f, score: scoreFund(f) })).sort((a, b) => b.score - a.score);
            const spScored = sp.map(f => ({ ...f, score: scoreFund(f) })).sort((a, b) => b.score - a.score);
            
            const rnq = nqScored.slice(0, 3);
            const rsp = spScored.slice(0, 2);
            
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
            const tradingDays = 22;
            const allocs = items.map(item => {
                const f = item.fund;
                const w = item.weight;
                const monthly = budget * w;
                const daily = monthly / tradingDays;
                return {
                    code: f.code, name: f.name, index_type: f.index_type || '',
                    weight: +w.toFixed(4), daily: +daily.toFixed(1), monthly: Math.round(monthly),
                    fee: +((f.mgmt_fee || 0) + (f.custody_fee || 0)).toFixed(4),
                    tracking_error: f.tracking_error, score: f.score || 0,
                    daily_limit: f.daily_limit || null, limit_status: f.limit_status || '',
                    exceeds_limit: false,
                };
            });
            const total = allocs.reduce((sum, a) => sum + a.monthly, 0);
            if (total > 0) {
                allocs.forEach(a => a.actual_weight = +(a.monthly / total).toFixed(4));
            }
            return allocs;
        }

        function allocatePractical(items) {
            const tradingDays = 22;
            const allocs = items.map(item => {
                const f = item.fund;
                const w = item.weight;
                const limit = f.daily_limit;
                const status = f.limit_status || '';
                const isSuspended = status.includes('暂停申购') || (status.includes('暂停') && limit === null);
                return {
                    fund: f, weight: w, limit: (limit !== null && limit !== undefined) ? limit : Infinity,
                    actual_daily: 0.0, actual_monthly: 0.0, exceeds_limit: false, is_suspended: isSuspended,
                };
            });

            let remainingBudget = budget;
            const activeAllocs = allocs.filter(a => !a.is_suspended);

            if (activeAllocs.length > 0) {
                while (remainingBudget > 0.01) {
                    const available = activeAllocs.filter(a => !a.exceeds_limit);
                    if (available.length === 0) break;

                    let totalWeight = available.reduce((sum, a) => sum + a.weight, 0);
                    if (totalWeight === 0) {
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

            const result = allocs.map(a => {
                const f = a.fund;
                return {
                    code: f.code, name: f.name, index_type: f.index_type || '',
                    weight: +a.weight.toFixed(4), daily: +a.actual_daily.toFixed(1), monthly: Math.round(a.actual_monthly),
                    fee: +((f.mgmt_fee || 0) + (f.custody_fee || 0)).toFixed(4),
                    tracking_error: f.tracking_error, score: f.score || 0,
                    daily_limit: a.limit !== Infinity ? a.limit : null, limit_status: f.limit_status || '',
                    exceeds_limit: a.exceeds_limit,
                };
            });

            const total = result.reduce((sum, a) => sum + a.monthly, 0);
            if (total > 0) {
                result.forEach(a => a.actual_weight = +(a.monthly / total).toFixed(4));
            }
            return result;
        }

        const strategiesDef = [
            { key: 'growth', name: '进取型', description: '纳指70%+标普30%，追求高成长', icon: '🚀', nq_pct: 0.7 },
            { key: 'balanced', name: '平衡型', description: '纳指50%+标普50%，攻守兼备', icon: '⚖️', nq_pct: 0.5 },
            { key: 'conservative', name: '稳健型', description: '纳指30%+标普70%，注重稳定性', icon: '🛡️', nq_pct: 0.3 }
        ];

        return strategiesDef.map(s => {
            const idealItems = pickFundsByStyle(s.nq_pct, false);
            const practicalItems = pickFundsByStyle(s.nq_pct, true);
            return {
                key: s.key,
                name: s.name,
                description: s.description,
                icon: s.icon,
                nq_pct: s.nq_pct,
                ideal: {
                    allocations: allocateIdeal(idealItems),
                    note: '不考虑限购的理论最优配置。'
                },
                practical: {
                    allocations: allocatePractical(practicalItems),
                    note: '排除暂停基金，遵守每日限购限额。'
                }
            };
        });
    }
    function hashCode(s) { let h = 0; for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0; return Math.abs(h) || 1; }

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
