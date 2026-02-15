import streamlit as st
import json
import os
from style_utils import inject_global_css
from data_handler import init_session_state

# --- 1. GLOBAL CONFIG ---
st.set_page_config(
    layout="wide", 
    page_title="Analyst in a Pocket", 
    page_icon="📊",
    initial_sidebar_state="expanded"
)
inject_global_css()

# --- 2. DATA INIT ---
init_session_state()

# --- 3. AUTHENTICATION (SIDEBAR) ---
if "is_pro" not in st.session_state:
    st.session_state.is_pro = False

with st.sidebar:
    st.image("logo.png", width=100) if os.path.exists("logo.png") else None
    
    if not st.session_state.get("is_logged_in", False):
        st.header("🔓 Member Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if password == "paid123":  # Demo Password
                    st.session_state.is_logged_in = True
                    st.session_state.username = username
                    st.session_state.is_pro = True 
                    st.rerun()
                else:
                    st.error("Invalid Credentials")
    else:
        st.success(f"Welcome, {st.session_state.username}")
        if st.button("Logout"):
            st.session_state.is_logged_in = False
            st.session_state.is_pro = False
            st.rerun()

# --- 4. DYNAMIC NAVIGATION SETUP (Option A) ---
is_pro = st.session_state.is_pro

# Helper to create Pro labels and icons
def get_pro_meta(label, icon, is_pro):
    return (label if is_pro else f"{label} 🔒"), (icon if is_pro else "🔒")

# Define Dynamic Metadata for Pro Tools
mort_label, mort_icon = get_pro_meta("Mortgage Scenarios", "📈", is_pro)
smith_label, smith_icon = get_pro_meta("Smith Maneuver", "💰", is_pro)
second_label, second_icon = get_pro_meta("Secondary Property", "🏢", is_pro)
renewal_label, renewal_icon = get_pro_meta("Renewal Scenario", "🔄", is_pro)
duel_label, duel_icon = get_pro_meta("Rental vs Stock", "📉", is_pro)

pages = {
    "Overview": [
        st.Page("home.py", title="Home Dashboard", icon="🏠", default=True),
        st.Page("scripts/profile.py", title="Client Profile", icon="👤"),
    ],
    "Foundations & Budgeting":[
        st.Page("scripts/affordability.py", title="Simple Affordability", icon="🤔"),
        st.Page("scripts/buy_vs_rent.py", title="Buy vs Rent", icon="⚖️"),
    ],
    "Advanced Wealth Strategy": [
        st.Page("scripts/mortgage_scenario.py", title=mort_label, icon=mort_icon),
        st.Page("scripts/affordability_second.py", title=second_label, icon=second_icon),
        st.Page("scripts/renewal_scenario.py", title=renewal_label, icon=renewal_icon),
        st.Page("scripts/rental_vs_stock.py", title=duel_label, icon=duel_icon),
        st.Page("scripts/smith_maneuver.py", title=smith_label, icon=smith_icon),
    ],
    "Account": [
        st.Page("scripts/membership.py", title="Membership 💎", icon="💎")
    ]
}

pg = st.navigation(pages)

# --- 5. THE "SIDEBAR INJECTION" PAYWALL (Bulletproof) ---
pro_titles = [mort_label, smith_label, second_label, renewal_label, duel_label]

if pg.title in pro_titles and not is_pro:
    
    # 1. Inject CSS to heavily blur the MAIN content area
    st.markdown("""
        <style>
            /* Blur the entire main content area */
            [data-testid="stMain"] {
                filter: blur(15px) grayscale(50%);
                pointer-events: none; /* Block clicks on the blurred content */
                user-select: none;    /* Block text highlighting */
                overflow: hidden;
            }
            
            /* Hide the top header to prevent clicking 'Deploy' or 'Settings' */
            header {
                display: none !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # 2. Inject the Membership Card via the SIDEBAR
    # By putting it in the sidebar, it avoids the blur filter applied to "stMain"
    with st.sidebar:
        st.markdown(f"""
        <div style="
            position: fixed; /* Force it out of the sidebar and onto the center screen */
            top: 50%;
            left: 55%; /* Offset slightly to account for sidebar width */
            transform: translate(-50%, -50%);
            z-index: 999999;
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.5);
            text-align: center;
            width: 500px;
            border: 2px solid #CEB36F;
            pointer-events: auto; /* Re-enable clicks for this card */
        ">
            <div style="font-size: 60px; margin-bottom: 15px;">💎</div>
            <h2 style="color: #4A4E5A; margin: 0; font-family: sans-serif;">Unlock {pg.title.replace(' 🔒', '')}</h2>
            
            <p style="color: #6c757d; font-size: 1.1em; margin-top: 15px; line-height: 1.5;">
                You've hit the limit of the Free Tier.<br>
                This tool is restricted to <b>Pro Analysts</b>.
            </p>
            
            <hr style="border: 0; border-top: 1px solid #eee; margin: 25px 0;">
            
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; text-align: left; margin-bottom: 25px;">
                <div style="color: #4A4E5A; font-weight: bold; margin-bottom: 5px;">Pro Benefits:</div>
                <div style="color: #6c757d; font-size: 0.9em;">✅ <b>Unlimited</b> Scenario Storage</div>
                <div style="color: #6c757d; font-size: 0.9em;">✅ <b>Export</b> to PDF Reports</div>
                <div style="color: #6c757d; font-size: 0.9em;">✅ <b>Advanced</b> Yield Calculators</div>
            </div>

            <p style="font-size: 0.9em; color: #CEB36F; font-weight: bold; margin-bottom: 0;">
                🔒 Login via Sidebar or Membership Page to unlock
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Note: We do NOT use st.stop() here. 
    # The script continues, rendering the charts in the background so they appear through the blur.

pg.run()


