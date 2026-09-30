# Citi Bike Analytics Warehouse — MCP Data Dictionary

## Purpose

This warehouse contains NYC Citi Bike trip data from January 2020 through
December 2021 together with hourly NYC weather observations.

The MCP server exposes this warehouse to an LLM through curated metrics,
station lookup, and a guarded read-only SQL tool.

Prefer curated MCP metrics over generating SQL manually whenever the required
metric is available.

---

# Analytical Tables and Views

## fact_citibike_trips

### Grain

One row per Citi Bike trip.

### Important columns

| Column | Meaning |
|---|---|
| ride_id | Unique identifier for a Citi Bike trip |
| trip_date | Calendar date of trip start |
| started_at | Trip start timestamp in UTC |
| ended_at | Trip end timestamp in UTC |
| trip_duration_minutes | Trip duration in minutes |
| rider_type | Rider category: member or casual |
| start_station_id | Starting station identifier |
| start_station_name | Starting station name |
| end_station_id | Ending station identifier |
| end_station_name | Ending station name |

### Notes

The fact table covers the January 2020 through December 2021 analysis period.

Trip timestamps are stored in UTC.

For local NYC analysis, timestamps should be interpreted using the
America/New_York timezone.

---

## dim_station

### Grain

One row per station identifier representing the latest known station
attributes in the analysis window.

### Important columns

| Column | Meaning |
|---|---|
| station_id | Citi Bike station identifier |
| station_name | Station name |
| latitude | Station latitude |
| longitude | Station longitude |

### Notes

This is an SCD Type 1 station dimension.

Station names and coordinates may change over time in the source data.
The dimension represents the latest known attributes.

Use `find_station` when a user provides a partial or fuzzy station name.

---

## hourly_weather

### Grain

One row per hourly NYC weather observation.

### Important columns

| Column | Meaning |
|---|---|
| weather_time | Weather observation timestamp |
| temperature_2m | Temperature at 2 metres |
| relative_humidity_2m | Relative humidity |
| precipitation | Total precipitation |
| rain | Rain amount |
| snowfall | Snowfall amount |
| cloud_cover | Cloud coverage |
| wind_speed_10m | Wind speed |
| weather_date | NYC calendar date associated with the observation |

### Notes

Weather observations come from Open-Meteo.

Weather timestamps are stored in UTC.

Weather observations are associated with Citi Bike trips by the UTC trip-start
hour.

---

# MCP Analytical Views

## trip_weather_vw

### Grain

One row per Citi Bike trip.

This view combines Citi Bike trip information with the hourly weather
observation corresponding to the trip start hour.

### Important analytical columns

- ride_id
- trip_date
- started_at
- ended_at
- trip_duration_minutes
- rider_type
- start_station_id
- start_station_name
- end_station_id
- end_station_name
- trip_hour
- hour_of_day
- day_of_week
- is_weekend
- temperature_2m
- relative_humidity_2m
- precipitation
- rain
- snowfall
- cloud_cover
- wind_speed_10m
- weather_condition
- temperature_bucket
- is_rainy
- is_snowy
- weather_available

### Caveat

A small number of trips do not have a matching weather observation.
Therefore weather-derived metrics should account for weather availability.

---

## hourly_trip_weather_vw

### Grain

One row per trip-start hour.

This view aggregates trip activity and associates it with hourly weather
conditions.

### Important metrics

- total_trips
- member_trips
- casual_trips
- member_trip_share_pct
- casual_trip_share_pct
- avg_trip_duration_minutes
- median_trip_duration_minutes
- active_start_stations
- rainy_trip_count
- snowy_trip_count

### Important dimensions

- trip_hour
- day_of_week
- hour_of_day
- is_weekend
- temperature_bucket
- weather_condition

---

## daily_trip_weather_vw

### Grain

One row per calendar day.

This view combines daily Citi Bike trip metrics with daily weather
aggregations.

### Trip metrics

- total_trips
- member_trips
- casual_trips
- avg_trip_duration_minutes
- median_trip_duration_minutes
- active_start_stations

### Weather metrics

- average temperature
- average relative humidity
- total precipitation
- total rain
- total snowfall
- average cloud cover
- average wind speed
- rainy weather hours
- snowy weather hours

### Important caveat

Weather metrics are calculated from the hourly weather observations rather
than only from hours in which trips occurred.

---

# Curated MCP Metrics

The `get_metric` tool provides the following predefined metrics.

Curated metrics should be preferred over manually generated SQL whenever
the requested metric is available.

---

## total_trips

### Definition

Total number of Citi Bike trips.

### Formula

```text
COUNT(*)