from database import *
import datetime
import streamlit as st
from pathlib import Path
import base64

# ─── Page & CSS Setup ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ME",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Path to your local background image and logo
img_path = Path(__file__).parent.parent / "resources/Landing.jpeg"  # Navigate up one level and access 'resources'
logo_path = Path(__file__).parent.parent / "resources/Melogo.png"  # Same for the logo
# Encode the images as base64
def get_base64(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

img_base64 = get_base64(img_path)
logo_base64 = get_base64(logo_path)

# Safer CSS loading
css_path = Path(__file__).parent / "style.css"
if css_path.exists():
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Inject custom CSS and JavaScript to collapse sidebar
st.markdown(
    f"""
    <style>
    /* Set body background */
    .stApp {{
        background-image: url("data:image/jpg;base64,{img_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        height: 100vh;
        width: 100vw;
    }}

    /* Center the content */
    .center-div {{
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100vh;
        text-align: center;
        padding: 0 10%;  /* Add some padding for responsiveness */
    }}

    /* Styling for the logo container */
    .logo-container {{
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 30px; /* Space between logo and heading */
    }}

    /* Styling for logo image */
    .logo {{
        width: 40vw;  /* 40% of the viewport width */
        max-width: 300px;  /* Max width to prevent logo from becoming too large */
    }}

    /* Styling for heading */
    h1 {{
        color: white;
        text-shadow: 2px 2px 4px black;
        margin-bottom: 20px;
        font-size: 4vw;  /* Scalable font size */
    }}

    /* Styling for button */
    .button {{
        background-color: #070000; /* Dark background */
        color: white; /* White text */
        padding: 15px 30px;
        border-radius: 10px;
        text-decoration: none;
        font-size: 1.5em;
        border: 2px solid #070000; /* Dark border */
        transition: all 0.3s ease;
        margin-top: 20px;  /* Space between button and heading */
    }}

    /* When the link is hovered */
    .button:hover {{
        background-color: #070000;
        color: white;
        border: 2px solid #070000;
    }}

    /* When the link is clicked */
    .button:active {{
        background-color: #070000;
        color: white;
        border: 2px solid #070000;
    }}
    </style>
    <script>
    // Collapsing the sidebar on page load
    window.onload = function() {{
        const sidebar = document.querySelector('.css-1d391kg');
        if (sidebar) {{
            sidebar.style.display = 'none';
        }}
    }};
    </script>
    """,
    unsafe_allow_html=True
)

def main():
    # ─── Top Navigation (just the header + compact date picker) ─────────────
    with st.container():
        st.markdown("<h1>ME</h1>", unsafe_allow_html=True)
        st.date_input(
            "Journal Date",                   # non-empty label for accessibility
            value=datetime.date.today(),
            label_visibility="collapsed"      # still visually hidden
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
            mode = st.radio(
                "Prompt Mode",
                options=["add", "update"],
                format_func=lambda x: f"{x}",
                horizontal=True,
                key="prompt_mode",
            )
        with cols[1]:
            prompt = st.text_input(
                "Thought prompt",                     # non-empty, but hidden
                placeholder="Reflect on today's achievements...",
                label_visibility="hidden"
            )
        with cols[2]:
            submitted = st.form_submit_button("Submit →")
            if submitted:
                st.success(f"Saved {mode} prompt: {prompt}")

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