{{ config(severity='warn') }}

SELECT
    weather_time,
    temperature_2m,
    relative_humidity_2m,
    precipitation,
    rain,
    snowfall,
    cloud_cover,
    wind_speed_10m

FROM {{ ref('stg_hourly_weather') }}

WHERE
       relative_humidity_2m < 0
    OR relative_humidity_2m > 100
    OR precipitation < 0
    OR rain < 0
    OR snowfall < 0
    OR cloud_cover < 0
    OR cloud_cover > 100
    OR wind_speed_10m < 0