import streamlit as st
from supabase import create_client, Client

# --- 1. SAFE SUPABASE INITIALIZATION ---
@st.cache_resource
def init_supabase():
    # Wrap in try-except to prevent app crash if secrets are missing
    try:
        if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            return create_client(url, key)
        else:
            return None
    except Exception:
        return None

# Initialize the client (will be None if offline)
supabase = init_supabase()

# --- 2. INPUT WIDGET HELPER ---
def cloud_input(label, section, key, input_type="number", step=None):
    # Initialize DB structure if missing
    if section not in st.session_state.app_db:
        st.session_state.app_db[section] = {}
    
    # Get current value from DB (or default)
    val = st.session_state.app_db[section].get(key)
    
    # Determine default based on type
    if val is None:
        val = 0.0 if input_type == "number" else ""

    # Create Widget
    if input_type == "number":
        # Use session state to persist changes locally instantly
        new_val = st.number_input(label, value=float(val), step=step, key=f"{section}_{key}")
    else:
        new_val = st.text_input(label, value=str(val), key=f"{section}_{key}")
        
    # Update Local DB immediately
    st.session_state.app_db[section][key] = new_val
    return new_val

# --- 3. SESSION STATE INIT ---
def init_session_state():
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    
    # Initialize basic keys to prevent KeyErrors elsewhere
    for k in ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver']:
        if k not in st.session_state.app_db:
            st.session_state.app_db[k] = {}
