from .config import (
    TICKERS,
    CANDIDATE_PAIRS,
    TRAIN_START,
    TRAIN_END,
    TEST_START,
    TEST_END,
    INTERVAL,
    TICKER_NAMES,
    RISK_FREE_RATE,
)

from .cointegration import (
    adf_test,
    engle_granger_test,
    screen_pairs,
)

from .spread_analysis import (
    compute_spread,
    compute_zscore,
    compute_half_life,
    compute_rolling_half_life,
    compute_hurst_exponent,
    compute_rolling_zscore,
    spread_summary,
)

from .return_estimation import (
    compute_spread_returns,
    build_spread_return_matrix,
    historical_mean_return,
    ewma_mean_return,
    ou_implied_spread_return,
    build_ou_implied_returns,
    sample_covariance,
    shrinkage_covariance,
    spread_vs_asset_estimates,
)

from .optimiser import (
    ols_hedge_ratio,
    rolling_hedge_ratio,
    optimise_portfolio,
    minimum_variance_weights,
    maximum_sharpe_weights,
    compute_efficient_frontier,
)

__all__ = [
    # Config
    "TICKERS",
    "CANDIDATE_PAIRS",
    "TRAIN_START",
    "TRAIN_END",
    "TEST_START",
    "TEST_END",
    "INTERVAL",
    "TICKER_NAMES",
    "RISK_FREE_RATE",
    # Cointegration
    "adf_test",
    "engle_granger_test",
    "screen_pairs",
    # Spread analysis
    "compute_spread",
    "compute_zscore",
    "compute_half_life",
    "compute_rolling_half_life",
    "compute_hurst_exponent",
    "compute_rolling_zscore",
    "spread_summary",
    # Return estimation
    "compute_spread_returns",
    "build_spread_return_matrix",
    "historical_mean_return",
    "ewma_mean_return",
    "ou_implied_spread_return",
    "build_ou_implied_returns",
    "sample_covariance",
    "shrinkage_covariance",
    "spread_vs_asset_estimates",
    # Optimiser
    "ols_hedge_ratio",
    "rolling_hedge_ratio",
    "optimise_portfolio",
    "minimum_variance_weights",
    "maximum_sharpe_weights",
    "compute_efficient_frontier",
]
