    async function runSimulation() {
        const codes = Array.from(msSelected);
        if (!codes.length) { alert('请至少选择一只基金'); return; }
        const btn = document.getElementById('btn-sim');
        btn.disabled = true; btn.textContent = '模拟中…';

        try {
            // 确保读取到有效的数值，fallback 到 HTML 默认值
            const monthlyEl = document.getElementById('sim-m');
            const yearsEl = document.getElementById('sim-y');
            const monthly = Math.max(500, parseInt(monthlyEl.value) || parseInt(monthlyEl.getAttribute('value')) || 2000);
            const years = Math.max(5, parseInt(yearsEl.value) || parseInt(yearsEl.getAttribute('value')) || 20);
            let result = null;

            if (codes.length === 1) {
                try {
                    const data = await apiGet(`/api/simulate?code=${codes[0]}&years=${years}&budget=${monthly}`);
                    result = data?.simulation || null;
                } catch (apiErr) {
                    console.warn('API call failed, using local simulation:', apiErr);
                    result = null;
                }
            } else {
                try {
                    const strategies = await apiGet(`/api/portfolio?years=${years}&budget=${monthly}`);
                    let best = null, bestOverlap = 0;
                    strategies.forEach(s => {
                        ['ideal', 'practical'].forEach(vk => {
                            const allocs = s[vk]?.allocations || [];
                            const overlap = allocs.filter(a => codes.includes(a.code)).length;
                            if (overlap > bestOverlap) {
                                bestOverlap = overlap;
                                best = s[vk];
                            }
                        });
                    });
                    result = best?.simulation || null;
                } catch (apiErr) {
                    console.warn('Portfolio API failed:', apiErr);
                    result = null;
                }
            }

            // 如果 API 结果无效，使用本地模拟
            if (!result || isNaN(result.medianFinal) || result.medianFinal <= 0) {
                const fundData = FUND_DATA.find(f => f.code === codes[0]);
                if (fundData) {
                    result = localSimulate(fundData, years, monthly);
                }
            }

            if (!result || isNaN(result.medianFinal) || result.medianFinal <= 0) {
                document.getElementById('sim-result').innerHTML = '<p style="color:var(--err);text-align:center;padding:2rem">无法获取模拟结果，请稍后重试</p>';
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

    // 本地蒙特卡洛模拟（API 不可用时的 fallback）
    function localSimulate(fund, years, budget) {
        const N_SIMS = 3000;
        const n_months = years * 12;
        const total_invested = budget * n_months;
        const is_sp = (fund.index_type || '').includes('标普');
        const te = fund.tracking_error || 0.015;
        const annual_fee = (fund.mgmt_fee || 0.008) + (fund.custody_fee || 0.002);
        const purchase_fee = 0.0012;
        const idx_ret_mean = (is_sp ? 0.11 : 0.14) / 12;
        const idx_ret_vol = (is_sp ? 0.18 : 0.22) / Math.sqrt(12);
        const te_vol = te / Math.sqrt(12);
        const fx_mean = 0.005 / 12;
        const fx_vol = 0.03 / Math.sqrt(12);
        const fee_m = annual_fee / 12;
        const div_m = 0.008 / 12 * 0.9;
        const invest_per_month = budget * (1 - purchase_fee);
        const seed = hashCode(fund.code);
        const final_values = [];

        for (let sim = 0; sim < N_SIMS; sim++) {
            let total_shares = 0;
            let nav = 1;
            let s = (seed + sim) || 1;
            for (let m = 0; m < n_months; m++) {
                s = (s * 1664525 + 1013904223) & 0xFFFFFFFF;
                const u1 = (s >>> 0) / 0xFFFFFFFF;
                s = (s * 1664525 + 1013904223) & 0xFFFFFFFF;
                const u2 = (s >>> 0) / 0xFFFFFFFF;
                const z = Math.sqrt(-2 * Math.log(u1 || 1e-10)) * Math.cos(2 * Math.PI * u2);
                const idx_r = idx_ret_mean + z * idx_ret_vol;
                s = (s * 1664525 + 1013904223) & 0xFFFFFFFF;
                const u3 = (s >>> 0) / 0xFFFFFFFF;
                s = (s * 1664525 + 1013904223) & 0xFFFFFFFF;
                const u4 = (s >>> 0) / 0xFFFFFFFF;
                const z2 = Math.sqrt(-2 * Math.log(u3 || 1e-10)) * Math.cos(2 * Math.PI * u4);
                const te_r = z2 * te_vol;
                s = (s * 1664525 + 1013904223) & 0xFFFFFFFF;
                const u5 = (s >>> 0) / 0xFFFFFFFF;
                s = (s * 1664525 + 1013904223) & 0xFFFFFFFF;
                const u6 = (s >>> 0) / 0xFFFFFFFF;
                const z3 = Math.sqrt(-2 * Math.log(u5 || 1e-10)) * Math.cos(2 * Math.PI * u6);
                const fx_r = fx_mean + z3 * fx_vol;
                const fund_r = idx_r + te_r - fee_m + div_m + fx_r;
                nav *= (1 + fund_r);
                total_shares += invest_per_month / nav;
            }
            final_values.push(total_shares * nav);
        }

        final_values.sort((a, b) => a - b);
        const mean = final_values.reduce((s, v) => s + v, 0) / N_SIMS;
        const median = final_values[Math.floor(N_SIMS * 0.5)];
        const returns = (mean / total_invested - 1) * 100;

        return {
            totalInvested: total_invested,
            medianFinal: Math.round(median),
            p5: Math.round(final_values[Math.floor(N_SIMS * 0.05)]),
            p25: Math.round(final_values[Math.floor(N_SIMS * 0.25)]),
            p75: Math.round(final_values[Math.floor(N_SIMS * 0.75)]),
            p95: Math.round(final_values[Math.floor(N_SIMS * 0.95)]),
            annualReturn: Math.round(returns / years * 100) / 100,
            meanReturnPct: Math.round(returns * 100) / 100,
        };
    }

    function hashCode(s) {
        let h = 0;
        for (let i = 0; i < s.length; i++) {
            h = ((h << 5) - h + s.charCodeAt(i)) | 0;
        }
        return Math.abs(h) || 1;
    }