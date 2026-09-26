{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='station_id'
) }}

WITH station_observations AS (

    -- Start station observations
    SELECT
        start_station_id AS station_id,
        start_station_name AS station_name,
        start_lat AS latitude,
        start_lng AS longitude,
        started_at AS observed_at,
        source_file,
        ingested_at
    FROM {{ ref('stg_citibike_trips') }}
    WHERE start_station_id IS NOT NULL

    UNION ALL

    -- End station observations
    SELECT
        end_station_id AS station_id,
        end_station_name AS station_name,
        end_lat AS latitude,
        end_lng AS longitude,
        ended_at AS observed_at,
        source_file,
        ingested_at
    FROM {{ ref('stg_citibike_trips') }}
    WHERE end_station_id IS NOT NULL

),

filtered_observations AS (

    SELECT *
    FROM station_observations

    {% if is_incremental() %}

    WHERE ingested_at > (
        SELECT COALESCE(
            MAX(ingested_at),
            TIMESTAMP('1900-01-01')
        )
        FROM {{ this }}
    )

    {% endif %}

),

latest_station_attributes AS (

    SELECT
        station_id,

        ARRAY_AGG(
            station_name IGNORE NULLS
            ORDER BY observed_at DESC, ingested_at DESC
            LIMIT 1
        )[SAFE_OFFSET(0)] AS station_name,

        ARRAY_AGG(
            latitude IGNORE NULLS
            ORDER BY observed_at DESC, ingested_at DESC
            LIMIT 1
        )[SAFE_OFFSET(0)] AS latitude,

        ARRAY_AGG(
            longitude IGNORE NULLS
            ORDER BY observed_at DESC, ingested_at DESC
            LIMIT 1
        )[SAFE_OFFSET(0)] AS longitude,

        MAX(observed_at) AS last_observed_at,
        MAX(ingested_at) AS ingested_at,

        ARRAY_AGG(
            source_file
            ORDER BY observed_at DESC, ingested_at DESC
            LIMIT 1
        )[SAFE_OFFSET(0)] AS source_file

    FROM filtered_observations
    GROUP BY station_id

),

final AS (

    SELECT
        s.station_id,

        COALESCE(
            s.station_name,
            t.station_name
        ) AS station_name,

        COALESCE(
            s.latitude,
            t.latitude
        ) AS latitude,

        COALESCE(
            s.longitude,
            t.longitude
        ) AS longitude,

        s.last_observed_at,

        COALESCE(
            s.source_file,
            t.source_file
        ) AS source_file,

        s.ingested_at

    FROM latest_station_attributes s

    {% if is_incremental() %}

    LEFT JOIN {{ this }} t
        ON s.station_id = t.station_id

    {% else %}

    LEFT JOIN (
        SELECT
            CAST(NULL AS STRING) AS station_id,
            CAST(NULL AS STRING) AS station_name,
            CAST(NULL AS FLOAT64) AS latitude,
            CAST(NULL AS FLOAT64) AS longitude,
            CAST(NULL AS TIMESTAMP) AS last_observed_at,
            CAST(NULL AS STRING) AS source_file,
            CAST(NULL AS TIMESTAMP) AS ingested_at
    ) t
        ON FALSE

    {% endif %}

)

SELECT
    station_id,
    station_name,
    latitude,
    longitude,
    last_observed_at,
    source_file,
    ingested_at

FROM final