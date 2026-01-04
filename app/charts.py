import pandas as pd
import plotly.graph_objects as go


def unit_bar_chart(df: pd.DataFrame, metric: str, metric_label: str, height: int):
    plot_df = df.sort_values(metric, ascending=False).copy()

    # Defensive defaults in case any team colors are missing
    plot_df["team_color"] = plot_df["team_color"].fillna("#888888")
    plot_df["team_color2"] = plot_df["team_color2"].fillna("#222222")
    plot_df["unit_label"] = plot_df["team"] + " " + plot_df["position"]

    customdata = plot_df[
        [
            "unit_label",
            "reg_ppg", "ppg_rank",
            "expected_games", "exp_games_rank",
            "expected_points", "exp_pts_rank",
        ]
    ].to_numpy()

    avg_value = plot_df[metric].mean()

    fig = go.Figure(
        data=[
            go.Bar(
                x=plot_df["team"],
                y=plot_df[metric],
                customdata=customdata,
                text=plot_df[metric].round(2),
                textposition="outside",
                textfont=dict(size=12),
                marker=dict(
                    color=plot_df["team_color"].tolist(),
                    line=dict(
                        color=plot_df["team_color2"].tolist(),
                        width=2,
                    ),
                ),
                hovertemplate = (
                    "<b>%{customdata[0]}</b><br>"
                    "PPG: %{customdata[1]:.4f} (%{customdata[2]})<br>"
                    "Exp Games: %{customdata[3]:.2f} (%{customdata[4]})<br>"
                    "Exp Pts: %{customdata[5]:.2f} (%{customdata[6]})"
                    "<extra></extra>"
                )
            )

        ]
    )

    # Average reference line
    fig.add_hline(
        y=avg_value,
        line_dash="dot",
        line_color="gray",
        opacity=0.6,
        annotation_text=f"Avg: {avg_value:.2f}",
        annotation_position="top right",
        annotation_xanchor="right",
    )

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=20, b=60),
        xaxis_tickangle=-45,
        showlegend=False,
    )

    return fig
