import streamlit as st
from supabase import create_client, Client

# --- 1. BULLETPROOF CONNECTION ---
@st.cache_resource
def init_supabase():
    # Attempt 1: Get keys from top-level secrets (Standard Cloud Setup)
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")

    # Attempt 2: Get keys from nested header (Common [supabase] TOML Setup)
    if not url and "supabase" in st.secrets:
        url = st.secrets["supabase"].get("SUPABASE_URL")
        key = st.secrets["supabase"].get("SUPABASE_KEY")

    # Connect if keys were found
    if url and key:
        try:
            return create_client(url, key)
        except Exception:
            return None # Connection failed, stay offline
            
    return None # No keys found, stay offline

# Initialize Client (Will be None if offline)
supabase = init_supabase()

# --- 2. DATA LOADER (CRITICAL FOR DORI'S DATA) ---
def load_user_data(user_id):
    """Fetches Dori's data from the cloud. If offline, does nothing."""
    if not supabase:
        st.warning("⚠️ Offline Mode: Check your Secrets setup.")
        init_session_state()
        return

    try:
        # Fetch the JSON blob for this user
        response = supabase.table('user_data').select('data').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            # Success! Load cloud data into the app
            cloud_data = response.data[0]['data']
            if cloud_data:
                st.session_state.app_db = cloud_data
                init_session_state() # Ensure structure is valid
        else:
            init_session_state() # New user, start fresh
            
    except Exception as e:
        st.error(f"⚠️ Error loading profile: {e}")
        init_session_state()

# --- 3. SESSION STATE INITIALIZER ---
def init_session_state():
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    
    # Ensure all required sections exist
    defaults = ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver']
    for k in defaults:
        if k not in st.session_state.app_db:
            st.session_state.app_db[k] = {}

# --- 4. WIDGET HELPERS ---
def cloud_input(label, section, key, input_type="number", step=None):
    # Initialize if missing
    if 'app_db' not in st.session_state:
        init_session_state()
    if section not in st.session_state.app_db:
        st.session_state.app_db[section] = {}
    
    # Get current value
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

def sync_widget(key_path):
    if ':' in key_path:
        section, key = key_path.split(":")
        if section not in st.session_state.app_db:
            st.session_state.app_db[section] = {}
        st.session_state.app_db[section][key] = st.session_state[key_path]
