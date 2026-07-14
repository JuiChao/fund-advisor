/**
 * 蒙特卡洛模拟 Web Worker
 * 在后台线程执行计算密集的模拟，避免阻塞主线程 UI
 *
 * 消息格式:
 *   入: { id, funds, weights, years, budget, config }
 *   出: { id, result } 或 { id, error }
 */
self.onmessage = function(e) {
    const { id, funds, weights, years, budget, config } = e.data;
    try {
        const result = simulate(funds, weights, years, budget, config);
        self.postMessage({ id, result });
    } catch (err) {
        self.postMessage({ id, error: err.message });
    }
};

function simulate(funds, weights, years, budget, cfg) {
    const N = cfg.simulation.n_sims_frontend;
    const months = years * 12;
    const totalInvested = budget * months;
    const finalValues = new Array(N).fill(0);

    const rho = cfg.simulation.correlation_nq_sp;
    const params = cfg.simulation.params;
    const defaults = cfg.defaults;

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
