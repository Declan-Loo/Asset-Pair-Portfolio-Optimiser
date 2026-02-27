"""
Engle-Granger two-step cointegration testing.

Implements ADF unit-root tests and the Engle-Granger procedure for
identifying cointegrated asset pairs with stationary residuals.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller


def adf_test(series: pd.Series, significance: float = 0.05) -> dict:
    """
    Augmented Dickey-Fuller unit-root test on a single series.

    Parameters
    ----------
    series : pd.Series
        Time series to test for stationarity.
    significance : float
        Significance level for the stationarity verdict.

    Returns
    -------
    dict with keys: adf_stat, p_value, critical_values, is_stationary
    """
    series_clean = series.dropna()
    result = adfuller(series_clean, autolag="AIC")

    return {
        "adf_stat": result[0],
        "p_value": result[1],
        "used_lag": result[2],
        "n_obs": result[3],
        "critical_values": result[4],
        "is_stationary": result[1] < significance,
    }


def engle_granger_test(
    y: pd.Series,
    x: pd.Series,
    significance: float = 0.05,
) -> dict:
    """
    Engle-Granger two-step cointegration test.

    Step 1: OLS regression  y = α + β·x + ε  (β is the hedge ratio).
    Step 2: ADF test on residuals ε.

    Parameters
    ----------
    y, x : pd.Series
        Price series of the two assets (aligned index).
    significance : float
        Significance level for ADF test on residuals.

    Returns
    -------
    dict with keys: hedge_ratio, intercept, adf_stat, p_value,
                    critical_values, is_cointegrated
    """
    # Align and drop NaNs
    aligned = pd.concat([y, x], axis=1).dropna()
    y_clean, x_clean = aligned.iloc[:, 0], aligned.iloc[:, 1]

    # Step 1 — OLS
    X = sm.add_constant(x_clean)
    model = sm.OLS(y_clean, X).fit()
    intercept, hedge_ratio = model.params

    # Step 2 — ADF on residuals
    residuals = model.resid
    adf_result = adf_test(residuals, significance=significance)

    return {
        "hedge_ratio": float(hedge_ratio),
        "intercept": float(intercept),
        "adf_stat": adf_result["adf_stat"],
        "p_value": adf_result["p_value"],
        "critical_values": adf_result["critical_values"],
        "is_cointegrated": adf_result["is_stationary"],
    }


def screen_pairs(
    prices_df: pd.DataFrame,
    candidate_pairs: list[tuple[str, str]],
    significance: float = 0.05,
) -> pd.DataFrame:
    """
    Run Engle-Granger on all candidate pairs, testing both directions
    (y~x and x~y) and keeping the result with the lower p-value.

    Parameters
    ----------
    prices_df : pd.DataFrame
        DataFrame with columns = ticker RICs, rows = dates, values = close prices.
    candidate_pairs : list of (str, str)
        Pairs to test.
    significance : float
        Significance level for the cointegration verdict.

    Returns
    -------
    pd.DataFrame sorted by p_value (ascending), one row per pair.
    """
    rows = []

    for ticker_y, ticker_x in candidate_pairs:
        y = prices_df[ticker_y]
        x = prices_df[ticker_x]

        # Test both orderings
        result_yx = engle_granger_test(y, x, significance=significance)
        result_xy = engle_granger_test(x, y, significance=significance)

        # Keep the ordering with the lower (better) p-value
        if result_yx["p_value"] <= result_xy["p_value"]:
            best = result_yx
            dep, indep = ticker_y, ticker_x
        else:
            best = result_xy
            dep, indep = ticker_x, ticker_y

        rows.append(
            {
                "y": dep,
                "x": indep,
                "hedge_ratio": best["hedge_ratio"],
                "intercept": best["intercept"],
                "adf_stat": best["adf_stat"],
                "p_value": best["p_value"],
                "is_cointegrated": best["is_cointegrated"],
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values("p_value")
        .reset_index(drop=True)
    )
