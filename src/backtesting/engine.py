"""
Pairs-trading backtesting engine.

Simulates a z-score-based mean-reversion strategy with configurable
entry / exit / stop-loss thresholds and transaction costs.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .metrics import compute_ex_post_sharpe_ratio, compute_max_drawdown, compute_var, compute_cvar


@dataclass
class BacktestConfig:
    """Parameters for the pairs-trading backtest."""

    entry_z: float = 2.0
    exit_z: float = 0.0
    stop_loss_z: float = 4.0
    lookback_window: int = 60
    transaction_cost_bps: float = 10.0
    initial_capital: float = 100_000.0


@dataclass
class BacktestResult:
    """Container for backtest outputs."""

    daily_returns: pd.Series
    cumulative_returns: pd.Series
    positions: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict
    spread: pd.Series
    zscore: pd.Series


class PairsBacktestEngine:
    """Z-score mean-reversion pairs-trading backtester."""

    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        y_prices: pd.Series,
        x_prices: pd.Series,
        hedge_ratio: float,
        intercept: float = 0.0,
    ) -> BacktestResult:
        """
        Run the full backtest pipeline.

        Parameters
        ----------
        y_prices, x_prices : pd.Series
            Close prices for the dependent (y) and independent (x) legs.
        hedge_ratio : float
            Static hedge ratio (β) from cointegration estimation.
        intercept : float
            Intercept (α) from cointegration estimation.

        Returns
        -------
        BacktestResult
        """
        cfg = self.config

        # 1. Compute spread and z-score
        spread = y_prices - hedge_ratio * x_prices - intercept
        spread.name = "spread"
        zscore = self._rolling_zscore(spread, cfg.lookback_window)

        # 2. Generate trading signals
        positions = self._generate_signals(zscore)

        # 3. Compute PnL
        pnl_df = self._compute_pnl(y_prices, x_prices, positions, hedge_ratio)
        daily_returns = pnl_df["strategy_return"]
        cumulative_returns = (1 + daily_returns).cumprod()

        # 4. Build trade log
        trades = self._build_trade_log(positions, zscore)

        # 5. Compute performance metrics
        metrics = self._compute_metrics(daily_returns, trades)

        return BacktestResult(
            daily_returns=daily_returns,
            cumulative_returns=cumulative_returns,
            positions=pnl_df[["position"]],
            trades=trades,
            metrics=metrics,
            spread=spread,
            zscore=zscore,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rolling_zscore(spread: pd.Series, window: int) -> pd.Series:
        rolling_mean = spread.rolling(window=window).mean()
        rolling_std = spread.rolling(window=window).std(ddof=1)
        zscore = (spread - rolling_mean) / rolling_std
        zscore.name = "zscore"
        return zscore

    def _generate_signals(self, zscore: pd.Series) -> pd.Series:
        """
        Generate position signals based on z-score thresholds.

        +1 = long spread (z < -entry_z, expecting reversion up)
        -1 = short spread (z > +entry_z, expecting reversion down)
         0 = flat
        """
        cfg = self.config
        positions = pd.Series(0.0, index=zscore.index, name="position")

        pos = 0.0
        for i in range(len(zscore)):
            z = zscore.iloc[i]

            if np.isnan(z):
                positions.iloc[i] = 0.0
                continue

            # Stop-loss: forced exit
            if abs(z) >= cfg.stop_loss_z and pos != 0.0:
                pos = 0.0
            # Exit: z-score crosses back to exit threshold
            elif pos == 1.0 and z >= -cfg.exit_z:
                pos = 0.0
            elif pos == -1.0 and z <= cfg.exit_z:
                pos = 0.0
            # Entry: z-score crosses entry threshold
            elif pos == 0.0 and z <= -cfg.entry_z:
                pos = 1.0  # long spread
            elif pos == 0.0 and z >= cfg.entry_z:
                pos = -1.0  # short spread

            positions.iloc[i] = pos

        return positions

    def _compute_pnl(
        self,
        y_prices: pd.Series,
        x_prices: pd.Series,
        positions: pd.Series,
        hedge_ratio: float,
    ) -> pd.DataFrame:
        """
        Daily mark-to-market PnL with transaction costs.

        The spread return on day t is:
            r_t = position_{t-1} * (Δy_t - hedge_ratio * Δx_t) / capital
        """
        cfg = self.config

        # Daily price changes
        dy = y_prices.diff()
        dx = x_prices.diff()

        # Spread dollar PnL per unit position
        spread_pnl = positions.shift(1) * (dy - hedge_ratio * dx)
        spread_pnl = spread_pnl.fillna(0.0)

        # Transaction costs on position changes
        position_change = positions.diff().abs().fillna(0.0)
        # Cost proportional to notional (approximate using y price level)
        notional_traded = position_change * (y_prices + hedge_ratio * x_prices)
        tc = notional_traded * (cfg.transaction_cost_bps / 10_000)

        net_pnl = spread_pnl - tc
        strategy_return = net_pnl / cfg.initial_capital

        return pd.DataFrame(
            {
                "position": positions,
                "spread_pnl": spread_pnl,
                "transaction_cost": tc,
                "net_pnl": net_pnl,
                "strategy_return": strategy_return,
            },
            index=y_prices.index,
        )

    def _build_trade_log(
        self, positions: pd.Series, zscore: pd.Series
    ) -> pd.DataFrame:
        """Build a log of trade events (entries and exits)."""
        changes = positions.diff().fillna(0.0)
        trade_mask = changes != 0.0
        trade_dates = changes[trade_mask]

        records = []
        for date, change in trade_dates.items():
            direction = "entry_long" if change > 0 else "entry_short" if change < 0 else "exit"
            if positions.loc[date] == 0.0:
                direction = "exit"
            records.append(
                {
                    "date": date,
                    "direction": direction,
                    "position_after": positions.loc[date],
                    "zscore": zscore.loc[date] if date in zscore.index else np.nan,
                }
            )

        return pd.DataFrame(records)

    def _compute_metrics(
        self, daily_returns: pd.Series, trades: pd.DataFrame
    ) -> dict:
        """Aggregate performance metrics using existing metric functions."""
        valid_returns = daily_returns.dropna()

        if len(valid_returns) < 2:
            return {
                "sharpe_ratio": np.nan,
                "max_drawdown": np.nan,
                "total_return": 0.0,
                "num_trades": 0,
                "win_rate": np.nan,
                "profit_factor": np.nan,
                "annualised_volatility": np.nan,
                "var_95": np.nan,
                "cvar_95": np.nan,
            }

        sharpe = compute_ex_post_sharpe_ratio(valid_returns)
        max_dd = compute_max_drawdown(valid_returns)
        total_return = float((1 + valid_returns).prod() - 1)
        ann_vol = float(valid_returns.std(ddof=1) * np.sqrt(252))
        var_95 = compute_var(valid_returns, confidence=0.95)
        cvar_95 = compute_cvar(valid_returns, confidence=0.95)

        # Trade-level stats
        num_round_trips = len(trades[trades["direction"] == "exit"])

        # Win rate from return between entry-exit pairs
        exits = trades[trades["direction"] == "exit"]
        entries = trades[trades["direction"].str.startswith("entry")]
        n_entries = len(entries)

        # Approximate win rate from daily returns on active days
        active_returns = valid_returns[valid_returns != 0.0]
        wins = (active_returns > 0).sum()
        losses = (active_returns < 0).sum()
        win_rate = float(wins / (wins + losses)) if (wins + losses) > 0 else np.nan
        profit_factor = (
            float(active_returns[active_returns > 0].sum() / abs(active_returns[active_returns < 0].sum()))
            if (active_returns < 0).any()
            else np.inf
        )

        return {
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "total_return": total_return,
            "num_trades": n_entries,
            "num_round_trips": num_round_trips,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "annualised_volatility": ann_vol,
            "var_95": var_95,
            "cvar_95": cvar_95,
        }
