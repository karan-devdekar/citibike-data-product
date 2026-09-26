WITH source_data AS (

    SELECT
        ride_id,
        rideable_type,

        SAFE_CAST(started_at AS TIMESTAMP) AS started_at,
        SAFE_CAST(ended_at AS TIMESTAMP) AS ended_at,

        start_station_name,
        start_station_id,

        end_station_name,
        end_station_id,

        SAFE_CAST(start_lat AS FLOAT64) AS start_lat,
        SAFE_CAST(start_lng AS FLOAT64) AS start_lng,

        SAFE_CAST(end_lat AS FLOAT64) AS end_lat,
        SAFE_CAST(end_lng AS FLOAT64) AS end_lng,

        member_casual,

        source_file,
        source_month,
        ingested_at

    FROM `citi-509517.raw.citibike_trips`

),

transformed AS (

    SELECT
        ride_id,
        rideable_type,

        started_at,
        ended_at,

        TIMESTAMP_DIFF(
            ended_at,
            started_at,
            SECOND
        ) AS trip_duration_seconds,

        DATE(started_at) AS trip_date,

        start_station_name,
        start_station_id,

        end_station_name,
        end_station_id,

        start_lat,
        start_lng,

        end_lat,
        end_lng,

        member_casual AS rider_type,

        source_file,
        source_month,
        ingested_at

    FROM source_data

)

SELECT *
FROM transformed