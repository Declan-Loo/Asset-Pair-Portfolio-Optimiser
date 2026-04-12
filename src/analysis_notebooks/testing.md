# Implementation

This chapter describes the software implementation of the methodology. The system is implemented in Python and organised into a modular pipeline of reusable library code, analysis notebooks, a backtesting engine, and an interactive dashboard.

## 1. Pipeline Overview

The project follows a **four-stage notebook pipeline**, each building on the outputs of the previous stage, supported by three library packages (`src/modelling`, `src/backtesting`, `src/data`) and an interactive dashboard (`src/dashboard`).

1. **Spread Exploration** (`01_spread_exploration.ipynb`) — data ingestion, spread construction, and visual characterisation.
2. **Cointegration Validation** (`02_cointegration_validation.ipynb`) — unit root testing, Engle–Granger screening, and out-of-sample stability checks.
3. **Return Estimation** (`03_return_estimation.ipynb`) — OU-implied and historical mean return estimation, covariance estimation, and comparison.
4. **Backtest Results** (`04_backtest_results.ipynb`) — portfolio optimisation, pair-level backtesting, portfolio-level evaluation, and benchmark comparison.

The library packages expose a clean public API through their `__init__.py` modules, allowing notebooks to import functions such as `screen_pairs()`, `compute_half_life()`, and `maximum_sharpe_weights()` without knowledge of internal file structure.

```text
Refinitiv API ──> data/refinitiv_client.py ──> CSV cache (data/raw/)
                                                      │
          ┌───────────────────────────────────────────┘
          ▼
01_spread_exploration ──> 02_cointegration_validation
          │                         │
          ▼                         ▼
03_return_estimation ──────> 04_backtest_results
          │                         │
          └──────────┬──────────────┘
                     ▼
              dashboard/app.py (Streamlit)
```

Intermediate outputs — cointegrated pairs, spread return matrices, expected return vectors, and covariance matrices — are persisted as CSV files in `data/processed/`, decoupling each notebook stage and ensuring reproducibility.

## 1.1 Data Ingestion and Caching

Price data are retrieved from the LSEG Refinitiv Workspace API via a custom client (`src/data/refinitiv_client.py`). The client implements an **incremental caching strategy**: on first request, the full date range is fetched and persisted as a CSV in `data/raw/`. Subsequent requests check the cache and only fetch date gaps not yet covered, merging new data with the existing cache.

The client handles column normalisation (mapping LSEG field codes such as `TRDPRC_1` to `Close`), forward-filling of up to five consecutive missing values to account for staggered exchange holidays, and automatic dropping of columns with more than 10% missing data. S&P 500 benchmark prices are sourced separately via `yfinance`.

***

## 2. Spread Exploration

The first notebook (`01_spread_exploration`) loads in-sample close prices and constructs the 16 candidate spreads using OLS hedge ratios. For each pair it produces:

- Normalised price overlays to visualise co-movement.
- Spread level and distribution plots, including kernel density estimates.
- Rolling half-life and Hurst exponent time series to identify structural breaks.
- Rolling z-score plots with entry/exit threshold annotations.

These are implemented in the `spread_analysis` module, which provides `compute_spread()`, `compute_half_life()`, `compute_hurst_exponent()`, and `compute_rolling_zscore()`. The `spread_summary()` function aggregates all diagnostics into a single DataFrame for tabular comparison across pairs, enabling rapid screening of candidates prior to formal cointegration testing.

***

## 3. Cointegration Validation

The second notebook (`02_cointegration_validation`) applies the full Engle–Granger screening pipeline to all 16 candidate pairs on in-sample data, then assesses out-of-sample stability.

## 3.1 Screening Implementation

The `cointegration` module implements the screening procedure via three functions:

- `adf_test(series)` — applies the ADF test using `statsmodels` with automatic AIC-based lag selection. Returns the test statistic, $p$-value, number of lags, and critical values.
- `engle_granger_test(y, x)` — performs the two-step procedure: fits the OLS cointegrating regression via `statsmodels.OLS`, extracts residuals, and applies the ADF test. Both orderings are tested and the one with the lower residual $p$-value is retained. Returns $\hat{\beta}$, $\hat{\alpha}$, ADF statistic, $p$-value, and selected ordering.
- `screen_pairs(prices, pairs)` — iterates over all candidate pairs, verifies both legs are $I(1)$, runs the Engle–Granger test, and returns a DataFrame with a boolean `is_cointegrated` column (true if $p < 0.05$).

## 3.2 Out-of-Sample Stability

To assess whether in-sample cointegration relationships persist into the OOS period, the notebook re-estimates the cointegrating regression on OOS data and compares hedge ratios, ADF $p$-values, and spread dynamics across periods. Rolling half-life plots spanning both in-sample and OOS windows provide visual confirmation of parameter stability, which is a key diagnostic given that static hedge ratios estimated in-sample are applied without recalibration to the OOS period.

***

## 4. Return Estimation

The third notebook (`03_return_estimation`) computes expected returns under both the OU-implied and historical mean approaches, and estimates the covariance matrix for use in portfolio optimisation.

The `return_estimation` module provides:

- `compute_spread_returns(y_prices, x_prices, hedge_ratio)` — computes daily log spread returns as $r_t^S = \ln(Y_t / Y_{t-1}) - \hat{\beta} \cdot \ln(X_t / X_{t-1})$, ensuring consistency with the log-price spread used in the OU model.
- `build_spread_return_matrix(prices, coint_pairs)` — constructs the full $T \times n$ matrix of spread returns for all cointegrated pairs, indexed by date.
- `ou_implied_spread_return(spread, half_life)` — implements the conditional OU expected return formula, computing $\kappa = \ln 2 / h$ and the expected spread change $(\theta - S_T)(1 - e^{-\kappa})$.
- `build_ou_implied_returns(prices, coint_pairs)` — applies the OU estimator across all pairs and returns an annualised expected return vector $\boldsymbol{\mu}^{\text{OU}} = 252 \cdot \mathbb{E}[\Delta \mathbf{S}_T]$.
- `historical_mean_return(returns)` — computes the annualised sample mean, optionally over a trailing lookback window.
- `shrinkage_covariance(returns)` — estimates the covariance matrix using the Ledoit–Wolf shrinkage estimator from `scikit-learn`, returning an annualised covariance matrix $\boldsymbol{\Sigma}_{\text{ann}} = 252 \cdot \boldsymbol{\Sigma}_{\text{daily}}$.

The notebook saves the resulting $\boldsymbol{\mu}$ and $\boldsymbol{\Sigma}$ (both annualised) to `data/processed/` for consumption by the backtesting notebook.

***

## 5. Portfolio Optimisation Module

The `optimiser` module implements the Markowitz mean-variance framework for both spread-space and asset-space portfolios.

## 5.1 Input Convention

All inputs to the optimiser are expressed in **annualised units**: an annualised expected return vector $\boldsymbol{\mu}_{\text{ann}}$ and an annualised covariance matrix $\boldsymbol{\Sigma}_{\text{ann}}$. The optimiser is called with `periods_per_year=1`, preventing double-annualisation inside `_portfolio_stats`. This convention ensures that the $L_2$ regularisation strength ($\delta = 0.05$) operates on the same scale as the covariance objective — with annualised spread variances on the order of $0.02$–$0.04$, the regularisation provides moderate shrinkage toward equal weights without dominating the covariance structure.

## 5.2 Solver

Both the minimum-variance and maximum-Sharpe problems are solved using `scipy.optimize.minimize` with the SLSQP (Sequential Least Squares Programming) method:

- `minimum_variance_weights(returns, cov_matrix, l2_reg)` — minimises $\mathbf{w}^\top \boldsymbol{\Sigma} \mathbf{w} + \delta \|\mathbf{w}\|^2$ subject to $\mathbf{1}^\top \mathbf{w} = 1$ and $\mathbf{w} \geq \mathbf{0}$, with tolerance $10^{-12}$ and maximum 1000 iterations.
- `maximum_sharpe_weights(returns, expected_returns, cov_matrix, rf_annual, l2_reg)` — minimises the negative Sharpe ratio $-(r_P - r_f) / \sigma_P + \delta \|\mathbf{w}\|^2$ subject to the same constraints.
- `compute_efficient_frontier(returns, expected_returns, cov_matrix, n_points, rf_annual, l2_reg)` — traces the mean-variance frontier by solving the minimum-variance problem for 80 equally-spaced target return levels between the global minimum-variance return and the maximum feasible return, returning a DataFrame of $(\sigma, \mu, \text{SR})$ tuples.
- `optimise_portfolio(returns, expected_returns, cov_matrix, rf_annual, periods_per_year, l2_reg)` — convenience wrapper that returns both min-variance and max-Sharpe weights together with their associated return and volatility figures.

## 5.3 The Zero-Return Baseline in Practice

Because `minimum_variance_weights` does not accept an expected return argument, passing $\boldsymbol{\mu} = \mathbf{0}$ into `optimise_portfolio` produces identical min-variance weights to any other $\boldsymbol{\mu}$ — only the same covariance matrix determines the solution. This reflects the theoretical result that the minimum-variance portfolio is the zero-return baseline. In the backtesting notebook, only one min-variance row is reported (labelled **Spread Min-Var**); the zero-return test is operationalised by comparing the **Spread Max-Sharpe (OU)** portfolio — which uses $\boldsymbol{\mu}^{\text{OU}}$ — against this min-variance baseline.

***

## 6. Backtesting Engine

The backtesting engine (`src/backtesting/engine.py`) simulates pair-level z-score trading and computes portfolio-level performance metrics.

## 6.1 Architecture

The engine uses a dataclass-based configuration pattern:

- `BacktestConfig` — stores all strategy parameters (entry, exit, and stop-loss z-score thresholds, lookback window, transaction cost rate, and initial capital) with `__post_init__` validation enforcing $z_{\text{exit}} < z_{\text{entry}} < z_{\text{stop}}$.
- `BacktestResult` — a container holding daily returns, cumulative returns, position history, trade log, summary metrics, spread series, and z-score series.
- `PairsBacktestEngine` — the main class orchestrating the full pipeline: spread and z-score computation, signal generation, PnL calculation, trade logging, and metric aggregation.

## 6.2 Signal Generation

The signal generator implements a sequential z-score state machine over positions in $\{-1, 0, +1\}$. The loop iterates day-by-day through the z-score series, maintaining a position state variable that transitions according to entry, exit, and stop-loss thresholds. Sequential iteration is required because position on day $t$ depends on position on day $t-1$, precluding vectorised computation. The resulting position series is then used as an input to the PnL calculation.

## 6.3 PnL and Transaction Costs

The PnL computation deploys full initial capital $C_0$ into each active spread position. On each day, the number of spread units is recalculated as $n_t = C_0 / (Y_t + |\hat{\beta}| X_t)$ to account for changing notional values. Dollar PnL is $\text{pos}_{t-1} \cdot n_{t-1} \cdot (\Delta Y_t - \hat{\beta} \cdot \Delta X_t)$, from which transaction costs proportional to the absolute position change are deducted. The resulting daily return series is $r_t = \text{net PnL}_t / C_0$.

## 6.4 Metrics and Benchmarks

The `metrics` module provides three functions: `compute_ex_post_sharpe_ratio()`, `compute_max_drawdown()`, and `compute_volatility_reduction()`. Each accepts a `pd.Series` of daily returns and returns a scalar metric consistent with the definitions in Section 6.3 of the Methodology.

The `benchmarks` module constructs the comparison series used in the results table:

- `risk_free_returns(index, rf_annual)` — constant daily rate $r_f / 252$.
- `buy_and_hold_returns(prices, weights)` — equal-weight buy-and-hold of the two legs of the first cointegrated pair, using arithmetic `pct_change` returns.
- `equal_weight_pairs_returns(prices, coint_pairs)` — arithmetic spread returns averaged equally across all cointegrated pairs, used as the primary benchmark for volatility reduction.
- `market_returns(market_prices)` — daily arithmetic returns of SPY.
- `compute_benchmark_metrics(returns, rf_annual, benchmark_returns)` — computes Sharpe ratio, max drawdown, total return, annualised volatility, and (optionally) volatility reduction for any return series.

***

## 7. Dashboard Interface

An interactive **Streamlit** dashboard (`src/dashboard/app.py`) provides a user-facing interface for exploring the full pipeline without requiring notebook execution. The dashboard enables users to:

- Select candidate pairs and configure date ranges and initial capital.
- View cointegration screening results as a horizontal bar chart of $p$-values against the 5% significance threshold.
- Inspect spread dynamics: spread levels with $\pm 2\sigma$ Bollinger bands, z-score evolution with entry/exit annotations, and position timelines.
- Compare return estimation methods via grouped bar charts and rolling estimate plots.
- Run the backtesting engine interactively and view cumulative return curves, drawdown profiles, return distribution histograms, and rolling Sharpe ratios.
- Visualise the mean-variance efficient frontier with annotated min-variance and max-Sharpe portfolios for both spread-space and asset-space formulations.
- Compare all strategy variants against benchmarks in a unified cumulative return chart with a live metrics summary table.

The visualisation layer is implemented in a separate `components.py` module using **Plotly**, providing interactive zoom, pan, hover tooltips, and chart export. All chart functions are stateless and accept data as arguments, making them reusable across both the dashboard and the analysis notebooks.
