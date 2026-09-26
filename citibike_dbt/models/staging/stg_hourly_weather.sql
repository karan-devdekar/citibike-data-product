WITH source_data AS (

    SELECT
        weather_time,
        temperature_2m,
        relative_humidity_2m,
        precipitation,
        rain,
        snowfall,
        cloud_cover,
        wind_speed_10m,
        source,
        weather_date,
        ingested_at

    FROM `citi-509517.raw.hourly_weather`

)

SELECT
    weather_time,
    weather_date,

    temperature_2m,
    relative_humidity_2m,
    precipitation,
    rain,
    snowfall,
    cloud_cover,
    wind_speed_10m,

    source,
    ingested_at

FROM source_data