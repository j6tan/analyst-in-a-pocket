import streamlit as st
from supabase import create_client, Client

print("--- RELOADING DATA HANDLER (V3 FIX) ---")

# ==========================================
# 1. ROBUST CONNECTION
# ==========================================
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
    except Exception:
        return None

supabase = init_supabase()

# ==========================================
# 2. SESSION STATE SETUP
# ==========================================
def init_session_state():
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    
    defaults = ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver']
    for section in defaults:
        if section not in st.session_state.app_db:
            st.session_state.app_db[section] = {}

# ==========================================
# 3. WIDGET SYNC (THE CRASH FIX)
# ==========================================
def sync_widget(key_path):
    """
    Fixes the KeyError by ignoring the colon key and using the underscore key.
    """
    if 'app_db' not in st.session_state:
        init_session_state()
        
    if ':' in key_path:
        section, key = key_path.split(":")
        
        # CRITICAL FIX: We use underscore (_) to find the widget
        widget_id = f"{section}_{key}"
        
        # Only save if the widget actually exists in memory
        if widget_id in st.session_state:
            if section not in st.session_state.app_db:
                st.session_state.app_db[section] = {}
            
            # Save the value to the database
            st.session_state.app_db[section][key] = st.session_state[widget_id]

# ==========================================
# 4. DEEP DATA LOADER (BLANK DATA FIX)
# ==========================================
def load_user_data(user_id):
    init_session_state()
    
    if not supabase:
        st.warning("⚠️ Offline Mode")
        return

    try:
        # Fetch data
        response = supabase.table('user_vault').select('data').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            cloud_data = response.data[0]['data']
            
            if cloud_data:
                # 1. Update Master DB
                st.session_state.app_db = cloud_data
                
                # 2. Force Update Widgets (Crucial)
                for section, content in cloud_data.items():
                    if isinstance(content, dict):
                        for key, value in content.items():
                            widget_id = f"{section}_{key}"
                            st.session_state[widget_id] = value
                
                init_session_state()
        else:
            # New user case
            pass
            
    except Exception as e:
        print(f"Sync Error: {e}")

# ==========================================
# 5. INPUT HELPER
# ==========================================
def cloud_input(label, section, key, input_type="number", step=None):
    if 'app_db' not in st.session_state:
        init_session_state()
    if section not in st.session_state.app_db:
        st.session_state.app_db[section] = {}
    
    widget_id = f"{section}_{key}"
    db_val = st.session_state.app_db[section].get(key)
    
    # Initialize widget if missing
    if widget_id not in st.session_state and db_val is not None:
        st.session_state[widget_id] = db_val
    
    current_val = st.session_state.get(widget_id)
    if current_val is None:
        current_val = 0.0 if input_type == "number" else ""

    # Render Widget
    # Note: We pass "section:key" to args, but sync_widget handles it safely now
    if input_type == "number":
        st.number_input(
            label, 
            value=float(current_val), 
            step=step, 
            key=widget_id,
            on_change=sync_widget,
            args=(f"{section}:{key}",)
        )
    else:
        st.text_input(
            label, 
            value=str(current_val), 
            key=widget_id,
            on_change=sync_widget,
            args=(f"{section}:{key}",)
        )
