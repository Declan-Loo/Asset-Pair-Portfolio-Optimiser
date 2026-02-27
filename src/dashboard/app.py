"""
Pairs-Trading Portfolio Optimiser — Streamlit Dashboard

Launch:  streamlit run src/dashboard/app.py
"""

import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so imports work when run via streamlit
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.data.refinitiv_client import get_close_prices
from src.modelling.cointegration import screen_pairs, engle_granger_test
from src.modelling.spread_analysis import (
    compute_spread,
    compute_zscore,
    spread_summary,
)
from src.modelling.optimiser import (
    mean_variance_weights,
    efficient_frontier,
    rolling_hedge_ratio,
)
from src.modelling.config import (
    TICKERS,
    CANDIDATE_PAIRS,
    TICKER_NAMES,
    TRAIN_START,
    TRAIN_END,
    TEST_START,
    TEST_END,
)
from src.backtesting.engine import PairsBacktestEngine, BacktestConfig
from src.backtesting.metrics import compute_volatility_reduction
from src.dashboard.components import (
    plot_spread_with_bands,
    plot_cointegration_results,
    plot_cumulative_returns,
    plot_efficient_frontier,
    plot_zscore_heatmap,
    plot_position_timeline,
    format_metrics_table,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Pairs-Trading Portfolio Optimiser",
    layout="wide",
)
st.title("Pairs-Trading Portfolio Optimiser")

# ---------------------------------------------------------------------------
# Sidebar — inputs
# ---------------------------------------------------------------------------
st.sidebar.header("Parameters")

budget = st.sidebar.number_input(
    "Total Budget (£)", min_value=1_000, value=100_000, step=5_000
)

st.sidebar.subheader("Current Holdings")
holdings = {}
for t in TICKERS:
    holdings[t] = st.sidebar.number_input(
        f"{TICKER_NAMES.get(t, t)} qty",
        min_value=0, value=0, step=1, key=f"hold_{t}",
    )

st.sidebar.subheader("Backtest Settings")
entry_z = st.sidebar.slider("Entry Z", 1.0, 4.0, 2.0, 0.1)
exit_z = st.sidebar.slider("Exit Z", 0.0, 2.0, 0.0, 0.1)
stop_z = st.sidebar.slider("Stop-Loss Z", 2.5, 6.0, 4.0, 0.25)
lookback = st.sidebar.slider("Lookback Window", 20, 120, 60, 5)
tx_cost = st.sidebar.number_input(
    "Transaction Cost (bps)", min_value=0.0, value=10.0, step=1.0
)

st.sidebar.subheader("Date Ranges")
train_start = st.sidebar.date_input("Train Start", datetime.fromisoformat(TRAIN_START))
train_end = st.sidebar.date_input("Train End", datetime.fromisoformat(TRAIN_END))
test_start = st.sidebar.date_input("Test Start", datetime.fromisoformat(TEST_START))
test_end = st.sidebar.date_input("Test End", datetime.fromisoformat(TEST_END))


# ---------------------------------------------------------------------------
# Cached data loading
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Fetching price data from LSEG…")
def load_prices(tickers: tuple, start: str, end: str) -> pd.DataFrame:
    return get_close_prices(list(tickers), start=start, end=end)


# Convert dates to strings for hashing / API calls
train_start_str = str(train_start)
train_end_str = str(train_end)
test_start_str = str(test_start)
test_end_str = str(test_end)

unique_tickers = sorted({t for pair in CANDIDATE_PAIRS for t in pair})

train_prices = load_prices(
    tuple(unique_tickers), train_start_str, train_end_str
)
test_prices = load_prices(
    tuple(unique_tickers), test_start_str, test_end_str
)


# ===================================================================
# TAB LAYOUT
# ===================================================================
tab_coint, tab_spread, tab_bt, tab_opt, tab_rebal = st.tabs([
    "Cointegration Screening",
    "Spread Analysis",
    "Backtesting",
    "Portfolio Optimisation",
    "Rebalancing Signals",
])


# -------------------------------------------------------------------
# TAB 1 — Cointegration Screening
# -------------------------------------------------------------------
with tab_coint:
    st.header("Cointegration Screening (Training Period)")

    screening_df = screen_pairs(train_prices, CANDIDATE_PAIRS)
    st.dataframe(
        screening_df.style.format({
            "hedge_ratio": "{:.4f}",
            "intercept": "{:.4f}",
            "adf_stat": "{:.4f}",
            "p_value": "{:.6f}",
        }),
        use_container_width=True,
    )

    st.plotly_chart(
        plot_cointegration_results(screening_df),
        use_container_width=True,
    )

    coint_pairs = screening_df[screening_df["is_cointegrated"]]
    st.info(
        f"{len(coint_pairs)} of {len(CANDIDATE_PAIRS)} pairs are "
        f"cointegrated at the 5% level."
    )


# -------------------------------------------------------------------
# TAB 2 — Spread Analysis
# -------------------------------------------------------------------
with tab_spread:
    st.header("Spread Analysis")

    pair_labels = [f"{y} / {x}" for y, x in CANDIDATE_PAIRS]
    selected_label = st.selectbox("Select Pair", pair_labels)
    idx = pair_labels.index(selected_label)
    sel_y, sel_x = CANDIDATE_PAIRS[idx]

    # Get cointegration params (from training data)
    eg = engle_granger_test(train_prices[sel_y], train_prices[sel_x])
    hr_static, intercept_static = eg["hedge_ratio"], eg["intercept"]

    # Rolling hedge ratio toggle
    use_rolling = st.checkbox("Use rolling hedge ratio", value=False)

    if use_rolling:
        roll_df = rolling_hedge_ratio(
            train_prices[sel_y], train_prices[sel_x], window=lookback,
        )
        hr_latest = roll_df["hedge_ratio"].iloc[-1]
        int_latest = roll_df["intercept"].iloc[-1]

        st.caption(
            f"Rolling HR (window={lookback}): β = {hr_latest:.4f}, "
            f"α = {int_latest:.4f}  |  "
            f"Static HR: β = {hr_static:.4f}, α = {intercept_static:.4f}"
        )

        # Show rolling hedge ratio chart
        import plotly.graph_objects as go
        hr_fig = go.Figure()
        hr_fig.add_trace(go.Scatter(
            x=roll_df.index, y=roll_df["hedge_ratio"],
            name="Rolling β", line=dict(color="#636EFA"),
        ))
        hr_fig.add_hline(
            y=hr_static,
            line=dict(color="red", dash="dash", width=1),
            annotation_text=f"Static β = {hr_static:.4f}",
        )
        hr_fig.update_layout(
            yaxis_title="Hedge Ratio (β)",
            height=280, margin=dict(t=20, b=20),
        )
        st.plotly_chart(hr_fig, use_container_width=True)

        hr, intercept = hr_latest, int_latest
    else:
        hr, intercept = hr_static, intercept_static

    spread = compute_spread(train_prices[sel_y], train_prices[sel_x], hr, intercept)
    zscore = compute_zscore(spread, window=lookback)

    st.plotly_chart(
        plot_spread_with_bands(spread, zscore, entry_z=entry_z, exit_z=exit_z),
        use_container_width=True,
    )

    summary = spread_summary(
        train_prices[sel_y], train_prices[sel_x],
        hr, intercept, window=lookback,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Half-Life (days)", f"{summary['half_life']:.1f}")
    col2.metric("Hurst Exponent", f"{summary['hurst']:.3f}")
    col3.metric("ADF p-value", f"{summary['adf_pvalue']:.4f}")
    col4.metric("Current Z-Score", f"{summary['current_zscore']:.2f}")


# -------------------------------------------------------------------
# TAB 3 — Backtesting
# -------------------------------------------------------------------
with tab_bt:
    st.header("Backtesting (Test Period)")

    if coint_pairs.empty:
        st.warning("No cointegrated pairs found — nothing to backtest.")
    else:
        config = BacktestConfig(
            entry_z=entry_z,
            exit_z=exit_z,
            stop_loss_z=stop_z,
            lookback_window=lookback,
            transaction_cost_bps=tx_cost,
            initial_capital=float(budget),
        )
        engine = PairsBacktestEngine(config)

        bt_pair_labels = [
            f"{r['y']} / {r['x']}" for _, r in coint_pairs.iterrows()
        ]
        bt_selected = st.selectbox(
            "Select cointegrated pair", bt_pair_labels, key="bt_pair"
        )
        bt_idx = bt_pair_labels.index(bt_selected)
        bt_row = coint_pairs.iloc[bt_idx]

        y_test = test_prices[bt_row["y"]]
        x_test = test_prices[bt_row["x"]]

        result = engine.run(
            y_test, x_test,
            hedge_ratio=bt_row["hedge_ratio"],
            intercept=bt_row["intercept"],
        )

        # Metrics
        st.subheader("Performance Metrics")
        st.dataframe(
            format_metrics_table(result.metrics),
            use_container_width=True,
            hide_index=True,
        )

        # Volatility reduction vs equal-weight benchmark
        y_ret = y_test.pct_change().fillna(0)
        x_ret = x_test.pct_change().fillna(0)
        benchmark_ret = 0.5 * y_ret + 0.5 * x_ret  # equal-weight buy-hold

        vol_red = compute_volatility_reduction(result.daily_returns, benchmark_ret)
        st.metric(
            "Volatility Reduction vs Equal-Weight B&H",
            f"{vol_red:.1%}",
            help="Positive = strategy is less volatile than the benchmark",
        )

        # Cumulative returns
        st.subheader("Cumulative Returns")
        y_bh = (1 + y_ret).cumprod()
        x_bh = (1 + x_ret).cumprod()
        st.plotly_chart(
            plot_cumulative_returns(result.cumulative_returns, y_bh, x_bh),
            use_container_width=True,
        )

        # Position timeline
        st.subheader("Position Timeline")
        st.plotly_chart(
            plot_position_timeline(result.positions["position"]),
            use_container_width=True,
        )

        # Trade log
        st.subheader("Trade Log")
        if not result.trades.empty:
            st.dataframe(result.trades, use_container_width=True)
        else:
            st.info("No trades generated in the test period.")


# -------------------------------------------------------------------
# TAB 4 — Portfolio Optimisation
# -------------------------------------------------------------------
with tab_opt:
    st.header("Portfolio Optimisation (Efficient Frontier)")

    if coint_pairs.empty:
        st.warning("No cointegrated pairs — cannot optimise.")
    else:
        # Build daily spread returns for each cointegrated pair
        pair_returns = {}
        for _, row in coint_pairs.iterrows():
            label = f"{row['y']}/{row['x']}"
            y_ret = test_prices[row["y"]].pct_change()
            x_ret = test_prices[row["x"]].pct_change()
            # Spread return ≈ y_ret − hedge_ratio * x_ret
            pair_returns[label] = y_ret - row["hedge_ratio"] * x_ret

        returns_df = pd.DataFrame(pair_returns).dropna()

        if returns_df.shape[1] < 2:
            st.info(
                "Need at least 2 cointegrated pairs for frontier. "
                "Showing single-pair stats."
            )
            st.dataframe(returns_df.describe(), use_container_width=True)
        else:
            # Mean-variance
            mv = mean_variance_weights(returns_df)
            frontier_df = efficient_frontier(returns_df)

            max_sharpe_pt = (mv["max_sharpe_vol"], mv["max_sharpe_return"])
            min_var_pt = (mv["min_var_vol"], mv["min_var_return"])

            st.plotly_chart(
                plot_efficient_frontier(frontier_df, max_sharpe_pt, min_var_pt),
                use_container_width=True,
            )

            # Weight tables
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Max-Sharpe Weights")
                w_sharpe_df = pd.DataFrame({
                    "Pair": returns_df.columns,
                    "Weight": mv["max_sharpe_weights"],
                })
                w_sharpe_df["Weight"] = w_sharpe_df["Weight"].map("{:.2%}".format)
                st.dataframe(w_sharpe_df, hide_index=True)

            with col_b:
                st.subheader("Min-Variance Weights")
                w_mv_df = pd.DataFrame({
                    "Pair": returns_df.columns,
                    "Weight": mv["min_var_weights"],
                })
                w_mv_df["Weight"] = w_mv_df["Weight"].map("{:.2%}".format)
                st.dataframe(w_mv_df, hide_index=True)


# -------------------------------------------------------------------
# TAB 5 — Rebalancing Signals
# -------------------------------------------------------------------
with tab_rebal:
    st.header("Rebalancing Signals")

    if coint_pairs.empty:
        st.warning("No cointegrated pairs — no signals to generate.")
    else:
        # Current z-scores for each cointegrated pair
        zscore_dict = {}
        signal_rows = []

        for _, row in coint_pairs.iterrows():
            label = f"{row['y']} / {row['x']}"
            y_full = test_prices[row["y"]]
            x_full = test_prices[row["x"]]
            spr = compute_spread(y_full, x_full, row["hedge_ratio"], row["intercept"])
            zs = compute_zscore(spr, window=lookback)
            zscore_dict[label] = zs

            current_z = zs.iloc[-1] if not np.isnan(zs.iloc[-1]) else 0.0

            if current_z <= -entry_z:
                signal = "BUY SPREAD (Long Y, Short X)"
            elif current_z >= entry_z:
                signal = "SELL SPREAD (Short Y, Long X)"
            else:
                signal = "HOLD / FLAT"

            signal_rows.append({
                "Pair": label,
                "Current Z": f"{current_z:.2f}",
                "Signal": signal,
            })

        st.subheader("Current Signals")
        signals_df = pd.DataFrame(signal_rows)
        st.dataframe(signals_df, use_container_width=True, hide_index=True)

        # Z-score heatmap
        st.subheader("Z-Score Heatmap")
        st.plotly_chart(
            plot_zscore_heatmap(zscore_dict),
            use_container_width=True,
        )

        # Capital allocation using MPT weights
        st.subheader("Capital Allocation")

        pair_returns_rebal = {}
        for _, row in coint_pairs.iterrows():
            label = f"{row['y']}/{row['x']}"
            y_ret = test_prices[row["y"]].pct_change()
            x_ret = test_prices[row["x"]].pct_change()
            pair_returns_rebal[label] = y_ret - row["hedge_ratio"] * x_ret

        returns_rebal = pd.DataFrame(pair_returns_rebal).dropna()

        if returns_rebal.shape[1] >= 2:
            mv_rebal = mean_variance_weights(returns_rebal)
            weights = mv_rebal["max_sharpe_weights"]
        else:
            weights = np.array([1.0])

        alloc_rows = []
        for i, (_, row) in enumerate(coint_pairs.iterrows()):
            label = f"{row['y']} / {row['x']}"
            w = weights[i] if i < len(weights) else 0.0
            alloc_rows.append({
                "Pair": label,
                "MPT Weight": f"{w:.2%}",
                "Capital (£)": f"£{budget * w:,.0f}",
            })

        st.dataframe(
            pd.DataFrame(alloc_rows),
            use_container_width=True,
            hide_index=True,
        )
