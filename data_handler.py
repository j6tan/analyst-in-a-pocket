import streamlit as st
from supabase import create_client, Client

# --- 1. SAFE SUPABASE INITIALIZATION ---
@st.cache_resource
def init_supabase():
    try:
        # Use .get() to avoid crashing if keys are temporarily missing
        # We check both top-level keys AND nested [supabase] keys just in case
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        
        # Fallback: check if they are nested under a [supabase] header
        if not url and "supabase" in st.secrets:
             url = st.secrets["supabase"].get("SUPABASE_URL")
             key = st.secrets["supabase"].get("SUPABASE_KEY")

        # Only connect if we found valid credentials
        if url and key:
            return create_client(url, key)
        return None
    except Exception:
        # If anything goes wrong, return None (Offline Mode) instead of crashing
        return None

# Initialize the client 
supabase = init_supabase()

# --- 2. INPUT WIDGET HELPER ---
def cloud_input(label, section, key, input_type="number", step=None):
    # Ensure DB structure exists
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    if section not in st.session_state.app_db:
        st.session_state.app_db[section] = {}
    
    # Get current value (or default)
    val = st.session_state.app_db[section].get(key)
    
    if val is None:
        val = 0.0 if input_type == "number" else ""

    # Create Widget
    if input_type == "number":
        new_val = st.number_input(label, value=float(val), step=step, key=f"{section}_{key}")
    else:
        new_val = st.text_input(label, value=str(val), key=f"{section}_{key}")
        
    # Update Local DB immediately
    st.session_state.app_db[section][key] = new_val
    return new_val

# --- 3. SYNC HELPER FOR RADIOS/SELECTBOXES ---
def sync_widget(key_path):
    # Splits "profile:housing_status" into ["profile", "housing_status"]
    section, key = key_path.split(":")
    if section not in st.session_state.app_db:
        st.session_state.app_db[section] = {}
    
    # Update the DB with the new widget value
    st.session_state.app_db[section][key] = st.session_state[key_path]
