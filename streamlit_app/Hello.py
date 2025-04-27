import streamlit as st
import base64
from pathlib import Path

st.set_page_config(page_title="Landing Page", layout="wide")

# Path to your local background image and logo
img_path = Path(__file__).parent / "resources/Landing.jpeg"
logo_path = Path(__file__).parent / "resources/Melogo.png"  # Assuming logo is in the resources folder
icon_path = Path(__file__).parent / "resources/Restack.png"  # Add path to the new image (next to the text)

# Encode the image as base64
def get_base64(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Get base64 encoded versions of the background, logo, and new icon images
img_base64 = get_base64(img_path)
logo_base64 = get_base64(logo_path)
icon_base64 = get_base64(icon_path)  # Get the base64 for the new image

# Sidebar Custom Styling
st.markdown("""
<style>
    /* Sidebar Styling */
    [data-testid=stSidebar] {
        background-color: #000000;  /* Darker background for the sidebar */
        color: white;  /* White text color */
        border-radius: 15px;  /* Rounded corners for the sidebar */
        box-shadow: 4px 0px 8px rgba(0, 0, 0, 0.2);  /* Subtle shadow for the sidebar */
        padding: 20px;  /* Add some padding inside the sidebar */
    }
    
    /* Sidebar Header Styling */
    [data-testid=stSidebar] .sidebar-content h1 {
        font-family: 'Manrope', sans-serif;
        font-size: 24px;
        color: white;
    }

    /* Sidebar Link Styling */
    .css-1n6k2ms a {
        font-size: 18px;
        color: white;
        text-decoration: none;
        padding: 10px;
    }

    /* Sidebar link hover effect */
    .css-1n6k2ms a:hover {
        background-color: rgba(255, 255, 255, 0.1);
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Inject custom CSS and font
st.markdown(
    f"""
<style>
    /* Importing Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;600;800&display=swap'); /* For h1 */
    @import url('https://fonts.googleapis.com/css2?family=General+Sans:wght@300;400;600;700&display=swap'); /* For p and a */

    /* Set body background */
    .stApp {{
        background-image: url("data:image/jpg;base64,{img_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        height: 100vh;
        width: 100vw;
        font-family: 'General Sans', sans-serif;  /* Apply General Sans to the body */
    }}

    /* Center the content (text and button) */
    .center-div {{
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100vh;
        text-align: center;
    }}

    /* Styling for heading */
    h1 {{
        color: white;
        margin-bottom: 40px;
        font-family: 'Manrope', sans-serif;  /* Apply Manrope font to heading */
    }}

    /* Styling for transparent button */
    .button {{
        background-color: transparent;  /* Make the background transparent */
        color: white;  /* Text color remains white */
        padding: 15px 30px;
        border: 2px solid white;  /* Add a white border to the button */
        border-radius: 10px;
        text-decoration: none;
        font-size: 1.5em;
        font-family: 'General Sans', sans-serif;  /* Apply General Sans font to the button */
    }}

    /* Remove default link styles (like blue color and underline) */
    a {{
        text-decoration: none;
        color: inherit; /* Inherit the color from parent */
    }}

    /* When the link is hovered */
    .button:hover {{
        background-color: rgba(255, 255, 255, 0.2);  /* Light transparent background on hover */
        border: 2px solid white;
        color: white;
    }}

    /* When the link is clicked */
    .button:active {{
        background-color: rgba(255, 255, 255, 0.3);  /* Slightly more transparent on click */
        border: 2px solid white;
        color: white;
    }}

    .powered-div {{
        display: flex;
        align-items: center;  /* Vertically center the text and image */
        justify-content: center;  /* Center the content horizontally */
    }}

    .powered-div h1 {{
        margin: 0;  /* Remove default margin of h1 */
        padding: 0;  /* Remove default padding of h1 */
        display: inline-block;  /* Make h1 act like an inline element */
    }}

    .powered-div img {{
        width: 120px;  /* Increase the size of the image */
        margin-left: 10px;  /* Space between text and image */
        vertical-align: middle;  /* Ensures the image aligns vertically with the text */

    /* Footer Styling */
    .footer {{ 
        display: flex;  /* Enables flexbox */
        justify-content: center;  /* Horizontally center the content */
        align-items: center;  /* Vertically center the content */
        position: fixed;
        bottom: 0;
        width: 100%;
        background-color: #070000;
        color: white;
        text-align: center;
        padding: 10px 0;
        font-size: 1em;
        box-shadow: 0 -2px 5px rgba(0, 0, 0, 0.1);
    }}

    .footer a:hover {{ 
        text-decoration: underline;
    }}
    .footer a {{
        color: white;  /* Inherit the color from the parent, so it will be white */
        text-decoration: none;  /* Remove underline */
    }}
    }}
</style>
    """,
    unsafe_allow_html=True
)

# Content (Add the logo above the heading)
st.markdown(
    f"""
    <div class="center-div">
        <!-- Add Logo Above the Heading -->
        <img src="data:image/png;base64,{logo_base64}" width="500vh" />
    <p style="font-size:2em; color: grey; max-width: 700px; margin: 20px auto; line-height: 1.6;">
        TRACK YOUR <span style="color: white;">THOUGHTS 🧠</span>, <span style="color: white;">DAILY ACTIVITIES 🗓️</span>, AND <span style="color: white;">RELATIONSHIPS ❤️</span>. 
    </p>        
    </div>
    """,
    unsafe_allow_html=True
)


# Content for "Powered by Restack" text with the icon next to it
st.markdown(
    f"""
    <div class="powered-div">
        <h1>Powered by</h1>
        <img src="data:image/png;base64,{icon_base64}" alt="Icon" />
    </div>
    """,
    unsafe_allow_html=True
)

# Content for the button
st.markdown(
    f"""
    <div class="center-div">
        <a href="/Home" class="button" style="text-decoration: none; color: white;">Get Started 🤘 </a>    
    </div>
    """,
    unsafe_allow_html=True
)

# Footer content
st.markdown(
    """
    <div class="footer">
        <p>© 2025 ME | <a href="mailto:TZM2002@protonmail.com" target="_blank" style="text-decoration: underline; color: white;">Contact Us</a></p>
    </div>
    """,
    unsafe_allow_html=True
)