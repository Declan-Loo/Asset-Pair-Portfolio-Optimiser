# Source code for computing Sharpe ratio, volatility reduction and maximum drawdown

import numpy as np
import pandas as pd

# Perform Ex-Post sharpe ratio
def compute_ex_post_sharpe_ratio(returns: pd.Series, rf_annual: float = 0.02, periods_per_year : int = 252) -> float:
    """
    Sharpe (1994) ex-post Sharpe ratio on realised portfolio returns.
    
    Parameters:
    -----------
    returns : pd.Series
        Daily portfolio returns (test period 2024)
    rf_annual : float
        Annualised risk-free rate (e.g., 3-month T-bill)
    periods_per_year : int
        Trading days per year (252=US stocks)
    
    Returns:
    --------
    float: Annualised ex-post Sharpe ratio [web:179]
    """
    if len(returns) < 2:
        raise ValueError("Need at least 2 returns for std dev")

    excess_returns = returns - (rf_annual / periods_per_year)

    mean_excess = excess_returns.mean()
    std_excess = excess_returns.std(ddof=1)

    if std_excess == 0:
        return np.nan

    return (mean_excess / std_excess) * np.sqrt(periods_per_year)


def compute_max_drawdown(returns: pd.Series) -> float:
    """
    Compute the maximum drawdown of a return series.

    Maximum drawdown is the largest peak-to-trough decline in cumulative
    portfolio value over the observed period.

    Parameters:
    -----------
    returns : pd.Series
        Daily portfolio returns.

    Returns:
    --------
    float: Maximum drawdown as a negative fraction (e.g., -0.15 = -15%).
    """
    if len(returns) < 2:
        raise ValueError("Need at least 2 returns to compute drawdown")

    cum_returns = (1 + returns).cumprod()
    rolling_max = cum_returns.cummax()
    drawdowns = (cum_returns - rolling_max) / rolling_max

    return float(drawdowns.min())


def compute_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Historical Value-at-Risk (VaR).

    Returns the loss threshold such that losses exceed this value only
    (1 - confidence)% of the time.  Reported as a negative number
    (e.g. -0.02 means a 2% daily loss at the given confidence level).

    Parameters
    ----------
    returns : pd.Series
        Daily portfolio returns.
    confidence : float
        Confidence level, e.g. 0.95 for 95% VaR.

    Returns
    -------
    float: VaR as a negative fraction.
    """
    if len(returns) < 2:
        raise ValueError("Need at least 2 returns to compute VaR")
    return float(np.percentile(returns.dropna(), (1 - confidence) * 100))


def compute_cvar(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Conditional Value-at-Risk (CVaR) / Expected Shortfall.

    Mean of all returns that fall below the VaR threshold — captures
    the expected loss in the worst (1 - confidence)% of days.

    Parameters
    ----------
    returns : pd.Series
        Daily portfolio returns.
    confidence : float
        Confidence level, e.g. 0.95 for 95% CVaR.

    Returns
    -------
    float: CVaR as a negative fraction.
    """
    if len(returns) < 2:
        raise ValueError("Need at least 2 returns to compute CVaR")
    var = compute_var(returns, confidence)
    tail = returns[returns <= var]
    return float(tail.mean()) if len(tail) > 0 else var


def compute_volatility_reduction(portfolio_returns: pd.Series, benchmark_returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    Compute the annualised volatility reduction of the portfolio relative to a
    benchmark (e.g., an equally-weighted or single-asset baseline).

    Volatility reduction = 1 - (sigma_portfolio / sigma_benchmark)

    A positive value indicates the portfolio is less volatile than the
    benchmark; a negative value means it is more volatile.

    Parameters:
    -----------
    portfolio_returns : pd.Series
        Daily returns of the optimised portfolio.
    benchmark_returns : pd.Series
        Daily returns of the benchmark portfolio.
    periods_per_year : int
        Trading days per year used for annualisation (252 for equities).

    Returns:
    --------
    float: Fractional volatility reduction (e.g., 0.20 = 20% reduction).
    """
    if len(portfolio_returns) < 2 or len(benchmark_returns) < 2:
        raise ValueError("Need at least 2 returns to compute volatility")

    sigma_portfolio = portfolio_returns.std(ddof=1) * np.sqrt(periods_per_year)
    sigma_benchmark = benchmark_returns.std(ddof=1) * np.sqrt(periods_per_year)

    if sigma_benchmark == 0:
        raise ValueError("Benchmark volatility is zero; cannot compute reduction")

    return float(1 - (sigma_portfolio / sigma_benchmark))