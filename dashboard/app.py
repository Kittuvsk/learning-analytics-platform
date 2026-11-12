
import json
import os
import urllib.request
import urllib.error

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Learning Analytics Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

ENDPOINTS = {
    "Overview": "/analytics/overview",
    "Courses": "/analytics/courses",
    "Assessments": "/analytics/assessments",
    "Engagement": "/analytics/engagement",
    "Cohorts": "/analytics/cohorts",
    "Outcomes": "/analytics/outcomes",
    "Anomalies": "/analytics/anomalies",
    "Processing Runs": "/analytics/processing-runs"
}


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "api_data" not in st.session_state:
    st.session_state.api_data = {}


# --------------------------------------------------
# API CONNECTION
# --------------------------------------------------

def api_request(path, method="GET", payload=None, token=None):

    headers = {"Content-Type": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = None

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        API_URL + path,
        data=data,
        headers=headers,
        method=method
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8")
        raise Exception(f"HTTP {error.code}: {message}")

    except urllib.error.URLError as error:
        raise Exception(f"API connection failed: {error}")


# --------------------------------------------------
# DATA HELPERS
# --------------------------------------------------

def find_records(data):
    """Find the first list of dictionary records in an API response."""

    if isinstance(data, list):
        if data and isinstance(data[0], dict):
            return data
        return []

    if isinstance(data, dict):
        preferred_keys = [
            "records", "courses", "assessments",
            "cohorts", "outcomes", "anomalies",
            "processing_runs", "data", "results"
        ]

        for key in preferred_keys:
            if key in data:
                records = find_records(data[key])
                if records:
                    return records

        for value in data.values():
            if isinstance(value, (dict, list)):
                records = find_records(value)
                if records:
                    return records

    return []


def get_summary(data):
    if not isinstance(data, dict):
        return {}

    for key in ["summary", "metrics"]:
        if isinstance(data.get(key), dict):
            return data[key]

    return data


def show_metrics(summary):

    numeric_items = [
        (key, value)
        for key, value in summary.items()
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
    ]

    if not numeric_items:
        st.info("No numeric summary metrics are available.")
        return

    columns_per_row = 4

    for start in range(0, len(numeric_items), columns_per_row):

        columns = st.columns(columns_per_row)

        for column, (key, value) in zip(
            columns,
            numeric_items[start:start + columns_per_row]
        ):

            label = key.replace("_", " ").title()

            display_value = (
                f"{value:,.2f}"
                if isinstance(value, float)
                else f"{value:,}"
            )

            column.metric(label, display_value)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:

    st.title("📊 Learning Analytics")
    st.caption("Learning Analytics Platform")

    st.divider()

    if not st.session_state.access_token:

        st.subheader("Account Login")

        with st.form("login_form"):

            email = st.text_input("Email address")
            password = st.text_input(
                "Password",
                type="password"
            )

            login_button = st.form_submit_button(
                "Login",
                use_container_width=True
            )

        if login_button:

            try:
                result = api_request(
                    "/auth/login",
                    method="POST",
                    payload={
                        "username_or_email": email,
                        "password": password
                    }
                )

                st.session_state.access_token = result["access_token"]
                st.session_state.user_email = email

                st.rerun()

            except Exception as error:
                st.error(str(error))

    else:

        st.success("Connected")
        st.write(st.session_state.user_email)

        if st.button("Logout", use_container_width=True):

            st.session_state.access_token = None
            st.session_state.user_email = None
            st.session_state.api_data = {}

            st.rerun()

        st.divider()

        selected_page = st.selectbox(
            "Analytics Sections",
            list(ENDPOINTS.keys())
        )

        st.caption("Backend: FastAPI")
        st.caption("Database: MySQL 8")


# --------------------------------------------------
# MAIN APPLICATION
# --------------------------------------------------

st.title("Learning Analytics Platform")

st.caption(
    "Monitor learner activity, course performance, "
    "assessment progress and learning outcomes."
)

if not st.session_state.access_token:

    st.info("Please log in using your registered account.")

else:

    # Header
    col1, col2 = st.columns([4, 1])

    with col1:
        st.subheader(selected_page)

    with col2:
        refresh = st.button(
            "↻ Refresh Data",
            use_container_width=True
        )

    # Fetch data
    if refresh or selected_page not in st.session_state.api_data:

        try:

            with st.spinner("Fetching analytics from backend..."):

                result = api_request(
                    ENDPOINTS[selected_page],
                    token=st.session_state.access_token
                )

                st.session_state.api_data[selected_page] = result

        except Exception as error:
            st.error(str(error))

    result = st.session_state.api_data.get(selected_page)

    if result is not None:

        st.success("Analytics data loaded from FastAPI.")

        summary = get_summary(result)

        # KPI SECTION
        # KPI SECTION
        # KPI SECTION
        st.markdown("### Key Performance Indicators")

        if selected_page == "Outcomes":
            outcome_summary = summary.copy()

            content_completion = outcome_summary.pop(
            "average_content_completion_percent", None
            )

            show_metrics(outcome_summary)

            st.info("Content Completion: Not calculated")

        else:
            show_metrics(summary)
        st.divider()

        # CHARTS AND TABLES
        records = find_records(result)

        if records:

            dataframe = pd.json_normalize(records)

            st.markdown("### Data Visualization")

            numeric_columns = dataframe.select_dtypes(
                include="number"
            ).columns.tolist()

            categorical_columns = dataframe.select_dtypes(
                include=["object", "category"]
            ).columns.tolist()

            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:

                if categorical_columns:

                    category = st.selectbox(
                        "Select category",
                        categorical_columns,
                        key=f"{selected_page}_category"
                    )

                    chart_data = (
                        dataframe[category]
                        .fillna("Unknown")
                        .astype(str)
                        .value_counts()
                        .head(15)
                        .reset_index()
                    )

                    chart_data.columns = ["Category", "Count"]

                    figure = px.bar(
                        chart_data,
                        x="Category",
                        y="Count",
                        title=f"{category.replace('_', ' ').title()} Distribution"
                    )

                    st.plotly_chart(
                        figure,
                        use_container_width=True
                    )

            with chart_col2:

                if numeric_columns:

                    metric = st.selectbox(
                        "Select numeric metric",
                        numeric_columns,
                        key=f"{selected_page}_metric"
                    )

                    chart_data = dataframe.nlargest(
                        min(15, len(dataframe)),
                        metric
                    )

                    label_column = (
                        categorical_columns[0]
                        if categorical_columns
                        else dataframe.columns[0]
                    )

                    figure = px.bar(
                        chart_data,
                        x=label_column,
                        y=metric,
                        title=f"Top Records by {metric.replace('_', ' ').title()}"
                    )

                    st.plotly_chart(
                        figure,
                        use_container_width=True
                    )

            st.divider()

            st.markdown("### Detailed Records")

            st.dataframe(
                dataframe,
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                f"Records displayed: {len(dataframe):,}"
            )

        else:

            st.info(
                "No detailed records are currently available "
                "for this section."
            )

        # DEBUG SECTION
        with st.expander("View Raw API Response"):

            st.json(result)

    else:

        st.info("Click Refresh Data to retrieve analytics.")
