from mcp.server import MCPServer

from metrics import get_metric as calculate_metric
from station_search import find_stations
from query_guard import run_readonly_query as execute_readonly_query
from pathlib import Path

mcp = MCPServer(
    "Citi Bike Analytics",
    instructions=(
        "Use this server to answer questions about the Citi Bike analytics warehouse. "
        "Prefer curated metrics over arbitrary SQL queries."
    ),
)


@mcp.resource("warehouse://data-dictionary")
def data_dictionary() -> str:
    """Return the warehouse data dictionary for LLM context."""

    dictionary_path = Path(__file__).parent / "data_dictionary.md"

    return dictionary_path.read_text(
        encoding="utf-8"
    )


@mcp.tool()
def ping() -> str:
    """Check that the Citi Bike MCP server is running."""
    return "Citi Bike MCP server is running."


@mcp.tool()
def find_station(search_term: str, limit: int = 5) -> list[dict]:
    """
    Find Citi Bike stations using a partial or fuzzy station name.

    Returns matching station IDs, names, coordinates, and similarity scores.
    """
    if not search_term.strip():
        raise ValueError("search_term cannot be empty")

    if limit < 1 or limit > 10:
        raise ValueError("limit must be between 1 and 10")

    return find_stations(search_term.strip(), limit)

@mcp.tool()
def get_metric(
    metric: str,
    grain: str,
    start_date: str,
    end_date: str,
    station: str | None = None,
) -> list[dict]:
    """
    Return a curated Citi Bike metric for a date range.

    Supported metrics:
    - total_trips
    - avg_trip_duration_minutes
    - member_trip_share_pct
    - casual_trip_share_pct
    - rainy_trip_share_pct

    Supported grains:
    - day
    - month

    station is optional and can be a partial or fuzzy station name.
    """

    station_id = None

    if station:
        matches = find_stations(station.strip(), limit=1)

        if not matches:
            raise ValueError(
                f"No station found matching: {station}"
            )

        best_match = matches[0]
        station_id = best_match["station_id"]

    return calculate_metric(
        metric=metric,
        grain=grain,
        start_date=start_date,
        end_date=end_date,
        station_id=station_id,
    )

@mcp.tool()
def run_readonly_query(sql: str) -> dict:
    """
    Execute a safe read-only SQL query against approved analytics tables.

    Only SELECT statements are allowed. Queries are restricted to approved
    analytics tables, limited to 1000 rows, and rejected if estimated
    bytes processed exceed the configured cost limit.
    """
    try:
        return execute_readonly_query(sql)

    except ValueError as e:
        return {
            "blocked": True,
            "reason": str(e),
        }

if __name__ == "__main__":
    mcp.run()