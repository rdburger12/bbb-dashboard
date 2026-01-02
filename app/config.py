from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"

PTS_CSV = DATA_RAW_DIR / "pts_2025.csv"
ODDS_CSV = DATA_RAW_DIR / "playoff_odds.csv"

# Canonical unit order (used later for sorting/display)
UNIT_ORDER = ["QB", "RB", "WR", "TE", "K", "OTH"]
