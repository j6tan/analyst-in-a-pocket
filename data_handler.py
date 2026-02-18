import streamlit as st
from supabase import create_client, Client

# --- 1. BULLETPROOF CONNECTION ---
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        
        # Check nested secrets just in case
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

# --- 3. WIDGET SYNC (NOW WITH AUTO-SAVE) ---
def sync_widget(key_path):
    """
    Updates local session state AND pushes changes to Supabase immediately.
    """
    # 1. Init Check
    if 'app_db' not in st.session_state:
        init_session_state()
        
    # 2. Local Update
    if ':' in key_path:
        section, key = key_path.split(":")
        widget_id = f"{section}_{key}"
        
        if widget_id in st.session_state:
            if section not in st.session_state.app_db:
                st.session_state.app_db[section] = {}
            st.session_state.app_db[section][key] = st.session_state[widget_id]
            
            # 3. CLOUD AUTO-SAVE (The Fix)
            # If the user is logged in, we push the new data to the Vault immediately.
            if st.session_state.get('is_logged_in') and st.session_state.get('username') and supabase:
                try:
                    user_id = st.session_state.username
                    # Upsert ensures we update the existing row for this user
                    supabase.table('user_vault').upsert({
                        'id': user_id, 
                        'data': st.session_state.app_db
                    }).execute()
                except Exception as e:
                    # Log silently to console so we don't spam the UI
                    print(f"Auto-Save Error: {e}")

# --- 4. DATA LOADER ---
def load_user_data(user_id):
    init_session_state()
    
    if not supabase:
        st.error("🚨 Cloud Disconnected: Check secrets.")
        return

    try:
        # Looking for 'user_vault' and 'id'
        response = supabase.table('user_vault').select('data').eq('id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            cloud_data = response.data[0]['data']
            
            if cloud_data:
                st.session_state.app_db = cloud_data
                
                # Force Update Widgets
                for section, content in cloud_data.items():
                    if isinstance(content, dict):
                        for key, value in content.items():
                            widget_id = f"{section}_{key}"
                            st.session_state[widget_id] = value
                
                init_session_state()
                st.toast(f"✅ Data Loaded for: {user_id}", icon="📂")
        else:
            # If user has no data yet, create a blank entry so they can start saving
            st.toast(f"🆕 Creating new profile for: {user_id}", icon="✨")
            try:
                supabase.table('user_vault').insert({
                    'id': user_id, 
                    'data': st.session_state.app_db
                }).execute()
            except Exception:
                pass # If it already exists, ignore
            
    except Exception as e:
        st.error(f"Sync Error: {e}")

# --- 5. SMART INPUT HELPER ---
def cloud_input(label, section, key, input_type="number", step=None, **kwargs):
    if 'app_db' not in st.session_state: init_session_state()
    if section not in st.session_state.app_db: st.session_state.app_db[section] = {}
    
    widget_id = f"{section}_{key}"
    db_val = st.session_state.app_db[section].get(key)
    
    if widget_id not in st.session_state and db_val is not None:
        st.session_state[widget_id] = db_val
    
    current_val = st.session_state.get(widget_id)
    if current_val is None: current_val = 0.0 if input_type == "number" else ""

    if input_type == "number":
        val = st.number_input(
            label, value=float(current_val), step=step, key=widget_id, 
            on_change=sync_widget, args=(f"{section}:{key}",),
            **kwargs 
        )
    else:
        val = st.text_input(
            label, value=str(current_val), key=widget_id, 
            on_change=sync_widget, args=(f"{section}:{key}",),
            **kwargs
        )
        
    return val
