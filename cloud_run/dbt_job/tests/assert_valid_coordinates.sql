{{ config(
    severity = 'warn'
) }}

SELECT
    ride_id,
    start_lat,
    start_lng,
    end_lat,
    end_lng,
    source_month,
    source_file

FROM {{ ref('stg_citibike_trips') }}

WHERE
    (
        -- Invalid start coordinate
        start_lat IS NOT NULL
        AND start_lng IS NOT NULL
        AND (
            (start_lat = 0 AND start_lng = 0)
            OR
            start_lat < 40
            OR start_lat > 41
            OR start_lng < -75
            OR start_lng > -73
        )
    )

    OR

    (
        -- Invalid end coordinate
        end_lat IS NOT NULL
        AND end_lng IS NOT NULL
        AND (
            (end_lat = 0 AND end_lng = 0)
            OR
            end_lat < 40
            OR end_lat > 41
            OR end_lng < -75
            OR end_lng > -73
        )
    )