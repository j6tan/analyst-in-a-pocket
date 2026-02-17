import streamlit as st
# Safety check: ensure libraries are installed
try:
    from supabase import create_client, Client
except ImportError:
    st.error("🚨 Critical Error: 'supabase' library is missing. Please add it to requirements.txt.")
    st.stop()

# --- 1. SAFE SUPABASE INITIALIZATION ---
@st.cache_resource
def init_supabase():
    try:
        # Use .get() to prevent crashing if secrets are missing
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        
        # Fallback for nested secrets (common in local setups)
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
    
    # Initialize required sections to prevent KeyErrors
    defaults = ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver']
    for k in defaults:
        if k not in st.session_state.app_db:
            st.session_state.app_db[k] = {}

# --- 3. DATA LOADER (THIS WAS MISSING) ---
def load_user_data(user_id):
    """Fetches the user's JSON blob from Supabase and loads it into session state."""
    if not supabase:
        return # Stay offline if no connection
        
    try:
        # Fetch data row for this user
        response = supabase.table('user_data').select('data').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            # Success: Load cloud data into app
            cloud_data = response.data[0]['data']
            if cloud_data:
                st.session_state.app_db = cloud_data
                # Re-run init to ensure any new keys are added
                init_session_state()
        else:
            # No data found (New User) -> Initialize empty
            init_session_state()
            
    except Exception as e:
        st.error(f"⚠️ Error loading profile: {e}")

# --- 4. INPUT WIDGET HELPER ---
def cloud_input(label, section, key, input_type="number", step=None):
    # Ensure DB structure exists
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

# --- 5. SYNC HELPER ---
def sync_widget(key_path):
    if ':' in key_path:
        section, key = key_path.split(":")
        if section not in st.session_state.app_db:
            st.session_state.app_db[section] = {}
        st.session_state.app_db[section][key] = st.session_state[key_path]
