import streamlit as st
from supabase import create_client, Client

# --- 1. CONNECTION SETUP ---
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

# --- 2. SESSION STATE INITIALIZER ---
def init_session_state():
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    
    defaults = ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver']
    for k in defaults:
        if k not in st.session_state.app_db:
            st.session_state.app_db[k] = {}

# --- 3. DATA LOADER (DEBUG MODE) ---
def load_user_data(user_id):
    """Fetches user data and reports status VISIBLY."""
    # Ensure state exists before we try to load into it
    init_session_state()
    
    if not supabase:
        st.warning("⚠️ Offline Mode: Secrets missing or connection failed.")
        return

    try:
        # DEBUG: Tell the user exactly what we are searching for
        st.toast(f"🔍 Searching Cloud for User ID: {user_id}...", icon="☁️")
        
        # Execute Query
        response = supabase.table('user_data').select('data').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            cloud_data = response.data[0]['data']
            if cloud_data:
                # SUCCESS: Load data into session
                st.session_state.app_db = cloud_data
                init_session_state() # Re-verify structure after load
                st.toast("✅ Data Found & Loaded!", icon="🎉")
            else:
                st.toast("⚠️ Row found, but 'data' column was empty.", icon="🤷")
        else:
            # FAILURE: No data found for this ID
            st.error(f"❌ No data found for ID: {user_id}. Please check your Supabase 'user_data' table to ensure the IDs match exactly.")
            
    except Exception as e:
        st.error(f"🔥 Database Error: {e}")

# --- 4. WIDGET HELPERS ---
def cloud_input(label, section, key, input_type="number", step=None):
    # SAFETY: Ensure DB exists
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
    # SAFETY: Use init_session_state() to prevent AttributeError
    if 'app_db' not in st.session_state:
        init_session_state()
        
    if ':' in key_path:
        section, key = key_path.split(":")
        
        # Double check section exists
        if section not in st.session_state.app_db:
            st.session_state.app_db[section] = {}
            
        # Safe Assignment
        st.session_state.app_db[section][key] = st.session_state[key_path]
