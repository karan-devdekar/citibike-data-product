{{ config(
    materialized='view'
) }}

SELECT
    trip_hour,

    -- Trip volume
    COUNT(*) AS total_trips,

    COUNTIF(rider_type = 'member') AS member_trips,
    COUNTIF(rider_type = 'casual') AS casual_trips,

    -- Rider mix
    ROUND(
        SAFE_DIVIDE(
            COUNTIF(rider_type = 'member'),
            COUNT(*)
        ) * 100,
        2
    ) AS member_trip_share_pct,

    ROUND(
        SAFE_DIVIDE(
            COUNTIF(rider_type = 'casual'),
            COUNT(*)
        ) * 100,
        2
    ) AS casual_trip_share_pct,

    -- Trip duration
    ROUND(
        AVG(trip_duration_minutes),
        2
    ) AS avg_trip_duration_minutes,

    ROUND(
        APPROX_QUANTILES(
            trip_duration_minutes,
            100
        )[OFFSET(50)],
        2
    ) AS median_trip_duration_minutes,

    -- Station activity
    COUNT(DISTINCT start_station_id) AS active_start_stations,

    -- Time dimensions
    ANY_VALUE(day_of_week) AS day_of_week,
    ANY_VALUE(hour_of_day) AS hour_of_day,
    ANY_VALUE(is_weekend) AS is_weekend,

    -- Weather
    ANY_VALUE(temperature_2m) AS temperature_2m,
    ANY_VALUE(relative_humidity_2m) AS relative_humidity_2m,
    ANY_VALUE(precipitation) AS precipitation,
    ANY_VALUE(rain) AS rain,
    ANY_VALUE(snowfall) AS snowfall,
    ANY_VALUE(cloud_cover) AS cloud_cover,
    ANY_VALUE(wind_speed_10m) AS wind_speed_10m,

    ANY_VALUE(weather_condition) AS weather_condition,
    ANY_VALUE(temperature_bucket) AS temperature_bucket,

    -- Weather-related trip metrics
    COUNTIF(is_rainy = TRUE) AS rainy_trip_count,
    COUNTIF(is_snowy = TRUE) AS snowy_trip_count,

    COUNTIF(weather_available = TRUE) AS trips_with_weather,
    COUNTIF(weather_available = FALSE) AS trips_without_weather

FROM {{ ref('trip_weather_vw') }}

GROUP BY trip_hour