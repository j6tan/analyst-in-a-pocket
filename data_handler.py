import streamlit as st
from supabase import create_client, Client

# ==========================================
# 1. ROBUST CONNECTION
# ==========================================
@st.cache_resource
def init_supabase():
    """Connects to Supabase safely."""
    try:
        # Check standard secrets
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")

        # Check nested secrets
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
# 2. SESSION STATE MANAGEMENT
# ==========================================
def init_session_state():
    """Ensures database structure exists."""
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    
    defaults = ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver']
    for section in defaults:
        if section not in st.session_state.app_db:
            st.session_state.app_db[section] = {}

# ==========================================
# 3. WIDGET SYNC (THE FIX IS HERE)
# ==========================================
def sync_widget(key_path):
    """
    Saves widget data to the database.
    Fixes the KeyError by converting 'profile:name' -> 'profile_name'.
    """
    if 'app_db' not in st.session_state:
        init_session_state()
        
    if ':' in key_path:
        section, key = key_path.split(":")
        
        # FIX: Construct the actual widget ID (Underscore)
        widget_id = f"{section}_{key}"
        
        # Only try to read if the widget actually exists
        if widget_id in st.session_state:
            # Ensure section exists in DB
            if section not in st.session_state.app_db:
                st.session_state.app_db[section] = {}
                
            # Save the value
            st.session_state.app_db[section][key] = st.session_state[widget_id]

# ==========================================
# 4. DEEP DATA LOADER
# ==========================================
def load_user_data(user_id):
    """Downloads data and forces widgets to update."""
    init_session_state()
    
    if not supabase:
        st.warning("⚠️ Offline Mode")
        return

    try:
        # Fetch data
        response = supabase.table('user_data').select('data').eq('user_id', user_id).execute()
        
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
        else:
            pass # New user
            
    except Exception as e:
        st.error(f"Sync Error: {e}")

# ==========================================
# 5. INPUT HELPER
# ==========================================
def cloud_input(label, section, key, input_type="number", step=None):
    if 'app_db' not in st.session_state:
        init_session_state()
    if section not in st.session_state.app_db:
        st.session_state.app_db[section] = {}
    
    widget_id = f"{section}_{key}"
    
    # Priority: DB Value > Widget Value > Default
    db_val = st.session_state.app_db[section].get(key)
    
    if widget_id not in st.session_state:
        if db_val is not None:
            st.session_state[widget_id] = db_val
    
    current_val = st.session_state.get(widget_id)
    if current_val is None:
        current_val = 0.0 if input_type == "number" else ""

    if input_type == "number":
        st.number_input(
            label, 
            value=float(current_val), 
            step=step, 
            key=widget_id,
            on_change=sync_widget,
            args=(f"{section}:{key}",) # This passes the 'colon' key to sync_widget
        )
    else:
        st.text_input(
            label, 
            value=str(current_val), 
            key=widget_id,
            on_change=sync_widget,
            args=(f"{section}:{key}",)
        )
