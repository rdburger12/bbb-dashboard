from pathlib import Path
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data" / "raw"

PTS_PATH = DATA_RAW / "pts_2025.csv"
ODDS_PATH = DATA_RAW / "playoff_odds.csv"

# Validate raw CSV headers (before canonicalization)
REQUIRED_PTS_COLS = {"team", "position", "pts", "reg_ppg"}

# You now depend on Odds Source + Seed in main.py
REQUIRED_ODDS_COLS = {"Team", "Odds Source", "Seed", "Win WC", "Win Div", "Win Conf"}


def _normalize_team(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip()


@st.cache_data
def load_raw_data():
    pts_df = pd.read_csv(PTS_PATH)
    odds_df = pd.read_csv(ODDS_PATH)
    return pts_df, odds_df


def validate_schema(df: pd.DataFrame, required_cols: set[str]) -> list[str]:
    """Return missing required columns (empty list means pass)."""
    return sorted(list(required_cols - set(df.columns)))


def canonicalize_pts(pts_df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize pts table to canonical column names:
      - team (abbr)
      - position (QB/RB/WR/TE/K/OTH)
    """
    out = pts_df.copy()
    out["team"] = _normalize_team(out["team"])
    out["position"] = out["position"].astype(str).str.strip()
    return out


def canonicalize_odds(odds_df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize odds table to canonical column names:
      - team
      - Odds Source
      - Seed
      - Win WC / Win Div / Win Conf
    """
    out = odds_df.copy()
    out = out.rename(columns={"Team": "team"})
    out["team"] = _normalize_team(out["team"])
    # Keep existing column names used in main.py: "Odds Source", "Seed", "Win WC", ...
    return out


def join_pts_with_odds(pts_c: pd.DataFrame, odds_c: pd.DataFrame) -> pd.DataFrame:
    """
    Inner-join odds onto team×position rows, restricting to teams present in playoff odds.
    Expected rows: (#odds teams) * 6 positions (assuming complete pts coverage).
    """
    merged = pts_c.merge(
        odds_c,
        on="team",
        how="inner",
        suffixes=("", "_odds"),
        validate="many_to_one",
    )
    return merged
