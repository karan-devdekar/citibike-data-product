import sqlglot
from sqlglot import exp

from bigquery_client import get_client


PROJECT_ID = "citi-509517"
MAX_ROWS = 1000
MAX_BYTES = 50 * 1024 * 1024  # 50 MB


ALLOWED_TABLES = {
    f"{PROJECT_ID}.analytics_mcp_views.trip_weather_vw",
    f"{PROJECT_ID}.analytics_mcp_views.hourly_trip_weather_vw",
    f"{PROJECT_ID}.analytics_mcp_views.daily_trip_weather_vw",
    f"{PROJECT_ID}.analytics.dim_station",
    f"{PROJECT_ID}.analytics.hourly_weather",
    f"{PROJECT_ID}.analytics.fact_citibike_trips",
}


def normalize_table(table: exp.Table) -> str:
    """Return a fully-qualified BigQuery table name."""

    catalog = table.catalog
    db = table.db
    name = table.name

    if catalog and db:
        return f"{catalog}.{db}.{name}"

    if db:
        return f"{PROJECT_ID}.{db}.{name}"

    return name


def validate_sql(sql: str) -> str:
    """
    Validate that SQL is a single read-only SELECT statement
    referencing only approved warehouse tables.
    """

    if not sql or not sql.strip():
        raise ValueError("SQL query cannot be empty.")

    statements = sqlglot.parse(sql, read="bigquery")

    if len(statements) != 1:
        raise ValueError(
            "Only one SQL statement is allowed."
        )

    statement = statements[0]

    # Only SELECT statements are allowed.
    if not isinstance(statement, exp.Select):
        raise ValueError(
            "Only SELECT statements are allowed."
        )

    # Check every referenced physical table.
    referenced_tables = statement.find_all(exp.Table)

    for table in referenced_tables:
        table_name = normalize_table(table)

        if table_name not in ALLOWED_TABLES:
            raise ValueError(
                f"Table is not allowed: {table_name}"
            )

    return statement.sql(dialect="bigquery")


def add_row_limit(sql: str) -> str:
    """
    Wrap a validated query and enforce the maximum number of rows.
    """

    return f"""
        SELECT *
        FROM (
            {sql}
        )
        LIMIT {MAX_ROWS}
    """


def run_readonly_query(sql: str) -> dict:
    """
    Validate, dry-run, and execute a read-only warehouse query.
    """

    validated_sql = validate_sql(sql)
    limited_sql = add_row_limit(validated_sql)

    client = get_client()

    # Dry run to determine bytes that would be processed.
    dry_run_config = client.query(
        limited_sql,
        job_config=__import__(
            "google.cloud.bigquery",
            fromlist=["QueryJobConfig"],
        ).QueryJobConfig(
            dry_run=True,
            use_query_cache=False,
        ),
    )

    bytes_processed = dry_run_config.total_bytes_processed

    if bytes_processed > MAX_BYTES:
        raise ValueError(
            f"Query exceeds the {MAX_BYTES} byte limit. "
            f"Estimated bytes: {bytes_processed}"
        )

    # Execute with BigQuery's own bytes-billed protection as a second guard.
    query_config = __import__(
        "google.cloud.bigquery",
        fromlist=["QueryJobConfig"],
    ).QueryJobConfig(
        maximum_bytes_billed=MAX_BYTES
    )

    result = client.query(
        limited_sql,
        job_config=query_config,
    ).result()

    rows = [dict(row) for row in result]

    return {
        "rows": rows,
        "row_count": len(rows),
        "max_rows": MAX_ROWS,
        "bytes_processed": bytes_processed,
        "truncated": len(rows) == MAX_ROWS,
    }