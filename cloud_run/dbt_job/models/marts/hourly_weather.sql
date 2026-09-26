{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='weather_time',

    partition_by={
        "field": "weather_date",
        "data_type": "date",
        "granularity": "day"
    },

    cluster_by=[
        "source"
    ]
) }}

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

FROM {{ ref('stg_hourly_weather') }}

{% if is_incremental() %}

WHERE ingested_at > (
    SELECT COALESCE(
        MAX(ingested_at),
        TIMESTAMP('1900-01-01')
    )
    FROM {{ this }}
)

{% endif %}