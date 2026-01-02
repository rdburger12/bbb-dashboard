import plotly.express as px
import pandas as pd


def unit_bar_chart(df: pd.DataFrame, metric: str, metric_label: str):
    """
    Vertical bar chart ranking teams within a unit by a selected metric,
    with a dotted reference line at the unit average.
    """
    plot_df = df.sort_values(metric, ascending=False)

    avg_value = plot_df[metric].mean()

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
        title=f"Teams ranked by {metric_label}",
    )

    # Average reference line
    fig.add_hline(
        y=avg_value,
        line_dash="dot",
        line_color="gray",
        opacity=0.6,
        annotation_text=f"Avg: {avg_value:.2f}",
        annotation_position="top right",
    )

    fig.update_layout(
        xaxis_title="Team",
        yaxis_title=metric_label,
        height=650,
        margin=dict(l=10, r=10, t=60, b=80),
        xaxis_tickangle=-45,
    )

    return fig
