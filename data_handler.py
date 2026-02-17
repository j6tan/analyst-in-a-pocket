import streamlit as st
from supabase import create_client, Client

# --- 1. UNIVERSAL CONNECTION LOGIC ---
@st.cache_resource
def init_supabase():
    """
    Connects to Supabase. Checks root keys first, then nested keys.
    Returns None instead of crashing if secrets are missing.
    """
    try:
        # Attempt 1: Root level (Standard)
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")

        # Attempt 2: Nested [supabase] section (Fallback)
        if not url and "supabase" in st.secrets:
            url = st.secrets["supabase"].get("SUPABASE_URL")
            key = st.secrets["supabase"].get("SUPABASE_KEY")

        if url and key:
            return create_client(url, key)
        
        # If we get here, keys are missing.
        print("⚠️ Supabase Keys Missing in Secrets.")
        return None
    except Exception as e:
        print(f"⚠️ Connection Error: {e}")
        return None

# Initialize immediately
supabase = init_supabase()

# --- 2. SESSION STATE MANAGEMENT ---
def init_session_state():
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    
    defaults = ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver']
    for section in defaults:
        if section not in st.session_state.app_db:
            st.session_state.app_db[section] = {}

# --- 3. WIDGET SYNC (Crash-Proof) ---
def sync_widget(key_path):
    if 'app_db' not in st.session_state:
        init_session_state()
        
    if ':' in key_path:
        section, key = key_path.split(":")
        
        # We use UNDERSCORE for widget IDs to prevent KeyErrors
        widget_id = f"{section}_{key}"
        
        # Only save if the widget actually exists
        if widget_id in st.session_state:
            if section not in st.session_state.app_db:
                st.session_state.app_db[section] = {}
            st.session_state.app_db[section][key] = st.session_state[widget_id]

# --- 4. DATA LOADER (Uses 'user_vault') ---
def load_user_data(user_id):
    init_session_state()
    
    if not supabase:
        st.error("🚨 Cloud Connection Lost. Please check Secrets.")
        return

    try:
        # We search 'user_vault' because that is your actual table name
        response = supabase.table('user_vault').select('data').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            cloud_data = response.data[0]['data']
            if cloud_data:
                st.session_state.app_db = cloud_data
                
                # Force-Push Data to Widgets
                for section, content in cloud_data.items():
                    if isinstance(content, dict):
                        for key, value in content.items():
                            widget_id = f"{section}_{key}"
                            st.session_state[widget_id] = value
                
                init_session_state()
                st.toast(f"✅ Data Synced for user: {user_id}", icon="☁️")
        else:
            st.warning(f"⚠️ No data found in 'user_vault' for ID: {user_id}")
            
    except Exception as e:
        st.error(f"Sync Error: {e}")

# --- 5. SMART INPUT HELPER ---
def cloud_input(label, section, key, input_type="number", step=None):
    if 'app_db' not in st.session_state: init_session_state()
    if section not in st.session_state.app_db: st.session_state.app_db[section] = {}
    
    widget_id = f"{section}_{key}"
    db_val = st.session_state.app_db[section].get(key)
    
    if widget_id not in st.session_state and db_val is not None:
        st.session_state[widget_id] = db_val
    
    current_val = st.session_state.get(widget_id)
    if current_val is None: current_val = 0.0 if input_type == "number" else ""

    if input_type == "number":
        st.number_input(label, value=float(current_val), step=step, key=widget_id, on_change=sync_widget, args=(f"{section}:{key}",))
    else:
        st.text_input(label, value=str(current_val), key=widget_id, on_change=sync_widget, args=(f"{section}:{key}",))
