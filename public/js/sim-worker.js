/**
 * 蒙特卡洛模拟 Web Worker
 * 在后台线程执行计算密集的模拟，避免阻塞主线程 UI
 *
 * 消息格式:
 *   入: { id, funds, weights, years, budget, config }
 *   出: { id, result } 或 { id, error }
 */
self.onmessage = function(e) {
    const { id, funds, weights, years, budget, config, dynamicDCA, sensitivity } = e.data;
    try {
        const result = simulate(funds, weights, years, budget, config, dynamicDCA, sensitivity);
        self.postMessage({ id, result });
    } catch (err) {
        self.postMessage({ id, error: err.message });
    }
};

function simulate(funds, weights, years, budget, cfg, dynamicDCA, sensitivity) {
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

    funds.forEach((fund, fIdx) => {
        const weight = weights[fIdx];
        if (weight <= 0) return;

        const fundBudget = budget * weight;
        const isSP = (fund.index_type || '').includes('标普');
        const te = fund.tracking_error || defaults.tracking_error_for_simulation;
        const fee = (fund.mgmt_fee || defaults.mgmt_fee) + (fund.custody_fee || defaults.custody_fee) + (fund.sales_fee || 0);

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
