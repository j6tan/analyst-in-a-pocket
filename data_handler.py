import streamlit as st
from supabase import create_client, Client

# --- 1. SAFE SUPABASE INITIALIZATION ---
@st.cache_resource
def init_supabase():
    try:
        # .get() returns None instead of crashing if key is missing
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        
        # Only connect if both keys exist
        if url and key:
            return create_client(url, key)
        return None
    except Exception:
        return None

# Initialize (Result is either the Client or None)
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

# --- 3. SESSION STATE INIT ---
def init_session_state():
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    
    # Initialize basic keys to prevent KeyErrors elsewhere
    for k in ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver']:
        if k not in st.session_state.app_db:
            st.session_state.app_db[k] = {}
