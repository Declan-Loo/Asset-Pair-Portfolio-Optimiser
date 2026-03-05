"""
Pairs-Trading Portfolio Optimiser — Streamlit Dashboard

  Mode 1 — Research / Backtest: universe, date range, pair selection → cointegration,
           spread & z-scores, backtest metrics, efficient frontier.
  Mode 2 — PM / Rebalancing (Experimental): current portfolio + rebalancing frequency
           → recent history, recomputed hedge ratios & MPT weights, target weights & impact.

Launch:  streamlit run src/dashboard/app.py
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta

import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Path and imports
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
    build_pair_returns,
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

st.set_page_config(
    page_title="Pairs-Trading Portfolio Optimiser",
    layout="wide",
)
st.title("Pairs-Trading Portfolio Optimiser")

# ---------------------------------------------------------------------------
# Mode selector
# ---------------------------------------------------------------------------
st.sidebar.header("Mode")
mode = st.sidebar.radio(
    "Select view",
    ["Research / Backtest", "PM / Rebalancing (Experimental)"],
    index=0,
    help="Research: cointegration, spreads, backtest, frontier. PM: portfolio rebalancing with latest data.",
)

# ---------------------------------------------------------------------------
# ==========  MODE 1 — Research / Backtest  ==========
# ---------------------------------------------------------------------------
if mode == "Research / Backtest":
    st.sidebar.subheader("Universe & dates")
    pair_options = [f"{y} / {x}" for y, x in CANDIDATE_PAIRS]
    selected_pair_labels = st.sidebar.multiselect(
        "Pair selection",
        options=pair_options,
        default=pair_options,
        help="Pairs to include in cointegration and backtest.",
    )
    portfolio_pairs = []
    for label in selected_pair_labels:
        parts = label.split(" / ", 1)
        if len(parts) == 2:
            portfolio_pairs.append((parts[0].strip(), parts[1].strip()))

    train_start = st.sidebar.date_input("Train start", datetime.fromisoformat(TRAIN_START))
    train_end = st.sidebar.date_input("Train end", datetime.fromisoformat(TRAIN_END))
    test_start = st.sidebar.date_input("Test start", datetime.fromisoformat(TEST_START))
    test_end = st.sidebar.date_input("Test end", datetime.fromisoformat(TEST_END))

    st.sidebar.subheader("Backtest settings")
    entry_z = st.sidebar.slider("Entry Z", 1.0, 4.0, 2.0, 0.1)
    exit_z = st.sidebar.slider("Exit Z", 0.0, 2.0, 0.0, 0.1)
    stop_z = st.sidebar.slider("Stop-loss Z", 2.5, 6.0, 4.0, 0.25)
    lookback = st.sidebar.slider("Lookback window", 20, 120, 60, 5)
    tx_cost = st.sidebar.number_input("Transaction cost (bps)", min_value=0.0, value=10.0, step=1.0)
    initial_capital = st.sidebar.number_input("Initial capital (£) for backtest", min_value=1_000, value=100_000, step=5_000)

    if not portfolio_pairs:
        st.warning("Select at least one pair in the sidebar.")
        st.stop()

    @st.cache_data(show_spinner="Fetching price data from LSEG…")
    def load_prices(tickers: tuple, start: str, end: str) -> pd.DataFrame:
        return get_close_prices(list(tickers), start=start, end=end)

    unique_tickers = sorted({t for pair in portfolio_pairs for t in pair})
    train_prices = load_prices(tuple(unique_tickers), str(train_start), str(train_end))
    test_prices = load_prices(tuple(unique_tickers), str(test_start), str(test_end))

    screening_df = screen_pairs(train_prices, portfolio_pairs)
    coint_pairs = screening_df[screening_df["is_cointegrated"]]

    tab_coint, tab_spread, tab_bt, tab_opt = st.tabs([
        "Cointegration tests",
        "Spread & z-scores",
        "Backtest metrics",
        "Efficient frontier",
    ])

    with tab_coint:
        st.header("Cointegration tests (training period)")
        st.dataframe(
            screening_df.style.format({
                "hedge_ratio": "{:.4f}",
                "intercept": "{:.4f}",
                "adf_stat": "{:.4f}",
                "p_value": "{:.6f}",
            }),
            use_container_width=True,
        )
        st.plotly_chart(plot_cointegration_results(screening_df), use_container_width=True)
        st.info(f"{len(coint_pairs)} of {len(portfolio_pairs)} pairs are cointegrated at the 5% level.")

    with tab_spread:
        st.header("Spread & z-scores")
        all_pair_labels = [f"{y} / {x}" for y, x in portfolio_pairs]
        selected_label = st.selectbox("Select pair", all_pair_labels)
        idx = all_pair_labels.index(selected_label)
        sel_y, sel_x = portfolio_pairs[idx]
        eg = engle_granger_test(train_prices[sel_y], train_prices[sel_x])
        hr_static, intercept_static = eg["hedge_ratio"], eg["intercept"]
        use_rolling = st.checkbox("Use rolling hedge ratio", value=False)
        if use_rolling:
            roll_df = rolling_hedge_ratio(train_prices[sel_y], train_prices[sel_x], window=lookback)
            hr_latest = roll_df["hedge_ratio"].iloc[-1]
            int_latest = roll_df["intercept"].iloc[-1]
            st.caption(f"Rolling β = {hr_latest:.4f}, α = {int_latest:.4f}  |  Static β = {hr_static:.4f}, α = {intercept_static:.4f}")
            import plotly.graph_objects as go
            hr_fig = go.Figure()
            hr_fig.add_trace(go.Scatter(x=roll_df.index, y=roll_df["hedge_ratio"], name="Rolling β", line=dict(color="#636EFA")))
            hr_fig.add_hline(y=hr_static, line=dict(color="red", dash="dash"), annotation_text=f"Static β = {hr_static:.4f}")
            hr_fig.update_layout(yaxis_title="Hedge ratio (β)", height=280, margin=dict(t=20, b=20))
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
        summary = spread_summary(train_prices[sel_y], train_prices[sel_x], hr, intercept, window=lookback)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Half-life (days)", f"{summary['half_life']:.1f}")
        c2.metric("Hurst exponent", f"{summary['hurst']:.3f}")
        c3.metric("ADF p-value", f"{summary['adf_pvalue']:.4f}")
        c4.metric("Current z-score", f"{summary['current_zscore']:.2f}")

    with tab_bt:
        st.header("Backtest metrics (test period)")
        if coint_pairs.empty:
            st.warning("No cointegrated pairs — nothing to backtest.")
        else:
            config = BacktestConfig(
                entry_z=entry_z, exit_z=exit_z, stop_loss_z=stop_z,
                lookback_window=lookback, transaction_cost_bps=tx_cost,
                initial_capital=float(initial_capital),
            )
            engine = PairsBacktestEngine(config)
            bt_pair_labels = [f"{r['y']} / {r['x']}" for _, r in coint_pairs.iterrows()]
            bt_selected = st.selectbox("Select cointegrated pair", bt_pair_labels, key="bt_pair")
            bt_idx = bt_pair_labels.index(bt_selected)
            bt_row = coint_pairs.iloc[bt_idx]
            y_test = test_prices[bt_row["y"]]
            x_test = test_prices[bt_row["x"]]
            result = engine.run(y_test, x_test, hedge_ratio=bt_row["hedge_ratio"], intercept=bt_row["intercept"])
            st.subheader("Performance metrics")
            st.dataframe(format_metrics_table(result.metrics), use_container_width=True, hide_index=True)
            vol_red = result.metrics.get("volatility_reduction", float("nan"))
            st.metric("Volatility reduction vs equal-weight B&H", f"{vol_red:.1%}" if pd.notna(vol_red) else "N/A")
            st.subheader("Cumulative returns")
            y_ret = y_test.pct_change().fillna(0)
            x_ret = x_test.pct_change().fillna(0)
            y_bh = (1 + y_ret).cumprod()
            x_bh = (1 + x_ret).cumprod()
            st.plotly_chart(plot_cumulative_returns(result.cumulative_returns, y_bh, x_bh), use_container_width=True)
            st.subheader("Position timeline")
            st.plotly_chart(plot_position_timeline(result.positions["position"]), use_container_width=True)
            st.subheader("Trade log")
            if not result.trades.empty:
                st.dataframe(result.trades, use_container_width=True)
            else:
                st.info("No trades in the test period.")

    with tab_opt:
        st.header("Efficient frontier")
        if coint_pairs.empty:
            st.warning("No cointegrated pairs — cannot optimise.")
        else:
            returns_df = build_pair_returns(test_prices, coint_pairs)
            if returns_df.shape[1] < 2:
                st.info("Need at least 2 cointegrated pairs for the frontier.")
                st.dataframe(returns_df.describe(), use_container_width=True)
            else:
                mv = mean_variance_weights(returns_df)
                frontier_df = efficient_frontier(returns_df)
                max_sharpe_pt = (mv["max_sharpe_vol"], mv["max_sharpe_return"])
                min_var_pt = (mv["min_var_vol"], mv["min_var_return"])
                st.plotly_chart(
                    plot_efficient_frontier(frontier_df, max_sharpe_pt, min_var_pt),
                    use_container_width=True,
                )
                bench_ret = returns_df.mean(axis=1)
                port_ret_sharpe = (returns_df * mv["max_sharpe_weights"]).sum(axis=1)
                port_ret_minvar = (returns_df * mv["min_var_weights"]).sum(axis=1)
                mask = port_ret_sharpe.notna() & bench_ret.notna()
                vol_red_sharpe = compute_volatility_reduction(port_ret_sharpe[mask], bench_ret[mask])
                vol_red_minvar = compute_volatility_reduction(port_ret_minvar[mask], bench_ret[mask])
                st.subheader("Portfolio-level volatility reduction")
                col1, col2 = st.columns(2)
                col1.metric("Max-Sharpe vs equal-weight", f"{vol_red_sharpe:.1%}")
                col2.metric("Min-variance vs equal-weight", f"{vol_red_minvar:.1%}")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader("Max-Sharpe weights")
                    w_df = pd.DataFrame({"Pair": returns_df.columns, "Weight": mv["max_sharpe_weights"]})
                    w_df["Weight"] = w_df["Weight"].map("{:.2%}".format)
                    st.dataframe(w_df, hide_index=True)
                with col_b:
                    st.subheader("Min-variance weights")
                    w_df = pd.DataFrame({"Pair": returns_df.columns, "Weight": mv["min_var_weights"]})
                    w_df["Weight"] = w_df["Weight"].map("{:.2%}".format)
                    st.dataframe(w_df, hide_index=True)

# ---------------------------------------------------------------------------
# ==========  MODE 2 — PM / Rebalancing (Experimental)  ==========
# ---------------------------------------------------------------------------
else:
    st.warning(
        "**Experimental rebalancing module (extension of core research).** "
        "Pull recent history, recompute hedge ratios & MPT weights, and view target weights and impact on metrics."
    )

    st.sidebar.subheader("Current portfolio")
    pair_options_pm = [f"{y} / {x}" for y, x in CANDIDATE_PAIRS]
    selected_pm = st.sidebar.multiselect(
        "Portfolio pairs",
        options=pair_options_pm,
        default=pair_options_pm[:4],
        key="pm_pairs",
    )
    portfolio_pairs_pm = []
    for label in selected_pm:
        parts = label.split(" / ", 1)
        if len(parts) == 2:
            portfolio_pairs_pm.append((parts[0].strip(), parts[1].strip()))

    capital_pm = st.sidebar.number_input(
        "Total capital (£)",
        min_value=1_000,
        value=100_000,
        step=5_000,
        key="pm_capital",
    )
    rebal_freq = st.sidebar.selectbox(
        "Rebalancing frequency",
        ["Daily", "Weekly", "Monthly"],
        index=2,
        key="rebal_freq",
        help="Intended rebalance cadence (used for display; actual recompute runs on demand).",
    )

    if not portfolio_pairs_pm:
        st.info("Select at least one pair in the sidebar for your portfolio.")
        st.stop()

    unique_pm = sorted({t for pair in portfolio_pairs_pm for t in pair})
    # Recent history: e.g. last 2 years for hedge ratio & MPT
    end_pm = date.today()
    start_pm = end_pm - timedelta(days=730)

    @st.cache_data(show_spinner="Fetching recent price data from LSEG…")
    def load_prices_pm(tickers: tuple, start: str, end: str) -> pd.DataFrame:
        return get_close_prices(list(tickers), start=start, end=end)

    recent_prices = load_prices_pm(tuple(unique_pm), str(start_pm), str(end_pm))

    screening_pm = screen_pairs(recent_prices, portfolio_pairs_pm)
    coint_pm = screening_pm[screening_pm["is_cointegrated"]]

    if coint_pm.empty:
        st.warning("No cointegrated pairs in the selected portfolio over the recent period. Adjust pairs or date range.")
        st.dataframe(screening_pm, use_container_width=True)
        st.stop()

    # Recompute hedge ratios (from screening) and MPT weights (from recent spread returns)
    returns_pm = build_pair_returns(recent_prices, coint_pm)
    if returns_pm.shape[1] < 2:
        st.info("Only one cointegrated pair — showing single-pair stats. Target weight = 100%.")
        mv_pm = None
        weights_pm = np.array([1.0])
    else:
        mv_pm = mean_variance_weights(returns_pm)
        weights_pm = mv_pm["max_sharpe_weights"]

    st.subheader("Target weights (recomputed from recent history)")
    st.caption(f"Based on data from {start_pm} to {end_pm}. Rebalancing frequency: {rebal_freq}.")

    alloc_rows = []
    for i, (_, row) in enumerate(coint_pm.iterrows()):
        label = f"{row['y']} / {row['x']}"
        w = float(weights_pm[i]) if i < len(weights_pm) else 0.0
        alloc_rows.append({
            "Pair": label,
            "Target weight": f"{w:.2%}",
            "Capital (£)": f"£{capital_pm * w:,.0f}",
        })
    st.dataframe(pd.DataFrame(alloc_rows), use_container_width=True, hide_index=True)

    if mv_pm is not None:
        st.subheader("Impact on metrics (target portfolio on recent data)")
        bench_ret_pm = returns_pm.mean(axis=1)
        port_ret_pm = (returns_pm * weights_pm).sum(axis=1)
        mask_pm = port_ret_pm.notna() & bench_ret_pm.notna()
        if mask_pm.sum() >= 2:
            vol_red_pm = compute_volatility_reduction(port_ret_pm[mask_pm], bench_ret_pm[mask_pm])
            ann_vol_pm = port_ret_pm[mask_pm].std(ddof=1) * np.sqrt(252)
            total_ret_pm = (1 + port_ret_pm[mask_pm]).prod() - 1
            st.metric("Volatility reduction vs equal-weight", f"{vol_red_pm:.1%}")
            c1, c2 = st.columns(2)
            c1.metric("Ann. volatility (target)", f"{ann_vol_pm:.2%}")
            c2.metric("Total return (period)", f"{total_ret_pm:.2%}")

    st.subheader("Current z-scores & signals")
    zscore_dict_pm = {}
    signal_rows_pm = []
    entry_z_pm = 2.0
    lookback_pm = 60
    for _, row in coint_pm.iterrows():
        label = f"{row['y']} / {row['x']}"
        spr = compute_spread(
            recent_prices[row["y"]], recent_prices[row["x"]],
            row["hedge_ratio"], row["intercept"],
        )
        zs = compute_zscore(spr, window=lookback_pm)
        zscore_dict_pm[label] = zs
        current_z = zs.iloc[-1] if not np.isnan(zs.iloc[-1]) else 0.0
        if current_z <= -entry_z_pm:
            signal = "BUY SPREAD (Long Y, Short X)"
        elif current_z >= entry_z_pm:
            signal = "SELL SPREAD (Short Y, Long X)"
        else:
            signal = "HOLD / FLAT"
        signal_rows_pm.append({"Pair": label, "Current Z": f"{current_z:.2f}", "Signal": signal})
    st.dataframe(pd.DataFrame(signal_rows_pm), use_container_width=True, hide_index=True)
    st.plotly_chart(plot_zscore_heatmap(zscore_dict_pm), use_container_width=True)
