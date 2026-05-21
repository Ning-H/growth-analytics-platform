from __future__ import annotations

import streamlit as st


def configure_page(title: str) -> None:
    st.set_page_config(
        page_title=f"{title} | Growth Analytics Platform",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        #MainMenu, footer, header {visibility: hidden;}
        .block-container {
            padding-top: 2.25rem;
            padding-bottom: 3rem;
            max-width: 1240px;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        [data-testid="stMetric"] {
            background: #f7f9fb;
            border: 1px solid #dce5ef;
            border-radius: 8px;
            padding: 14px 16px;
        }
        .hero {
            background: linear-gradient(135deg, #082f49 0%, #14532d 58%, #7f1d1d 100%);
            border-radius: 8px;
            color: white;
            padding: 34px 36px;
            margin-bottom: 22px;
        }
        .hero h1 {
            font-size: 42px;
            line-height: 1.05;
            margin: 0 0 10px 0;
            letter-spacing: 0;
        }
        .hero p {
            font-size: 18px;
            line-height: 1.45;
            max-width: 780px;
            margin: 0;
        }
        .panel {
            background: #ffffff;
            border: 1px solid #dce5ef;
            border-radius: 8px;
            padding: 16px 18px;
            margin: 8px 0 16px 0;
        }
        .panel h3 {
            margin-top: 0;
            margin-bottom: 8px;
        }
        .problem {
            background: #f7f9fb;
            border-left: 4px solid #0f766e;
            padding: 18px 20px;
            margin: 16px 0 20px 0;
            border-radius: 6px;
        }
        .label {
            color: #0f766e;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .quiet {
            color: #5f6f82;
            font-size: 0.94rem;
        }
        div[data-testid="stAlert"] {
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_intro(title: str, body: str) -> None:
    st.title(title)
    st.caption(body)


def show_sql(sql: str) -> None:
    if not sql:
        return
    with st.expander("View underlying MetricFlow SQL"):
        st.code(sql, language="sql")
