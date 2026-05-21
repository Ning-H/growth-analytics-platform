from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dashboard.components.data import ask_agent
from dashboard.components.layout import configure_page, page_intro


configure_page("Ask The Data")
page_intro(
    "Ask The Data",
    "Ask plain-English growth questions. The assistant can only use governed MetricFlow metrics.",
)

suggestions = [
    "What was our DAU last week?",
    "Which channel has the most time decay attributed revenue?",
    "Show funnel dropoff by objective.",
    "What is our retention rate by week since signup?",
    "Which channel drove the most new signups?",
]

st.sidebar.subheader("Try asking")
for suggestion in suggestions:
    if st.sidebar.button(suggestion, use_container_width=True):
        st.session_state["pending_question"] = suggestion

use_openai = st.sidebar.toggle("Use OpenAI answer synthesis", value=True)

if "messages" not in st.session_state:
    st.session_state["messages"] = []

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("data"):
            st.dataframe(pd.DataFrame(message["data"]), hide_index=True, use_container_width=True)
        if message.get("sql"):
            with st.expander("View underlying SQL"):
                st.code(message["sql"], language="sql")

pending = st.session_state.pop("pending_question", None)
question = pending or st.chat_input("Ask about attribution, CAC, ROAS, funnel, retention, or active users")

if question:
    st.session_state["messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.status("Working on your question...", expanded=True) as status:
            st.write("Interpreting the business question")
            time.sleep(0.2)
            st.write("Selecting the governed MetricFlow metric")
            time.sleep(0.2)
            st.write("Running the warehouse-backed MetricFlow query")
            result = ask_agent(question, use_openai=use_openai)
            if result.get("underlying_sql"):
                st.write("Preparing chart and audit SQL")
            if use_openai:
                st.write("Synthesizing the business-language answer")
            status.update(label="Answer ready", state="complete", expanded=False)
        st.markdown(result["answer"])
        if result.get("data_preview"):
            frame = pd.DataFrame(result["data_preview"])
            st.dataframe(frame, hide_index=True, use_container_width=True)
            numeric_columns = [
                column for column in frame.columns if pd.to_numeric(frame[column], errors="coerce").notna().any()
            ]
            if len(frame.columns) >= 2 and numeric_columns:
                chart_value = numeric_columns[-1]
                chart_label = next((column for column in frame.columns if column != chart_value), None)
                if chart_label:
                    chart_frame = frame.copy()
                    chart_frame[chart_value] = pd.to_numeric(chart_frame[chart_value], errors="coerce")
                    st.bar_chart(chart_frame.set_index(chart_label)[chart_value], use_container_width=True)
        if result.get("underlying_sql"):
            with st.expander("View underlying SQL"):
                st.code(result["underlying_sql"], language="sql")

    st.session_state["messages"].append(
        {
            "role": "assistant",
            "content": result["answer"],
            "data": result.get("data_preview", []),
            "sql": result.get("underlying_sql", ""),
        }
    )
