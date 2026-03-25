# Overall Conclusion

## Research Hypothesis

> *Spread-based return estimation from cointegrated pairs produces superior portfolio allocations compared to historical mean-variance optimisation, as measured by Sharpe ratio, volatility reduction, and maximum drawdown.*

## Summary of Findings

### Pair Selection and Spread Characterisation

Of 16 sector-paired candidates screened over the in-sample period (2018–2023), three passed the Augmented Engle-Granger cointegration test at the 5% significance level: **GS.N/MS.N** (p = 0.020), **KO.N/PEP.O** (p = 0.035), and **DAL.N/UAL.O** (p = 0.036). All three spreads exhibited Hurst exponents below 0.5 and mean-reversion half-lives of 41–53 days, confirming the statistical preconditions for Ornstein-Uhlenbeck return estimation. The remaining 12 pairs — including all semiconductor, cloud, and oil service candidates — showed no evidence of stable long-run equilibrium.

### Out-of-Sample Cointegration Stability

Applying in-sample hedge ratios to the OOS period (2024–2025) revealed structural instability. ADF p-values rose to 0.452 (GS/MS) and 0.622 (KO/PEP), and spread half-lives doubled or quadrupled relative to in-sample estimates. KO/PEP's Hurst exponent exceeded 0.5 OOS, indicating trend-following rather than mean-reverting behaviour. Re-estimation over the OOS window confirmed GS/MS as fragile (p = 0.019) and KO/PEP as structurally inverted (hedge ratio −0.350 vs in-sample +0.641). This cointegration breakdown is consistent with the 2024–2025 bull market constituting a distinct macroeconomic regime.

### Return Estimation

OU-implied annualised returns were **−7.2%** (GS/MS) and **+0.9%** (KO/PEP), reflecting the near-zero or negative z-scores at the OOS start (−0.285, −0.665). Historical estimates were uniformly positive (6.4–15.5%). The divergence between estimators is structural: OU returns are conditioned on current spread deviation and therefore penalise pairs near equilibrium, whereas historical means are unconditional. In a two-pair universe with no active mispricing, OU max-Sharpe weights collapsed to a corner solution — an instability inherent to small, near-equilibrium universes.

### Portfolio Optimisation and Backtesting

| Portfolio | Sharpe | Max DD | Total Return | Ann. Vol |
|-----------|--------|--------|--------------|----------|
| **OU Min-Var** | **1.359** | **−8.7%** | **34.2%** | **9.8%** |
| OU Max-Sharpe | 0.895 | −16.1% | 29.3% | 13.2% |
| Hist Min-Var | 0.335 | −14.3% | 12.1% | 14.1% |
| Hist Max-Sharpe | 0.838 | −20.0% | 37.2% | 18.7% |
| Equal-Weight | 1.363 | −8.4% | 34.5% | 9.8% |
| Buy & Hold | 1.403 | −30.0% | 108.0% | 27.5% |
| S&P 500 | 1.110 | −18.9% | 44.3% | 16.0% |

OU Min-Var achieved a Sharpe of 1.359 — 4× that of Hist Min-Var (0.335), with maximum drawdown halved (−8.7% vs −14.3%) and annualised volatility reduced by 30%. It also exceeded the S&P 500 on a risk-adjusted basis (1.359 vs 1.110) while bearing one-third of the market's volatility. However, equal-weight spread allocation matched OU Min-Var almost exactly (Sharpe 1.363), indicating that the performance advantage derives primarily from the **spread covariance structure** rather than the precision of the OU-implied weights. Max-Sharpe degraded performance under both estimators, confirming that extreme \(\mu\) inputs destabilise the optimiser in small universes.

## Hypothesis Evaluation

The hypothesis is **partially supported**.

**Supported**: OU Min-Var decisively outperformed Hist Min-Var across all three evaluation metrics — Sharpe ratio, maximum drawdown, and volatility — validating the core claim that cointegration-based portfolio construction produces superior risk-adjusted allocations.

**Qualified**: The near-identical performance of equal-weight and OU Min-Var implies that the benefit is concentrated in the **spread covariance structure** rather than OU return estimation per se. The hypothesis holds for minimum-variance optimisation, but not for max-Sharpe, where OU \(\mu\) estimates proved too unstable to improve allocation.

**Not supported**: Per-pair z-score signals failed to trigger meaningful trades OOS, as spreads remained near equilibrium throughout the test period. The signal-generation layer of the strategy did not contribute to performance.

## Limitations

- **Small universe**: Three cointegrated pairs limits diversification and amplifies sensitivity to individual spread behaviour
- **Parameter instability**: In-sample hedge ratios and OU parameters degraded OOS, suggesting rolling re-estimation is necessary
- **Regime dependency**: The 2024–2025 bull market compressed spread volatility, disadvantaging mean-reversion strategies
- **\(\mu\) fragility**: OU-implied returns are sensitive to current z-score and become degenerate near equilibrium, making max-Sharpe unreliable in small universes

## Conclusion

Cointegration-based portfolio construction offers a **structurally superior risk framework** relative to historical mean-variance optimisation, achieving substantially higher risk-adjusted returns with lower drawdown and volatility. The primary source of this advantage is the **spread covariance matrix** — not the OU return vector — which naturally captures the low-correlation, mean-reverting dynamics of sector-paired spreads. Return estimation via OU processes remains theoretically sound but practically fragile in small, near-equilibrium universes. Future work should prioritise rolling parameter estimation, larger spread universes, and regime-adaptive signal generation to realise the full potential of cointegration-driven allocation.