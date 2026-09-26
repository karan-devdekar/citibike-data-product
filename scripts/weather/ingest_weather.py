import calendar
import json
import time
from datetime import date, datetime,timedelta

import pandas as pd
import requests
from google.cloud import bigquery, storage
from zoneinfo import ZoneInfo


# ============================================================
# Configuration
# ============================================================

PROJECT_ID = "citi-509517"

BUCKET_NAME = "citibike-weather-landing"

RAW_DATASET = "raw"
RAW_TABLE = "hourly_weather"

LATITUDE = 40.7128
LONGITUDE = -74.0060

TIMEZONE = "UTC"

API_URL = "https://archive-api.open-meteo.com/v1/archive"

HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "snowfall",
    "cloud_cover",
    "wind_speed_10m",
]


# ============================================================
# Clients
# ============================================================

bq_client = bigquery.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)


# ============================================================
# BigQuery schema
# ============================================================

SCHEMA = [
    bigquery.SchemaField("weather_time", "TIMESTAMP"),
    bigquery.SchemaField("temperature_2m", "FLOAT64"),
    bigquery.SchemaField("relative_humidity_2m", "FLOAT64"),
    bigquery.SchemaField("precipitation", "FLOAT64"),
    bigquery.SchemaField("rain", "FLOAT64"),
    bigquery.SchemaField("snowfall", "FLOAT64"),
    bigquery.SchemaField("cloud_cover", "FLOAT64"),
    bigquery.SchemaField("wind_speed_10m", "FLOAT64"),
    bigquery.SchemaField("source", "STRING"),
    bigquery.SchemaField("weather_date", "DATE"),
    bigquery.SchemaField("ingested_at", "TIMESTAMP"),
]


# ============================================================
# Create raw table
# ============================================================

def create_raw_table():

    table_id = f"{PROJECT_ID}.{RAW_DATASET}.{RAW_TABLE}"

    try:
        table = bq_client.get_table(table_id)
        print(f"Raw weather table already exists: {table_id}")

    except Exception:

        table = bigquery.Table(
            table_id,
            schema=SCHEMA
        )

        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="weather_date",
        )

        bq_client.create_table(table)

        print(f"Created raw weather table: {table_id}")


# ============================================================
# Month boundaries
# ============================================================

def get_month_dates(year, month):

    first_day = date(year, month, 1)

    last_day = date(
        year,
        month,
        calendar.monthrange(year, month)[1]
    )

    return first_day, last_day


# ============================================================
# Fetch Open-Meteo
# ============================================================

def fetch_weather(start_date, end_date):

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": TIMEZONE,
    }

    max_attempts = 5

    for attempt in range(1, max_attempts + 1):

        print(
            f"Fetching weather: "
            f"{start_date} -> {end_date} "
            f"(attempt {attempt}/{max_attempts})"
        )

        try:

            response = requests.get(
                API_URL,
                params=params,
                timeout=120,
            )

            # Retry temporary server/rate-limit errors
            if response.status_code in {
                429, 500, 502, 503, 504
            }:

                if attempt == max_attempts:
                    response.raise_for_status()

                wait_seconds = 2 ** attempt

                print(
                    f"Open-Meteo returned "
                    f"{response.status_code}. "
                    f"Retrying in {wait_seconds} seconds..."
                )

                time.sleep(wait_seconds)

                continue

            # For other HTTP errors, fail immediately.
            response.raise_for_status()

            return response.json()

        except requests.exceptions.Timeout:

            if attempt == max_attempts:
                raise

            wait_seconds = 2 ** attempt

            print(
                f"Request timed out. "
                f"Retrying in {wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)

        except requests.exceptions.ConnectionError:

            if attempt == max_attempts:
                raise

            wait_seconds = 2 ** attempt

            print(
                f"Connection error. "
                f"Retrying in {wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)

    raise RuntimeError(
        f"Failed to fetch weather data for "
        f"{start_date} -> {end_date}"
    )

# ============================================================
# Save raw response to GCS
# ============================================================

def save_to_gcs(data, year, month):

    blob_name = (
        f"weather/hourly/"
        f"{year}/{year}{month:02d}-open-meteo.json"
    )

    bucket = storage_client.bucket(BUCKET_NAME)

    blob = bucket.blob(blob_name)

    blob.upload_from_string(
        json.dumps(data),
        content_type="application/json",
    )

    print(
        f"Saved raw response to "
        f"gs://{BUCKET_NAME}/{blob_name}"
    )


# ============================================================
# Transform API response
# ============================================================

def transform_weather_response(data):

    hourly = data["hourly"]

    rows = []

    ny_timezone = ZoneInfo("America/New_York")

    now_utc = pd.Timestamp.now(tz="UTC")

    for i, time_value in enumerate(hourly["time"]):

        # Open-Meteo is returning UTC because
        # timezone=UTC.
        utc_time = datetime.fromisoformat(
            time_value
        ).replace(
            tzinfo=ZoneInfo("UTC")
        )

        # Convert UTC to NYC only for deriving the
        # local calendar date.
        ny_local_time = utc_time.astimezone(
            ny_timezone
        )

        rows.append(
            {
                "weather_time": utc_time,

                "temperature_2m": hourly[
                    "temperature_2m"
                ][i],

                "relative_humidity_2m": hourly[
                    "relative_humidity_2m"
                ][i],

                "precipitation": hourly[
                    "precipitation"
                ][i],

                "rain": hourly[
                    "rain"
                ][i],

                "snowfall": hourly[
                    "snowfall"
                ][i],

                "cloud_cover": hourly[
                    "cloud_cover"
                ][i],

                "wind_speed_10m": hourly[
                    "wind_speed_10m"
                ][i],

                "source": "open-meteo",

                "weather_date": ny_local_time.date(),

                "ingested_at": now_utc,
            }
        )

    return rows

# ============================================================
# Load month into BigQuery
# ============================================================

def load_month_to_bigquery(rows, year, month):

    table_id = f"{PROJECT_ID}.{RAW_DATASET}.{RAW_TABLE}"

    month_start = date(year, month, 1)

    # --------------------------------------------------------
    # Delete existing month
    # --------------------------------------------------------

    delete_sql = f"""
        DELETE FROM `{table_id}`
        WHERE weather_date >= DATE('{month_start}')
          AND weather_date < DATE_ADD(
              DATE('{month_start}'),
              INTERVAL 1 MONTH
          )
    """

    bq_client.query(delete_sql).result()

    print(
        f"Removed existing data for "
        f"{year}-{month:02d}"
    )

    # --------------------------------------------------------
    # Convert to DataFrame
    # --------------------------------------------------------

    df = pd.DataFrame(rows)

    if df.empty:

        print(
            f"No rows returned for "
            f"{year}-{month:02d}"
        )

        return

    # --------------------------------------------------------
    # BigQuery load job
    # --------------------------------------------------------

    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition="WRITE_APPEND",
    )

    print(
        f"Loading {len(df):,} rows into BigQuery..."
    )

    load_job = bq_client.load_table_from_dataframe(
        df,
        table_id,
        job_config=job_config,
    )

    load_job.result()

    # Make sure BigQuery reports success.
    if load_job.errors:

        raise RuntimeError(
            f"BigQuery load errors: "
            f"{load_job.errors}"
        )

    print(
        f"Successfully loaded "
        f"{len(df):,} rows for "
        f"{year}-{month:02d}"
    )


# ============================================================
# Validate month
# ============================================================

def validate_month(year, month):

    table_id = f"{PROJECT_ID}.{RAW_DATASET}.{RAW_TABLE}"

    month_start = date(year, month, 1)

    query = f"""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT weather_time) AS distinct_hours,
            MIN(weather_time) AS min_weather_time,
            MAX(weather_time) AS max_weather_time
        FROM `{table_id}`
        WHERE weather_date >= DATE('{month_start}')
          AND weather_date < DATE_ADD(
              DATE('{month_start}'),
              INTERVAL 1 MONTH
          )
    """

    result = list(
        bq_client.query(query).result()
    )[0]

    print(
        f"\nValidation {year}-{month:02d}"
    )

    print(
        f"Rows: {result.row_count:,}"
    )

    print(
        f"Distinct timestamps: "
        f"{result.distinct_hours:,}"
    )

    print(
        f"Min timestamp: "
        f"{result.min_weather_time}"
    )

    print(
        f"Max timestamp: "
        f"{result.max_weather_time}"
    )

    if result.row_count != result.distinct_hours:

        raise ValueError(
            f"Duplicate weather timestamps "
            f"detected for {year}-{month:02d}"
        )

    if result.row_count == 0:

        raise ValueError(
            f"No rows loaded for "
            f"{year}-{month:02d}"
        )

    print("Validation PASSED")


# ============================================================
# Process one month
# ============================================================

def process_month(year, month):

    start_date, end_date = get_month_dates(
        year,
        month
    )

    # Fetch one extra day on either side because
    # weather_date is ultimately based on NYC local time.
    api_start_date = start_date - timedelta(days=1)
    api_end_date = end_date + timedelta(days=1)

    data = fetch_weather(
        api_start_date,
        api_end_date
    )

    save_to_gcs(
        data,
        year,
        month
    )

    rows = transform_weather_response(
        data
    )

    # Keep only observations belonging to the
    # requested NYC calendar month.
    rows = [
        row
        for row in rows
        if row["weather_date"] >= start_date
        and row["weather_date"] <= end_date
    ]

    print(
        f"Filtered to "
        f"{len(rows):,} NYC hourly records "
        f"for {year}-{month:02d}"
    )

    load_month_to_bigquery(
        rows,
        year,
        month
    )

    validate_month(
        year,
        month
    )

# ============================================================
# Main
# ============================================================

def main():

    print("=" * 60)
    print("Starting weather ingestion")
    print("=" * 60)

    create_raw_table()

    for year in range(2020, 2022):

        for month in range(1, 13):

            process_month(
                year,
                month
            )
    # process_month(2020, 3)
    print("=" * 60)
    print("Weather ingestion completed successfully")
    print("=" * 60)


if __name__ == "__main__":
    main()