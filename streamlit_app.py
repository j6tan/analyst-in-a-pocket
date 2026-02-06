import streamlit as st
import json
import os
from style_utils import inject_global_css


# --- 1. GLOBAL CONFIG (Universal De-Squish) ---
st.set_page_config(layout="wide", page_title="Analyst in a Pocket", page_icon="📊")

inject_global_css() # Keep styles active on this page

# --- 2. DATA PERSISTENCE & VAULT ---
DB_FILE = "user_profile_db.json"

def load_profile():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "p1_name": "Investor", "p1_t4": 0.0, "p1_bonus": 0.0, 
        "p1_commission": 0.0, "p1_pension": 0.0, "p2_t4": 0.0,
        "province": "Ontario", "is_pro": False
    }

if 'user_profile' not in st.session_state:
    st.session_state.user_profile = load_profile()

if 'is_pro' not in st.session_state:
    st.session_state.is_pro = st.session_state.user_profile.get("is_pro", False)

# --- 3. DEV TOOLS ---
with st.sidebar:
    st.title("🛠️ Dev Tools")
    st.session_state.is_pro = st.checkbox("Simulate Paid Account", value=st.session_state.is_pro)
    st.divider()

# --- 4. OPTION C NAVIGATION (Grouped Sidebar) ---
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
        st.Page("scripts/mortgage_scenario.py", title="Mortgage Scenarios 🔒", icon="📈"),
        st.Page("scripts/smith_maneuver.py", title="Smith Maneuver 🔒", icon="🛡️"),
        st.Page("scripts/affordability_second.py", title="Secondary Property 🔒", icon="🏢"),
        st.Page("scripts/renewal_scenario.py", title="Renewal Scenario 🔒", icon="🔄"),
        st.Page("scripts/rental_vs_stock.py", title="Rental vs Stock 🔒", icon="📉"),
    ]
}

pg = st.navigation(pages)
pg.run()







