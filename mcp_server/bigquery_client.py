from google.cloud import bigquery


PROJECT_ID = "citi-509517"


def get_client() -> bigquery.Client:
    """Return a BigQuery client for the Citi Bike project."""
    return bigquery.Client(project=PROJECT_ID)


def run_query(sql: str):
    """Execute a BigQuery query and return the result rows."""
    client = get_client()
    query_job = client.query(sql)
    return list(query_job.result())