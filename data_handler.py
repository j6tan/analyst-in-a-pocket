import streamlit as st
from supabase import create_client, Client

# --- 1. BULLETPROOF CONNECTION ---
@st.cache_resource
def init_supabase():
    """
    Connects to Supabase safely. 
    Uses .get() so it NEVER crashes with a KeyError.
    """
    try:
        # Attempt 1: Standard Streamlit Cloud Secrets
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")

        # Attempt 2: Nested TOML Secrets (e.g. [supabase] folder)
        if not url and "supabase" in st.secrets:
            url = st.secrets["supabase"].get("SUPABASE_URL")
            key = st.secrets["supabase"].get("SUPABASE_KEY")

        # Only connect if keys exist
        if url and key:
            return create_client(url, key)
        
        # If missing, print warning but DO NOT CRASH
        print("⚠️ Supabase Keys Not Found in Secrets")
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
        widget_id = f"{section}_{key}"
        
        if widget_id in st.session_state:
            if section not in st.session_state.app_db:
                st.session_state.app_db[section] = {}
            st.session_state.app_db[section][key] = st.session_state[widget_id]


# --- 4. DATA LOADER (Targeting 'user_vault' & 'id') ---
def load_user_data(user_id):
    init_session_state()
    
    if not supabase:
        st.error("🚨 Cloud Disconnected: Please check secrets in Manage App.")
        return

    try:
        # CORRECTED QUERY:
        # Table: 'user_vault' (not 'user_data')
        # Column: 'id' (not 'user_id')
        response = supabase.table('user_vault').select('data').eq('id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            cloud_data = response.data[0]['data']
            
            if cloud_data:
                # 1. Update Master DB
                st.session_state.app_db = cloud_data
                
                # 2. Force Update Widgets
                for section, content in cloud_data.items():
                    if isinstance(content, dict):
                        for key, value in content.items():
                            widget_id = f"{section}_{key}"
                            st.session_state[widget_id] = value
                
                init_session_state()
                st.toast(f"✅ Data Loaded for: {user_id}", icon="📂")
        else:
            st.toast(f"⚠️ User '{user_id}' not found in Vault.", icon="🤷")
            
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
        st.number_input(
            label, value=float(current_val), step=step, key=widget_id, 
            on_change=sync_widget, args=(f"{section}:{key}",)
        )
    else:
        st.text_input(
            label, value=str(current_val), key=widget_id, 
            on_change=sync_widget, args=(f"{section}:{key}",)
        )
