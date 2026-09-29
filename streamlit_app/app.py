import streamlit as st

from llm import ask_question_with_data
from charts import create_metric_chart


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Citi Bike Analytics",
    page_icon="🚲",
    layout="wide",
)


# ---------------------------------------------------------
# Page header
# ---------------------------------------------------------

st.title("🚲 Citi Bike Analytics")

st.caption(
    "Ask questions about Citi Bike trips, stations, and weather "
    "using Gemini + MCP."
)


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

with st.sidebar:

    st.header("About")

    st.write(
        """
        This application uses:

        - **Gemini** for natural-language understanding
        - **MCP** as the controlled analytics interface
        - **BigQuery** as the warehouse
        - **dbt** analytical models
        """
    )

    st.divider()

    st.subheader("Available analytics")

    st.write(
        """
        You can ask about:

        - Total trips
        - Average trip duration
        - Member vs casual riders
        - Rainy trips
        - Stations
        - Weather
        - Daily and monthly trends
        - More complex analytical questions
        """
    )

    st.divider()

    st.caption(
        "Data period: January 2020 – December 2021"
    )


# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------

if "messages" not in st.session_state:

    st.session_state.messages = []


# ---------------------------------------------------------
# Helper: chart configuration
# ---------------------------------------------------------

def get_chart_config(metric):
    """
    Return chart configuration for a curated MCP metric.
    """

    if metric == "total_trips":

        return {
            "title": "Citi Bike trips over time",
            "y_axis_title": "Trips",
            "value_format": "number",
        }

    if metric == "avg_trip_duration_minutes":

        return {
            "title": "Average trip duration over time",
            "y_axis_title": "Average duration",
            "value_format": "minutes",
        }

    if metric == "member_trip_share_pct":

        return {
            "title": "Member trip share over time",
            "y_axis_title": "Member trip share",
            "value_format": "percentage",
        }

    if metric == "casual_trip_share_pct":

        return {
            "title": "Casual trip share over time",
            "y_axis_title": "Casual trip share",
            "value_format": "percentage",
        }

    if metric == "rainy_trip_share_pct":

        return {
            "title": "Rainy trip share over time",
            "y_axis_title": "Rainy trip share",
            "value_format": "percentage",
        }

    return {
        "title": "Citi Bike trend",
        "y_axis_title": "Value",
        "value_format": "number",
    }


# ---------------------------------------------------------
# Display previous conversation
# ---------------------------------------------------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(
            message["content"]
        )

        # Render saved chart for previous responses.
        if (
            message["role"] == "assistant"
            and message.get("data")
            and message.get("metric")
        ):

            chart = create_metric_chart(
                result=message["data"],
                title=message.get(
                    "chart_title",
                    "Citi Bike trend",
                ),
                y_axis_title=message.get(
                    "y_axis_title",
                    "Value",
                ),
                value_format=message.get(
                    "value_format",
                    "number",
                ),
            )

            if chart:

                st.plotly_chart(
                    chart,
                    use_container_width=True,
                )


# ---------------------------------------------------------
# Chat input
# ---------------------------------------------------------

question = st.chat_input(
    "Ask a question about Citi Bike analytics..."
)


# ---------------------------------------------------------
# Process question
# ---------------------------------------------------------

if question:

    # ---------------------------------------------
    # Display user question
    # ---------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):

        st.markdown(question)


    # ---------------------------------------------
    # Generate answer
    # ---------------------------------------------

    with st.chat_message("assistant"):

        with st.spinner(
            "Analyzing the Citi Bike warehouse..."
        ):

            try:

                # Get both the natural-language answer
                # and the structured MCP result.
                result = ask_question_with_data(
                    question
                )

                answer = result.get(
                    "answer",
                    "",
                )

                data = result.get(
                    "data"
                )

                metric = result.get(
                    "metric"
                )


                # ---------------------------------
                # Handle empty response
                # ---------------------------------

                if not answer:

                    st.warning(
                        "Gemini returned an empty response."
                    )

                    with st.expander(
                        "Debug details",
                        expanded=True,
                    ):

                        st.write(
                            "Raw response:"
                        )

                        st.write(
                            repr(result)
                        )

                    answer = (
                        "I couldn't generate an answer "
                        "for that question."
                    )


                # ---------------------------------
                # Display answer
                # ---------------------------------

                st.markdown(answer)


                # ---------------------------------
                # Chart configuration
                # ---------------------------------

                chart_config = get_chart_config(
                    metric
                )

                chart_title = chart_config[
                    "title"
                ]

                y_axis_title = chart_config[
                    "y_axis_title"
                ]

                value_format = chart_config[
                    "value_format"
                ]


                # ---------------------------------
                # Create chart
                # ---------------------------------

                chart = None

                # Only create a chart when we have
                # multiple data points.
                if (
                    isinstance(data, list)
                    and len(data) > 1
                    and metric
                ):

                    chart = create_metric_chart(
                        result=data,
                        title=chart_title,
                        y_axis_title=y_axis_title,
                        value_format=value_format,
                    )


                # ---------------------------------
                # Display chart
                # ---------------------------------

                if chart:

                    st.plotly_chart(
                        chart,
                        use_container_width=True,
                    )


                # ---------------------------------
                # Save assistant response
                # ---------------------------------

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "data": data,
                        "metric": metric,
                        "chart_title": chart_title,
                        "y_axis_title": y_axis_title,
                        "value_format": value_format,
                    }
                )


            except Exception as exc:

                error_message = (
                    "I couldn't complete the request. "
                    "Please try again or rephrase "
                    "your question."
                )

                st.error(
                    error_message
                )

                # Keep technical details available
                # while developing locally.
                with st.expander(
                    "Technical details",
                    expanded=True,
                ):

                    st.exception(exc)