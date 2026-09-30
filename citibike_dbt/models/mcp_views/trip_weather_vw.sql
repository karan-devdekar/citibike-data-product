{{ config(
    materialized='view'
) }}

-- Purpose:
--   Creates one analytical record per Citi Bike trip and enriches
--   the trip with hourly weather information.
-- Grain:
--   One row per ride_id / trip.
-- Main uses:
--   Trip-level analysis
--   Weather impact analysis
--   Time-of-day / day-of-week analysis
--   Feeding higher-level hourly and daily views


SELECT


    f.ride_id,

    f.trip_date,

    f.started_at,

    f.ended_at,


    -- Convert trip duration from seconds to minutes.
    -- ROUND(..., 2) keeps the value to 2 decimal places.
    ROUND(
        f.trip_duration_seconds / 60.0,
        2
    ) AS trip_duration_minutes,


    -- Rider classification:
    -- member or casual
    f.rider_type,



    f.start_station_id,
    f.start_station_name,

    f.end_station_id,
    f.end_station_name,


    -- This is also the key used to join trips with hourly weather.
    TIMESTAMP_TRUNC(
        f.started_at,
        HOUR
    ) AS trip_hour,


    -- This is important because the stored timestamp is UTC,
    -- while Citi Bike activity is being analyzed in NYC time.
    EXTRACT(
        HOUR
        FROM DATETIME(
            f.started_at,
            "America/New_York"
        )
    ) AS hour_of_day,

    FORMAT_DATE(
        '%A',
        DATE(
            DATETIME(
                f.started_at,
                "America/New_York"
            )
        )
    ) AS day_of_week,


    -- Identify whether the trip occurred on a weekend.
    -- BigQuery DAYOFWEEK:
    --   1 = Sunday
    --   7 = Saturday
    CASE
        WHEN EXTRACT(
            DAYOFWEEK
            FROM DATE(
                DATETIME(
                    f.started_at,
                    "America/New_York"
                )
            )
        ) IN (1, 7)
        THEN TRUE
        ELSE FALSE
    END AS is_weekend,



    -- Weather measurements corresponding to the trip start hour.
    w.temperature_2m,
    w.relative_humidity_2m,
    w.precipitation,
    w.rain,
    w.snowfall,
    w.cloud_cover,
    w.wind_speed_10m,



    -- Categorize the weather into a simple condition.
    --
    -- Priority:
    --   1. Snow
    --   2. Rain
    --   3. Other precipitation
    --   4. Cloudy
    --   5. Clear
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


    -- Flag the trip as rainy when either rain or precipitation
    -- is greater than zero.
    CASE
        WHEN w.rain > 0
             OR w.precipitation > 0
        THEN TRUE
        ELSE FALSE
    END AS is_rainy,


    -- Flag the trip as snowy when snowfall is greater than zero.
    CASE
        WHEN w.snowfall > 0
        THEN TRUE
        ELSE FALSE
    END AS is_snowy,


    -- Indicates whether matching weather data was available
    -- for the trip's start hour.
    CASE
        WHEN w.weather_time IS NOT NULL
        THEN TRUE
        ELSE FALSE
    END AS weather_available


FROM `citi-509517.analytics.fact_citibike_trips` f


LEFT JOIN `citi-509517.analytics.hourly_weather` w

    ON TIMESTAMP_TRUNC(
        f.started_at,
        HOUR
    ) = w.weather_time


WHERE f.trip_date BETWEEN '2020-01-01' AND '2021-12-31'