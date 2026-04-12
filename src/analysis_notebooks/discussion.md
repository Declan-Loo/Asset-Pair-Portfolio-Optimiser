# Discussion

## 1. Overview of Out-of-Sample Results

The out-of-sample backtest covers 502 trading days from 1 January 2024 to 31 December 2025. The corrected results, obtained after ensuring portfolio optimisation inputs are expressed in consistent annualised units, are summarised below.

| Portfolio | Sharpe | Max DD | Total Return | Ann. Vol | Vol. Reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| Equal-Weight Spreads | 0.63 | −10.6% | 16.3% | 9.7% | — |
| **Spread Min-Var** | **0.72** | **−9.5%** | **17.8%** | **9.2%** | **+4.5%** |
| Spread Max-Sharpe (OU) | 0.96 | −11.5% | 34.8% | 14.6% | −51.3% |
| Hist Min-Var | 0.71 | −13.1% | 24.3% | 13.9% | −43.6% |
| Hist Max-Sharpe | 0.87 | −20.0% | 38.8% | 18.7% | −93.4% |
| Buy & Hold (GS/MS) | 1.40 | −30.0% | 108.0% | 27.5% | — |
| S&P 500 (SPY) | 1.11 | −18.9% | 44.3% | 16.0% | — |

*Volatility reduction is computed relative to the equal-weight spread benchmark.*

The OOS period (2024–2025) coincided with a strong bull market, particularly for financial equities. GS and MS — the legs of the first cointegrated pair — returned 126% and 89% respectively over the two-year window, which inflates the Buy & Hold benchmark and makes it an unusually demanding standard.

***

## 2. Does Covariance Optimisation Add Value over Equal-Weighting?

The first comparison — Equal-Weight Spreads versus Spread Min-Var — tests whether exploiting the spread covariance structure improves upon a naive allocation. Spread Min-Var achieves a Sharpe ratio of 0.72 against 0.63 for equal-weighting, a reduction in maximum drawdown from −10.6% to −9.5%, and a modest positive volatility reduction of +4.5%. These improvements are moderate but consistent, supporting the view that the covariance structure of mean-reverting spreads contains exploitable risk information.

The min-variance weights assigned by the optimiser are $\mathbf{w} = [0.35, 0.36, 0.29]$ across the GS/MS, KO/PEP, and DAL/UAL spreads respectively. The underweighting of the DAL/UAL spread relative to equal weight is consistent with its higher annualised variance (3.7% versus 2.5% and 2.0% for the other two pairs), confirming that the optimiser is acting on the covariance structure rather than collapsing to equal weights.

***

## 3. Does the OU Return Signal Add Value?

The minimum-variance objective does not use expected returns. It therefore serves as the zero-return baseline: the optimal allocation under the assumption that all spread expected returns are equal (or zero). Any incremental value from the OU-implied return estimates must therefore manifest through the **maximum-Sharpe objective**, where $\boldsymbol{\mu}^{\text{OU}}$ enters the optimisation directly.

Comparing Spread Max-Sharpe (OU) against Spread Min-Var isolates the effect of the OU return signal. The OU-implied expected returns are computed from the last observed spread level and its rolling 60-day mean: $\mu^{\text{OU}} = 252 \cdot (\theta - S_T)(1 - e^{-\kappa})$. At the end of the in-sample period (31 December 2023), all three spreads were trading **above** their rolling equilibrium — the GS/MS spread had risen sharply with the late-2023 financial-sector rally, and the airline spreads were elevated following post-pandemic volatility. Consequently, all three OU-implied expected returns were negative: GS/MS: −9.5%, KO/PEP: −8.6%, DAL/UAL: −23.8% (annualised). The model predicted mean reversion downward, not upward, for all pairs. The maximum-Sharpe optimiser therefore concentrates entirely in the least-negative spread (GS/MS, weight = 1.0), eliminating diversification across the other two pairs.

This concentrated allocation yields a Sharpe ratio of 0.96 and total return of 34.8% — a marked improvement over the min-variance baseline in return terms — but at the cost of higher annualised volatility (14.6% vs 9.2%) and a negative volatility reduction of −51.3% relative to the equal-weight benchmark. The OU signal therefore passes the "zero-return test" in the sense that it improves absolute and risk-adjusted returns over the min-variance baseline; however, it does so by accepting substantially more risk, which is a natural consequence of concentrating in a single spread.

Whether the OU signal provides genuine alpha — or whether the GS/MS spread would have been the best allocation regardless — is difficult to disentangle in a single OOS window. The strong performance of financial equities over 2024–2025 means the weight concentration in GS/MS was serendipitously correct, but this is not necessarily attributable to the OU model's accuracy.

***

## 4. Per-Pair Z-Score Trading Results

The portfolio-level analysis in sections 2–3 uses the spread returns passively — weighted combinations of daily log-return differentials — without any active entry or exit logic. The backtesting engine also supports a separate active layer: a z-score state machine that enters and exits positions at configurable thresholds ($z_{\text{entry}} = \pm 2.0$, $z_{\text{exit}} = \pm 0.5$, $z_{\text{stop}} = \pm 3.5$). The distinction matters because passive spread returns and active z-score strategy returns are structurally different objects: passive returns are always invested, whereas z-score returns depend on the frequency and profitability of individual trade cycles.

Over the OOS window, all three pairs produced **negative Sharpe ratios** under the active z-score strategy:

| Pair | Sharpe (Active) | Interpretation |
| --- | ---: | --- |
| GS.N / MS.N | −0.28 | Occasional mean reversion, offset by costs and failed trades |
| KO.N / PEP.O | −0.66 | Spread drifted persistently; few profitable reversions |
| DAL.N / UAL.O | −0.29 | High volatility, frequent stop-loss triggers |

These negative results stand in contrast to the positive Sharpe ratios achieved by the passive portfolio strategies. The divergence has two explanations. First, the z-score strategy requires the spread to complete a full mean-reversion cycle within a single trade — entering when the spread is stretched and exiting when it narrows — whereas the passive approach simply earns the spread's average drift over the full period. When mean reversion is slow or incomplete, the active strategy incurs transaction costs without capturing the reversion. Second, the GS/MS spread trended upward throughout 2024–2025 (driven by the financial equity rally), meaning many long-spread entries triggered the stop-loss rather than the exit threshold, producing a pattern of small losses rather than the expected profits.

This finding also contextualises the OU model's role. The OU-implied return signal predicts the direction and speed of mean reversion; it does not guarantee that an active strategy exploiting that reversion will be profitable once transaction costs and discrete signal latency are accounted for. The positive contribution of OU returns at the portfolio level (Section 3) operates through the allocation weights, not through the timing of individual trades.

***

## 5. Spread-Space versus Asset-Space Minimum Variance

Comparing Spread Min-Var and Hist Min-Var reveals the structural advantage of operating in spread space. Both portfolios use the minimum-variance objective and achieve nearly identical Sharpe ratios (0.72 vs 0.71); however, the risk profiles differ substantially. Spread Min-Var achieves annualised volatility of 9.2% against 13.9% for Hist Min-Var, and a shallower maximum drawdown (−9.5% vs −13.1%).

These differences arise directly from the construction of the spread universe. Each spread is a hedged position that removes common-factor exposure to the extent captured by the hedge ratio $\hat{\beta}$, so spread returns are inherently lower-variance than the underlying asset returns. The spread covariance matrix has diagonal entries of 0.025–0.037 (annualised), compared to 0.04–0.09 for individual stock variances. Hist Min-Var attempts to recover some of this diversification by underweighting high-volatility stocks (UAL receives zero weight) and concentrating in lower-volatility consumer staples (KO and PEP receive 36% each), but cannot replicate the inherent variance reduction achieved by the hedged spread construction.

This finding supports the primary motivation for spread-based portfolio construction: the cointegration relationship embeds a natural hedge that reduces risk independently of the optimisation strategy applied.

***

## 6. Comparison with Market Benchmarks

Both the Buy & Hold benchmark (Sharpe 1.40, total return 108%) and the S&P 500 (Sharpe 1.11, total return 44.3%) outperform all systematic spread strategies on headline Sharpe ratio during the OOS period. This result is important context but should be interpreted carefully for two reasons.

First, the 2024–2025 period coincided with an unusually strong equity bull market, particularly in financials. The Buy & Hold benchmark consisting solely of GS and MS is therefore a high-variance, sector-concentrated exposure rather than a diversified baseline. Second, the spread portfolios operate at fundamentally different volatility levels: Spread Min-Var has annualised volatility of 9.2% — roughly one-third that of Buy & Hold (27.5%) — and a maximum drawdown of −9.5% versus −30.0%. An investor with a volatility constraint or capital preservation objective would find the spread portfolios materially more attractive despite the lower absolute Sharpe ratio.

This illustrates a broader limitation of the Sharpe ratio as a sole evaluation criterion: it does not penalise absolute risk levels. The relative merit of spread-based strategies is most apparent in drawdown and volatility terms, not in raw return-maximisation.

***

## 7. Limitations and Caveats

**OOS cointegration breakdown.** Out-of-sample Engle–Granger $p$-values deteriorated for all three pairs relative to the in-sample estimates: the GS/MS $p$-value rose from 0.02 to 0.11, KO/PEP from 0.03 to 0.08, and DAL/UAL from 0.04 to 0.31. None of the pairs would pass a strict 5% threshold if tested on OOS data alone. Rolling ADF $p$-values over the OOS window show further episodes of breakdown, particularly for DAL/UAL, where the spread exhibited a persistent upward drift inconsistent with mean reversion. This instability explains the negative Sharpe ratios observed in the active z-score strategy (Section 4): when the cointegration relationship breaks down, the spread no longer mean-reverts reliably within a trade cycle, so the signal generator enters positions that trend against it. The passive portfolios are insulated from this because they hold the spread continuously rather than timing individual cycles.

**Small universe.** Only three pairs passed the cointegration screen, making portfolio-level results sensitive to the idiosyncratic performance of individual pairs. In particular, the DAL/UAL spread's near-complete OOS breakdown means it functions as a noise contributor in the portfolio, and removing it reduces the effective universe to two pairs.

**Static parameters.** All model parameters — hedge ratios, OU half-lives, and portfolio weights — are estimated once on the in-sample period and held fixed for the full two-year OOS window. Rolling recalibration would likely improve robustness to parameter drift, particularly for the hedge ratio and OU equilibrium level.

**Single OOS window.** A single two-year evaluation period is insufficient to distinguish genuine alpha from regime-specific luck. The 2024–2025 equity bull market is not representative of all market conditions, and the strong performance of financials in particular limits the generalisability of conclusions about the GS/MS spread.

**Return type consistency.** Spread-space portfolios use log-return spreads while the historical asset-space portfolios use arithmetic returns. At daily frequency the difference is negligible, but this asymmetry means comparisons between the two universes should be treated with appropriate caution.

***

## 8. Summary

The results support the following conclusions:

1. **Covariance structure adds value.** Spread Min-Var modestly but consistently outperforms equal-weighting on Sharpe, drawdown, and volatility, confirming that the spread covariance matrix captures exploitable risk information.

2. **OU return estimates improve return, not risk.** Spread Max-Sharpe (OU) surpasses the zero-return baseline (Spread Min-Var) on Sharpe ratio and total return, but at significantly higher volatility. The OU signal concentrates allocation rather than diversifying it. Notably, all three OU-implied expected returns were negative at the point of construction, so the max-Sharpe result reflects concentration in the least-negative pair rather than a positively-directional forecast.

3. **Spread construction reduces volatility versus asset space.** Spread Min-Var achieves similar risk-adjusted performance to Hist Min-Var at roughly two-thirds of the volatility, owing to the inherent variance reduction from the hedged pair construction. This is the most robust finding of the study.

4. **Active z-score trading fails under OOS conditions.** All three pair-level z-score strategies produced negative Sharpe ratios, attributable to OOS cointegration breakdown and the tendency of the GS/MS spread to trend rather than revert during 2024–2025. The positive portfolio results come from passive spread exposure, not from timing.

5. **Market conditions favour passive exposure in this window.** Buy & Hold and SPY dominate on headline Sharpe during a strong bull market. The comparative advantage of systematic spread strategies lies in drawdown control and volatility management — characteristics that are best appreciated over longer evaluation horizons or in adverse market conditions.

The research hypothesis is **partially supported**: spread-based construction provides clear benefits for risk management, and OU-implied returns add incremental signal through the max-Sharpe objective. However, the risk-reduction benefit is better attributed to the spread construction itself than to the OU return model specifically. The failure of active z-score trading further highlights that mean-reversion forecasting does not automatically translate into profitable tactical trading when cointegration is imperfect or when the holding-period assumption is violated.
