# app.py

from database import *
import datetime
import streamlit as st
from pathlib import Path

# ─── Page & CSS Setup ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ME Journal",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Load external CSS
css_path = Path(__file__).parent / "style.css"
st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

def main():
    # ─── Top Navigation (just the header + compact date picker) ─────────────
    with st.container():
        st.markdown("<h1>ME Journal</h1>", unsafe_allow_html=True)
        st.date_input(
            "",
            value=datetime.date.today(),
            label_visibility="collapsed"
        )

    st.divider()

    # ─── Three Panels WITH .block styling ──────────────────────────────────
    col1, col2, col3 = st.columns(3, gap="large")
    with col1:
        st.markdown(
            """
            <div class='block'>
              <h3>Schedule</h3>
              <ul>
                <li>09:00 Morning Routine</li>
                <li>11:00 Team Meeting</li>
                <li>14:00 Creative Work</li>
                <li>18:00 Exercise</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            """
            <div class='block'>
              <h3>Relationships</h3>
              <p><strong>Alice Smith</strong><br/>
              Birthday: March 15<br/>
              Last met: 2 days ago</p>
              <p><strong>Bob Johnson</strong><br/>
              Project partner<br/>
              Deadline: Friday</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            """
            <div class='block'>
              <h3>Mind Space</h3>
              <ul>
                <li>Need to finalize project scope</li>
                <li>Research new UI patterns</li>
                <li>Schedule dentist appointment</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # ─── Thought Input ───────────────────────────────────────────────────────
    st.markdown("### Thought Input")
    with st.form("prompt_form"):
        cols = st.columns([1, 6, 1], gap="medium")
        with cols[0]:
            st.markdown("", unsafe_allow_html=True)
            mode = st.radio(
                "Prompt Mode",
                options=["add", "update"],
                format_func=lambda x: f"{x}",
                horizontal=True,
                key="prompt_mode",
            )
            st.markdown("<div class='prompt-mode'></div>", unsafe_allow_html=True)
        with cols[1]:
            st.markdown("<br>", unsafe_allow_html=True)
            prompt = st.text_input(
                "text",
                placeholder="Reflect on today's achievements...",
                label_visibility="hidden"
            )
        with cols[2]:
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Submit →")
            if submitted:
                st.success(f"Saved `{mode}` prompt: {prompt}")

    st.divider()

    # ─── Knowledge Search ───────────────────────────────────────────────────
    st.markdown("### Knowledge Search")
    query = st.text_input(
        "Search your journal",
        placeholder="Enter search terms...",
        help="Search across all entries and notes"
    )
    if query:
        st.info("🔍 This feature is on its way!")

if __name__ == "__main__":
    main()
