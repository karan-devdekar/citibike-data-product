{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='ride_id',

    partition_by={
        "field": "trip_date",
        "data_type": "date",
        "granularity": "day"
    },

    cluster_by=[
        "start_station_id",
        "end_station_id",
        "rider_type"
    ]
) }}
--Transactional Fact 
WITH source_data AS (

    SELECT
        ride_id,
        rideable_type,
        started_at,
        ended_at,
        trip_duration_seconds,
        trip_date,

        start_station_name,
        start_station_id,
        end_station_name,
        end_station_id,

        start_lat,
        start_lng,
        end_lat,
        end_lng,

        rider_type,

        source_file,
        source_month,
        ingested_at

    FROM {{ ref('stg_citibike_trips') }}

    {% if is_incremental() %}

        WHERE ingested_at > (
            SELECT COALESCE(
                MAX(ingested_at),
                TIMESTAMP('1900-01-01')
            )
            FROM {{ this }}
        )

    {% endif %}

)

SELECT
    ride_id,
    rideable_type,
    started_at,
    ended_at,
    trip_duration_seconds,
    trip_date,

    start_station_name,
    start_station_id,
    end_station_name,
    end_station_id,

    start_lat,
    start_lng,
    end_lat,
    end_lng,

    rider_type,

    source_file,
    source_month,
    ingested_at

FROM source_data