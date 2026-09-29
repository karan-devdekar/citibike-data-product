import json
import os

from google import genai
from google.genai import types

from mcp_client import call_tool, read_resource



MODEL_NAME = "gemini-3.8-flash"


def get_client():
    """Create the Gemini client."""

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable is not set."
        )

    return genai.Client(api_key=api_key)


def get_data_dictionary():
    """Read the warehouse data dictionary from the MCP server."""

    result = read_resource(
        "warehouse://data-dictionary"
    )

    # MCP returns a ReadResourceResult containing contents.
    if not result.contents:
        return ""

    return result.contents[0].text


# ---------------------------------------------------------
# MCP-backed functions exposed to Gemini
# ---------------------------------------------------------

def get_metric(
    metric: str,
    grain: str,
    start_date: str,
    end_date: str,
    station: str = "",
):
    """
    Get a predefined Citi Bike metric from the Citi Bike warehouse.

    IMPORTANT:

    The metric parameter must be exactly one of:

    - total_trips
    - avg_trip_duration_minutes
    - member_trip_share_pct
    - casual_trip_share_pct
    - rainy_trip_share_pct

    Grain must be exactly:

    - day
    - month

    For station-specific metrics, the station parameter must be
    the exact station NAME returned by find_station.

    Do NOT pass the station_id.

    For total_trips with a station specified, the metric represents
    trips involving that station according to the warehouse metric
    definition.

    If this tool returns a successful result, use that result directly
    and do not query the warehouse again using run_readonly_query.
    """

    # Normalize common natural-language aliases.
    metric_aliases = {
        "total trips": "total_trips",
        "total_trip": "total_trips",
        "member trip share": "member_trip_share_pct",
        "member trip share percentage": "member_trip_share_pct",
        "member percentage": "member_trip_share_pct",
        "member share": "member_trip_share_pct",
        "casual trip share": "casual_trip_share_pct",
        "casual percentage": "casual_trip_share_pct",
        "casual share": "casual_trip_share_pct",
        "average trip duration": "avg_trip_duration_minutes",
        "avg trip duration": "avg_trip_duration_minutes",
        "rainy trip share": "rainy_trip_share_pct",
        "rain percentage": "rainy_trip_share_pct",
    }

    normalized_metric = metric.strip().lower()

    normalized_metric = metric_aliases.get(
        normalized_metric,
        normalized_metric,
    )

    valid_metrics = {
        "total_trips",
        "avg_trip_duration_minutes",
        "member_trip_share_pct",
        "casual_trip_share_pct",
        "rainy_trip_share_pct",
    }

    if normalized_metric not in valid_metrics:

        return {
            "error": True,
            "message": (
                f"Invalid metric '{metric}'. "
                f"Valid metrics are: "
                f"{', '.join(sorted(valid_metrics))}"
            ),
        }

    arguments = {
        "metric": normalized_metric,
        "grain": grain,
        "start_date": start_date,
        "end_date": end_date,
    }

    if station:
        arguments["station"] = station

    result = call_tool(
        "get_metric",
        arguments,
    )

    return extract_mcp_result(result)


def find_station(
    search_term: str,
    limit: int = 5,
):
    """
    Find Citi Bike stations using a partial or fuzzy station name.
    """

    result = call_tool(
        "find_station",
        {
            "search_term": search_term,
            "limit": limit,
        },
    )

    return extract_mcp_result(result)


def run_readonly_query(sql: str):
    """
    Execute a guarded, read-only SELECT query against
    approved analytical warehouse objects.

    The MCP server enforces SELECT-only access,
    approved tables, row limits, and a bytes-billed cap.
    """

    result = call_tool(
        "run_readonly_query",
        {
            "sql": sql,
        },
    )

    return extract_mcp_result(result)


def extract_mcp_result(result):
    """
    Convert the MCP CallToolResult into a Python object
    that Gemini can consume.
    """

    if getattr(result, "is_error", False):
        return {
            "error": True,
            "message": "MCP tool returned an error.",
        }

    # Prefer structured content when available.
    structured = getattr(
        result,
        "structured_content",
        None,
    )

    if structured:
        return structured.get(
            "result",
            structured,
        )

    # Fall back to text content.
    content = getattr(
        result,
        "content",
        [],
    )

    for item in content:

        text = getattr(
            item,
            "text",
            None,
        )

        if text:

            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text

    return None


# ---------------------------------------------------------
# Gemini + MCP
# ---------------------------------------------------------

def ask_question_with_data(question: str):
    """
    Ask Gemini a warehouse question using MCP tools.

    Returns:
        {
            "answer": str,
            "data": list | dict | None,
            "metric": str | None
        }
    """

    client = get_client()

    data_dictionary = get_data_dictionary()

    system_instruction = f"""
You are a Citi Bike analytics assistant.

You answer questions using the Citi Bike warehouse through
the provided MCP tools.

IMPORTANT RULES:

1. Always use MCP tools for warehouse data.
2. Never invent, estimate, or alter warehouse results.
3. Prefer get_metric whenever the requested metric is available.
4. Use find_station when the user provides a partial or fuzzy
   station name.

5. For a station-specific question:
   - First use find_station.
   - Identify the best exact station_name match.
   - Pass the station_name to get_metric.
   - NEVER pass the station_id to get_metric.
   - If get_metric returns a successful result, STOP calling tools
     and answer the user using that result.
   - Do NOT verify or recalculate a successful get_metric result
     with run_readonly_query.

6. Use run_readonly_query only when get_metric genuinely cannot
   answer the question.

7. Never query raw warehouse tables directly.
8. Never use information_schema.

9. For get_metric, use ONLY these exact metric names:

   - total_trips
   - avg_trip_duration_minutes
   - member_trip_share_pct
   - casual_trip_share_pct
   - rainy_trip_share_pct

10. For get_metric, grain must be exactly:
    - day
    - month

11. If a tool returns an error, correct the tool arguments
    rather than repeatedly calling the same invalid request.

12. Do not make unnecessary tool calls.

13. Respect all definitions and caveats in the data dictionary.

14. If no matching data exists, clearly tell the user.

15. After receiving successful tool results, provide a concise
    natural-language answer using the returned values.

16. Do not expose internal tool calls, MCP implementation details,
    or SQL unless the user explicitly asks for them.

17. IMPORTANT TOOL-USE RULE:
    When get_metric returns a successful non-empty result, treat
    that result as authoritative for the requested metric.
    Do not call another tool to independently calculate the same
    metric.

DATA DICTIONARY:

{data_dictionary}
"""

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[
            get_metric,
            find_station,
            run_readonly_query,
        ],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
    )

    # Conversation history used for manual function calling.
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=question)
            ],
        )
    ]

    # Store the most recent successful analytical result.
    last_data_result = None
    last_metric_name = None

    # Application-level safety limit.
    max_tool_rounds = 6

    for _ in range(max_tool_rounds):

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=config,
        )

        # -------------------------------------------------
        # Gemini returned the final natural-language answer
        # -------------------------------------------------
        if response.text:
            return {
                "answer": response.text,
                "data": last_data_result,
                "metric": last_metric_name,
            }

        if not response.candidates:
            return {
                "answer": "Gemini did not return a response.",
                "data": last_data_result,
                "metric": last_metric_name,
            }

        model_content = response.candidates[0].content

        if not model_content or not model_content.parts:
            return {
                "answer": "Gemini returned an empty response.",
                "data": last_data_result,
                "metric": last_metric_name,
            }

        # -------------------------------------------------
        # Find function calls requested by Gemini
        # -------------------------------------------------
        function_calls = []

        for part in model_content.parts:

            function_call = getattr(
                part,
                "function_call",
                None,
            )

            if function_call:
                function_calls.append(function_call)

        # -------------------------------------------------
        # No function call -> try extracting text manually
        # -------------------------------------------------
        if not function_calls:

            text_parts = []

            for part in model_content.parts:

                text = getattr(
                    part,
                    "text",
                    None,
                )

                if text:
                    text_parts.append(text)

            if text_parts:
                return {
                    "answer": "\n".join(text_parts),
                    "data": last_data_result,
                    "metric": last_metric_name,
                }

            return {
                "answer": (
                    "Gemini completed the request but did not "
                    "return a textual answer."
                ),
                "data": last_data_result,
                "metric": last_metric_name,
            }

        # Add Gemini's function-call message to conversation.
        contents.append(model_content)

        function_response_parts = []

        # -------------------------------------------------
        # Execute requested functions
        # -------------------------------------------------
        for function_call in function_calls:

            function_name = function_call.name

            function_args = dict(
                function_call.args or {}
            )

            print(
                f"[Gemini tool call] "
                f"{function_name}({function_args})"
            )

            try:

                if function_name == "get_metric":

                    result = get_metric(
                        **function_args
                    )

                    # Save successful analytical results
                    # for the chart layer.
                    if (
                        isinstance(result, list)
                        and result
                        and not any(
                            isinstance(item, dict)
                            and item.get("error")
                            for item in result
                        )
                    ):
                        last_data_result = result

                        last_metric_name = (
                            function_args.get("metric")
                        )

                elif function_name == "find_station":

                    result = find_station(
                        **function_args
                    )

                elif function_name == "run_readonly_query":

                    result = run_readonly_query(
                        **function_args
                    )

                else:

                    result = {
                        "error": True,
                        "message": (
                            f"Unknown tool requested: "
                            f"{function_name}"
                        ),
                    }

            except Exception as exc:

                result = {
                    "error": True,
                    "message": str(exc),
                }

            print(
                "[Gemini tool result] "
                f"{json.dumps(result, default=str)[:2000]}"
            )

            # Send the tool result back to Gemini.
            #
            # IMPORTANT:
            # Do not pass id= here because the installed
            # google-genai SDK does not support that argument.
            function_response_parts.append(
                types.Part.from_function_response(
                    name=function_name,
                    response={
                        "result": result
                    },
                )
            )

        # Add MCP results to the conversation.
        contents.append(
            types.Content(
                role="user",
                parts=function_response_parts,
            )
        )

    # -----------------------------------------------------
    # Tool-call safety limit reached
    # -----------------------------------------------------
    return {
        "answer": (
            "I couldn't complete the request within the "
            "allowed number of tool calls. Please try "
            "rephrasing your question."
        ),
        "data": last_data_result,
        "metric": last_metric_name,
    }


def ask_question(question: str):
    """
    Backward-compatible wrapper.

    Returns only the natural-language answer so existing
    Streamlit code continues to work.
    """

    result = ask_question_with_data(question)

    return result["answer"]
# ---------------------------------------------------------
# Test
# ---------------------------------------------------------

def main():

    print("========================================")
    print("GEMINI + MCP TEST")
    print("========================================")

    question = (
        "How many total Citi Bike trips were there "
        "in each month from January 2020 through March 2020?"
    )

    print("\nQuestion:")
    print(question)

    print("\nAsking Gemini...\n")

    answer = ask_question(question)

    print("Gemini answer:")
    print(answer)

    print("\n========================================")
    print("GEMINI + MCP TEST COMPLETED")
    print("========================================")


if __name__ == "__main__":
    main()