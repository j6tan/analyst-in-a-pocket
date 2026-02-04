import streamlit as st
import json

# --- 1. CONFIG & INITIALIZATION ---
st.set_page_config(layout="wide", page_title="FIRE Toolkit")

# Shared data vault (Persists across all pages)
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        "p1_name": "Investor", "p1_t4": 0.0, "province": "Ontario", 
        "setup_complete": False # Track if they filled the profile
    }

# --- 2. DEFINE NATIVE NAVIGATION (SIDEBAR HIDDEN) ---
# Each tool should be its own file in a 'scripts/' folder
pages = [
    st.Page("main_dashboard.py", title="Home", icon="🏠", default=True),
    st.Page("scripts/profile.py", title="Client Profile", icon="👤"),
    st.Page("scripts/affordability.py", title="Affordability", icon="📊"),
    st.Page("scripts/smith_maneuver.py", title="Smith Maneuver", icon="🛡️"),
    st.Page("scripts/buy_vs_rent.py", title="Buy vs Rent", icon="⚖️")
]

# Set position="hidden" to remove the sidebar navigation list
pg = st.navigation(pages, position="hidden") 

# --- 3. RUN THE SELECTED PAGE ---
pg.run()
