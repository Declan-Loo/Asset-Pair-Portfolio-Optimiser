# Discussion

## 1. Overview of Out-of-Sample Results

The out-of-sample backtest covers 501 trading days from 1 January 2024 to 31 December 2025. Results are summarised below.

| Portfolio | Sharpe | Max DD | Total Return | Ann. Vol | Vol. Reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| Equal-Weight Spreads | 0.625 | −10.6% | +16.3% | 9.7% | — |
| **Spread Min-Var (μ=0)** | **0.720** | **−9.5%** | **+17.8%** | **9.2%** | **+4.5%** |
| Spread Max-Sharpe (OU) | 0.963 | −11.5% | +34.8% | 14.6% | −51.3% |
| Hist Min-Var | 0.711 | −13.1% | +24.3% | 13.9% | −43.6% |
| Hist Max-Sharpe | 0.868 | −20.0% | +38.8% | 18.7% | −93.4% |
| Buy & Hold (All Pairs) | 1.245 | −27.8% | +74.0% | 22.9% | — |
| S&P 500 (SPY) | 1.110 | −18.9% | +44.3% | 16.0% | — |

*Volatility reduction is computed relative to the equal-weight spread benchmark.*

The OOS period (2024–2025) coincided with a strong bull market, particularly for financial equities. The Buy & Hold benchmark (all pair constituents, equal-weight) returned +74.0% at a Sharpe of 1.245, making it an unusually demanding standard that reflects the strong sector-specific tailwinds rather than a diversified market proxy.

***

## 2. Does Covariance Optimisation Add Value over Equal-Weighting?

The first comparison — Equal-Weight Spreads versus Spread Min-Var — tests whether exploiting the spread covariance structure improves upon a naive allocation. Spread Min-Var achieves a Sharpe ratio of 0.720 against 0.625 for equal-weighting, a reduction in maximum drawdown from −10.6% to −9.5%, and a positive volatility reduction of +4.5%. These improvements are moderate but consistent, supporting the view that the covariance structure of mean-reverting spreads contains exploitable risk information.

The min-variance weights assigned by the optimiser are **w** = [0.35, 0.36, 0.29] across the GS/MS, KO/PEP, and DAL/UAL spreads respectively. The underweighting of DAL/UAL is consistent with its higher annualised variance, confirming that the optimiser is acting on the covariance structure rather than collapsing to equal weights.

***

## 3. Does the OU Return Signal Add Value?

The minimum-variance objective (Spread Min-Var, μ=0) serves as the zero-return baseline — the optimal allocation assuming all spread expected returns are equal. Any incremental value from OU-implied returns must manifest through the maximum-Sharpe objective, where **μ**^OU enters directly.

At the IS/OOS boundary (31 December 2023), the end-of-sample z-scores were: GS/MS +1.74, KO/PEP −0.76, DAL/UAL +1.32. The OU-implied annualised expected returns were −10.69% (GS/MS), +1.93% (KO/PEP), and −0.24% (DAL/UAL) respectively — all three spreads at or above equilibrium, so the max-Sharpe optimiser concentrated entirely in GS/MS (w = 1.0), the least-negative pair.

This concentrated allocation yields Sharpe 0.963 and total return +34.8%, a meaningful improvement over Spread Min-Var (Sharpe 0.720, +17.8%), but at higher annualised volatility (14.6% vs 9.2%) and a negative volatility reduction of −51.3%.

**Statistical robustness.** Bootstrap confidence intervals (10,000 resamples, 95% CI) straddle zero for all strategies: OU Max-Sharpe [−0.476, +2.352], Hist Max-Sharpe [−0.477, +2.258]. A paired t-test (t = −0.138, p = 0.890) and Wilcoxon signed-rank test (W = 62,557, p = 0.922) both fail to reject the null of equal mean daily returns between OU Max-Sharpe and Hist Max-Sharpe. The annualised return difference is only −2.15%. The observed Sharpe advantage (0.963 vs 0.868) is **not statistically significant** over this OOS window.

Whether the OU signal provides genuine alpha is difficult to disentangle in a single OOS window. The strong performance of financial equities over 2024–2025 means weight concentration in GS/MS was serendipitously correct, but this is not necessarily attributable to the accuracy of the OU model itself.

***

## 4. Per-Pair Z-Score Trading Results

All three pairs produced **negative Sharpe ratios** under the active z-score strategy (entry ±2.0σ, exit ±0.5σ):

| Pair | Sharpe (Active) | Max DD | Total Return | Ann. Vol | Trades |
| --- | ---: | ---: | ---: | ---: | ---: |
| GS.N / MS.N | −0.285 | −20.7% | −8.4% | 17.2% | 9 |
| KO.N / PEP.O | −0.665 | −15.1% | −6.3% | 7.5% | 8 |
| DAL.N / UAL.O | −0.286 | −16.0% | −1.2% | 7.9% | 8 |

These negative results stand in contrast to the positive passive portfolio Sharpe ratios, for two reasons. First, the z-score strategy requires the spread to complete a full mean-reversion cycle within a single trade, whereas the passive approach earns the spread's average drift over the full period. Second, the GS/MS spread trended upward throughout 2024–2025, meaning many long-spread entries triggered the stop-loss rather than the exit threshold.

**Sensitivity analysis.** A grid sweep over entry z-scores {1.5, 2.0, 2.5, 3.0} and transaction costs {0, 5, 10, 20, 30} bps shows GS/MS produces positive Sharpe at z_entry = 2.5 and 3.0 even at 30 bps (+0.485 and +0.275 respectively). KO/PEP is negative across all configurations; DAL/UAL is borderline only at z_entry = 1.5 with zero costs.

***

## 5. Spread-Space versus Asset-Space Minimum Variance

Comparing Spread Min-Var and Hist Min-Var reveals the structural advantage of operating in spread space. Both use the minimum-variance objective and achieve nearly identical Sharpe ratios (0.720 vs 0.711); however, Spread Min-Var achieves annualised volatility of 9.2% against 13.9% for Hist Min-Var, and a shallower maximum drawdown (−9.5% vs −13.1%).

These differences arise directly from the hedged spread construction: each spread removes common-factor exposure captured by the hedge ratio β̂, so spread returns are inherently lower-variance than underlying asset returns. Hist Min-Var concentrates in lower-volatility consumer staples (KO: 48.7%, PEP: 39.7%) and zeros out MS.N, but cannot replicate the inherent variance reduction of the hedged construction.

This is the most robust finding of the study: cointegration-based spread construction provides clear risk reduction independently of the optimisation strategy or return model applied.

***

## 6. Comparison with Market Benchmarks

Buy & Hold (all pairs, 1.245 Sharpe, +74.0%) and S&P 500 (1.110, +44.3%) outperform all systematic spread strategies on headline Sharpe. However, the spread portfolios operate at fundamentally different volatility levels: Spread Min-Var has annualised volatility of 9.2% and maximum drawdown of −9.5%, versus 22.9% and −27.8% for Buy & Hold. An investor with a volatility constraint or capital preservation objective would find the spread portfolios materially more attractive despite the lower absolute Sharpe ratio.

***

## 7. OOS Cointegration Instability

All three pairs show formal OOS cointegration breakdown, confirmed by multiple tests:

- **ADF p-values** rise from IS levels (0.020, 0.035, 0.036) to OOS levels (0.452, 0.622, 0.583) — none pass a 5% threshold OOS.
- **KPSS complement:** All three pairs strongly reject the null of stationarity OOS (p ≤ 0.010), losing the IS mean-reversion consensus in every case.
- **Chow structural break test:** All three cointegrating regressions exhibit highly significant structural breaks at the IS/OOS boundary (F > 269, p < 0.001 for all pairs), formally confirming hedge-ratio drift and spread displacement.
- **OOS half-lives** collapse from 40–53 days IS to 81–156 days OOS, consistent with a level shift in spread equilibrium rather than temporary displacement.

This breakdown explains the failure of the active z-score strategies and contextualises the OU model's role: the positive passive-portfolio contribution operates through allocation weights, not through the timing of individual trades.

***

## 8. Robustness Tests

**Leave-one-pair-out (LOPO).** Dropping KO/PEP or DAL/UAL leaves the OU Max-Sharpe portfolio unchanged (Sharpe = 0.963), confirming the optimiser assigns all weight to GS/MS. Dropping GS/MS reduces Sharpe to 0.903, confirming GS/MS is the dominant pair but the result is not entirely driven by it.

**Bootstrap CIs.** 95% bootstrap confidence intervals for all strategies straddle zero (T ≈ 501 trading days), confirming that no Sharpe point estimate is statistically distinguishable from zero at conventional significance levels.

**Sensitivity.** Active z-score results are robust to parameter choice only for GS/MS at higher entry thresholds (z ≥ 2.5); KO/PEP and DAL/UAL fail across all tested configurations.

***

## 9. Limitations and Caveats

**OOS cointegration breakdown.** Chow tests and KPSS tests formally confirm structural breaks in all three pairs, invalidating IS-calibrated hedge ratios and OU equilibrium levels. This is the primary source of active strategy underperformance.

**Small universe.** Only three pairs passed the cointegration screen; the LOPO analysis confirms the portfolio is effectively a single-pair strategy (GS/MS). Portfolio-level conclusions are sensitive to the idiosyncratic performance of this pair.

**Static parameters.** Hedge ratios, OU half-lives, and portfolio weights are estimated once IS and held fixed. Rolling recalibration would improve robustness to parameter drift.

**Short OOS window.** A single 501-day evaluation period is insufficient to distinguish genuine alpha from regime-specific luck. All 95% bootstrap CIs contain zero.

**Single OOS regime.** The 2024–2025 bull market in financials is not representative of all market conditions, limiting the generalisability of conclusions about the GS/MS spread.

***

## 10. Summary

1. **Covariance structure adds value.** Spread Min-Var modestly but consistently outperforms equal-weighting on Sharpe, drawdown, and volatility.
2. **OU return estimates improve return, not risk.** Spread Max-Sharpe (OU) surpasses the zero-return baseline on Sharpe and total return, but at significantly higher volatility. The observed Sharpe advantage is not statistically significant (paired t-test p = 0.890, Wilcoxon p = 0.922).
3. **Spread construction reduces volatility versus asset space.** Spread Min-Var achieves similar risk-adjusted performance to Hist Min-Var at roughly two-thirds of the volatility — the most robust finding of the study.
4. **Active z-score trading fails OOS.** All three pair-level z-score strategies produced negative Sharpe ratios, attributable to OOS cointegration breakdown confirmed by Chow tests, KPSS, and rolling ADF p-values.
5. **Market conditions favour passive exposure in this window.** Buy & Hold and SPY dominate on headline Sharpe in a strong bull market; spread strategies' advantage lies in drawdown control and volatility management.

The research hypothesis is **partially supported**: spread-based construction provides clear risk-management benefits, and OU-implied returns add incremental signal through the max-Sharpe objective. However, the risk-reduction benefit is better attributed to spread construction itself than to the OU return model, and no statistical test can distinguish the OU Sharpe advantage from sampling noise over the available OOS window.
