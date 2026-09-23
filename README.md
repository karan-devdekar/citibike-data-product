# NYC Citi Bike Data Product

Data engineering assignment using NYC Citi Bike trip data
and hourly NYC weather data.

## Project Overview

This project builds an end-to-end data product using:

- NYC Citi Bike trip data
- Open-Meteo historical weather data
- Google Cloud Storage
- BigQuery
- dbt
- Python

## Architecture

Citi Bike / Open-Meteo
        ↓
      GCS
        ↓
   BigQuery RAW
        ↓
       dbt
        ↓
 BigQuery ANALYTICS