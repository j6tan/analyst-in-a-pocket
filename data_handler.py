import streamlit as st
from supabase import create_client, Client

# --- 1. FRESH CONNECTION (NO CACHE) ---
# We removed @st.cache_resource to force a fresh connection check every reload
def init_supabase():
    try:
        # Check standard secrets
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")

        # Check nested secrets (toml format)
        if not url and "supabase" in st.secrets:
            url = st.secrets["supabase"].get("SUPABASE_URL")
            key = st.secrets["supabase"].get("SUPABASE_KEY")

        if url and key:
            return create_client(url, key)
        return None
    except Exception:
        return None

supabase = init_supabase()

# --- 2. DATA LOADER WITH DEBUGGING ---
def load_user_data(user_id):
    """Fetches user data and reports status."""
    if not supabase:
        st.warning("⚠️ Cloud Disconnected: Check Secrets.")
        init_session_state()
        return

    try:
        # Fetch the JSON blob
        response = supabase.table('user_data').select('data').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            cloud_data = response.data[0]['data']
            
            # SUCCESS: Load data into session
            if cloud_data:
                st.session_state.app_db = cloud_data
                # Fix: Ensure all keys exist even if cloud data is partial
                init_session_state() 
                
                # DEBUG NOTE: Remove this line after you see it works!
                # st.toast(f"✅ Data Loaded! Found profile for {cloud_data.get('profile', {}).get('p1_name', 'User')}", icon="cloud")
                
        else:
            # No data found for this user_id
            st.toast("⚠️ New User: No existing data found.", icon="new")
            init_session_state()
            
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        init_session_state()

# --- 3. SESSION STATE INITIALIZER ---
def init_session_state():
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    
    defaults = ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver']
    for k in defaults:
        if k not in st.session_state.app_db:
            st.session_state.app_db[k] = {}

# --- 4. WIDGET HELPERS ---
def cloud_input(label, section, key, input_type="number", step=None):
    # Just in case app_db isn't ready
    if 'app_db' not in st.session_state:
        init_session_state()
    if section not in st.session_state.app_db:
        st.session_state.app_db[section] = {}
    
    # Get current value from DB
    val = st.session_state.app_db[section].get(key)
    
    # Handle missing/null values
    if val is None:
        val = 0.0 if input_type == "number" else ""

    # Create Widget
    if input_type == "number":
        new_val = st.number_input(label, value=float(val), step=step, key=f"{section}_{key}")
    else:
        new_val = st.text_input(label, value=str(val), key=f"{section}_{key}")
        
    # Save back to local state immediately
    st.session_state.app_db[section][key] = new_val
    return new_val

def sync_widget(key_path):
    if ':' in key_path:
        section, key = key_path.split(":")
        if section not in st.session_state.app_db:
            st.session_state.app_db[section] = {}
        st.session_state.app_db[section][key] = st.session_state[key_path]
