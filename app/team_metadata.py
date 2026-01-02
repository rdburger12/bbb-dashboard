import pandas as pd
import streamlit as st

NFLVERSE_TEAM_URL = (
    "https://raw.githubusercontent.com/guga31bb/nflfastR-data/master/teams_colors_logos.csv"
)

@st.cache_data
def load_team_metadata():
    df = pd.read_csv(NFLVERSE_TEAM_URL)

    # Normalize column names defensively
    df = df.rename(columns=str.lower)

    # We only need a few fields for now
    return df[
        [
            "team_abbr",
            "team_name",
            "team_color",
            "team_color2",
        ]
    ]
