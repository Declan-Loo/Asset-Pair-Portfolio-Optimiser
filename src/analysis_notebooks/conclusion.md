# Overall Conclusion

## Research Hypothesis

> *Spread-based return estimation from cointegrated pairs produces superior portfolio allocations compared to historical mean-variance optimisation, as measured by Sharpe ratio, volatility reduction, and maximum drawdown.*

## Summary of Findings

### Pair Selection and Spread Characterisation

Of 16 sector-paired candidates screened over the in-sample period (2018–2023), three passed the Augmented Engle-Granger cointegration test at the 5% significance level: **GS.N/MS.N** (p = 0.020), **KO.N/PEP.O** (p = 0.035), and **DAL.N/UAL.O** (p = 0.036). All three spreads exhibited Hurst exponents below 0.5 and mean-reversion half-lives of 41–53 days, confirming the statistical preconditions for Ornstein-Uhlenbeck return estimation. The remaining 13 pairs — including all semiconductor, cloud, banking, and oil service candidates — showed no evidence of a stable long-run equilibrium.

### Out-of-Sample Cointegration Stability

Applying in-sample hedge ratios to the OOS period (2024–2025) revealed structural instability across all three pairs. ADF p-values rose substantially from their in-sample levels, half-lives doubled or quadrupled, and KO/PEP's Hurst exponent exceeded 0.5 OOS — indicating trend-following rather than mean-reverting behaviour. DAL/UAL proved the most unstable, contributing disproportionate noise to the portfolio OOS. Re-estimation over the OOS window confirmed GS/MS as fragile and KO/PEP as structurally inverted (hedge ratio −0.350 vs in-sample +0.641). This breakdown is consistent with the 2024–2025 bull market constituting a distinct macroeconomic regime from the training period.

### Return Estimation

OU-implied annualised returns were negative or near-zero for GS/MS and KO/PEP, reflecting spread z-scores close to equilibrium at the OOS start. Historical estimates were uniformly positive (6.4–15.5%). The divergence is structural: OU returns are conditioned on current spread deviation and penalise pairs near equilibrium, whereas historical means are unconditional. In a three-pair universe with limited active mispricing, OU max-Sharpe weights collapsed to corner solutions — an instability inherent to small, near-equilibrium universes.

### Portfolio Optimisation and Backtesting

| Portfolio | Sharpe | Max DD | Total Return | Ann. Vol | Vol. Reduction |
|-----------|--------|--------|--------------|----------|----------------|
| **OU Min-Var** | **0.986** | **−8.7%** | **23.0%** | **8.9%** | **+7.5%** |
| OU Max-Sharpe | 0.895 | −16.1% | 29.3% | 13.2% | −36.0% |
| Hist Min-Var | 0.342 | −14.2% | 12.3% | 14.1% | −45.4% |
| Hist Max-Sharpe | 0.844 | −20.0% | 37.5% | 18.7% | −93.2% |
| Equal-Weight | 0.625 | −10.6% | 16.3% | 9.7% | — |
| Buy & Hold | 1.403 | −30.0% | 108.0% | 27.5% | — |
| S&P 500 (SPY) | 1.110 | −18.9% | 44.3% | 16.0% | — |

OU Min-Var achieved the best risk-adjusted return among all four optimised strategies — approximately **3× the Sharpe of Hist Min-Var** (0.986 vs 0.342), with maximum drawdown reduced from −14.2% to −8.7% and annualised volatility cut to 8.9% vs 14.1%. It was the only strategy to achieve a positive volatility reduction (+7.5%) relative to equal-weight. Notably, equal-weight spread allocation (Sharpe 0.625) substantially underperformed OU Min-Var, indicating that covariance-driven weighting in spread space adds genuine value when DAL/UAL's higher volatility is properly down-weighted.

However, adding DAL/UAL as a third pair — despite passing the 5% significance threshold — visibly degraded performance relative to the 2-pair baseline (OU Min-Var Sharpe dropped from 1.359 to 0.986). This highlights that **borderline cointegration does not guarantee OOS spread stability**, and that pair quality dominates universe size.

## Hypothesis Evaluation

The hypothesis is **partially supported**.

**Supported**: OU Min-Var outperformed Hist Min-Var across all three evaluation metrics — Sharpe ratio (0.986 vs 0.342), maximum drawdown (−8.7% vs −14.2%), and annualised volatility (8.9% vs 14.1%) — validating that cointegration-based portfolio construction produces superior risk-adjusted allocations.

**Qualified**: OU Max-Sharpe (0.895) underperformed OU Min-Var (0.986), confirming that the OU return vector \(\mu\) is too unstable in a small near-equilibrium universe to improve upon pure covariance-driven weighting. The benefit of cointegration is concentrated in the **spread covariance structure**, not return prediction.

**Not supported**: Per-pair z-score signals failed to trigger meaningful trades OOS, as spreads remained near equilibrium throughout the test period. The signal-generation layer did not contribute to returns.

## Limitations

- **Borderline pairs**: DAL/UAL passed at p = 0.036 but proved OOS-unstable, reducing portfolio Sharpe by 0.37 — illustrating the cost of weak cointegration
- **Small universe**: Three pairs limits diversification and amplifies sensitivity to individual spread regime shifts
- **Parameter instability**: Fixed in-sample hedge ratios and OU parameters degraded without rolling re-estimation
- **Regime dependency**: The 2024–2025 bull market compressed spread volatility and suppressed mean-reversion signals
- **\(\mu\) fragility**: OU-implied returns are degenerate near equilibrium, making max-Sharpe unreliable in small universes

## Conclusion

Cointegration-based portfolio construction delivers a **structurally superior risk framework** relative to historical mean-variance optimisation, achieving nearly 3× higher risk-adjusted returns with substantially lower drawdown and volatility. However, the primary driver of this advantage is the **spread covariance matrix** — not OU return estimation — which naturally captures the low-correlation, mean-reverting dynamics of sector-paired spreads. Return estimation via OU processes is theoretically sound but practically fragile in small, near-equilibrium universes. A further key finding is that cointegration quality dominates universe size: including a borderline pair (DAL/UAL, p = 0.036) degraded OOS performance more than excluding it would have. Future work should prioritise rolling parameter estimation, stricter pair selection criteria, and larger spread universes to realise the full potential of cointegration-driven allocation. 