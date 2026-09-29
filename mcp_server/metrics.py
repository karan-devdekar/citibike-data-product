from datetime import date

from google.cloud import bigquery

from bigquery_client import get_client


PROJECT_ID = "citi-509517"
TABLE = f"`{PROJECT_ID}.analytics_mcp_views.trip_weather_vw`"


METRICS = {
    "total_trips": "COUNT(*)",

    "avg_trip_duration_minutes": (
        "AVG(trip_duration_minutes)"
    ),

    "member_trip_share_pct": (
        "100 * SAFE_DIVIDE("
        "COUNTIF(rider_type = 'member'), "
        "COUNT(*)"
        ")"
    ),

    "casual_trip_share_pct": (
        "100 * SAFE_DIVIDE("
        "COUNTIF(rider_type = 'casual'), "
        "COUNT(*)"
        ")"
    ),

    "rainy_trip_share_pct": (
        "100 * SAFE_DIVIDE("
        "COUNTIF(is_rainy = TRUE), "
        "COUNT(*)"
        ")"
    ),
}


GRAIN_EXPRESSIONS = {
    "day": "trip_date",
    "month": "DATE_TRUNC(trip_date, MONTH)",
}


def get_metric(
    metric: str,
    grain: str,
    start_date: str,
    end_date: str,
    station_id: str | None = None,
) -> list[dict]:
    """
    Calculate a curated Citi Bike metric.

    Args:
        metric: Name of the curated metric.
        grain: Aggregation grain: day or month.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        station_id: Optional Citi Bike station ID.

    Returns:
        List of metric results grouped by the requested grain.
    """

    # Validate metric
    if metric not in METRICS:
        raise ValueError(
            f"Unsupported metric: {metric}. "
            f"Available metrics: {list(METRICS.keys())}"
        )

    # Validate grain
    if grain not in GRAIN_EXPRESSIONS:
        raise ValueError(
            f"Unsupported grain: {grain}. "
            f"Available grains: {list(GRAIN_EXPRESSIONS.keys())}"
        )

    # Validate dates
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        raise ValueError(
            "Dates must use YYYY-MM-DD format."
        )

    if start > end:
        raise ValueError(
            "start_date cannot be after end_date."
        )

    grain_expression = GRAIN_EXPRESSIONS[grain]
    metric_expression = METRICS[metric]

    # Base date filter
    where_clause = """
        trip_date BETWEEN @start_date AND @end_date
    """

    # Optional station filter
    if station_id:
        where_clause += """
        AND (
            start_station_id = @station_id
            OR end_station_id = @station_id
        )
        """

    sql = f"""
        SELECT
            {grain_expression} AS period,
            {metric_expression} AS metric_value
        FROM {TABLE}
        WHERE {where_clause}
        GROUP BY period
        ORDER BY period
    """

    client = get_client()

    # Build all query parameters before creating QueryJobConfig.
    query_parameters = [
        bigquery.ScalarQueryParameter(
            "start_date",
            "DATE",
            start,
        ),
        bigquery.ScalarQueryParameter(
            "end_date",
            "DATE",
            end,
        ),
    ]

    # Add station parameter only when station filtering is requested.
    if station_id:
        query_parameters.append(
            bigquery.ScalarQueryParameter(
                "station_id",
                "STRING",
                station_id,
            )
        )

    job_config = bigquery.QueryJobConfig(
        query_parameters=query_parameters
    )

    rows = client.query(
        sql,
        job_config=job_config,
    ).result()

    return [
        {
            "period": row.period.isoformat(),
            "metric": metric,
            "value": row.metric_value,
        }
        for row in rows
    ]