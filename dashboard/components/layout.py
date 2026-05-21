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
        :root {
            --tt-black: #010101;
            --tt-cyan: #25F4EE;
            --tt-red: #FE2C55;
            --tt-ink: #15171a;
            --tt-muted: #667085;
            --tt-line: #e5e7eb;
            --tt-soft: #f8fafc;
        }
        .block-container {
            padding-top: 2.25rem;
            padding-bottom: 3rem;
            max-width: 1240px;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        [data-testid="stMetric"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid var(--tt-line);
            border-top: 3px solid var(--tt-cyan);
            border-radius: 8px;
            padding: 14px 16px;
        }
        .hero {
            background:
                linear-gradient(135deg, rgba(37,244,238,0.28) 0%, rgba(1,1,1,0) 34%),
                linear-gradient(315deg, rgba(254,44,85,0.26) 0%, rgba(1,1,1,0) 36%),
                #010101;
            border-radius: 8px;
            color: white;
            padding: 34px 36px;
            margin-bottom: 22px;
            border: 1px solid #1f2937;
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
            border: 1px solid var(--tt-line);
            border-radius: 8px;
            padding: 16px 18px;
            margin: 8px 0 16px 0;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        }
        .panel h3 {
            margin-top: 0;
            margin-bottom: 8px;
        }
        .problem {
            background: linear-gradient(90deg, rgba(37,244,238,0.10), rgba(254,44,85,0.08));
            border-left: 4px solid var(--tt-cyan);
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
        .tt-red {
            color: var(--tt-red);
            font-weight: 700;
        }
        .tt-cyan {
            color: #0891b2;
            font-weight: 700;
        }
        .comparison-note {
            border-left: 4px solid var(--tt-red);
            background: #fff7f9;
            border-radius: 6px;
            padding: 14px 16px;
            margin: 10px 0 18px 0;
        }
        .quiet {
            color: var(--tt-muted);
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
