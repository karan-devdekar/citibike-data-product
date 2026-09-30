{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key='station_id'
    )
}}


-- A station can appear as either:
--   1. a starting station
--   2. an ending station
-- We combine both types of observations into one dataset so that every station can be captured in the dimension.

WITH station_observations AS (
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


-- A station can have multiple observations over time.
-- We want the latest known:
--     station_name
--     latitude
--     longitude
-- observed_at determines which observation is newest.
-- ingested_at is used as a secondary ordering criterion
-- when observations have the same observed_at timestamp.

latest_station_attributes AS (

    SELECT

        station_id,


        -- ARRAY_AGG orders observations from newest to oldest
        -- and takes the first non-null station name.

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


        -- Last time this station was observed.
        MAX(observed_at) AS last_observed_at,

        -- Latest ingestion timestamp associated with the
        -- station observations.
        MAX(ingested_at) AS ingested_at,


        -- Latest source file containing this station.
        ARRAY_AGG(
            source_file
            ORDER BY observed_at DESC, ingested_at DESC
            LIMIT 1
        )[SAFE_OFFSET(0)] AS source_file

    FROM filtered_observations

    -- One final record per station.
    GROUP BY station_id

),

final AS (

    SELECT

        s.station_id,


        -- Use the newly observed station name when available.
        -- Otherwise retain the existing value.
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