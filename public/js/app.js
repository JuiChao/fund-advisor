/**
 * 主应用逻辑 - 调用 API 获取预计算结果
 */
const App = (() => {
    let FUND_DATA = [];
    let chartPool = {};

    const API_BASE = ''; // 同源，Cloudflare Pages Functions

    function fmt(v) { return v == null ? '-' : (v * 100).toFixed(2) + '%'; }
    function money(v) { return v == null ? '-' : v >= 10000 ? (v / 10000).toFixed(1) + '万' : v.toLocaleString('zh-CN'); }
    function stars(n) { return (!n || n === 0) ? '-' : '★'.repeat(n); }
    function pill(s) {
        if (!s) return '<span class="pill pb">未知</span>';
        if (s.includes('暂停')) return '<span class="pill pr">' + s + '</span>';
        if (s.includes('限10元')) return '<span class="pill py">' + s + '</span>';
        return '<span class="pill pg">' + s + '</span>';
    }
    function feeC(f) { return f <= 0.006 ? 'color:#375623;font-weight:700' : f <= 0.007 ? 'color:#548235' : f <= 0.01 ? '' : 'color:#C00000'; }

    // 页面切换
    function initNav() {
        document.querySelectorAll('#nav-links a').forEach(a => {
            a.addEventListener('click', e => {
                e.preventDefault();
                const page = a.dataset.page;
                document.querySelectorAll('#nav-links a').forEach(x => x.classList.remove('on'));
                a.classList.add('on');
                document.querySelectorAll('[id^="page-"]').forEach(p => p.style.display = 'none');
                document.getElementById('page-' + page).style.display = '';
                if (page === 'ranking') renderRanking();
                if (page === 'simulator') populateSimSelect();
                if (page === 'portfolio') computePortfolio();
            });
        });
    }

    // 首页
    function renderHome() {
        const nq = FUND_DATA.filter(f => f.index_type === '纳斯达克100');
        const sp = FUND_DATA.filter(f => f.index_type === '标普500');
        const avail = FUND_DATA.filter(f => !(f.limit_status || '').includes('暂停'));
        const minFee = Math.min(...FUND_DATA.map(f => (f.mgmt_fee || 0) + (f.custody_fee || 0)));

        document.getElementById('home-stats').innerHTML = `
            <div class="stat"><div class="lb">基金总数</div><div class="vl">${FUND_DATA.length}</div><div class="sub">纳指${nq.length} + 标普${sp.length}</div></div>
            <div class="stat"><div class="lb">可购买</div><div class="vl">${avail.length}</div><div class="sub">未暂停申购</div></div>
            <div class="stat"><div class="lb">最低费率</div><div class="vl">${(minFee * 100).toFixed(2)}%</div><div class="sub">管理费+托管费</div></div>
            <div class="stat"><div class="lb">数据日期</div><div class="vl" style="font-size:.95rem">${FUND_DATA[0]?.updated_at?.split('T')[0] || '-'}</div><div class="sub">每日自动更新</div></div>
        `;

        // 费率图
        function feeChart(id, list) {
            const data = list.map(f => ({ code: f.code, fee: ((f.mgmt_fee || 0) + (f.custody_fee || 0)) * 100 })).sort((a, b) => a.fee - b.fee);
            if (chartPool[id]) chartPool[id].destroy();
            chartPool[id] = new Chart(document.getElementById(id), {
                type: 'bar', data: { labels: data.map(d => d.code), datasets: [{ label: '费率%', data: data.map(d => d.fee), backgroundColor: data.map(d => d.fee <= 0.7 ? '#548235' : d.fee <= 1.0 ? '#4472C4' : '#C00000') }] },
                options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
            });
        }
        feeChart('ch-nq', nq);
        feeChart('ch-sp', sp);

        // 策略预览 - 调用 API
        loadStrategiesPreview();
    }

    async function loadStrategiesPreview() {
        try {
            const strategies = await apiGet('/api/portfolio?years=20&budget=2000');
            let html = '<table><thead><tr><th>策略</th><th>说明</th><th>基金数</th><th>预期年化</th><th>20年终值</th></tr></thead><tbody>';
            strategies.forEach(s => {
                const sim = s.simulation || {};
                html += `<tr><td><strong>${s.name}</strong></td><td style="text-align:left;font-size:.83rem">${s.description || ''}</td><td>${(s.allocations || []).length}</td><td>${sim.annualReturn ? sim.annualReturn + '%' : '-'}</td><td>${sim.medianFinal ? money(sim.medianFinal) : '-'}</td></tr>`;
            });
            html += '</tbody></table>';
            document.getElementById('home-strategies').innerHTML = html;
        } catch (e) {
            document.getElementById('home-strategies').innerHTML = '<p style="color:var(--err)">加载失败: ' + e.message + '</p>';
        }
    }

    // API 调用
    async function apiGet(url) {
        const resp = await fetch(API_BASE + url);
        if (!resp.ok) throw new Error(`API error: ${resp.status}`);
        return resp.json();
    }

    // 排名页 - 前端本地计算（轻量，不需要API）
    let rankData = [];
    const rankCols = [
        { key: 'rank', label: '排名' }, { key: 'code', label: '代码' }, { key: 'name', label: '名称', render: r => '<strong>' + r.name + '</strong>' },
        { key: 'fee', label: '综合费率', render: r => { const f = (r.mgmt_fee || 0) + (r.custody_fee || 0); return '<span style="' + feeC(f) + '">' + fmt(f) + '</span>'; } },
        { key: 'tracking_error', label: '跟踪误差', render: r => fmt(r.tracking_error) },
        { key: 'scale', label: '规模(亿)', render: r => r.scale?.toFixed(1) || '-' },
        { key: 'return_3yr', label: '近3年', render: r => fmt(r.return_3yr) },
        { key: 'morningstar', label: '晨星', render: r => stars(r.morningstar) },
        { key: 'limit_status', label: '限购', render: r => pill(r.limit_status) },
        { key: 'score', label: '评分', render: r => '<strong>' + r.score + '</strong>' },
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
        thead.innerHTML = '<tr>' + rankCols.map(c => `<th data-key="${c.key}">${c.label} ⇅</th>`).join('') + '</tr>';

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

    // 模拟器页 - 调用 API
    function populateSimSelect() {
        const sel = document.getElementById('sim-sel');
        if (sel.options.length > 0) return;
        FUND_DATA.forEach(f => {
            const o = document.createElement('option');
            o.value = f.code;
            o.textContent = `${f.code} ${f.name} (${((f.mgmt_fee||0)+(f.custody_fee||0))*100}%)`;
            sel.appendChild(o);
        });
    }

    async function runSimulation() {
        const sel = document.getElementById('sim-sel');
        const codes = Array.from(sel.selectedOptions).map(o => o.value);
        if (!codes.length) { alert('请至少选择一只基金'); return; }
        const btn = document.getElementById('btn-sim');
        btn.disabled = true; btn.textContent = '模拟中...';

        try {
            const monthly = +document.getElementById('sim-m').value;
            const years = +document.getElementById('sim-y').value;

            // 对于单基金，调用 /api/simulate
            // 对于多基金组合，调用 /api/portfolio 并找到匹配的策略
            let result;
            if (codes.length === 1) {
                const data = await apiGet(`/api/simulate?code=${codes[0]}&years=${years}&budget=${monthly}`);
                result = data.simulation;
            } else {
                // 多基金：从预计算策略中找最接近的
                const strategies = await apiGet(`/api/portfolio?years=${years}&budget=${monthly}`);
                // 找到包含最多匹配基金的策略
                let best = null, bestOverlap = 0;
                strategies.forEach(s => {
                    const overlap = (s.allocations || []).filter(a => codes.includes(a.code)).length;
                    if (overlap > bestOverlap) { bestOverlap = overlap; best = s; }
                });
                result = best?.simulation;
            }

            if (!result) {
                document.getElementById('sim-result').innerHTML = '<p style="color:var(--err)">无法获取模拟结果</p>';
                btn.disabled = false; btn.textContent = '运行模拟';
                return;
            }

            const total = monthly * years * 12;
            document.getElementById('sim-result').innerHTML = `
                <div class="stats">
                    <div class="stat"><div class="lb">总投入</div><div class="vl" style="font-size:1.15rem">${money(total)}</div></div>
                    <div class="stat"><div class="lb">预期终值(中位)</div><div class="vl" style="font-size:1.15rem;color:var(--ok)">${money(result.medianFinal)}</div></div>
                    <div class="stat"><div class="lb">收益率</div><div class="vl" style="font-size:1.15rem">${result.meanReturnPct || result.annualReturn}%</div></div>
                </div>
                <table style="margin-top:.8rem">
                    <tr><td>5%悲观</td><td><strong>${money(result.p5)}</strong></td></tr>
                    <tr><td>25%</td><td><strong>${money(result.p25)}</strong></td></tr>
                    <tr><td>50%中位</td><td><strong>${money(result.medianFinal)}</strong></td></tr>
                    <tr><td>75%</td><td><strong>${money(result.p75)}</strong></td></tr>
                    <tr><td>95%乐观</td><td><strong>${money(result.p95)}</strong></td></tr>
                </table>`;

            if (chartPool.sim) chartPool.sim.destroy();
            chartPool.sim = new Chart(document.getElementById('ch-sim'), {
                type: 'bar', data: { labels: ['5%分位', '25%', '中位数', '75%', '95%'], datasets: [{ label: '万元', data: [result.p5/10000, result.p25/10000, result.medianFinal/10000, result.p75/10000, result.p95/10000], backgroundColor: ['#C00000','#ED7D31','#4472C4','#70AD47','#548235'] }] },
                options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { title: { display: true, text: '万元' } } } }
            });
        } catch (e) {
            document.getElementById('sim-result').innerHTML = `<p style="color:var(--err)">模拟失败: ${e.message}</p>`;
        }

        btn.disabled = false; btn.textContent = '运行模拟';
    }

    // 定投方案页 - 调用 API
    let pfCharts = {};

    async function computePortfolio() {
        const btn = document.getElementById('btn-pf');
        btn.disabled = true; btn.textContent = '计算中...';

        try {
            const monthly = +document.getElementById('pf-m').value;
            const years = +document.getElementById('pf-y').value;
            Object.values(pfCharts).forEach(c => c.destroy());
            pfCharts = {};

            const strategies = await apiGet(`/api/portfolio?years=${years}&budget=${monthly}`);

            let html = '';
            strategies.forEach(s => {
                const sim = s.simulation || {};
                const allocs = s.allocations || [];
                const rows = allocs.map(a => `<tr class="${a.exceeds_limit ? 'wr' : ''}">
                    <td>${a.code}</td><td style="text-align:left">${a.name}</td><td style="${feeC(a.fee)}">${(a.fee*100).toFixed(2)}%</td>
                    <td>${a.daily}元</td><td>${a.monthly}元</td><td>${(a.actual_weight*100).toFixed(0)}%</td><td>${pill(a.limit_status)}</td>
                </tr>`).join('');

                const cid = 'ch-' + s.key;
                html += `<div class="card"><h3>${s.name} <span class="tag">${s.key}</span></h3><p style="color:var(--txt2);font-size:.88rem;margin-bottom:.8rem">${s.description || ''}</p>
                <div class="g2"><div><table><thead><tr><th>代码</th><th>名称</th><th>费率</th><th>每日</th><th>月合计</th><th>占比</th><th>限购</th></tr></thead><tbody>${rows}</tbody></table></div>
                <div><div class="cht"><canvas id="${cid}"></canvas></div>
                ${sim.medianFinal ? `<div style="margin-top:.8rem"><div class="stats"><div class="stat"><div class="lb">预期年化</div><div class="vl" style="font-size:1.15rem">${sim.annualReturn}%</div></div><div class="stat"><div class="lb">${years}年终值</div><div class="vl" style="font-size:1.15rem;color:var(--ok)">${money(sim.medianFinal)}</div></div></div>
                <div style="font-size:.82rem;color:var(--txt2);margin-top:.3rem">5%: ${money(sim.p5)} | 25%: ${money(sim.p25)} | 75%: ${money(sim.p75)} | 95%: ${money(sim.p95)}</div></div>` : ''}</div></div></div>`;
            });
            document.getElementById('pf-container').innerHTML = html;

            // 画饼图
            strategies.forEach(s => {
                const cid = 'ch-' + s.key;
                const el = document.getElementById(cid);
                if (!el || !s.allocations.length) return;
                pfCharts[cid] = new Chart(el, {
                    type: 'doughnut', data: { labels: s.allocations.map(a => a.name.substring(0, 8)), datasets: [{ data: s.allocations.map(a => a.monthly), backgroundColor: ['#4472C4','#ED7D31','#A5A5A5','#FFC000','#5B9BD5','#70AD47'] }] },
                    options: { responsive: true, plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } } }
                });
            });
        } catch (e) {
            document.getElementById('pf-container').innerHTML = `<p style="color:var(--err)">计算失败: ${e.message}</p>`;
        }

        btn.disabled = false; btn.textContent = '重新计算';
    }

    // 初始化
    async function init() {
        initNav();
        try {
            const resp = await fetch('data/funds.json');
            FUND_DATA = await resp.json();
            renderHome();
        } catch (e) {
            document.getElementById('home-stats').innerHTML = '<div class="card"><p style="color:var(--err)">数据加载失败: ' + e.message + '</p></div>';
        }

        document.getElementById('rank-filter').addEventListener('change', renderRanking);
        document.getElementById('sim-m').addEventListener('input', e => document.getElementById('sim-mv').textContent = e.target.value + '元');
        document.getElementById('sim-y').addEventListener('input', e => document.getElementById('sim-yv').textContent = e.target.value + '年');
        document.getElementById('pf-m').addEventListener('input', e => document.getElementById('pf-mv').textContent = e.target.value + '元');
        document.getElementById('pf-y').addEventListener('input', e => document.getElementById('pf-yv').textContent = e.target.value + '年');
        document.getElementById('btn-sim').addEventListener('click', runSimulation);
        document.getElementById('btn-pf').addEventListener('click', computePortfolio);
    }

    return { init };
})();

document.addEventListener('DOMContentLoaded', App.init);
