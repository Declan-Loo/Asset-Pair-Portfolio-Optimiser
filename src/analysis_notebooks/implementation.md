## Implementation

This chapter describes the software implementation of the methodology. The system is implemented in Python and organised into a modular pipeline of reusable library code, analysis notebooks, a backtesting engine, and an interactive dashboard.

### 1. Pipeline Overview

The project follows a **four-stage notebook pipeline**, each building on the outputs of the previous stage, supported by three library packages (`src/modelling`, `src/backtesting`, `src/data`) and an interactive dashboard (`src/dashboard`).

1. **Spread Exploration** (`01_spread_exploration.ipynb`) — data ingestion, spread construction, and visual characterisation.
2. **Cointegration Validation** (`02_cointegration_validation.ipynb`) — unit root testing, Engle–Granger screening, and out-of-sample stability checks.
3. **Return Estimation** (`03_return_estimation.ipynb`) — OU-implied and historical mean return estimation, covariance estimation, and comparison.
4. **Backtest Results** (`04_backtest_results.ipynb`) — portfolio optimisation, pair-level backtesting, portfolio-level evaluation, and benchmark comparison.

The library packages expose a clean public API through their `__init__.py` modules, allowing notebooks to import functions such as `screen_pairs()`, `compute_half_life()`, and `maximum_sharpe_weights()` without knowledge of internal file structure.

```
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

#### 1.1 Data Ingestion and Caching

Price data are retrieved from the LSEG Refinitiv Workspace API via a custom client (`src/data/refinitiv_client.py`). The client implements an **incremental caching strategy**: on first request, the full date range is fetched and persisted as a CSV in `data/raw/`. Subsequent requests check the cache and only fetch date gaps not yet covered, merging new data with the existing cache.

The client also handles column normalisation (mapping LSEG field codes such as `TRDPRC_1` to `Close`), forward-filling of up to five consecutive missing values, and automatic dropping of columns with more than 10% missing data. S&P 500 benchmark prices are sourced separately via `yfinance`.

***

### 2. Spread Exploration

The first notebook (`01_spread_exploration`) loads in-sample close prices and constructs the 16 candidate spreads using OLS hedge ratios. For each pair it produces:

- Normalised price overlays to visualise co-movement.
- Spread level and distribution plots.
- Rolling half-life and Hurst exponent time series.
- Rolling z-score plots with entry/exit threshold annotations.

These are implemented in the `spread_analysis` module, which provides `compute_spread()`, `compute_half_life()`, `compute_hurst_exponent()`, and `compute_rolling_zscore()`. The `spread_summary()` function aggregates all diagnostics into a single DataFrame for tabular comparison across pairs.

***

### 3. Cointegration Validation

The second notebook (`02_cointegration_validation`) applies the full Engle–Granger screening pipeline to all 16 candidate pairs on in-sample data, then assesses out-of-sample stability.

#### 3.1 Screening Implementation

The `cointegration` module implements the screening procedure as follows:

- `adf_test(series)` — applies the ADF test using `statsmodels` with automatic AIC-based lag selection. Returns the test statistic, $p$-value, number of lags, and critical values.
- `engle_granger_test(y, x)` — performs the two-step procedure: fits the OLS cointegrating regression, extracts residuals, and applies the ADF test to the residuals. Both orderings are tested and the one with the lower residual $p$-value is retained. Returns the hedge ratio $\hat{\beta}$, intercept $\hat{\alpha}$, ADF statistic, $p$-value, and selected ordering.
- `screen_pairs(prices, pairs)` — iterates over all candidate pairs, verifies both legs are $I(1)$, runs the Engle–Granger test, and returns a DataFrame with a boolean `cointegrated` column (true if $p < 0.05$).

#### 3.2 Out-of-Sample Stability

To assess whether in-sample cointegration relationships persist, the notebook re-estimates the cointegrating regression on the OOS period and compares hedge ratios, ADF statistics, and spread dynamics. Rolling half-life plots spanning both periods provide visual confirmation of parameter stability.

***

### 4. Return Estimation

The third notebook (`03_return_estimation`) computes expected returns under both the OU-implied and historical mean approaches.

The `return_estimation` module provides:

- `compute_spread_returns(y_prices, x_prices, hedge_ratio)` — computes daily log spread returns as $\ln(Y_t/Y_{t-1}) - \beta \cdot \ln(X_t/X_{t-1})$.
- `build_spread_return_matrix(prices, coint_pairs)` — constructs the full $T \times n$ matrix of spread returns for all cointegrated pairs.
- `ou_implied_spread_return(spread, half_life)` — implements the OU conditional expected return formula, computing $\kappa = \ln 2 / h$ and the expected spread change.
- `build_ou_implied_returns(prices, coint_pairs)` — applies the OU-implied estimator to all pairs and returns an annualised expected return vector.
- `historical_mean_return(returns)` — computes the sample mean, optionally over a trailing window.
- `shrinkage_covariance(returns)` — estimates the covariance matrix using the Ledoit–Wolf shrinkage estimator from `scikit-learn`.

The notebook produces a grouped bar chart comparing OU-implied, historical mean, and EWMA return estimates across pairs, along with a correlation heatmap to visualise diversification potential.

***

### 5. Portfolio Optimisation Module

The `optimiser` module implements the Markowitz mean-variance framework in spread space:

- `minimum_variance_weights(cov, delta)` — solves the minimum-variance problem using Sequential Least Squares Programming (SLSQP) from `scipy.optimize`. The long-only constraint ($w_i \geq 0$) and full-investment constraint ($\sum w_i = 1$) are enforced explicitly, with an optional $L_2$ regularisation term.
- `maximum_sharpe_weights(mu, cov, rf)` — solves the maximum Sharpe ratio problem by minimising the negative Sharpe ratio subject to the same constraints.
- `compute_efficient_frontier(mu, cov, rf, n_points)` — generates the efficient frontier by solving the minimum-variance problem for a range of target returns between the global minimum-variance return and the maximum achievable return.

Return and volatility figures are annualised from daily values: $\mu_{\text{ann}} = \exp(252 \cdot \mu_{\text{daily}}) - 1$ and $\sigma_{\text{ann}} = \sigma_{\text{daily}} \cdot \sqrt{252}$.

***

### 6. Backtesting Engine

The backtesting engine (`src/backtesting/engine.py`) simulates pair-level trading and computes performance metrics.

#### 6.1 Architecture

The engine uses a dataclass-based configuration pattern:

- `BacktestConfig` — stores all strategy parameters (entry, exit, and stop-loss z-score thresholds, lookback window, transaction cost rate, and initial capital) with validation in `__post_init__` to enforce $z_{\text{exit}} < z_{\text{entry}} < z_{\text{stop}}$.
- `BacktestResult` — a container holding daily returns, cumulative returns, position history, trade log, summary metrics, spread, and z-score series.
- `PairsBacktestEngine` — orchestrates the full pipeline: spread and z-score computation, signal generation, PnL calculation, trade logging, and metric aggregation.

#### 6.2 Signal Generation

The signal generator implements the z-score state machine described in the Methodology. It iterates sequentially through the z-score series, maintaining a position state variable that transitions between $\{-1, 0, +1\}$ based on threshold crossings. Sequential iteration is necessary because position on day $t$ depends on position on day $t-1$, precluding vectorised computation.

#### 6.3 PnL and Transaction Costs

The PnL computation deploys the full initial capital into each active position. On each day, the number of spread units is recalculated as $n_t = C_0 / (Y_t + |\beta| X_t)$ to reflect changing notional values. The dollar PnL is $\text{pos}_{t-1} \cdot n_{t-1} \cdot (\Delta Y_t - \beta \cdot \Delta X_t)$, from which transaction costs (proportional to the absolute position change) are deducted.

#### 6.4 Metrics and Benchmarks

The `metrics` module provides `compute_ex_post_sharpe_ratio()`, `compute_max_drawdown()`, and `compute_volatility_reduction()`. The `benchmarks` module constructs: a constant risk-free rate, equal-weight buy-and-hold of all universe constituents, per-pair buy-and-hold of both legs, and the S&P 500 index. A `historical_mpt_returns()` function computes the out-of-sample returns of a traditional max-Sharpe portfolio estimated on in-sample asset returns, serving as the primary baseline.

***

### 7. Dashboard Interface

An interactive **Streamlit** dashboard (`src/dashboard/app.py`) provides a user-facing interface for exploring the full pipeline. The dashboard enables users to:

- Select candidate pairs and configure date ranges and capital.
- View cointegration screening results (horizontal bar chart of $p$-values with significance threshold).
- Inspect spread dynamics: spread with ±2σ Bollinger bands, z-score with entry/exit thresholds, and position timelines.
- Compare return estimation methods via grouped bar charts and rolling estimate plots.
- Run backtests and view cumulative return plots, drawdown charts, return distribution histograms, and rolling Sharpe ratios.
- Visualise the efficient frontier with annotated max-Sharpe and min-variance portfolios.
- Compare strategy performance against all benchmarks in a unified cumulative return chart with a metrics summary table.

The visualisation layer is implemented in a separate `components.py` module using **Plotly**, providing interactive zoom, hover tooltips, and export capabilities. Chart functions are stateless and accept data as arguments, making them reusable across both notebooks and the dashboard.