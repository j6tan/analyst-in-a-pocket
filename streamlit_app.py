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

# --- 5. BULLETPROOF FROSTED GLASS PAYWALL ---
pro_titles = [mort_label, smith_label, second_label, renewal_label, duel_label]

if pg.title in pro_titles and not is_pro:
    # We use 'st.markdown' to inject a full-screen overlay that sits ON TOP of the content
    # The 'backdrop-filter' property does the blurring for us.
    st.markdown(f"""
    <style>
        /* 1. The Overlay: Covers the screen, blurs what's behind it */
        .paywall-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-color: rgba(255, 255, 255, 0.1); /* Slight white tint */
            backdrop-filter: blur(12px); /* THE KEY: Blurs everything behind this div */
            -webkit-backdrop-filter: blur(12px); /* Safari support */
            z-index: 99999; /* High enough to cover content, low enough for sidebar */
            display: flex;
            justify-content: center;
            align-items: center;
        }}

        /* 2. The Card: Sharp, centered, and opaque */
        .paywall-card {{
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.3);
            text-align: center;
            width: 450px;
            border: 2px solid #CEB36F;
            z-index: 100000; /* Sits on top of the blur layer */
        }}
        
        /* 3. Sidebar Safety: Force sidebar to sit ABOVE the overlay so login works */
        [data-testid="stSidebar"] {{
            z-index: 100001 !important; 
        }}
    </style>

    <div class="paywall-overlay">
        <div class="paywall-card">
            <div style="font-size: 50px; margin-bottom: 10px;">💎</div>
            <h2 style="color: #4A4E5A; margin: 0;">Unlock {pg.title.replace(' 🔒', '')}</h2>
            <p style="color: #6c757d; font-size: 1.1em; margin-top: 10px;">This is a <b>Pro Analyst Feature</b></p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <div style="text-align: left; display: inline-block; color: #4A4E5A; font-size: 0.95em; line-height: 1.8;">
                ✅ Deep-dive investment comparisons<br>
                ✅ Advanced tax-deductibility modeling<br>
                ✅ Save & Export unlimited scenarios
            </div>
            <div style="margin-top: 30px;">
                <p style="font-size: 0.9em; color: #CEB36F; font-weight: bold;">Login via sidebar to remove the blur.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # NOTE: We do NOT use st.stop() here. 
    # We let the script continue running so the charts generate BEHIND the frosted glass.

pg.run()

