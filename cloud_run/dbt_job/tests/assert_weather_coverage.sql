{{ config(severity='error') }}

SELECT
    MIN(weather_date) AS min_weather_date,
    MAX(weather_date) AS max_weather_date,
    COUNT(DISTINCT weather_date) AS distinct_dates

FROM {{ ref('stg_hourly_weather') }}

HAVING
    MIN(weather_date) != DATE('2020-01-01')
    OR MAX(weather_date) != DATE('2021-12-31')