import pandas as pd
import numpy as np
import streamlit as st

from .data_loader import (
    canonicalize_pts,
    canonicalize_odds,
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
from .team_metadata import load_team_metadata


def build_model(pts_df: pd.DataFrame, odds_df: pd.DataFrame, selected_source: str):
    """
    Build all derived datasets for the dashboard, driven by Odds Source.

    Returns:
      m: team×position dataframe with expected metrics + ranks + colors
      rank_table: base ranking table (global ranks computed later based on baseline)
      team_display: right table (14 teams) with expected games + play distribution
      odds_sources: list[str] available in odds data
    """
    pts_c = canonicalize_pts(pts_df)
    odds_c = canonicalize_odds(odds_df)

    odds_sources = sorted(odds_c["Odds Source"].dropna().unique().tolist())
    if selected_source not in odds_sources and odds_sources:
        selected_source = odds_sources[0]

    odds_sel = odds_c[odds_c["Odds Source"] == selected_source].copy()

    merged = join_pts_with_odds(pts_c, odds_sel)

    # Core metrics
    m = add_expected_games(merged)
    m = add_expected_points(m, base_col="reg_ppg")
    m = add_position_averages(m, value_col="expected_points")
    m = add_value_vs_position_avg(m, value_col="expected_points")
    m = add_position_mins(m, value_col="expected_points")
    m = add_value_vs_position_min(m, value_col="expected_points")

    # Ranks within position for tooltip + table
    m["ppg_rank"] = m.groupby("position")["reg_ppg"].rank(method="min", ascending=False).astype(int)
    m["exp_games_rank"] = m.groupby("position")["expected_games"].rank(method="min", ascending=False).astype(int)
    m["exp_pts_rank"] = m.groupby("position")["expected_points"].rank(method="min", ascending=False).astype(int)

    # Team colors
    team_meta = load_team_metadata()
    m = m.merge(team_meta, left_on="team", right_on="team_abbr", how="left")

    # Rank table base (global ranks based on baseline computed in UI layer)
    rank_table = m.copy()
    rank_table["unit_label"] = rank_table["team"].astype(str) + " " + rank_table["position"].astype(str)

    rank_table["position_rank"] = (
        rank_table.groupby("position")["expected_points"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    rank_table["ppg_rank"] = (
        rank_table.groupby("position")["reg_ppg"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    # Right table: playoff distribution
    team = odds_sel.copy()
    for c in ["Win WC", "Win Div", "Win Conf"]:
        team[c] = pd.to_numeric(team[c], errors="coerce").fillna(0.0)

    team["Seed"] = pd.to_numeric(team.get("Seed"), errors="coerce")
    is_bye = team["Seed"].eq(1)

    seed = (
        team["Seed"]
        .astype(str)
        .str.strip()
        .str.extract(r"(\d+)", expand=False)
    )
    seed_num = pd.to_numeric(seed, errors="coerce")
    is_bye = seed_num.eq(1)

    team["Expected Games"] = np.where(
        is_bye,
        (1 + team["Win Div"] + team["Win Conf"]),
        (1 + team["Win WC"] + team["Win Div"] + team["Win Conf"]),
    ).round(2)

    # Non-bye: games played 1–4
    play1_nonbye = 1 - team["Win WC"]
    play2_nonbye = team["Win WC"] - team["Win Div"]
    play3_nonbye = team["Win Div"] - team["Win Conf"]
    play4_nonbye = team["Win Conf"]
    play3plus_nonbye = team["Win Div"]

    # Bye: games played 1–3 (no 4-game path)
    play1_bye = 1 - team["Win Div"]                 # lose first game (Div)
    play2_bye = team["Win Div"] - team["Win Conf"]  # win Div, lose Conf
    play3_bye = team["Win Conf"]                    # reach SB (3 games played)
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

    return m, rank_table, team_display, odds_sources, selected_source

@st.cache_data(show_spinner=False)
def build_model_cached(pts_df: pd.DataFrame, odds_df: pd.DataFrame, selected_source: str):
    """
    Cached wrapper around build_model.
    Streamlit will recompute only when inputs change (including selected_source).
    """
    return build_model(pts_df, odds_df, selected_source)
