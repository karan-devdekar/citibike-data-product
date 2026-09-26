from google.cloud import bigquery
from google.cloud import storage
from datetime import datetime
import re
import os


# --------------------------------------------------
# Configuration
# --------------------------------------------------

PROJECT_ID = "citi-509517"
BUCKET_NAME = "citibike-weather-landing"

RAW_DATASET = "raw"
RAW_TABLE = "citibike_trips"


# --------------------------------------------------
# Clients
# --------------------------------------------------

bq_client = bigquery.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)


# --------------------------------------------------
# Source schema
# --------------------------------------------------

SOURCE_SCHEMA = [
    bigquery.SchemaField("ride_id", "STRING"),
    bigquery.SchemaField("rideable_type", "STRING"),
    bigquery.SchemaField("started_at", "STRING"),
    bigquery.SchemaField("ended_at", "STRING"),
    bigquery.SchemaField("start_station_name", "STRING"),
    bigquery.SchemaField("start_station_id", "STRING"),
    bigquery.SchemaField("end_station_name", "STRING"),
    bigquery.SchemaField("end_station_id", "STRING"),
    bigquery.SchemaField("start_lat", "STRING"),
    bigquery.SchemaField("start_lng", "STRING"),
    bigquery.SchemaField("end_lat", "STRING"),
    bigquery.SchemaField("end_lng", "STRING"),
    bigquery.SchemaField("member_casual", "STRING"),
]


# --------------------------------------------------
# Months to process
# --------------------------------------------------

MONTHS = [
    f"{year}{month:02d}"
    for year in [2020, 2021]
    for month in range(1, 13)
]


# --------------------------------------------------
# Find files for a month
# --------------------------------------------------

def get_month_files(month):

    year = month[:4]

    bucket = storage_client.bucket(BUCKET_NAME)

    blobs = bucket.list_blobs(
        prefix=f"citibike/{year}/"
    )

    pattern = re.compile(
        rf"{month}-citibike-tripdata.*\.csv$"
    )

    files = []

    for blob in blobs:

        filename = blob.name.split("/")[-1]

        if pattern.match(filename):

            files.append({
                "uri": f"gs://{BUCKET_NAME}/{blob.name}",
                "filename": filename
            })

    return sorted(files, key=lambda x: x["filename"])


# --------------------------------------------------
# Create final raw table
# --------------------------------------------------

def create_raw_table():

    table_id = (
        f"{PROJECT_ID}.{RAW_DATASET}.{RAW_TABLE}"
    )

    schema = SOURCE_SCHEMA + [
        bigquery.SchemaField("source_file", "STRING"),
        bigquery.SchemaField("source_month", "DATE"),
        bigquery.SchemaField("ingested_at", "TIMESTAMP"),
    ]

    table = bigquery.Table(
        table_id,
        schema=schema
    )

    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.MONTH,
        field="source_month"
    )

    table = bq_client.create_table(
        table,
        exists_ok=True
    )

    print(f"Raw table ready: {table_id}")

    return table_id


# --------------------------------------------------
# Load one source file into a temporary table
# --------------------------------------------------

def load_file_to_temp_table(
    gcs_uri,
    temp_table_id
):

    job_config = bigquery.LoadJobConfig(
        schema=SOURCE_SCHEMA,
        skip_leading_rows=1,
        source_format=bigquery.SourceFormat.CSV,
        write_disposition=(
            bigquery.WriteDisposition.WRITE_TRUNCATE
        ),
        allow_quoted_newlines=True,
    )

    load_job = bq_client.load_table_from_uri(
        gcs_uri,
        temp_table_id,
        job_config=job_config
    )

    load_job.result()

    return load_job.output_rows


# --------------------------------------------------
# Process one month
# --------------------------------------------------

def process_month(month, raw_table_id):

    print("\n" + "=" * 60)
    print(f"Processing month: {month}")
    print("=" * 60)

    files = get_month_files(month)

    if not files:
        raise RuntimeError(
            f"No Citi Bike files found for {month}"
        )

    print(f"Found {len(files)} file(s):")

    for file in files:
        print(f"  {file['filename']}")

    temp_tables = []
    total_rows = 0

    try:

        # ------------------------------------------
        # Load every source file into its own temp table
        # ------------------------------------------

        for index, file in enumerate(files, start=1):

            temp_table_id = (
                f"{PROJECT_ID}.{RAW_DATASET}."
                f"_citibike_temp_{month}_{index}"
            )

            print(f"\nLoading {file['filename']}")

            rows = load_file_to_temp_table(
                file["uri"],
                temp_table_id
            )

            print(f"  Loaded {rows:,} rows")

            temp_tables.append({
                "table_id": temp_table_id,
                "filename": file["filename"],
                "rows": rows
            })

            total_rows += rows

        print(
            f"\nTotal rows prepared for {month}: "
            f"{total_rows:,}"
        )

        # ------------------------------------------
        # Monthly partition
        # ------------------------------------------

        source_month_date = (
            f"{month[:4]}-{month[4:]}-01"
        )

        # ------------------------------------------
        # Step 1: Delete existing monthly partition
        # ------------------------------------------

        print(
            f"\nDeleting existing partition: "
            f"{source_month_date}"
        )

        delete_query = f"""
            DELETE FROM `{raw_table_id}`
            WHERE source_month = DATE('{source_month_date}');
        """

        delete_job = bq_client.query(delete_query)
        delete_job.result()

        print(
            f"Existing partition deleted: "
            f"{source_month_date}"
        )

        # ------------------------------------------
        # Step 2: Insert the month's source data
        # ------------------------------------------

        for temp in temp_tables:

            print(
                f"Inserting {temp['filename']} "
                f"into {source_month_date}"
            )

            insert_query = f"""
                INSERT INTO `{raw_table_id}`
                (
                    ride_id,
                    rideable_type,
                    started_at,
                    ended_at,
                    start_station_name,
                    start_station_id,
                    end_station_name,
                    end_station_id,
                    start_lat,
                    start_lng,
                    end_lat,
                    end_lng,
                    member_casual,
                    source_file,
                    source_month,
                    ingested_at
                )

                SELECT
                    ride_id,
                    rideable_type,
                    started_at,
                    ended_at,
                    start_station_name,
                    start_station_id,
                    end_station_name,
                    end_station_id,
                    start_lat,
                    start_lng,
                    end_lat,
                    end_lng,
                    member_casual,
                    '{temp["filename"]}',
                    DATE('{source_month_date}'),
                    CURRENT_TIMESTAMP()

                FROM `{temp["table_id"]}`;
            """

            insert_job = bq_client.query(insert_query)
            insert_job.result()

            print(
                f"  Inserted {temp['rows']:,} rows"
            )

        print(
            f"\nSuccessfully replaced "
            f"{source_month_date} partition."
        )

        print(
            f"Rows processed: {total_rows:,}"
        )

    finally:

        # ------------------------------------------
        # Always clean up temporary tables
        # ------------------------------------------

        for temp in temp_tables:

            bq_client.delete_table(
                temp["table_id"],
                not_found_ok=True
            )

        print("Temporary tables cleaned up.")

# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    print("=" * 60)
    print("Citi Bike ingestion started")
    print("=" * 60)

    raw_table_id = create_raw_table()

    # Cloud Run task information
    task_index = int(os.getenv("CLOUD_RUN_TASK_INDEX", "0"))
    task_count = int(os.getenv("CLOUD_RUN_TASK_COUNT", "1"))

    print(f"Cloud Run task index: {task_index}")
    print(f"Cloud Run task count: {task_count}")

    if task_count > len(MONTHS):
        raise ValueError(
            f"Task count ({task_count}) cannot exceed "
            f"number of months ({len(MONTHS)})"
        )

    # One task processes one month
    month = MONTHS[task_index]

    print(f"Assigned month: {month}")

    process_month(
        month,
        raw_table_id
    )

    print("\n" + "=" * 60)
    print(f"Task {task_index} completed successfully")
    print("=" * 60)


if __name__ == "__main__":
    main()