{{ config(
    materialized='view'
) }}

SELECT
    f.ride_id,
    f.trip_date,
    f.started_at,
    f.ended_at,

    ROUND(f.trip_duration_seconds / 60.0, 2)
        AS trip_duration_minutes,

    f.rider_type,

    -- Station information
    f.start_station_id,
    f.start_station_name,
    f.end_station_id,
    f.end_station_name,

    -- UTC hour used for the weather join
    TIMESTAMP_TRUNC(f.started_at, HOUR) AS trip_hour,

    -- New York local time dimensions
    EXTRACT(
        HOUR FROM DATETIME(f.started_at, "America/New_York")
    ) AS hour_of_day,

    FORMAT_DATE(
        '%A',
        DATE(DATETIME(f.started_at, "America/New_York"))
    ) AS day_of_week,

    CASE
        WHEN EXTRACT(
            DAYOFWEEK FROM DATE(DATETIME(f.started_at, "America/New_York"))
        ) IN (1, 7)
        THEN TRUE
        ELSE FALSE
    END AS is_weekend,

    -- Weather
    w.temperature_2m,
    w.relative_humidity_2m,
    w.precipitation,
    w.rain,
    w.snowfall,
    w.cloud_cover,
    w.wind_speed_10m,

    -- Derived weather dimensions
    CASE
        WHEN w.snowfall > 0 THEN 'snow'
        WHEN w.rain > 0 THEN 'rain'
        WHEN w.precipitation > 0 THEN 'precipitation'
        WHEN w.cloud_cover >= 75 THEN 'cloudy'
        ELSE 'clear'
    END AS weather_condition,

    CASE
        WHEN w.temperature_2m < 0 THEN 'below_0'
        WHEN w.temperature_2m < 5 THEN '0_to_5'
        WHEN w.temperature_2m < 10 THEN '5_to_10'
        WHEN w.temperature_2m < 15 THEN '10_to_15'
        WHEN w.temperature_2m < 20 THEN '15_to_20'
        WHEN w.temperature_2m < 25 THEN '20_to_25'
        ELSE '25_plus'
    END AS temperature_bucket,

    CASE
        WHEN w.rain > 0 OR w.precipitation > 0 THEN TRUE
        ELSE FALSE
    END AS is_rainy,

    CASE
        WHEN w.snowfall > 0 THEN TRUE
        ELSE FALSE
    END AS is_snowy,

    CASE
        WHEN w.weather_time IS NOT NULL THEN TRUE
        ELSE FALSE
    END AS weather_available

FROM `citi-509517.analytics.fact_citibike_trips` f

LEFT JOIN `citi-509517.analytics.hourly_weather` w
    ON TIMESTAMP_TRUNC(f.started_at, HOUR) = w.weather_time

WHERE f.trip_date BETWEEN '2020-01-01' AND '2021-12-31'