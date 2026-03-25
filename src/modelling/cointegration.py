"""
Engle-Granger two-step cointegration testing.

Implements ADF unit-root tests and the Engle-Granger procedure for
identifying cointegrated asset pairs with stationary residuals.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm

# adfuller() function performs the ADF test - second part of the Engle-Granger test
# coint() function uses MacKinnon's (1991) critical values in ADF test (preferably use this over adfuller() to reduce false positives)
from statsmodels.tsa.stattools import adfuller, coint


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

def is_I1(series: pd.Series, significance: float = 0.05) -> dict:
    """
    Check if a series is plausibly I(1):
    - non-stationary in levels
    - stationary in first differences
    """
    level_result = adf_test(series, significance=significance)
    diff_result = adf_test(series.diff(), significance=significance)

    return {
        "level": level_result,
        "diff": diff_result,
        "is_I1": (not level_result["is_stationary"]) and diff_result["is_stationary"],
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
    aligned = pd.concat([y, x], axis=1).dropna().astype(float)
    y_clean, x_clean = aligned.iloc[:, 0], aligned.iloc[:, 1]

    # I(1) diagnostics (for reporting only)
    y_I1 = is_I1(y_clean, significance=significance)
    x_I1 = is_I1(x_clean, significance=significance)

    
    # Step 1 — OLS regression - get hedge ratio/intercept for trading
    X = sm.add_constant(x_clean)
    model = sm.OLS(y_clean, X).fit()
    intercept, hedge_ratio = model.params

    # Step 2 - Get CORRECT cointegration stats via `coint` function from `stattools` with MacKinnon (1991) critical values
    # perform coiuntegration test with a constant, augmented Engle-Granger (AEG) and lag with minimised AIC
    coint_stat, p_value, critical_values = coint(
        y_clean, x_clean, trend="c", method="aeg", autolag="AIC"
    )

    return {
        "hedge_ratio": float(hedge_ratio),
        "intercept": float(intercept),
        "adf_stat": float(coint_stat),
        "p_value": float(p_value),
        "critical_values": critical_values,
        "is_cointegrated": bool(p_value < significance and y_I1["is_I1"] and x_I1["is_I1"]),
        "y_is_I1": y_I1["is_I1"],
        "x_is_I1": x_I1["is_I1"],
    }

def screen_pairs(
    prices_df: pd.DataFrame,
    candidate_pairs: list[tuple[str, str]],
    significance: float = 0.05,
) -> pd.DataFrame:
    """
    Run Engle-Granger on all candidate pairs, testing both directions
    (y~x and x~y) and keeping the result with the lower p-value. (todo: check raw pirce of day - raw price of day before)

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
                "y_is_I1": best["y_is_I1"],
                "x_is_I1": best["x_is_I1"],
                "is_cointegrated": best["is_cointegrated"], # obtained from coint
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values("p_value")
        .reset_index(drop=True)
    )
