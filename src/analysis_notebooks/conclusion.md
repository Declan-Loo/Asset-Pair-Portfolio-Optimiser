# Overall Conclusion

## Research Hypothesis

> *Spread-based return estimation from cointegrated pairs produces superior portfolio allocations compared to historical mean-variance optimisation, as measured by Sharpe ratio, volatility reduction, and maximum drawdown.*

## Summary of Findings

### Pair Screening and Stability

From 16 within-sector candidate pairs (2018-2023 in-sample), three passed the 5% cointegration threshold: **GS.N/MS.N**, **KO.N/PEP.O**, and **DAL.N/UAL.O**. However, out-of-sample (2024-2025) diagnostics showed instability in all three relationships, with DAL/UAL the weakest and most noise-contributing spread in portfolio construction.

### Portfolio-Level Backtest Results

Values below match the summary `metrics_df` produced at the end of `04_backtest_results.ipynb` (out-of-sample 2024–2025).

| Portfolio | Sharpe | Max DD | Total Return | Ann. Vol | Vol. Reduction |
| --- | --- | --- | --- | --- | --- |
| Equal-Weight | 0.6253 | -10.62% | 16.28% | 9.68% | — |
| Spread Min-Var (μ = 0) | 0.7200 | -9.48% | 17.77% | 9.24% | +4.54% |
| Spread Max-Sharpe (OU) | 0.9630 | -11.54% | 34.82% | 14.64% | -51.25% |
| Hist Min-Var | 0.7113 | -13.08% | 24.26% | 13.91% | -43.62% |
| Hist Max-Sharpe | 0.8677 | -20.02% | 38.83% | 18.73% | -93.44% |
| Buy & Hold | 1.4029 | -29.96% | 108.04% | 27.54% | — |
| S&P 500 (SPY) | 1.1099 | -18.90% | 44.33% | 15.98% | — |

*Volatility reduction is relative to the equal-weight spread benchmark (where not shown as NaN).*

**Note on OU Min-Var:** Minimum-variance weights depend only on the covariance matrix, not on the expected-return vector. In this implementation, **OU Min-Var** and **Spread Min-Var (μ = 0)** therefore use the same weights and identical OOS return series — only one row is needed in the table.

Buy-and-hold and SPY achieved higher headline Sharpe and total return but with much larger drawdowns and volatility than spread-based min-variance. **Spread Min-Var** remains the conservative spread-space baseline: modest positive volatility reduction versus equal-weight, with lower drawdown than **Spread Max-Sharpe (OU)**.

### Interpretation

**Covariance-only spread allocation (Spread Min-Var)** versus **historical asset min-variance (Hist Min-Var)** is now the clean cross-frontier comparison: Sharpe ratios are almost identical (0.7200 vs 0.7113), but spread min-variance delivers lower annualised volatility (9.24% vs 13.91%) and a shallower maximum drawdown (-9.48% vs -13.08%). That supports using spread-space construction for risk control even when mean forecasts are doubtful.

**Where OU μ enters the model** is the **max-Sharpe** objective, not min-variance. **Spread Max-Sharpe (OU)** raises Sharpe (0.9630) and total return (34.82%) relative to Spread Min-Var, but at the cost of higher volatility (14.64%) and negative volatility reduction versus equal-weight — a classic risk–return trade-off rather than uniform dominance.

A recurring theme remains **cointegration quality**: weak or borderline pairs can add noise; expanding the universe without stability checks can dilute performance.

## Hypothesis Evaluation

The hypothesis is **partially supported**.

- **Supported (risk-focused):** Spread Min-Var matched Hist Min-Var on Sharpe but with clearly lower volatility and drawdown — a meaningful improvement in risk-adjusted profile for a conservative objective.
- **Qualified:** OU-implied means do not affect min-variance weights; their role shows up in **Spread Max-Sharpe (OU)**, which improves return and Sharpe versus Spread Min-Var but increases risk.
- **Not supported at signal layer:** Pair-level z-score trading contributed little OOS under the observed 2024–2025 regime.

## Limitations

- Small final universe (three pairs) increases sensitivity to pair-specific instability.
- Fixed in-sample parameters degrade under regime shift without rolling re-estimation.
- Borderline cointegration significance can fail to hold OOS.
- OU-implied expected returns are fragile when spreads start near equilibrium.

## Final Conclusion

Cointegration-driven spread portfolios remain useful for **downside and volatility control** relative to asset-space min-variance in this OOS window, while OU-implied means matter chiefly for **max-Sharpe** (not min-variance). Future work should focus on stricter pair-quality filters, rolling parameter updates, and larger candidate universes to improve OOS robustness.
