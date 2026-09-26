{{ config(
    severity = 'warn'
) }}

SELECT
    ride_id,
    started_at,
    ended_at,
    trip_duration_seconds,
    source_month,
    source_file

FROM {{ ref('stg_citibike_trips') }}

WHERE trip_duration_seconds > 86400