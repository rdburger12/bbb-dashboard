import plotly.express as px
import pandas as pd


def unit_bar_chart(df: pd.DataFrame, metric: str):
    """
    Vertical bar chart ranking teams within a unit by a selected metric.
    Expects df to already be filtered to a single unit.
    """
    plot_df = df.sort_values(metric, ascending=False)

    fig = px.bar(
        plot_df,
        x="team",
        y=metric,
        hover_data={
            "team": True,
            "unit": True,
            "reg_ppg": True,
            "expected_games": True,
            "expected_points": True,
        },
        title=f"Teams ranked by {metric}",
    )

    fig.update_layout(
        xaxis_title="Team",
        yaxis_title=metric,
        height=650,
        margin=dict(l=10, r=10, t=60, b=80),
        xaxis_tickangle=-45,
    )

    return fig
