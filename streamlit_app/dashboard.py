import plotly.graph_objects as go
import streamlit as st

from google.cloud import bigquery


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

PROJECT_ID = "citi-509517"

DAILY_VIEW = (
    "citi-509517.analytics_mcp_views."
    "daily_trip_weather_vw"
)


# ---------------------------------------------------------
# BigQuery client
# ---------------------------------------------------------

@st.cache_resource
def get_bigquery_client():
    return bigquery.Client(
        project=PROJECT_ID
    )


# ---------------------------------------------------------
# Execute query
# ---------------------------------------------------------

@st.cache_data(ttl=3600)
def run_query(sql: str):
    client = get_bigquery_client()

    query_job = client.query(sql)

    rows = query_job.result()

    return [
        dict(row.items())
        for row in rows
    ]


# ---------------------------------------------------------
# Latest operational metrics
# ---------------------------------------------------------

def get_latest_day():

    sql = f"""
        SELECT
            trip_date,
            total_trips,
            member_trips,
            casual_trips,
            member_trip_share_pct,
            casual_trip_share_pct,
            avg_trip_duration_minutes,
            median_trip_duration_minutes,
            active_start_stations,
            avg_temperature_2m,
            total_precipitation,
            total_rain,
            total_snowfall,
            rainy_hours,
            snowy_hours
        FROM `{DAILY_VIEW}`
        ORDER BY trip_date DESC
        LIMIT 1
    """

    rows = run_query(sql)

    if not rows:
        return None

    return rows[0]


# ---------------------------------------------------------
# Monthly trip trends
# ---------------------------------------------------------

def get_monthly_trends():

    sql = f"""
        SELECT
            DATE_TRUNC(trip_date, MONTH) AS trip_month,

            SUM(total_trips) AS total_trips,

            SUM(member_trips) AS member_trips,

            SUM(casual_trips) AS casual_trips,

            ROUND(
                SAFE_DIVIDE(
                    SUM(member_trips),
                    SUM(total_trips)
                ) * 100,
                2
            ) AS member_trip_share_pct,

            ROUND(
                SAFE_DIVIDE(
                    SUM(casual_trips),
                    SUM(total_trips)
                ) * 100,
                2
            ) AS casual_trip_share_pct,

            ROUND(
                AVG(avg_trip_duration_minutes),
                2
            ) AS avg_trip_duration_minutes,

            ROUND(
                AVG(avg_temperature_2m),
                2
            ) AS avg_temperature_2m,

            ROUND(
                SUM(total_precipitation),
                2
            ) AS total_precipitation,

            SUM(rainy_hours) AS rainy_hours,

            SUM(snowy_hours) AS snowy_hours

        FROM `{DAILY_VIEW}`

        GROUP BY trip_month

        ORDER BY trip_month
    """

    return run_query(sql)


# ---------------------------------------------------------
# Dashboard page
# ---------------------------------------------------------

def render_dashboard():

    st.title("📊 Citi Bike Dashboard")

    st.caption(
        "Fixed operational views based on the Citi Bike "
        "analytical warehouse."
    )

    # -----------------------------------------------------
    # Load data
    # -----------------------------------------------------

    try:

        latest = get_latest_day()

        monthly = get_monthly_trends()

    except Exception as exc:

        st.error(
            "Unable to load dashboard data from BigQuery."
        )

        with st.expander("Technical details"):
            st.exception(exc)

        return

    if latest is None or not monthly:

        st.warning(
            "No dashboard data is currently available."
        )

        return

    # -----------------------------------------------------
    # Latest date
    # -----------------------------------------------------

    latest_date = latest["trip_date"]

    st.subheader(
        f"Latest available day: "
        f"{latest_date.strftime('%d %b %Y')}"
    )

    # -----------------------------------------------------
    # KPI cards
    # -----------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Total Trips",
            f"{int(latest['total_trips']):,}",
        )

    with col2:

        st.metric(
            "Member Share",
            f"{latest['member_trip_share_pct']:.2f}%",
        )

    with col3:

        st.metric(
            "Avg Trip Duration",
            f"{latest['avg_trip_duration_minutes']:.2f} min",
        )

    with col4:

        st.metric(
            "Active Stations",
            f"{int(latest['active_start_stations']):,}",
        )

    st.divider()

    # -----------------------------------------------------
    # Monthly trip volume
    # -----------------------------------------------------

    st.subheader("Monthly Trip Volume")

    trip_months = [
        row["trip_month"]
        for row in monthly
    ]

    total_trips = [
        row["total_trips"]
        for row in monthly
    ]

    fig_trips = go.Figure()

    fig_trips.add_trace(
        go.Scatter(
            x=trip_months,
            y=total_trips,
            mode="lines+markers",
            name="Total Trips",
        )
    )

    fig_trips.update_layout(
        title="Total Citi Bike Trips by Month",
        xaxis_title="Month",
        yaxis_title="Trips",
        hovermode="x unified",
    )

    st.plotly_chart(
        fig_trips,
        use_container_width=True,
    )

    # -----------------------------------------------------
    # Member vs Casual
    # -----------------------------------------------------

    st.subheader(
        "Member vs Casual Riders"
    )

    member_share = [
        row["member_trip_share_pct"]
        for row in monthly
    ]

    casual_share = [
        row["casual_trip_share_pct"]
        for row in monthly
    ]

    fig_riders = go.Figure()

    fig_riders.add_trace(
        go.Scatter(
            x=trip_months,
            y=member_share,
            mode="lines+markers",
            name="Member",
        )
    )

    fig_riders.add_trace(
        go.Scatter(
            x=trip_months,
            y=casual_share,
            mode="lines+markers",
            name="Casual",
        )
    )

    fig_riders.update_layout(
        title="Member vs Casual Share by Month",
        xaxis_title="Month",
        yaxis_title="Share (%)",
        hovermode="x unified",
    )

    st.plotly_chart(
        fig_riders,
        use_container_width=True,
    )

    # -----------------------------------------------------
    # Average trip duration
    # -----------------------------------------------------

    st.subheader(
        "Average Trip Duration"
    )

    avg_duration = [
        row["avg_trip_duration_minutes"]
        for row in monthly
    ]

    fig_duration = go.Figure()

    fig_duration.add_trace(
        go.Scatter(
            x=trip_months,
            y=avg_duration,
            mode="lines+markers",
            name="Average Duration",
        )
    )

    fig_duration.update_layout(
        title="Average Trip Duration by Month",
        xaxis_title="Month",
        yaxis_title="Minutes",
        hovermode="x unified",
    )

    st.plotly_chart(
        fig_duration,
        use_container_width=True,
    )

    # -----------------------------------------------------
    # Weather and trips
    # -----------------------------------------------------

    st.subheader(
        "Weather and Trip Activity"
    )

    precipitation = [
        row["total_precipitation"]
        for row in monthly
    ]

    rainy_hours = [
        row["rainy_hours"]
        for row in monthly
    ]

    weather_total_trips = [
        row["total_trips"]
        for row in monthly
    ]

    temperatures = [
        row["avg_temperature_2m"]
        for row in monthly
    ]

    fig_weather = go.Figure()

    fig_weather.add_trace(
        go.Scatter(
            x=precipitation,
            y=weather_total_trips,
            mode="markers",
            name="Monthly Trips",
            marker=dict(
                size=[
                    max(8, float(hours))
                    for hours in rainy_hours
                ],
            ),
            customdata=[
                [
                    month,
                    temperature,
                    rain_hours,
                ]
                for month, temperature, rain_hours
                in zip(
                    trip_months,
                    temperatures,
                    rainy_hours,
                )
            ],
            hovertemplate=(
                "Month: %{customdata[0]}<br>"
                "Precipitation: %{x}<br>"
                "Trips: %{y:,}<br>"
                "Avg Temperature: %{customdata[1]}<br>"
                "Rainy Hours: %{customdata[2]}"
                "<extra></extra>"
            ),
        )
    )

    fig_weather.update_layout(
        title=(
            "Monthly Trip Volume vs "
            "Total Precipitation"
        ),
        xaxis_title="Total Precipitation",
        yaxis_title="Total Trips",
    )

    st.plotly_chart(
        fig_weather,
        use_container_width=True,
    )

    # -----------------------------------------------------
    # Weather summary
    # -----------------------------------------------------

    st.subheader(
        "Latest Day Weather"
    )

    weather_col1, weather_col2, weather_col3, weather_col4 = (
        st.columns(4)
    )

    with weather_col1:

        st.metric(
            "Avg Temperature",
            f"{latest['avg_temperature_2m']:.2f}",
        )

    with weather_col2:

        st.metric(
            "Precipitation",
            f"{latest['total_precipitation']:.2f}",
        )

    with weather_col3:

        st.metric(
            "Rainy Hours",
            f"{int(latest['rainy_hours']):,}",
        )

    with weather_col4:

        st.metric(
            "Snowy Hours",
            f"{int(latest['snowy_hours']):,}",
        )