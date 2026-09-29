import plotly.express as px


def create_metric_chart(
    result,
    title: str,
    y_axis_title: str,
    value_format: str = "number",
):
    if not result or not isinstance(result, list):
        return None

    periods = []
    values = []

    for row in result:
        if not isinstance(row, dict):
            continue

        period = row.get("period")
        value = row.get("value")

        if period is None or value is None:
            continue

        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        periods.append(str(period))
        values.append(value)

    if not periods:
        return None

    if value_format == "percentage":
        fig = px.line(
            x=periods,
            y=values,
            markers=True,
            title=title,
        )
        fig.update_yaxes(
            title=y_axis_title,
            ticksuffix="%",
        )

    elif value_format == "minutes":
        fig = px.line(
            x=periods,
            y=values,
            markers=True,
            title=title,
        )
        fig.update_yaxes(
            title=y_axis_title,
            ticksuffix=" min",
        )

    else:
        fig = px.line(
            x=periods,
            y=values,
            markers=True,
            title=title,
        )
        fig.update_yaxes(title=y_axis_title)

    fig.update_xaxes(title="Period")
    fig.update_layout(
        hovermode="x unified",
        margin=dict(l=20, r=20, t=60, b=20),
    )

    return fig