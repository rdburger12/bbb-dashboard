import streamlit as st
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
import pandas as pd
import numpy as np



def run_app():
    st.title("Fantasy Football Dashboard")

    # --- Load + prepare data (no display) ---
    pts_df, odds_df = load_raw_data()

    # Optional: keep validation but do not display unless failing
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

    # IMPORTANT: adjust join key if needed
    # Assumes your `team` column matches nflverse `team_abbr`
    m = m.merge(
        team_meta,
        left_on="team",
        right_on="team_abbr",
        how="left",
    )


    # --- Chart controls + chart ---
    st.subheader("Team ranking within a position group")

    unit_order = ["QB", "RB", "WR", "TE", "K", "OTH"]

    # keep only units that actually exist in the data (defensive)
    units = [u for u in unit_order if u in set(m["unit"].unique())]

    selected_unit = st.selectbox("Position", units)


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

    # --- Ranked table (overall) ---
    st.subheader("Ranked table")

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

    st.dataframe(table_display, width="stretch", hide_index=True)


    # ---------------------------
    # Playoff game distribution (team-level)
    # ---------------------------
    st.subheader("Playoff game distribution (team-level)")

    team = odds_c.copy()

    # Coerce probabilities to floats; treat missing as 0 for POC
    for c in ["Win WC", "Win Div", "Win Conf"]:
        team[c] = pd.to_numeric(team[c], errors="coerce").fillna(0.0)

    # Identify bye teams (POC assumption: Seed == 1)
    team["Seed"] = pd.to_numeric(team.get("Seed"), errors="coerce")
    is_bye = team["Seed"].eq(1)

    # Expected games per your formula
    team["Expected Games"] = (
        1 + team["Win WC"] + team["Win Div"] + team["Win Conf"]
    ).round(2)

    # Non-bye: can play 1–4 games
    play1_nonbye = 1 - team["Win WC"]
    play2_nonbye = team["Win WC"] - team["Win Div"]
    play3_nonbye = team["Win Div"] - team["Win Conf"]
    play4_nonbye = team["Win Conf"]
    play3plus_nonbye = team["Win Div"]

    # Bye: max 3 games (Div, Conf, SB). 4 games is impossible.
    play1_bye = 1 - team["Win Div"]                 # lose Div (first game)
    play2_bye = team["Win Div"] - team["Win Conf"]  # win Div, lose Conf
    play3_bye = team["Win Conf"]                    # win Conf (reach SB)
    play4_bye = 0.0
    play3plus_bye = team["Win Conf"]

    # Choose the correct distribution by bye status
    team["Play 1"] = np.where(is_bye, play1_bye, play1_nonbye)
    team["Play 2"] = np.where(is_bye, play2_bye, play2_nonbye)
    team["Play 3"] = np.where(is_bye, play3_bye, play3_nonbye)
    team["Play 4"] = np.where(is_bye, play4_bye, play4_nonbye)
    team["Play 3+"] = np.where(is_bye, play3plus_bye, play3plus_nonbye)

    # Format probabilities as whole percentages (no decimals)
    prob_cols = ["Play 1", "Play 2", "Play 3", "Play 4", "Play 3+"]
    for c in prob_cols:
        team[c] = (team[c] * 100).round(0).astype(int).astype(str) + "%"

    team_display = (
        team[["team", "Expected Games"] + prob_cols]
        .rename(columns={"team": "Team"})
        .sort_values("Expected Games", ascending=False)
    )

# Format Expected Games to exactly 2 decimals (display only)
    team_display["Expected Games"] = team_display["Expected Games"].map(lambda x: f"{x:.2f}")

    # Dynamic height to avoid scrolling
    n_rows = len(team_display)
    row_height = 35   # adjust if needed (32–40 typical)
    header_height = 38
    table_height = header_height + row_height * n_rows  # small padding

    st.dataframe(
        team_display,
        width="stretch",
        height=table_height,
        hide_index=True,
    )




