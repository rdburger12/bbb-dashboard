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
    add_unit_averages,
    add_value_vs_unit_avg,
)
from .charts import unit_bar_chart
from .team_metadata import load_team_metadata


def run_app():
    st.title("Fantasy Football Dashboard")

    # --- Load + prepare data (no display) ---
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

    pts_c = canonicalize_pts(pts_df)
    odds_c = canonicalize_odds(odds_df)

    merged = join_pts_with_odds(pts_c, odds_c)

    m = add_expected_games(merged)
    m = add_expected_points(m, base_col="reg_ppg")
    m = add_unit_averages(m, value_col="expected_points")
    m = add_value_vs_unit_avg(m, value_col="expected_points")

    # --- Team colors (nflverse) ---
    team_meta = load_team_metadata()

    # Assumes your `team` column matches nflverse `team_abbr`
    m = m.merge(
        team_meta,
        left_on="team",
        right_on="team_abbr",
        how="left",
    )

    # ---------------------------
    # Build Ranked Table (overall)
    # ---------------------------
    table = m.copy()
    table["unit_label"] = table["team"].astype(str) + " " + table["unit"].astype(str)

    table["overall_rank"] = (
        table["value_vs_unit_avg_expected_points"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    table["position_rank"] = (
        table.groupby("unit")["expected_points"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    table["ppg_rank"] = (
        table.groupby("unit")["reg_ppg"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    table = table.sort_values(["overall_rank", "unit", "team"]).reset_index(drop=True)

    table_display = table[
        [
            "overall_rank",
            "unit_label",
            "value_vs_unit_avg_expected_points",
            "expected_points",
            "position_rank",
            "ppg_rank",
            "reg_ppg",
        ]
    ].rename(columns={
        "overall_rank": "Overall Rank",
        "unit_label": "Unit",
        "value_vs_unit_avg_expected_points": "Exp Pts vs Pos Avg",
        "expected_points": "Exp Pts",
        "position_rank": "Position Rank",
        "ppg_rank": "PPG Rank",
        "reg_ppg": "PPG",
    })

    # ------------------------------------------
    # Build Playoff Game Distribution (team-level)
    # ------------------------------------------
    team = odds_c.copy()

    for c in ["Win WC", "Win Div", "Win Conf"]:
        team[c] = pd.to_numeric(team[c], errors="coerce").fillna(0.0)

    # POC bye handling: Seed == 1
    team["Seed"] = pd.to_numeric(team.get("Seed"), errors="coerce")
    is_bye = team["Seed"].eq(1)

    team["Expected Games"] = (
        1 + team["Win WC"] + team["Win Div"] + team["Win Conf"]
    ).round(2)

    # Non-bye: can play 1–4 games
    play1_nonbye = 1 - team["Win WC"]
    play2_nonbye = team["Win WC"] - team["Win Div"]
    play3_nonbye = team["Win Div"] - team["Win Conf"]
    play4_nonbye = team["Win Conf"]
    play3plus_nonbye = team["Win Div"]

    # Bye: max 3 games
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

    # Display formatting
    team_display["Expected Games"] = team_display["Expected Games"].map(lambda x: f"{x:.2f}")

    # Dynamic height to avoid scrolling; no padding (per your preference)
    n_rows = len(team_display)
    row_height = 35
    header_height = 38
    table_height = header_height + row_height * n_rows

    # ---------------------------
    # Dashboard Layout (3 columns)
    # ---------------------------
    st.subheader("Dashboard")

    left, mid, right = st.columns([1.5, 1.8, 1.2], gap="small")

    with left:
        st.markdown("### Ranked table")
        st.dataframe(table_display, width="stretch", hide_index=True)

    with mid:
        st.markdown("### Team ranking within a position group")

        unit_order = ["QB", "RB", "WR", "TE", "K", "OTH"]
        units = [u for u in unit_order if u in set(m["unit"].unique())]
        # Controls side by side
        c_pos, c_metric = st.columns([1, 1])

        with c_pos:
            selected_unit = st.selectbox("Position", units)

        with c_metric:
            metric_label_map = {
                "Expected points": "expected_points",
                "PPG": "reg_ppg",
            }
            metric_label = st.selectbox("Metric", list(metric_label_map.keys()), index=0)
            metric = metric_label_map[metric_label]

        chart_df = m[m["unit"] == selected_unit].copy()

        fig = unit_bar_chart(
            chart_df,
            metric=metric,
            metric_label=metric_label,
        )
        st.plotly_chart(fig, width="stretch")

    with right:
        st.markdown("### Playoff game distribution")
        st.dataframe(
            team_display,
            width="stretch",
            height=table_height,
            hide_index=True,
        )
