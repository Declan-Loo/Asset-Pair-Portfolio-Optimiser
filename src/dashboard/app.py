"""
Pairs-Trading Portfolio Optimiser — Streamlit Dashboard

  Input:  portfolio (pair selection + date range + capital).
  Output: cointegration, spread & z-scores, estimated expected returns
          (spread-based vs traditional), backtest metrics with benchmarks
          (buy-and-hold, risk-free, S&P 500, equal-weight all pairs),
          and portfolio optimisation comparison.

Launch:  streamlit run src/dashboard/app.py
"""

import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.data.refinitiv_client import get_close_prices, open_session
from src.data.yfinance_sp500 import get_sp500_prices
from src.modelling.cointegration import screen_pairs, engle_granger_test
from src.modelling.spread_analysis import (
    compute_spread,
    compute_zscore,
    compute_half_life,
    compute_hurst_exponent,
    spread_summary,
)
from src.modelling.optimiser import (
    optimise_portfolio,
    compute_efficient_frontier,
    rolling_hedge_ratio,
)
from src.modelling.return_estimation import (
    build_spread_return_matrix,
    historical_mean_return,
    ewma_mean_return,
    build_ou_implied_returns,
    sample_covariance,
    shrinkage_covariance,
)
from src.modelling.config import (
    CANDIDATE_PAIRS,
    TRAIN_START,
    TRAIN_END,
    TEST_START,
    TEST_END,
)
from src.backtesting.engine import PairsBacktestEngine, BacktestConfig
from src.backtesting.metrics import compute_volatility_reduction
from src.backtesting.benchmarks import (
    build_all_benchmarks,
    compute_benchmark_metrics,
    historical_mpt_returns,
)
from src.dashboard.components import (
    plot_spread_with_bands,
    plot_cointegration_results,
    plot_cumulative_returns_multi,
    plot_efficient_frontier,
    plot_position_timeline,
    format_metrics_table,
    plot_return_estimates_comparison,
    plot_rolling_return_estimate,
    plot_drawdown,
    plot_returns_distribution,
    plot_rolling_sharpe,
)

st.set_page_config(
    page_title="Pairs-Trading Portfolio Optimiser",
    layout="wide",
)

# Extra sidebar button styling: dark mode and newer Streamlit builds often apply
# theme CSS after this block, so .streamlit/config.toml primaryColor is the main fix.
st.markdown(
    """
    <style>
    /* High-specificity: sidebar primary / Execute button — light & dark */
    section[data-testid="stSidebar"] button[kind="primary"],
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"],
    div[data-testid="stSidebar"] button[kind="primary"],
    div[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
        background-color: #22c55e !important;
        background: #22c55e !important;
        border-color: #16a34a !important;
        color: #ffffff !important;
        --primary-color: #22c55e !important;
    }
    section[data-testid="stSidebar"] button[kind="primary"]:hover,
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover,
    div[data-testid="stSidebar"] button[kind="primary"]:hover,
    div[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover {
        background-color: #16a34a !important;
        background: #16a34a !important;
        border-color: #15803d !important;
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] button[kind="primary"]:focus-visible,
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:focus-visible {
        box-shadow: 0 0 0 0.2rem rgba(34, 197, 94, 0.45) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Open LSEG once per Streamlit process as soon as the app loads. Subsequent
# reruns are no-ops (refinitiv_client.open_session is idempotent). Fails fast
# if Workspace / credentials are unavailable instead of failing on first fetch.
try:
    open_session()
except Exception as exc:
    st.error(f"LSEG session could not be started: {exc}")
    st.caption("Ensure LSEG Workspace / Eikon is running and API access is configured.")
    st.stop()

st.title("Pairs-Trading Portfolio Optimiser")
st.caption(
    "Estimating expected returns by predicting the spread between "
    "cointegrated asset pairs to optimise a portfolio."
)

# ---------------------------------------------------------------------------
# Sidebar — Portfolio input
# ---------------------------------------------------------------------------
st.sidebar.header("Portfolio")

pair_input_mode = st.sidebar.radio(
    "Pair input mode",
    ["Preset pairs", "Custom tickers"],
    horizontal=True,
    help="Use preset candidate pairs or enter your own LSEG ticker symbols.",
)

if pair_input_mode == "Preset pairs":
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
else:
    st.sidebar.caption(
        "Enter LSEG Workspace ticker symbols (RICs). "
        "Define pairs as comma-separated lines: `TICKER_Y, TICKER_X`"
    )
    custom_input = st.sidebar.text_area(
        "Custom pairs (one per line)",
        placeholder="AAPL.O, MSFT.O\nGOOGL.O, META.O\nXOM.N, CVX.N",
        height=120,
    )
    portfolio_pairs = []
    for line in custom_input.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [t.strip() for t in line.split(",")]
        if len(parts) == 2 and parts[0] and parts[1]:
            portfolio_pairs.append((parts[0], parts[1]))
    if portfolio_pairs:
        st.sidebar.success(f"{len(portfolio_pairs)} pair(s) defined.")
    elif custom_input.strip():
        st.sidebar.error("Invalid format. Use: TICKER_Y, TICKER_X (one pair per line).")

st.sidebar.subheader("Date range")
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
initial_capital = st.sidebar.number_input("Initial capital", min_value=1_000, value=100_000, step=5_000)
rf_annual = st.sidebar.number_input("Risk-free rate (annual)", value=0.02, min_value=0.0, max_value=0.2, step=0.005, format="%.3f")
l2_reg = st.sidebar.slider(
    "L2 regularisation (weight penalty)", 0.0, 0.20, 0.0, 0.01,
    help="Ridge penalty on portfolio weights. Pulls weights toward equal-weight "
         "to reduce concentration. 0 = standard Markowitz, typical range 0.01–0.10.",
)

include_sp500 = st.sidebar.checkbox("Include S&P 500 benchmark", value=True, help="Fetch S&P 500 via yfinance for the test date range.")

if not portfolio_pairs:
    st.warning("Select at least one pair in the sidebar.")
    st.stop()

st.sidebar.markdown("---")
if st.sidebar.button("▶ Execute", type="primary", width="stretch", key="execute_analysis"):
    st.session_state["executed"] = True

if not st.session_state.get("executed", False):
    st.info("Configure your portfolio in the sidebar, then click **▶ Execute** to run the analysis.")
    st.stop()

@st.cache_data(show_spinner=False)
def load_prices(tickers: tuple, start: str, end: str) -> pd.DataFrame:
    return get_close_prices(list(tickers), start=start, end=end)

@st.cache_data(show_spinner=False)
def run_screen_pairs(prices: pd.DataFrame, pairs: tuple) -> pd.DataFrame:
    return screen_pairs(prices, list(pairs))

unique_tickers = sorted({t for pair in portfolio_pairs for t in pair})

with st.status("Running analysis...", expanded=True) as _status:
    st.write(f"Fetching training prices ({train_start} – {train_end}) from LSEG for: {', '.join(unique_tickers)}")
    train_prices = load_prices(tuple(unique_tickers), str(train_start), str(train_end))

    st.write(f"Fetching test prices ({test_start} – {test_end}) from LSEG...")
    test_prices = load_prices(tuple(unique_tickers), str(test_start), str(test_end))

    sp500_prices = None
    if include_sp500:
        st.write("Fetching S&P 500 benchmark prices (yfinance)...")
        sp500_prices = get_sp500_prices(str(test_start), str(test_end))
        if sp500_prices.empty:
            st.warning("S&P 500 data unavailable — skipping benchmark.")
            sp500_prices = None

    st.write(
        f"Running Engle-Granger cointegration test (AEG / MacKinnon critical values) "
        f"on {len(portfolio_pairs)} candidate pair(s)..."
    )
    screening_df = run_screen_pairs(train_prices, tuple(map(tuple, portfolio_pairs)))
    coint_pairs = screening_df[screening_df["is_cointegrated"]]

    n_coint = len(coint_pairs)
    st.write(
        f"Cointegration screening complete — "
        f"**{n_coint} of {len(portfolio_pairs)} pair(s) cointegrated** at the 5% level."
    )
    _status.update(label="Analysis complete.", state="complete", expanded=False)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_coint, tab_spread, tab_returns, tab_bt, tab_compare, tab_opt = st.tabs([
    "Cointegration",
    "Spread & Z-Scores",
    "Return Estimation",
    "Backtest Results",
    "Strategy vs Benchmarks",
    "Portfolio Optimisation",
])

# ===== TAB 1: Cointegration =====
with tab_coint:
    st.header("Cointegration screening (training period)")
    st.dataframe(
        screening_df.style.format({
            "hedge_ratio": "{:.4f}",
            "intercept": "{:.4f}",
            "adf_stat": "{:.4f}",
            "p_value": "{:.6f}",
        }, na_rep="N/A"),
        width="stretch",
    )
    st.plotly_chart(plot_cointegration_results(screening_df), width="stretch", key="coint_bar")
    st.info(f"{len(coint_pairs)} of {len(portfolio_pairs)} pairs are cointegrated at the 5% level.")

# ===== TAB 2: Spread & Z-Scores =====
with tab_spread:
    st.header("Spread & Z-Scores")
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
        st.caption(f"Rolling B = {hr_latest:.4f}, a = {int_latest:.4f}  |  Static B = {hr_static:.4f}, a = {intercept_static:.4f}")
        import plotly.graph_objects as go
        hr_fig = go.Figure()
        hr_fig.add_trace(go.Scatter(x=roll_df.index, y=roll_df["hedge_ratio"], name="Rolling B", line=dict(color="#636EFA")))
        hr_fig.add_hline(y=hr_static, line=dict(color="red", dash="dash"), annotation_text=f"Static B = {hr_static:.4f}")
        hr_fig.update_layout(yaxis_title="Hedge ratio (B)", height=280, margin=dict(t=20, b=20))
        st.plotly_chart(hr_fig, width="stretch", key="rolling_hr")
        hr, intercept = hr_latest, int_latest
    else:
        hr, intercept = hr_static, intercept_static
    spread = compute_spread(train_prices[sel_y], train_prices[sel_x], hr, intercept)
    zscore = compute_zscore(spread, window=lookback)
    st.plotly_chart(
        plot_spread_with_bands(spread, zscore, entry_z=entry_z, exit_z=exit_z),
        width="stretch", key="spread_bands",
    )
    summary = spread_summary(train_prices[sel_y], train_prices[sel_x], hr, intercept, window=lookback)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Half-life (days)", f"{summary['half_life']:.1f}")
    c2.metric("Hurst exponent", f"{summary['hurst']:.3f}")
    c3.metric("ADF p-value", f"{summary['adf_pvalue']:.4f}")
    c4.metric("Current z-score", f"{summary['current_zscore']:.2f}")

# ===== TAB 3: Return Estimation (core FYP output) =====
with tab_returns:
    st.header("Estimated Expected Returns")
    st.caption(
        "Comparing return estimates derived from spread predictions (OU model) "
        "against traditional historical mean approaches — the core research question."
    )

    if coint_pairs.empty:
        st.warning("No cointegrated pairs found — cannot estimate returns.")
    else:
        # Build spread returns for training period
        train_spread_rets = build_spread_return_matrix(train_prices, coint_pairs)
        train_asset_rets = train_prices[
            list(dict.fromkeys(coint_pairs["y"].tolist() + coint_pairs["x"].tolist()))
        ].pct_change().dropna(how="all")

        # ------------------------------------------------------------------
        # 1. Spread-based return estimates (all three methods)
        # ------------------------------------------------------------------
        st.subheader("1. Spread-based return estimates (training period)")

        ou_mu = build_ou_implied_returns(
            train_prices, coint_pairs, window=lookback, annualise=True,
        )
        hist_mu = historical_mean_return(train_spread_rets, annualise=True)
        ewma_mu = ewma_mean_return(train_spread_rets, span=lookback, annualise=True)

        # Friendly pair labels
        pair_labels = [f"{r['y']} / {r['x']}" for _, r in coint_pairs.iterrows()]
        pair_keys = [f"{r['y']}_vs_{r['x']}" for _, r in coint_pairs.iterrows()]

        estimates_df = pd.DataFrame({
            "OU-implied (spread prediction)": ou_mu.reindex(pair_keys).values,
            "Historical mean": hist_mu.reindex(pair_keys).values,
            "EWMA": ewma_mu.reindex(pair_keys).values,
        }, index=pair_labels)

        st.plotly_chart(
            plot_return_estimates_comparison(estimates_df),
            width="stretch", key="return_estimates_bar",
        )
        st.dataframe(
            estimates_df.style.format("{:.2%}"),
            width="stretch",
        )

        # ------------------------------------------------------------------
        # 2. Detailed per-pair statistics
        # ------------------------------------------------------------------
        st.subheader("2. Per-pair spread statistics")

        detail_rows = []
        for _, row in coint_pairs.iterrows():
            label = f"{row['y']} / {row['x']}"
            key = f"{row['y']}_vs_{row['x']}"
            sp = compute_spread(
                train_prices[row["y"]], train_prices[row["x"]],
                row["hedge_ratio"], row.get("intercept", 0.0),
            )
            hl = compute_half_life(sp)
            hurst = compute_hurst_exponent(sp)
            zs = compute_zscore(sp, window=lookback)
            detail_rows.append({
                "Pair": label,
                "Hedge ratio": row["hedge_ratio"],
                "Half-life (days)": hl,
                "Hurst exponent": hurst,
                "Current z-score": float(zs.iloc[-1]) if not np.isnan(zs.iloc[-1]) else np.nan,
                "OU E[r] (ann.)": ou_mu.get(key, 0.0),
                "Hist. E[r] (ann.)": hist_mu.get(key, 0.0),
            })
        detail_df = pd.DataFrame(detail_rows).set_index("Pair")
        st.dataframe(
            detail_df.style
            .format("{:.4f}", subset=["Hedge ratio"], na_rep="N/A")
            .format("{:.1f}", subset=["Half-life (days)"], na_rep="N/A")
            .format("{:.3f}", subset=["Hurst exponent", "Current z-score"], na_rep="N/A")
            .format("{:.2%}", subset=["OU E[r] (ann.)", "Hist. E[r] (ann.)"], na_rep="N/A"),
            width="stretch",
        )

        st.caption(
            "Half-life < 30 days and Hurst < 0.5 indicate strong mean reversion. "
            "The OU model exploits this to predict expected returns from the current "
            "spread deviation."
        )

        # ------------------------------------------------------------------
        # 3. Spread-based vs Traditional asset-level estimates
        # ------------------------------------------------------------------
        st.subheader("3. Spread-based vs Traditional (asset-level) estimates")
        st.caption(
            "Traditional MPT uses historical mean returns of individual assets. "
            "Spread-based MPT uses OU-implied returns from cointegrated pair spreads."
        )

        asset_hist_mu = historical_mean_return(train_asset_rets, annualise=True)

        col_sp, col_tr = st.columns(2)
        with col_sp:
            st.markdown("**Spread-based estimates (OU-implied)**")
            sp_df = pd.DataFrame({
                "Pair": pair_labels,
                "E[r] (ann.)": ou_mu.reindex(pair_keys).values,
            })
            st.dataframe(
                sp_df.style.format("{:.2%}", subset=["E[r] (ann.)"]),
                hide_index=True, width="stretch",
            )
        with col_tr:
            st.markdown("**Traditional estimates (historical mean)**")
            tr_df = pd.DataFrame({
                "Asset": asset_hist_mu.index,
                "E[r] (ann.)": asset_hist_mu.values,
            })
            st.dataframe(
                tr_df.style.format("{:.2%}", subset=["E[r] (ann.)"]),
                hide_index=True, width="stretch",
            )

        # ------------------------------------------------------------------
        # 4. Rolling stability of return estimates
        # ------------------------------------------------------------------
        st.subheader("4. Rolling return estimate stability")
        st.caption(
            "Shows how noisy the return estimate is over time. "
            "More stable estimates lead to more reliable portfolio allocations."
        )

        pair_sel_ret = st.selectbox(
            "Select pair to examine", pair_labels, key="ret_stability_pair",
        )
        sel_key = pair_keys[pair_labels.index(pair_sel_ret)]

        if sel_key in train_spread_rets.columns:
            st.plotly_chart(
                plot_rolling_return_estimate(
                    train_spread_rets[sel_key], window=lookback,
                    pair_label=pair_sel_ret,
                ),
                width="stretch", key="rolling_return_est",
            )

        # ------------------------------------------------------------------
        # 5. Covariance comparison
        # ------------------------------------------------------------------
        st.subheader("5. Covariance matrix (spread returns)")

        cov_method = st.radio(
            "Covariance estimator",
            ["Sample", "Ledoit-Wolf shrinkage"],
            horizontal=True, key="cov_method",
        )
        if cov_method == "Ledoit-Wolf shrinkage":
            cov_mat = shrinkage_covariance(train_spread_rets.dropna(), annualise=True)
        else:
            cov_mat = sample_covariance(train_spread_rets.dropna(), annualise=True)

        cov_display = cov_mat.copy()
        cov_display.index = pair_labels
        cov_display.columns = pair_labels
        st.dataframe(cov_display.style.format("{:.6f}"), width="stretch")

# ===== TAB 4: Backtest Results (enhanced) =====
with tab_bt:
    st.header("Backtest results (test period)")
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

        # Metrics
        st.subheader("Strategy performance")
        st.dataframe(format_metrics_table(result.metrics), width="stretch", hide_index=True)

        # Benchmarks
        benchmarks = build_all_benchmarks(
            test_prices, coint_pairs, rf_annual=rf_annual, market_prices=sp500_prices,
        )
        b_cols = [k for k in ["buy_hold_pair", "risk_free", "equal_weight_pairs", "sp500"] if k in benchmarks]

        st.subheader("Benchmark comparison")
        bench_metrics = []
        for name in b_cols:
            ret = benchmarks[name]
            m = compute_benchmark_metrics(ret, rf_annual=rf_annual, benchmark_returns=benchmarks.get("buy_hold_pair"))
            m["name"] = name
            bench_metrics.append(m)
        bench_df = pd.DataFrame(bench_metrics).set_index("name")
        bench_df = bench_df[["sharpe_ratio", "max_drawdown", "total_return", "annualised_volatility", "volatility_reduction"]]
        bench_df.columns = ["Sharpe", "Max DD", "Total return", "Ann. vol", "Vol reduction vs B&H"]
        st.dataframe(
            bench_df.style.format("{:.2f}", subset=["Sharpe"], na_rep="N/A")
            .format("{:.2%}", subset=["Max DD", "Total return", "Ann. vol", "Vol reduction vs B&H"], na_rep="N/A"),
            width="stretch",
        )

        # Cumulative returns
        st.subheader("Cumulative returns")
        series_for_chart = {"Strategy (spread-based)": result.daily_returns}
        label_map = {"risk_free": "Risk-free", "buy_hold_pair": "B&H (pair)", "equal_weight_pairs": "Equal-weight pairs", "sp500": "S&P 500"}
        for k in b_cols:
            series_for_chart[label_map.get(k, k)] = benchmarks[k]
        st.plotly_chart(plot_cumulative_returns_multi(series_for_chart), width="stretch", key="bt_cumret")

        # Drawdown
        st.subheader("Drawdown")
        st.plotly_chart(plot_drawdown(result.daily_returns), width="stretch", key="bt_drawdown")

        # Rolling Sharpe
        st.subheader("Rolling Sharpe ratio")
        st.plotly_chart(
            plot_rolling_sharpe(result.daily_returns, window=lookback, rf_annual=rf_annual),
            width="stretch", key="bt_rolling_sharpe",
        )

        # Returns distribution
        st.subheader("Daily returns distribution")
        dist_series = {"Strategy": result.daily_returns}
        if "buy_hold_pair" in benchmarks:
            dist_series["B&H (pair)"] = benchmarks["buy_hold_pair"]
        st.plotly_chart(plot_returns_distribution(dist_series), width="stretch", key="bt_ret_dist")

        # Position timeline + trade log
        st.subheader("Position timeline")
        st.plotly_chart(plot_position_timeline(result.positions["position"]), width="stretch", key="bt_positions")
        st.subheader("Trade log")
        if not result.trades.empty:
            st.dataframe(result.trades, width="stretch")
        else:
            st.info("No trades in the test period.")

# ===== TAB 5: Strategy vs Benchmarks =====
with tab_compare:
    st.header("Combined portfolio: Spread-based vs Historical MPT vs Benchmarks")
    st.caption(
        "Full multi-pair portfolio comparison — spread-based equal-weight allocation across all "
        "cointegrated pairs vs traditional Markowitz (max-Sharpe, IS-estimated) vs passive benchmarks."
    )
    if coint_pairs.empty:
        st.warning("No cointegrated pairs.")
    else:
        # Spread-based: equal-weight across ALL cointegrated pair spreads
        from src.backtesting.benchmarks import equal_weight_pairs_returns
        strategy_ret = equal_weight_pairs_returns(test_prices, coint_pairs)

        # Historical MPT: max-Sharpe weights estimated on ALL cointegrated pair tickers using IS data
        all_tickers = list(dict.fromkeys(coint_pairs["y"].tolist() + coint_pairs["x"].tolist()))
        train_all = train_prices[all_tickers].copy()
        test_all = test_prices[all_tickers].copy()
        mpt_ret = historical_mpt_returns(train_all, test_all, rf_annual=rf_annual)

        # Benchmarks
        benchmarks_c = build_all_benchmarks(test_prices, coint_pairs, rf_annual=rf_annual, market_prices=sp500_prices)

        # Metrics table
        def row_metrics(name: str, ret: pd.Series, bench_bh: pd.Series | None = None) -> dict:
            m = compute_benchmark_metrics(ret, rf_annual=rf_annual, benchmark_returns=bench_bh)
            return {"Strategy": name, **m}

        bh_ret = benchmarks_c.get("buy_hold_pair")
        rows = [
            row_metrics("Spread-based (equal-weight)", strategy_ret, bh_ret),
            row_metrics("Historical MPT (max-Sharpe)", mpt_ret, bh_ret),
        ]
        for bname, bret in benchmarks_c.items():
            label = {"risk_free": "Risk-free", "buy_hold_pair": "B&H (pair)", "equal_weight_pairs": "Equal-weight pairs", "sp500": "S&P 500"}.get(bname, bname)
            rows.append(row_metrics(label, bret, bh_ret))
        compare_df = pd.DataFrame(rows).set_index("Strategy")
        compare_df = compare_df[["sharpe_ratio", "max_drawdown", "total_return", "annualised_volatility", "volatility_reduction"]]
        compare_df.columns = ["Sharpe", "Max DD", "Total return", "Ann. vol", "Vol reduction vs B&H"]
        st.dataframe(
            compare_df.style.format("{:.2f}", subset=["Sharpe"], na_rep="N/A")
            .format("{:.2%}", subset=["Max DD", "Total return", "Ann. vol", "Vol reduction vs B&H"], na_rep="N/A"),
            width="stretch",
        )

        st.subheader("Cumulative returns comparison")
        chart_series = {
            "Spread-based (equal-weight)": strategy_ret,
            "Historical MPT": mpt_ret,
        }
        for bname, bret in benchmarks_c.items():
            label = {"risk_free": "Risk-free", "buy_hold_pair": "B&H (pair)", "equal_weight_pairs": "Equal-weight pairs", "sp500": "S&P 500"}.get(bname, bname)
            chart_series[label] = bret
        st.plotly_chart(plot_cumulative_returns_multi(chart_series), width="stretch", key="cmp_cumret")

        # Drawdown comparison
        st.subheader("Drawdown comparison")
        dd_col1, dd_col2 = st.columns(2)
        with dd_col1:
            st.markdown("**Spread-based (equal-weight)**")
            st.plotly_chart(plot_drawdown(strategy_ret), width="stretch", key="cmp_dd_spread")
        with dd_col2:
            st.markdown("**Historical MPT**")
            st.plotly_chart(plot_drawdown(mpt_ret), width="stretch", key="cmp_dd_mpt")

        # Bootstrap confidence intervals
        st.subheader("Bootstrap confidence intervals for Sharpe ratio")
        st.caption(
            "95% confidence intervals derived from 10,000 bootstrap resamples (with replacement) "
            "of daily returns. Wide intervals reflect the short OOS window (~501 trading days)."
        )
        n_boot = 10_000
        rng = np.random.default_rng(42)

        def bootstrap_sharpe(returns: pd.Series, n: int, rf: float) -> tuple[float, float]:
            daily_rf = rf / 252
            excess = returns.values - daily_rf
            T = len(excess)
            idx = rng.integers(0, T, size=(n, T))
            samples = excess[idx]
            boot_sharpes = samples.mean(axis=1) / samples.std(axis=1, ddof=1) * np.sqrt(252)
            return float(np.percentile(boot_sharpes, 2.5)), float(np.percentile(boot_sharpes, 97.5))

        boot_rows = []
        all_strats = {"Spread-based (equal-weight)": strategy_ret, "Historical MPT": mpt_ret}
        for bname, bret in benchmarks_c.items():
            label = {"risk_free": "Risk-free", "buy_hold_pair": "B&H (pair)", "equal_weight_pairs": "Equal-weight pairs", "sp500": "S&P 500"}.get(bname, bname)
            if label != "Risk-free":
                all_strats[label] = bret

        for strat_name, ret in all_strats.items():
            daily_rf = rf_annual / 252
            sr = (ret.mean() - daily_rf) / ret.std(ddof=1) * np.sqrt(252)
            lo, hi = bootstrap_sharpe(ret, n_boot, rf_annual)
            boot_rows.append({
                "Strategy": strat_name,
                "Sharpe": sr,
                "95% CI Lower": lo,
                "95% CI Upper": hi,
                "Sig. > 0": "Yes" if lo > 0 else "No",
            })

        boot_df = pd.DataFrame(boot_rows).set_index("Strategy")
        st.dataframe(
            boot_df.style.format("{:.3f}", subset=["Sharpe", "95% CI Lower", "95% CI Upper"], na_rep="N/A"),
            width="stretch",
        )
        st.caption(
            "No strategy achieves a lower bound strictly above zero, reflecting high Sharpe "
            "estimation variance over a ~2-year OOS window."
        )

# ===== TAB 6: Portfolio Optimisation =====
with tab_opt:
    st.header("Portfolio Optimisation: Spread-Based vs Traditional MPT")
    st.caption(
        "Compares portfolio weights derived from spread-based return estimates "
        "(OU-implied) against traditional historical mean returns."
    )
    if coint_pairs.empty:
        st.warning("No cointegrated pairs — cannot optimise.")
    else:
        # Spread return matrices: IS (train) for traditional MPT, OOS (test) for spread-based
        train_spread_rets_opt = build_spread_return_matrix(train_prices, coint_pairs)
        spread_returns_df = build_spread_return_matrix(test_prices, coint_pairs)

        if spread_returns_df.shape[1] < 2:
            st.info("Need at least 2 cointegrated pairs for the frontier.")
            st.dataframe(spread_returns_df.describe(), width="stretch")
        else:
            # --- Return estimation method selector ---
            ret_method = st.radio(
                "Return estimation method (for spread-based MPT)",
                ["OU-implied (spread prediction)", "Historical mean"],
                horizontal=True,
            )

            if ret_method == "OU-implied (spread prediction)":
                spread_mu = build_ou_implied_returns(
                    test_prices, coint_pairs, window=lookback, annualise=False,
                )
                spread_mu = spread_mu.reindex(spread_returns_df.columns).fillna(0.0)
                custom_mu = spread_mu.values
            else:
                # Historical mean of OOS spread returns
                custom_mu = historical_mean_return(spread_returns_df, annualise=False).values

            # Traditional MPT: estimated entirely on IS training data (historical Markowitz)
            trad_mu = historical_mean_return(train_spread_rets_opt, annualise=False).values
            mv_traditional = optimise_portfolio(
                train_spread_rets_opt, expected_returns=trad_mu, rf_annual=rf_annual,
                l2_reg=l2_reg,
            )

            # --- Spread-based MPT ---
            st.subheader("Spread-based efficient frontier")
            mv_spread = optimise_portfolio(
                spread_returns_df, expected_returns=custom_mu, rf_annual=rf_annual,
                l2_reg=l2_reg,
            )
            frontier_spread = compute_efficient_frontier(
                spread_returns_df, expected_returns=custom_mu, rf_annual=rf_annual,
                l2_reg=l2_reg,
            )
            max_sharpe_pt = (mv_spread["max_sharpe_vol"], mv_spread["max_sharpe_return"])
            min_var_pt = (mv_spread["min_var_vol"], mv_spread["min_var_return"])
            st.plotly_chart(
                plot_efficient_frontier(frontier_spread, max_sharpe_pt, min_var_pt),
                width="stretch", key="opt_frontier",
            )

            # Volatility reduction
            bench_ret = spread_returns_df.mean(axis=1)
            port_ret_sharpe = (spread_returns_df * mv_spread["max_sharpe_weights"]).sum(axis=1)
            port_ret_minvar = (spread_returns_df * mv_spread["min_var_weights"]).sum(axis=1)
            mask = port_ret_sharpe.notna() & bench_ret.notna()
            vol_red_sharpe = compute_volatility_reduction(port_ret_sharpe[mask], bench_ret[mask])
            vol_red_minvar = compute_volatility_reduction(port_ret_minvar[mask], bench_ret[mask])
            st.subheader("Portfolio-level volatility reduction")
            col1, col2 = st.columns(2)
            col1.metric("Max-Sharpe vs equal-weight", f"{vol_red_sharpe:.1%}")
            col2.metric("Min-variance vs equal-weight", f"{vol_red_minvar:.1%}")

            # Weights comparison
            st.subheader("Weights: spread-based vs traditional MPT")
            st.caption(
                "Spread-based weights are optimised using OOS spread data with the selected return estimator. "
                "Traditional weights are estimated from in-sample (training) data only — the classic Markowitz approach."
            )

            opt_pair_labels = [c.replace("_vs_", " / ") for c in spread_returns_df.columns]

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Spread-based Max-Sharpe**")
                w_df = pd.DataFrame({"Pair": opt_pair_labels, "Weight": mv_spread["max_sharpe_weights"]})
                w_df["Weight"] = w_df["Weight"].map("{:.2%}".format)
                st.dataframe(w_df, hide_index=True)
            with col_b:
                st.markdown("**Traditional Max-Sharpe (historical mean)**")
                w_df = pd.DataFrame({"Pair": opt_pair_labels, "Weight": mv_traditional["max_sharpe_weights"]})
                w_df["Weight"] = w_df["Weight"].map("{:.2%}".format)
                st.dataframe(w_df, hide_index=True)

            col_c, col_d = st.columns(2)
            with col_c:
                st.markdown("**Spread-based Min-Variance**")
                w_df = pd.DataFrame({"Pair": opt_pair_labels, "Weight": mv_spread["min_var_weights"]})
                w_df["Weight"] = w_df["Weight"].map("{:.2%}".format)
                st.dataframe(w_df, hide_index=True)
            with col_d:
                st.markdown("**Traditional Min-Variance**")
                w_df = pd.DataFrame({"Pair": opt_pair_labels, "Weight": mv_traditional["min_var_weights"]})
                w_df["Weight"] = w_df["Weight"].map("{:.2%}".format)
                st.dataframe(w_df, hide_index=True)

            # Performance summary — OOS (test period) stats for both strategies
            st.subheader("Performance summary (OOS test period)")
            st.caption("Returns and volatility are computed on the out-of-sample test period for all strategies.")

            def _oos_stats(weights: np.ndarray) -> tuple[float, float]:
                """Annualised OOS return and vol by applying IS weights to OOS spread returns."""
                oos_ret = (spread_returns_df.dropna() * weights).sum(axis=1)
                ann_ret = float(oos_ret.mean() * 252)
                ann_vol = float(oos_ret.std(ddof=1) * np.sqrt(252))
                return ann_ret, ann_vol

            def _sharpe(ret, vol):
                return f"{(ret - rf_annual) / vol:.2f}" if vol > 0 else "N/A"

            sp_ms_ret, sp_ms_vol = _oos_stats(mv_spread["max_sharpe_weights"])
            sp_mv_ret, sp_mv_vol = _oos_stats(mv_spread["min_var_weights"])
            tr_ms_ret, tr_ms_vol = _oos_stats(mv_traditional["max_sharpe_weights"])
            tr_mv_ret, tr_mv_vol = _oos_stats(mv_traditional["min_var_weights"])

            summary_rows = [
                {"Portfolio": "Spread-based Max-Sharpe",   "Ann. Return": f"{sp_ms_ret:.2%}", "Ann. Vol": f"{sp_ms_vol:.2%}", "Sharpe": _sharpe(sp_ms_ret, sp_ms_vol)},
                {"Portfolio": "Traditional Max-Sharpe",    "Ann. Return": f"{tr_ms_ret:.2%}", "Ann. Vol": f"{tr_ms_vol:.2%}", "Sharpe": _sharpe(tr_ms_ret, tr_ms_vol)},
                {"Portfolio": "Spread-based Min-Variance", "Ann. Return": f"{sp_mv_ret:.2%}", "Ann. Vol": f"{sp_mv_vol:.2%}", "Sharpe": _sharpe(sp_mv_ret, sp_mv_vol)},
                {"Portfolio": "Traditional Min-Variance",  "Ann. Return": f"{tr_mv_ret:.2%}", "Ann. Vol": f"{tr_mv_vol:.2%}", "Sharpe": _sharpe(tr_mv_ret, tr_mv_vol)},
            ]
            st.dataframe(pd.DataFrame(summary_rows).set_index("Portfolio"), width="stretch")
