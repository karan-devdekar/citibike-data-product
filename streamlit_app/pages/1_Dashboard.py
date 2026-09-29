import streamlit as st

from dashboard import render_dashboard


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Citi Bike Dashboard",
    page_icon="📊",
    layout="wide",
)


# ---------------------------------------------------------
# Render dashboard
# ---------------------------------------------------------

render_dashboard()