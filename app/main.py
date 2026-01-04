import streamlit as st
import pandas as pd
import numpy as np

from .data_loader import (
    load_raw_data,
    validate_schema,
    canonicalize_pts,
    canonicalize_odds,
    REQUIRED_PTS_COLS,
    REQUIRED_ODDS_COLS,
    join_pts_with_odds,
)
from .metrics import (
    add_expected_games,
    add_expected_points,
    add_position_averages,
    add_value_vs_position_avg,
    add_position_mins,
    add_value_vs_position_min,
)
from .charts import unit_bar_chart
from .team_metadata import load_team_metadata


def run_app():
    st.title("Big Burger Bet 2026")

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

    pts_c = canonicalize_pts(pts_df)     # has: team, position, ...
    odds_c = canonicalize_odds(odds_df)  # has: team, Odds Source, Seed, Win WC/Div/Conf

    # ---------------------------
    # Dashboard Layout (3 columns)
    # ---------------------------
    left, mid, right = st.columns([1.5, 1.8, 1.2], gap="small")

    # Odds Source selector (RIGHT column, above table)
    with right:
        odds_sources = sorted(odds_c["Odds Source"].dropna().unique().tolist())
        if not odds_sources:
            st.error("No 'Odds Source' values found in playoff_odds data.")
            st.stop()
        selected_source = st.selectbox("Odds Source", odds_sources, index=0)

    odds_sel = odds_c[odds_c["Odds Source"] == selected_source].copy()

    merged = join_pts_with_odds(pts_c, odds_sel)

    # Compute metrics based on selected odds
    m = add_expected_games(merged)
    m = add_expected_points(m, base_col="reg_ppg")

    # IMPORTANT: these functions must group by POSITION (see metrics.py note below)
    m = add_position_averages(m, value_col="expected_points")
    m = add_value_vs_position_avg(m, value_col="expected_points")
    m = add_position_mins(m, value_col="expected_points")
    m = add_value_vs_position_min(m, value_col="expected_points")

    # Ranks within position (global within the selected odds source)
    m["ppg_rank"] = (
        m.groupby("position")["reg_ppg"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    m["exp_games_rank"] = (
        m.groupby("position")["expected_games"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    m["exp_pts_rank"] = (
        m.groupby("position")["expected_points"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    # Team colors (nflverse)
    team_meta = load_team_metadata()
    m = m.merge(team_meta, left_on="team", right_on="team_abbr", how="left")

    # Panel height
    visible_rows = 14
    row_height = 35
    header_height = 38
    panel_height = header_height + row_height * visible_rows

    # ---------------------------
    # Build Ranked Table (overall)
    # ---------------------------
    table = m.copy()

    # "unit_label" is the TEAM + POSITION display label (this is your intended "unit")
    table["unit_label"] = table["team"].astype(str) + " " + table["position"].astype(str)

    table["overall_rank"] = (
        table["value_vs_position_avg_expected_points"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    # Rank *within position group*
    table["position_rank"] = (
        table.groupby("position")["expected_points"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    table["ppg_rank"] = (
        table.groupby("position")["reg_ppg"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    table = table.sort_values(["overall_rank", "position", "team"]).reset_index(drop=True)
    rank_table = table.copy()

    # ------------------------------------------
    # Build Playoff Game Distribution (team-level)
    # ------------------------------------------
    team = odds_sel.copy()

    for c in ["Win WC", "Win Div", "Win Conf"]:
        team[c] = pd.to_numeric(team[c], errors="coerce").fillna(0.0)

    team["Seed"] = pd.to_numeric(team.get("Seed"), errors="coerce")
    is_bye = team["Seed"].eq(1)

    team["Expected Games"] = (1 + team["Win WC"] + team["Win Div"] + team["Win Conf"]).round(2)

    play1_nonbye = 1 - team["Win WC"]
    play2_nonbye = team["Win WC"] - team["Win Div"]
    play3_nonbye = team["Win Div"] - team["Win Conf"]
    play4_nonbye = team["Win Conf"]
    play3plus_nonbye = team["Win Div"]

    play1_bye = 1 - team["Win Div"]
    play2_bye = team["Win Div"] - team["Win Conf"]
    play3_bye = team["Win Conf"]
    play4_bye = 0.0
    play3plus_bye = team["Win Conf"]

    team["Play 1"] = np.where(is_bye, play1_bye, play1_nonbye)
    team["Play 2"] = np.where(is_bye, play2_bye, play2_nonbye)
    team["Play 3"] = np.where(is_bye, play3_bye, play3_nonbye)
    team["Play 4"] = np.where(is_bye, play4_bye, play4_nonbye)
    team["Play 3+"] = np.where(is_bye, play3plus_bye, play3plus_nonbye)

    prob_cols = ["Play 1", "Play 2", "Play 3", "Play 4", "Play 3+"]
    for c in prob_cols:
        team[c] = (team[c] * 100).round(0).astype(int).astype(str) + "%"

    team_display = (
        team[["team", "Expected Games"] + prob_cols]
        .rename(columns={"team": "Team"})
        .sort_values("Expected Games", ascending=False)
    )
    team_display["Expected Games"] = team_display["Expected Games"].map(lambda x: f"{x:.2f}")

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

        filtered = rank_table.copy()

        value_col = (
            "value_vs_position_avg_expected_points"
            if baseline == "avg"
            else "value_vs_position_min_expected_points"
        )

        # Start from the full table (global ranks), then filter down
        base = rank_table.copy()

        # Global overall rank based on chosen baseline (do NOT change with filters)
        base["overall_rank"] = (
            base[value_col]
            .rank(method="min", ascending=False)
            .astype(int)
        )

        # Global sort order (do NOT change with filters)
        base = base.sort_values(["overall_rank", "position", "team"]).reset_index(drop=True)

        # Apply filters ONLY to rows (no rank recompute)
        filtered = base.copy()

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
            metric_label = st.selectbox("Metric", list(metric_label_map.keys()), index=0)
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
