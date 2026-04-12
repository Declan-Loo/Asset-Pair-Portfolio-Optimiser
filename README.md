# Asset-Pair-Portfolio-Optimiser

Developed as part of my Final Year Project for UCL BSc Computer Science. The project estimates expected returns by modelling the mean-reverting spread between cointegrated asset pairs, then uses those estimates to construct Markowitz-optimal portfolios. It compares this **OU-Implied MPT** approach against traditional **Historical Mean-Variance** optimisation over an out-of-sample test period (January 2024 -- December 2025).

## Overview

Traditional portfolio optimisation relies on historical mean returns as inputs to Markowitz mean-variance optimisation. This project investigates whether replacing historical means with **Ornstein-Uhlenbeck (OU) implied returns** — derived from the current spread deviation and estimated mean-reversion half-life of cointegrated pairs — produces portfolios with better out-of-sample risk-adjusted performance.

The pipeline:

1. Screens 16 candidate pairs (across 7 sectors) for cointegration using the Engle-Granger two-step test
2. Characterises the spread of cointegrated pairs (half-life, Hurst exponent, z-scores)
3. Estimates expected returns via three methods: historical mean, EWMA, and OU-implied
4. Constructs minimum-variance and maximum-Sharpe portfolios under both return estimators
5. Backtests each portfolio over the OOS period with transaction costs and benchmark comparison

## Repository Structure

```text
Asset-Pair-Portfolio-Optimiser/
├── data/
│   ├── raw/                        # Cached LSEG API price CSVs
│   └── processed/                  # Processed outputs
├── src/
│   ├── data/
│   │   ├── refinitiv_client.py     # LSEG Workspace API wrapper with incremental caching
│   │   └── yfinance_sp500.py       # S&P 500 benchmark data (yfinance fallback)
│   ├── modelling/
│   │   ├── config.py               # Tickers, candidate pairs, date ranges
│   │   ├── cointegration.py        # Engle-Granger two-step test; screen_pairs()
│   │   ├── spread_analysis.py      # Spread construction, z-scores, half-life, Hurst exponent
│   │   ├── return_estimation.py    # Historical mean, EWMA, OU-implied returns; covariance shrinkage
│   │   └── optimiser.py            # OLS hedge ratio, min-variance, max-Sharpe, efficient frontier
│   ├── backtesting/
│   │   ├── engine.py               # Z-score mean-reversion backtester with transaction costs
│   │   ├── metrics.py              # Sharpe ratio, max drawdown, volatility reduction
│   │   └── benchmarks.py           # Risk-free, buy-and-hold, equal-weight, S&P 500 baselines
│   ├── dashboard/
│   │   ├── app.py                  # Streamlit application entry point
│   │   └── components.py           # Plotly visualisation components
│   └── analysis_notebooks/
│       ├── 01_spread_exploration.ipynb       # Spread EDA and characterisation
│       ├── 02_cointegration_validation.ipynb # Engle-Granger screening and OOS stability
│       ├── 03_return_estimation.ipynb        # Return estimator comparison
│       ├── 04_backtest_results.ipynb         # Portfolio backtest and benchmark comparison
│       └── figures/                          # Exported PDF figures
├── FYP Docs/
│   └── Report/
│       └── main.tex                # Final thesis
├── lseg-data.config.json           # LSEG Workspace session config (gitignored)
├── .env                            # EIKON_API_KEY (gitignored)
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.10+
- [LSEG Workspace](https://www.lseg.com/en/data-analytics/products/lseg-workspace) desktop application (for live data access)
- Jupyter Notebook or JupyterLab (to run the analysis notebooks)

## Installation

```bash
git clone <repo-url>
cd Asset-Pair-Portfolio-Optimiser
pip install -r requirements.txt
```

## Configuration

### LSEG API Key

Create a `lseg-data.config.json` in the project root (see [LSEG Data Library docs](https://developers.lseg.com/en/api-catalog/lseg-data-platform/lseg-data-library-for-python)):

```json
{
  "sessions": {
    "default": "desktop.workspace",
    "desktop": {
      "workspace": {
        "app-key": "YOUR_APP_KEY_HERE"
      }
    }
  }
}
```

Also create a `.env` file:

```text
EIKON_API_KEY=YOUR_APP_KEY_HERE
```

> **Note:** Cached price data is stored in `data/raw/` after the first run. Subsequent runs will use the cache and only fetch missing date ranges.

## Running the Dashboard

```bash
cd src/dashboard
streamlit run app.py
```

Open `http://localhost:8501` in your browser. The dashboard provides:

- **Cointegration screening** — Engle-Granger p-values for all 16 candidate pairs
- **Spread analysis** — z-score bands, rolling half-life, Hurst exponent
- **Return estimation** — comparison of historical mean, EWMA, and OU-implied estimates
- **Backtesting** — configurable z-score entry/exit thresholds with transaction costs
- **Portfolio optimisation** — efficient frontiers and weight allocation for both approaches
- **Benchmark comparison** — Sharpe, drawdown, and volatility metrics vs S&P 500 and buy-and-hold

## Reproducing the Analysis

Run the notebooks in order from `src/analysis_notebooks/`:

```bash
jupyter notebook src/analysis_notebooks/
```

| Notebook | Description |
| --- | --- |
| `01_spread_exploration.ipynb` | Spread construction, z-scores, half-life, and Hurst exponent for all candidate pairs |
| `02_cointegration_validation.ipynb` | Engle-Granger screening (IS) and out-of-sample stability checks |
| `03_return_estimation.ipynb` | Comparison of historical mean, EWMA, and OU-implied return estimates |
| `04_backtest_results.ipynb` | Portfolio backtest, per-pair performance, benchmark comparison, and efficient frontiers |

All figures are exported automatically to `src/analysis_notebooks/figures/` as PDF.

## Key Dependencies

| Package | Purpose |
| --- | --- |
| `statsmodels` | OLS regression, ADF unit-root tests, Engle-Granger cointegration |
| `scipy` | Portfolio optimisation (constrained minimisation) |
| `scikit-learn` | Ledoit-Wolf and OAS covariance shrinkage |
| `plotly` | Interactive visualisations in the dashboard |
| `streamlit` | Web framework for the interactive dashboard |
| `lseg-data` | LSEG Refinitiv Workspace API |
| `yfinance` | S&P 500 benchmark data |

Full dependency list: [`requirements.txt`](requirements.txt)

## Project Context

This project was submitted in partial fulfilment of the BSc Computer Science degree at University College London (UCL), academic year 2025--2026 (COMP0029 Final Year Project).
