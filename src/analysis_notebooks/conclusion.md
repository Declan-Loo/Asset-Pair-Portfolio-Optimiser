# Overall Conclusion

## Research Hypothesis

> *Spread-based return estimation from cointegrated pairs produces superior portfolio allocations compared to historical mean-variance optimisation, as measured by Sharpe ratio, volatility reduction, and maximum drawdown.*

## Summary of Findings

### Pair Screening and Stability

From 16 within-sector candidate pairs (2018–2023 in-sample), three passed the 5% cointegration threshold: **GS.N/MS.N**, **KO.N/PEP.O**, and **DAL.N/UAL.O**. Out-of-sample (2024–2025) diagnostics showed instability in all three relationships.

**KPSS + ADF consensus:** In-sample, KO/PEP and DAL/UAL achieve the mean-reversion consensus (ADF rejects non-stationarity and KPSS fails to reject stationarity). GS/MS passes ADF but fails KPSS in-sample (borderline stationarity). OOS, all three pairs lose the consensus — KPSS $p \leq 0.010$ for every pair, strongly rejecting stationarity.

**Chow structural break test:** All three cointegrating regressions exhibit highly significant structural breaks across the IS/OOS split ($F > 269$, $p < 0.001$ for all pairs). This formally confirms the hedge-ratio drift and spread displacement observed in the validation tables, providing a rigorous statistical basis for the OOS performance deterioration.

### Portfolio-Level Backtest Results

Values below match the summary `metrics_df` produced at the end of `04_backtest_results.ipynb` (out-of-sample 2024–2025).

| Portfolio | Sharpe | Max DD | Total Return | Ann. Vol | Vol. Reduction |
| --- | --- | --- | --- | --- | --- |
| Equal-Weight | 0.625 | −10.6% | +16.3% | 9.7% | — |
| Spread Min-Var (μ = 0) | 0.720 | −9.5% | +17.8% | 9.2% | +4.5% |
| Spread Max-Sharpe (OU) | 0.963 | −11.5% | +34.8% | 14.6% | −51.3% |
| Hist Min-Var | 0.711 | −13.1% | +24.3% | 13.9% | −43.6% |
| Hist Max-Sharpe | 0.868 | −20.0% | +38.8% | 18.7% | −93.4% |
| Buy & Hold (All Pairs) | 1.245 | −27.8% | +74.0% | 22.9% | — |
| S&P 500 (SPY) | 1.110 | −18.9% | +44.3% | 16.0% | — |

*Volatility reduction is relative to the equal-weight spread benchmark.*

### Statistical Robustness

**Bootstrap confidence intervals (10,000 resamples, 95% CI):**

| Strategy | Sharpe | 95% CI Lower | 95% CI Upper |
| --- | --- | --- | --- |
| OU Max-Sharpe | 0.963 | −0.476 | +2.352 |
| Hist Max-Sharpe | 0.868 | −0.477 | +2.258 |
| S&P 500 | 1.110 | −0.227 | +2.506 |

No strategy achieves a CI lower bound strictly above zero. With only ~501 OOS trading days, all Sharpe point estimates carry substantial sampling uncertainty and cannot be distinguished from zero at conventional significance levels.

**Paired test (OU Max-Sharpe vs Hist Max-Sharpe):** Paired $t$-test ($t = -0.138$, $p = 0.890$) and Wilcoxon signed-rank test ($W = 62{,}557$, $p = 0.922$) both fail to reject the null of equal mean daily returns. The annualised return difference is only −2.15%. The observed Sharpe advantage of OU-Implied (0.963 vs 0.868) is **not statistically significant** over this OOS window.

**Sensitivity to thresholds and costs (GS/MS):** The GS/MS pair produces positive Sharpe at entry $z = 2.5$ and $z = 3.0$ even at 30 bps transaction costs (+0.485 and +0.275 respectively), suggesting the signal persists at higher entry thresholds. KO/PEP is negative across all configurations; DAL/UAL is borderline only at $z = 1.5$ with zero costs.

**Leave-one-pair-out (LOPO):** Dropping KO/PEP or DAL/UAL leaves the OU Max-Sharpe portfolio unchanged (Sharpe = 0.963), confirming the optimiser concentrates all weight in GS/MS. Dropping GS/MS reduces Sharpe to 0.903, confirming GS/MS is the dominant pair but the result is not entirely driven by it.

### Interpretation

**Covariance-only spread allocation (Spread Min-Var)** versus **historical asset min-variance (Hist Min-Var)** is the cleanest cross-frontier comparison: Sharpe ratios are nearly identical (0.720 vs 0.711), but spread min-variance delivers lower volatility (9.2% vs 13.9%) and a shallower drawdown (−9.5% vs −13.1%). This supports using spread-space construction for risk control even when mean forecasts are unreliable.

**Where OU μ matters** is the max-Sharpe objective. Spread Max-Sharpe (OU) raises Sharpe (0.963) and total return (34.8%) relative to Spread Min-Var, but at higher volatility (14.6%) and negative volatility reduction — a classic risk–return trade-off, not uniform dominance.

**The core limitation** is cointegration breakdown OOS, confirmed by Chow tests and KPSS. The LOPO analysis shows the portfolio is essentially a single-pair strategy (GS/MS); expanding the universe with stricter quality filters would improve diversification.

## Hypothesis Evaluation

The hypothesis is **partially supported**.

- **Supported (risk-focused):** Spread Min-Var matched Hist Min-Var on Sharpe but with clearly lower volatility and drawdown — a meaningful improvement in the risk-adjusted profile for a conservative objective.
- **Qualified:** OU-implied means do not affect min-variance weights; their effect shows up only in Spread Max-Sharpe (OU), which improves return and Sharpe versus Spread Min-Var but increases risk.
- **Not supported statistically:** The paired $t$-test and Wilcoxon test confirm the Sharpe difference (0.963 vs 0.868) is not statistically significant. Bootstrap CIs for all strategies straddle zero.
- **Not supported at signal layer:** Per-pair $z$-score trading is negative for all three pairs at the default $z = 2.0$ threshold, consistent with OOS cointegration breakdown confirmed by Chow and KPSS tests.

## Limitations

- Small final universe (three pairs; effectively one dominant pair after LOPO) increases sensitivity to pair-specific instability.
- Fixed in-sample parameters degrade under regime shift without rolling re-estimation.
- Short OOS window (~501 days) makes Sharpe estimates statistically imprecise — all 95% bootstrap CIs contain zero.
- Chow tests confirm structural breaks in all three pairs, invalidating IS-calibrated hedge ratios OOS.
- OU-implied expected returns are fragile when spreads start near equilibrium or when the cointegrating relationship has broken down.

## Final Conclusion

Cointegration-driven spread portfolios provide meaningful **downside and volatility control** relative to asset-space min-variance in this OOS window. The Spread Max-Sharpe (OU) portfolio achieves the highest Sharpe among the spread strategies (0.963), but the advantage over the historical baseline (0.868) is not statistically significant given the short evaluation window. Chow tests formally confirm structural breaks in all cointegrating relationships, explaining why pair-level $z$-score strategies underperform OOS. Future work should focus on stricter pair-quality filters, rolling parameter re-estimation, and larger candidate universes to improve OOS robustness and statistical power.
