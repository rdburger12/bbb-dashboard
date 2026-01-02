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




def run_app():
    st.title("Fantasy Football Dashboard")

    pts_df, odds_df = load_raw_data()

    st.subheader("Schema validation")

    pts_missing = validate_schema(pts_df, REQUIRED_PTS_COLS)
    odds_missing = validate_schema(odds_df, REQUIRED_ODDS_COLS)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**pts_2025.csv**")
        if pts_missing:
            st.error(f"Missing required columns: {pts_missing}")
        else:
            st.success("Schema OK")
        st.write(f"Rows: {len(pts_df)} | Cols: {len(pts_df.columns)}")
        st.write(pts_df.head())

    with c2:
        st.markdown("**playoff_odds.csv**")
        if odds_missing:
            st.error(f"Missing required columns: {odds_missing}")
        else:
            st.success("Schema OK")
        st.write(f"Rows: {len(odds_df)} | Cols: {len(odds_df.columns)}")
        st.write(odds_df.head())

    st.subheader("Canonicalized preview (naming standardized)")

    pts_c = canonicalize_pts(pts_df)
    odds_c = canonicalize_odds(odds_df)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**pts (canonical)**")
        st.write(pts_c.head())

    with c4:
        st.markdown("**odds (canonical)**")
        st.write(odds_c.head())

    st.subheader("Join diagnostics (restricted to playoff-odds teams)")

    merged = join_pts_with_odds(pts_c, odds_c)

    st.subheader("Metric preview (expected games / expected points / value vs unit avg)")

    m = add_expected_games(merged)
    m = add_expected_points(m, base_col="reg_ppg")
    m = add_unit_averages(m, value_col="expected_points")
    m = add_value_vs_unit_avg(m, value_col="expected_points")

    preview_cols = [
        "team", "unit", "reg_ppg",
        "expected_games", "expected_points",
        "unit_avg_expected_points",
        "value_vs_unit_avg_expected_points",
    ]
    st.write(m[preview_cols])


    st.subheader("Chart: team ranking within a position group")

    units = sorted(m["unit"].unique().tolist())
    selected_unit = st.selectbox("Position group", units)

    metric_label_map = {
            "Expected points": "expected_points",
            "PPG": "reg_ppg",
    }
     

    metric_label = st.selectbox(
        "Metric",
        list(metric_label_map.keys()),
        index=0,
    )

    metric = metric_label_map[metric_label]

    chart_df = m[m["unit"] == selected_unit].copy()
    fig = unit_bar_chart(chart_df, metric=metric)
    st.plotly_chart(fig, use_container_width=True)



    odds_team_count = odds_c["team"].nunique()
    merged_team_count = merged["team"].nunique()

    st.write(f"Odds teams: {odds_team_count}")
    st.write(f"Merged teams: {merged_team_count}")
    st.write(f"Rows after join: {len(merged)} (expected ≈ odds teams × 6 units)")

    # Identify any odds teams missing from pts
    missing_pts_teams = sorted(set(odds_c["team"]) - set(pts_c["team"]))
    if missing_pts_teams:
        st.warning("Some playoff-odds teams were not found in pts data:")
        st.write(missing_pts_teams)
    else:
        st.success("All playoff-odds teams found in pts data.")

    st.subheader("Joined preview")
    st.write(merged.head(25))

