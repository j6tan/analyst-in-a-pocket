import streamlit as st
from supabase import create_client, Client

# --- 1. BULLETPROOF CONNECTION ---
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        
        if not url and "supabase" in st.secrets:
            url = st.secrets["supabase"].get("SUPABASE_URL")
            key = st.secrets["supabase"].get("SUPABASE_KEY")

        if url and key:
            return create_client(url, key)
        return None
    except Exception as e:
        print(f"⚠️ Connection Error: {e}")
        return None

supabase = init_supabase()

# --- 2. SESSION STATE MANAGEMENT ---
def init_session_state():
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    
    defaults = ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver', 'budget', 'affordability_second', 'sales_proceeds', 'simple_mortgage']
    for section in defaults:
        if section not in st.session_state.app_db:
            st.session_state.app_db[section] = {}

# --- 3. WIDGET SYNC (WITH AUTO-SAVE) ---
def sync_widget(key_path):
    """
    Updates local session state AND pushes changes to Supabase immediately.
    """
    if 'app_db' not in st.session_state:
        init_session_state()
        
    if ':' in key_path:
        section, key = key_path.split(":")
        widget_id = f"{section}_{key}"
        
        if widget_id in st.session_state:
            if section not in st.session_state.app_db:
                st.session_state.app_db[section] = {}
            st.session_state.app_db[section][key] = st.session_state[widget_id]
            
            # --- CLOUD AUTO-SAVE ---
            # Automatically pushes changes to the vault when you type
            if st.session_state.get('is_logged_in') and st.session_state.get('username') and supabase:
                try:
                    user_id = st.session_state.username
                    # Updates the existing row for this user
                    supabase.table('user_vault').upsert({
                        'id': user_id, 
                        'data': st.session_state.app_db
                    }).execute()
                except Exception as e:
                    # Log silently to console
                    print(f"Auto-Save Error: {e}")

# --- 4. DATA LOADER ---
def load_user_data(user_id):
    init_session_state()
    
    if not supabase:
        st.error("🚨 Cloud Disconnected: Check secrets.")
        return

    try:
        response = supabase.table('user_vault').select('data').eq('id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            cloud_data = response.data[0]['data']
            
            if cloud_data:
                st.session_state.app_db = cloud_data
                
                # Pre-fill Session State keys so widgets find them immediately
                for section, content in cloud_data.items():
                    if isinstance(content, dict):
                        for key, value in content.items():
                            widget_id = f"{section}_{key}"
                            st.session_state[widget_id] = value
                
                init_session_state()
                st.toast(f"✅ Data Loaded for: {user_id}", icon="📂")
        else:
            # Create blank profile if new user
            st.toast(f"🆕 Creating new profile for: {user_id}", icon="✨")
            try:
                supabase.table('user_vault').insert({
                    'id': user_id, 
                    'data': st.session_state.app_db
                }).execute()
            except Exception:
                pass
            
    except Exception as e:
        st.error(f"Sync Error: {e}")

# --- 5. SMART INPUT HELPER (WARNING FIXED) ---
def cloud_input(label, section, key, input_type="number", step=None, **kwargs):
    if 'app_db' not in st.session_state: init_session_state()
    if section not in st.session_state.app_db: st.session_state.app_db[section] = {}
    
    widget_id = f"{section}_{key}"
    db_val = st.session_state.app_db[section].get(key)
    
    # 1. Ensure Key Exists in Session State (The Source of Truth)
    if widget_id not in st.session_state:
        if db_val is not None:
             st.session_state[widget_id] = db_val
        else:
             # Set defaults if DB is empty
             st.session_state[widget_id] = 0.0 if input_type == "number" else ""

    # 2. Render Widget WITHOUT 'value=' argument
    # Streamlit will automatically use the value from st.session_state[widget_id]
    if input_type == "number":
        val = st.number_input(
            label, step=step, key=widget_id, 
            on_change=sync_widget, args=(f"{section}:{key}",),
            **kwargs 
        )
    else:
        val = st.text_input(
            label, key=widget_id, 
            on_change=sync_widget, args=(f"{section}:{key}",),
            **kwargs
        )
        
    return val
