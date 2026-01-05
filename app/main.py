import streamlit as st

from .data_loader import (
    load_raw_data,
    validate_schema,
    REQUIRED_PTS_COLS,
    REQUIRED_ODDS_COLS,
    canonicalize_odds,
)
from .model import build_model_cached
from .charts import unit_bar_chart


def run_app():
    st.title("Big Burger Bet 2026")

    # ---------------------------
    # Load raw data + validate
    # ---------------------------
    pts_df, odds_df = load_raw_data()

    pts_missing = validate_schema(pts_df, REQUIRED_PTS_COLS)
    odds_missing = validate_schema(odds_df, REQUIRED_ODDS_COLS)
    if pts_missing or odds_missing:
        st.error("Schema validation failed.")
        if pts_missing:
            st.write(f"pts_2025.csv missing: {pts_missing}")
        if odds_missing:
            st.write(f"playoff_odds.csv missing: {odds_missing}")
        st.stop()

    # ---------------------------
    # Panel height (aligned across columns)
    # ---------------------------
    visible_rows = 14
    row_height = 35
    header_height = 38
    panel_height = header_height + row_height * visible_rows

    # ---------------------------
    # Dashboard Layout (3 columns)
    # ---------------------------
    left, mid, right = st.columns([1.5, 1.8, 1.2], gap="small")

    # ---------------------------
    # Odds Source selector (RIGHT column, above table)
    # ---------------------------
    with right:
        odds_c = canonicalize_odds(odds_df)
        odds_sources = sorted(odds_c["Odds Source"].dropna().unique().tolist())
        if not odds_sources:
            st.error("No 'Odds Source' values found in playoff_odds data.")
            st.stop()

        default_index = odds_sources.index("Fanduel") if "Fanduel" in odds_sources else 0

        selected_source = st.selectbox(
            "Odds Source",
            odds_sources,
            index=default_index,
        )


    # ---------------------------
    # Build model (all derived tables + metrics)
    # ---------------------------
    m, rank_table, team_display, _, _ = build_model_cached(pts_df, odds_df, selected_source)

    # ---------------------------
    # LEFT: Ranked table + filters
    # ---------------------------
    with left:
        all_teams = sorted(rank_table["team"].dropna().unique().tolist())
        all_positions = ["QB", "RB", "WR", "TE", "K", "OTH"]
        present_positions = [p for p in all_positions if p in set(rank_table["position"].unique())]

        f_pos, f_team, f_base = st.columns([1, 1, 2])

        with f_base:
            baseline_label_map = {"Average": "avg", "Minimum": "min"}
            baseline_label = st.selectbox(
                "Compare Exp Pts vs Position:",
                list(baseline_label_map.keys()),
                index=0,
            )
            baseline = baseline_label_map[baseline_label]

        with f_pos:
            position_filter = st.multiselect("Position", options=present_positions, default=[])

        with f_team:
            team_filter = st.multiselect("Team", options=all_teams, default=[])

        value_col = (
            "value_vs_position_avg_expected_points"
            if baseline == "avg"
            else "value_vs_position_min_expected_points"
        )

        # Global overall rank based on baseline (does NOT change with filters)
        base = rank_table.copy()
        base["overall_rank"] = base[value_col].rank(method="min", ascending=False).astype(int)
        base = base.sort_values(["overall_rank", "position", "team"]).reset_index(drop=True)

        # Filters only hide rows; ranks remain global
        filtered = base
        if team_filter:
            filtered = filtered[filtered["team"].isin(team_filter)]
        if position_filter:
            filtered = filtered[filtered["position"].isin(position_filter)]

        value_label = "Exp Pts vs Pos Avg" if baseline == "avg" else "Exp Pts vs Pos Min"

        table_display = filtered[
            [
                "overall_rank",
                "unit_label",
                "position_rank",
                "reg_ppg",
                "ppg_rank",
                "expected_points",
                value_col,
            ]
        ].rename(columns={
            "overall_rank": "Overall Rank",
            "unit_label": "Unit",
            "position_rank": "Position Rank",
            "reg_ppg": "PPG",
            "ppg_rank": "PPG Rank",
            "expected_points": "Exp Pts",
            value_col: value_label,
        })

        st.dataframe(
            table_display,
            width="stretch",
            height=panel_height,
            hide_index=True,
        )

    # ---------------------------
    # MID: Chart
    # ---------------------------
    with mid:
        pos_order = ["QB", "RB", "WR", "TE", "K", "OTH"]
        positions = [p for p in pos_order if p in set(m["position"].unique())]

        c_pos, c_metric = st.columns([1, 1])
        with c_pos:
            selected_position = st.selectbox("Position", positions)
        with c_metric:
            metric_label_map = {
                "Expected Playoff Points": "expected_points",
                "Regular Season PPG": "reg_ppg",
            }
            metric_label = st.selectbox("Display Metric", list(metric_label_map.keys()), index=0)
            metric = metric_label_map[metric_label]

        chart_df = m[m["position"] == selected_position].copy()

        fig = unit_bar_chart(
            chart_df,
            metric=metric,
            metric_label=metric_label,
            height=panel_height,
        )
        st.plotly_chart(fig, width="stretch")

    # ---------------------------
    # RIGHT: Odds Source selector already shown + table
    # ---------------------------
    with right:
        st.dataframe(
            team_display,
            width="stretch",
            height=panel_height,
            hide_index=True,
        )
