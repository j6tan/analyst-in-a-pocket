import streamlit as st
import json
import os

# --- CONFIGURATION ---
# In production, this would be a database connection string
MOCK_DB_FOLDER = "user_data_vault"

# Ensure the vault exists (for paid user simulation)
if not os.path.exists(MOCK_DB_FOLDER):
    os.makedirs(MOCK_DB_FOLDER)

# Default Empty Profile Structure
DEFAULTS = {
    "profile": {
        "p1_name": "Investor", "province": "Ontario", "is_pro": False,
        "p1_t4": 0.0, "p1_bonus": 0.0, "p2_t4": 0.0
    },
    "smith": {
        "mortgage_amt": 500000.0, "amortization": 25, "mortgage_rate": 5.0,
        "heloc_rate": 6.0, "inv_return": 7.0, "div_yield": 5.0, 
        "initial_lump": 0.0, "tax_rate": 43.0, 
        "crash_drop": 30, "crash_year": 5, "crash_dur": 3
    },
    "mortgage": {
        "price": 800000.0, "down": 160000.0, "amort": 25
    }
}

def init_session_state():
    """
    Called once on app start.
    Sets up the 'app_db' bucket and basic auth states.
    """
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}

    # NEW: Initialize authentication and pro status defaults
    if 'is_logged_in' not in st.session_state:
        st.session_state.is_logged_in = False
    
    if 'is_pro' not in st.session_state:
        st.session_state.is_pro = False

    # Initialize with Defaults (Guest Mode by default)
    for category, fields in DEFAULTS.items():
        if category not in st.session_state.app_db:
            st.session_state.app_db[category] = {}
        for key, val in fields.items():
            if key not in st.session_state.app_db[category]:
                st.session_state.app_db[category][key] = val

def load_user_data(username):
    """
    PAID FEATURE: Loads data from the 'Cloud' (Simulated JSON file)
    """
    user_file = os.path.join(MOCK_DB_FOLDER, f"{username}.json")
    if os.path.exists(user_file):
        try:
            with open(user_file, "r") as f:
                data = json.load(f)
                st.session_state.app_db = data
                st.toast(f"Welcome back, {username}! Data loaded.", icon="☁️")
        except:
            st.error("Error loading user profile.")
    else:
        # New Paid User - Start fresh
        st.toast(f"Creating new profile for {username}...", icon="🆕")

def update_data(category, key, value):
    """
    The Master Save Function.
    1. Updates the immediate RAM (Session State) so UI is fast.
    2. If Logged In: Saves to the 'Cloud' (File) for permanence.
    """
    # 1. Update RAM (Instant)
    st.session_state.app_db[category][key] = value

    # 2. Check Authentication
    if st.session_state.get("is_logged_in", False):
        user = st.session_state.get("username")
        # Save to 'Cloud'
        user_file = os.path.join(MOCK_DB_FOLDER, f"{user}.json")
        with open(user_file, "w") as f:
            json.dump(st.session_state.app_db, f, indent=4)
