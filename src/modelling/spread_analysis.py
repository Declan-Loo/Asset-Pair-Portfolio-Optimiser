"""
Spread characterisation for pairs trading.

Computes spread series, rolling z-scores, half-life of mean reversion,
and the Hurst exponent to assess mean-reversion quality.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller


def compute_spread(
    y: pd.Series,
    x: pd.Series,
    hedge_ratio: float,
    intercept: float = 0.0,
) -> pd.Series:
    """
    Spread = y - hedge_ratio * x - intercept.
    """
    spread = y - hedge_ratio * x - intercept
    spread.name = "spread"
    return spread


def compute_zscore(spread: pd.Series, window: int = 60) -> pd.Series:
    """
    Rolling z-score: (spread - rolling_mean) / rolling_std.

    Parameters
    ----------
    spread : pd.Series
        Spread time series.
    window : int
        Rolling window size (trading days).

    Returns
    -------
    pd.Series of z-scores (NaN for the first `window-1` observations).
    """
    rolling_mean = spread.rolling(window=window).mean()
    rolling_std = spread.rolling(window=window).std(ddof=1)
    zscore = (spread - rolling_mean) / rolling_std
    zscore.name = "zscore"
    return zscore


def compute_half_life(spread: pd.Series) -> float:
    """
    Half-life of mean reversion via an AR(1) / Ornstein-Uhlenbeck model.

    Fits  Δs_t = λ · s_{t-1} + ε  via OLS.
    Half-life = -ln(2) / λ.

    Returns np.inf if the spread does not appear mean-reverting (λ >= 0).
    """
    spread_clean = spread.dropna()
    lag = spread_clean.shift(1)
    delta = spread_clean.diff()

    # Drop the first NaN row
    lag = lag.iloc[1:]
    delta = delta.iloc[1:]

    X = sm.add_constant(lag)
    model = sm.OLS(delta, X).fit()
    lam = model.params.iloc[1]

    if lam >= 0:
        return np.inf

    return float(-np.log(2) / lam)


def compute_hurst_exponent(series: pd.Series, max_lag: int = 100) -> float:
    """
    Rescaled-range (R/S) Hurst exponent.

    H < 0.5 → mean-reverting
    H ≈ 0.5 → random walk
    H > 0.5 → trending

    Parameters
    ----------
    series : pd.Series
        Time series (e.g. spread).
    max_lag : int
        Maximum lag to consider.

    Returns
    -------
    float: Estimated Hurst exponent.
    """
    series_clean = series.dropna().values
    n = len(series_clean)
    max_lag = min(max_lag, n // 2)

    lags = range(2, max_lag + 1)
    rs_values = []

    for lag in lags:
        n_subseries = n // lag
        rs_sub = []
        for i in range(n_subseries):
            sub = series_clean[i * lag : (i + 1) * lag]
            mean_sub = np.mean(sub)
            deviate = np.cumsum(sub - mean_sub)
            r = np.max(deviate) - np.min(deviate)
            s = np.std(sub, ddof=1)
            if s > 0:
                rs_sub.append(r / s)
        if rs_sub:
            rs_values.append(np.mean(rs_sub))
        else:
            rs_values.append(np.nan)

    # Fit log(R/S) = H * log(lag) + c
    valid = ~np.isnan(rs_values)
    log_lags = np.log(list(lags))[valid]
    log_rs = np.log(np.array(rs_values)[valid])

    if len(log_lags) < 2:
        return np.nan

    poly = np.polyfit(log_lags, log_rs, 1)
    return float(poly[0])


def spread_summary(
    y: pd.Series,
    x: pd.Series,
    hedge_ratio: float,
    intercept: float = 0.0,
    window: int = 60,
) -> dict:
    """
    Aggregate spread statistics.

    Returns dict with: half_life, hurst, current_zscore, spread_mean,
    spread_std, adf_stat, adf_pvalue, is_stationary.
    """
    spread = compute_spread(y, x, hedge_ratio, intercept)
    zscore = compute_zscore(spread, window=window)

    half_life = compute_half_life(spread)
    hurst = compute_hurst_exponent(spread)

    # ADF on the spread
    adf_result = adfuller(spread.dropna(), autolag="AIC")

    return {
        "half_life": half_life,
        "hurst": hurst,
        "current_zscore": float(zscore.iloc[-1]) if not np.isnan(zscore.iloc[-1]) else np.nan,
        "spread_mean": float(spread.mean()),
        "spread_std": float(spread.std(ddof=1)),
        "adf_stat": adf_result[0],
        "adf_pvalue": adf_result[1],
        "is_stationary": adf_result[1] < 0.05,
    }
