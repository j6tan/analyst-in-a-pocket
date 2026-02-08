import streamlit as st
import json
import os
from style_utils import inject_global_css
from data_handler import init_session_state, load_user_data

# --- 1. GLOBAL CONFIG (Universal De-Squish) ---
st.set_page_config(
    layout="wide", 
    page_title="Analyst in a Pocket", 
    page_icon="📊",
    initial_sidebar_state="expanded"
)
inject_global_css() # Keep styles active on this page

# --- 2. DATA INIT ---
init_session_state()
# --- 3. AUTHENTICATION SYSTEM (Sidebar) ---
with st.sidebar:
    st.image("logo.png", width=100) if "logo.png" in "." else None
    
    # Check if user is already logged in
    if not st.session_state.get("is_logged_in", False):
        st.header("🔓 Member Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                # SIMPLE AUTH LOGIC (Replace with real DB check later)
                if password == "paid123":  # Demo Password
                    st.session_state.is_logged_in = True
                    st.session_state.username = username
                    st.session_state.is_pro = True # Unlock Pro Features
                    load_user_data(username) # Load their permanent data
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        st.info("Guest Mode Active: Data will be lost when you close the tab.")
    
    else:
        # LOGGED IN VIEW
        st.success(f"Logged in as: **{st.session_state.username}**")
        st.caption("✅ Cloud Sync Active")
        
        if st.button("Logout"):
            st.session_state.is_logged_in = False
            st.session_state.username = None
            st.session_state.is_pro = False
            st.session_state.app_db = {} # Wipe sensitive data from RAM
            st.rerun()
    
    st.divider()

# --- 4. NAVIGATION ---
# Unlock Pro pages only if logged in (or if 'is_pro' is somehow simulated)
is_pro = st.session_state.get("is_pro", False)
lock_icon = "🔓" if is_pro else "🔒"

# --- 5. OPTION C NAVIGATION (Grouped Sidebar) ---
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










