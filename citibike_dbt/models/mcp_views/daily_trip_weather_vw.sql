{{ config(
    materialized='view'
) }}

WITH daily_trips AS (

    SELECT
        trip_date,

        COUNT(*) AS total_trips,

        COUNTIF(rider_type = 'member') AS member_trips,
        COUNTIF(rider_type = 'casual') AS casual_trips,

        ROUND(AVG(trip_duration_minutes), 2)
            AS avg_trip_duration_minutes,

        ROUND(
            APPROX_QUANTILES(
                trip_duration_minutes,
                100
            )[OFFSET(50)],
            2
        ) AS median_trip_duration_minutes,

        COUNT(DISTINCT start_station_id)
            AS active_start_stations

    FROM {{ ref('trip_weather_vw') }}

    GROUP BY trip_date
),

daily_weather AS (

    SELECT
        weather_date AS trip_date,

        ROUND(AVG(temperature_2m), 2)
            AS avg_temperature_2m,

        ROUND(AVG(relative_humidity_2m), 2)
            AS avg_relative_humidity_2m,

        ROUND(SUM(precipitation), 2)
            AS total_precipitation,

        ROUND(SUM(rain), 2)
            AS total_rain,

        ROUND(SUM(snowfall), 2)
            AS total_snowfall,

        ROUND(AVG(cloud_cover), 2)
            AS avg_cloud_cover,

        ROUND(AVG(wind_speed_10m), 2)
            AS avg_wind_speed_10m,

        COUNTIF(rain > 0) AS rainy_hours,

        COUNTIF(snowfall > 0) AS snowy_hours

    FROM {{ ref('hourly_weather') }}

    GROUP BY weather_date
)

SELECT
    t.trip_date,

    t.total_trips,
    t.member_trips,
    t.casual_trips,

    ROUND(
        SAFE_DIVIDE(t.member_trips, t.total_trips) * 100,
        2
    ) AS member_trip_share_pct,

    ROUND(
        SAFE_DIVIDE(t.casual_trips, t.total_trips) * 100,
        2
    ) AS casual_trip_share_pct,

    t.avg_trip_duration_minutes,
    t.median_trip_duration_minutes,
    t.active_start_stations,

    w.avg_temperature_2m,
    w.avg_relative_humidity_2m,
    w.total_precipitation,
    w.total_rain,
    w.total_snowfall,
    w.avg_cloud_cover,
    w.avg_wind_speed_10m,

    w.rainy_hours,
    w.snowy_hours

FROM daily_trips t

LEFT JOIN daily_weather w
    USING (trip_date)