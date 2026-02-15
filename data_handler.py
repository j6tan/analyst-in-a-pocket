import streamlit as st
import json
import os
from supabase import create_client, Client

# --- 1. CONNECTION SETUP ---
@st.cache_resource
def init_supabase():
    """Connects to Supabase using the secrets you just verified."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

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

# --- 2. THE CLOUD LOAD FUNCTION ---
def load_user_data(username):
    """
    Replaces the old JSON file loading. 
    It fetches the 'data' column from Supabase for the specific user.
    """
    try:
        # Search the 'user_vault' table for the matching username
        # Note: In production, we'll use UUIDs, but for your test users, we'll use 'id'
        response = supabase.table("user_vault").select("data").eq("id", username).execute()
        
        if response.data:
            # If user exists, pull their saved JSON into the app
            st.session_state.app_db = response.data[0]['data']
            st.toast(f"☁️ {username.capitalize()}'s data synced from Cloud")
        else:
            # If it's a new user, start with the DEFAULTS already in this file
            st.session_state.app_db = DEFAULTS
            supabase.table("user_vault").insert({"id": username, "data": DEFAULTS}).execute()
            st.toast("🆕 Created new Cloud Vault")
            
    except Exception as e:
        st.error(f"Cloud Load Error: {e}")

# --- 3. THE CLOUD SAVE FUNCTION ---
def update_data(category, key, value):
    """
    The Master Save: Updates the app's 'RAM' instantly, 
    then pushes the entire update to the Supabase Cloud.
    """
    # 1. Update the local session state (RAM) so the UI stays fast
    if 'app_db' not in st.session_state:
        return
        
    st.session_state.app_db[category][key] = value
    
    # 2. If the user is logged in, sync to the Cloud
    if st.session_state.get("is_logged_in", False):
        username = st.session_state.get("username")
        print(f"DEBUG: Attempting to save for {username}...") # ADD THIS
        try:
            res = supabase.table("user_vault").update({
                "data": st.session_state.app_db
            }).eq("id", username).execute()
            print(f"DEBUG: Supabase Response: {res}") # ADD THIS
        except Exception as e:
            print(f"DEBUG: ERROR SAVING TO CLOUD: {e}")
