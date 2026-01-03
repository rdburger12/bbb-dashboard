import pandas as pd

ODDS_COLS = ["Win WC", "Win Div", "Win Conf"]


def add_expected_games(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expected Games = 1 + Win WC + Win Div + Win Conf

    Assumes Win WC / Win Div / Win Conf are probabilities in [0, 1].
    """
    out = df.copy()
    for c in ODDS_COLS:
        if c not in out.columns:
            raise KeyError(f"Missing required odds column: {c}")

    out["expected_games"] = 1 + out["Win WC"] + out["Win Div"] + out["Win Conf"]
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


def add_unit_averages(df: pd.DataFrame, value_col: str = "expected_points") -> pd.DataFrame:
    """
    Adds unit-level average for the chosen value column.
    Produces: unit_avg_<value_col>
    """
    if value_col not in df.columns:
        raise KeyError(f"Missing value column: {value_col}")

    out = df.copy()
    avg_col = f"unit_avg_{value_col}"
    out[avg_col] = out.groupby("unit")[value_col].transform("mean")
    return out


def add_value_vs_unit_avg(df: pd.DataFrame, value_col: str = "expected_points") -> pd.DataFrame:
    """
    Adds value vs unit average:
      value_vs_unit_avg_<value_col> = value_col - unit_avg_<value_col>
    """
    avg_col = f"unit_avg_{value_col}"
    if value_col not in df.columns:
        raise KeyError(f"Missing value column: {value_col}")
    if avg_col not in df.columns:
        raise KeyError(f"{avg_col} not found. Call add_unit_averages() first.")

    out = df.copy()
    out[f"value_vs_unit_avg_{value_col}"] = out[value_col] - out[avg_col]
    return out

def add_unit_mins(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """
    Adds unit_min_<value_col> based on the minimum value within each unit.
    Example: unit_min_expected_points
    """
    out = df.copy()
    min_col = f"unit_min_{value_col}"
    out[min_col] = out.groupby("unit")[value_col].transform("min")
    return out


def add_value_vs_unit_min(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """
    Adds value_vs_unit_min_<value_col> = <value_col> - unit_min_<value_col>
    Example: value_vs_unit_min_expected_points
    """
    out = df.copy()
    min_col = f"unit_min_{value_col}"
    delta_col = f"value_vs_unit_min_{value_col}"

    if min_col not in out.columns:
        raise ValueError(f"Missing required column: {min_col}. Run add_unit_mins first.")

    out[delta_col] = out[value_col] - out[min_col]
    return out

