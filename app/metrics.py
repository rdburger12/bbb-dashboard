import pandas as pd
import numpy as np

ODDS_COLS = ["Win WC", "Win Div", "Win Conf"]


def add_expected_games(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expected Games:
      - Non-bye: 1 (WC) + P(win WC) + P(win Div) + P(win Conf)
      - Bye (Seed == 1): 1 (Div) + P(win Div) + P(win Conf)

    This remains correct even if bye teams have Win WC = 1 in the data.
    """
    out = df.copy()
    for c in ODDS_COLS:
        if c not in out.columns:
            raise KeyError(f"Missing required odds column: {c}")

    if "Seed" in out.columns:
        seed = (
            out["Seed"]
            .astype(str)
            .str.strip()
            .str.extract(r"(\d+)", expand=False)  # pull the first integer-looking token
        )
        seed_num = pd.to_numeric(seed, errors="coerce")
        is_bye = seed_num.eq(1)
        win_wc_played = np.where(is_bye, 0.0, out["Win WC"])
    else:
        # If Seed isn't present, assume everyone plays WC
        win_wc_played = out["Win WC"]

    out["expected_games"] = 1 + win_wc_played + out["Win Div"] + out["Win Conf"]
    return out


def add_expected_points(df: pd.DataFrame, base_col: str = "reg_ppg") -> pd.DataFrame:
    """
    Expected Points = base_col * expected_games
    Default base_col is reg_ppg (points per 6 games) per your description.
    """
    if base_col not in df.columns:
        raise KeyError(f"Missing base points column: {base_col}")
    if "expected_games" not in df.columns:
        raise KeyError("expected_games not found. Call add_expected_games() first.")

    out = df.copy()
    out["expected_points"] = out[base_col] * out["expected_games"]
    return out


def add_position_averages(df: pd.DataFrame, value_col: str = "expected_points") -> pd.DataFrame:
    """
    Adds position-group average for the chosen value column.
    Produces: position_avg_<value_col>

    NOTE: "position_avg_*" is a legacy name; it is actually per-position.
    """
    if value_col not in df.columns:
        raise KeyError(f"Missing value column: {value_col}")
    if "position" not in df.columns:
        raise KeyError("Missing grouping column: position")

    out = df.copy()
    avg_col = f"position_avg_{value_col}"
    out[avg_col] = out.groupby("position")[value_col].transform("mean")
    return out


def add_value_vs_position_avg(df: pd.DataFrame, value_col: str = "expected_points") -> pd.DataFrame:
    """
    Adds value vs position-group average:
      value_vs_position_avg_<value_col> = value_col - position_avg_<value_col>
    """
    avg_col = f"position_avg_{value_col}"
    if value_col not in df.columns:
        raise KeyError(f"Missing value column: {value_col}")
    if avg_col not in df.columns:
        raise KeyError(f"{avg_col} not found. Call add_position_averages() first.")

    out = df.copy()
    out[f"value_vs_position_avg_{value_col}"] = out[value_col] - out[avg_col]
    return out


def add_position_mins(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """
    Adds position-group minimum for the chosen value column.
    Produces: position_min_<value_col>

    NOTE: "position_min_*" is a legacy name; it is actually per-position.
    """
    if value_col not in df.columns:
        raise KeyError(f"Missing value column: {value_col}")
    if "position" not in df.columns:
        raise KeyError("Missing grouping column: position")

    out = df.copy()
    min_col = f"position_min_{value_col}"
    out[min_col] = out.groupby("position")[value_col].transform("min")
    return out


def add_value_vs_position_min(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """
    Adds value vs position-group minimum:
      value_vs_position_min_<value_col> = value_col - position_min_<value_col>
    """
    out = df.copy()
    min_col = f"position_min_{value_col}"
    delta_col = f"value_vs_position_min_{value_col}"

    if value_col not in out.columns:
        raise KeyError(f"Missing value column: {value_col}")
    if min_col not in out.columns:
        raise ValueError(f"Missing required column: {min_col}. Run add_position_mins first.")

    out[delta_col] = out[value_col] - out[min_col]
    return out
