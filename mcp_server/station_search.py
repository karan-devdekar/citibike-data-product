from rapidfuzz import process, fuzz
from bigquery_client import run_query,get_client
from datetime import date


def find_stations(search_term: str, limit: int = 5) -> list[dict]:
    """
    Find Citi Bike stations using partial/fuzzy name matching.
    """

    sql = """
        SELECT
            station_id,
            station_name,
            latitude,
            longitude
        FROM `citi-509517.analytics.dim_station`
        WHERE station_name IS NOT NULL
    """

    rows = run_query(sql)

    stations = [
        {
            "station_id": row.station_id,
            "station_name": row.station_name,
            "latitude": row.latitude,
            "longitude": row.longitude,
        }
        for row in rows
    ]

    choices = {
        station["station_name"]: station
        for station in stations
    }

    matches = process.extract(
        search_term,
        choices.keys(),
        scorer=fuzz.WRatio,
        limit=limit,
    )

    results = []

    for station_name, score, _ in matches:
        station = choices[station_name].copy()
        station["match_score"] = round(score, 2)
        results.append(station)

    return results