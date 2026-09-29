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

# Citi Bike Data Product — MCP Warehouse Assistant

## Overview

This project implements a data engineering pipeline and a Model Context
Protocol (MCP) server that allows an LLM to answer questions about NYC
Citi Bike data safely and consistently.

The warehouse contains Citi Bike trip data from January 2020 through
December 2021 together with hourly NYC weather observations.

The project has two major stages:

1. Data ingestion and transformation using Google Cloud Platform and dbt.
2. A Python MCP server that provides safe, curated access to the analytical
   warehouse.

---

# Architecture

```text
                    Citi Bike Source Data
                            |
                            v
                    Google Cloud Storage
                            |
                            v
                  Cloud Run Ingestion Jobs
                            |
                            v
                        BigQuery
                       raw layer
                            |
                            v
                           dbt
                            |
                            v
                    BigQuery Analytics
                            |
              +-------------+-------------+
              |             |             |
              v             v             v
        Trip/Weather   Hourly Weather   Daily Weather
           Views           Views           Views
              |             |             |
              +-------------+-------------+
                            |
                            v
                    Python MCP Server
                            |
          +-----------------+-----------------+
          |                 |                 |
          v                 v                 v
    Data Dictionary    Curated Metrics   Guarded SQL
          |                 |                 |
          |                 v                 |
          |           Station Lookup          |
          |                 |                 |
          +-----------------+-----------------+
                            |
                            v
                    MCP Inspector / LLM