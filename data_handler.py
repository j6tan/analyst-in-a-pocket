import streamlit as st
from supabase import create_client, Client

# ==========================================
# 1. BULLETPROOF CONNECTION
# ==========================================
def init_supabase():
    """Connects to Supabase safely without crashing on missing secrets."""
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
# 2. SESSION STATE & WIDGET MANAGEMENT
# ==========================================
def init_session_state():
    """Ensures the internal database structure exists."""
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    
    defaults = ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver']
    for section in defaults:
        if section not in st.session_state.app_db:
            st.session_state.app_db[section] = {}

def sync_widget(key_path):
    """
    Updates the database when a user changes a specific input.
    """
    # Ensure DB exists
    if 'app_db' not in st.session_state:
        init_session_state()
        
    if ':' in key_path:
        section, key = key_path.split(":")
        
        # FIX: The widget key uses an underscore, not a colon
        widget_key = f"{section}_{key}"
        
        # Only update if the widget exists in state
        if widget_key in st.session_state:
            # Update the master DB with the new widget value
            if section not in st.session_state.app_db:
                 st.session_state.app_db[section] = {}
            st.session_state.app_db[section][key] = st.session_state[widget_key]


# ==========================================
# 3. DEEP SYNC DATA LOADER
# ==========================================
def load_user_data(user_id):
    """Downloads user data AND forces the UI widgets to update."""
    init_session_state()
    
    if not supabase:
        st.warning("⚠️ Cloud Disconnected: Please check secrets.toml")
        return

    try:
        response = supabase.table('user_data').select('data').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            cloud_data = response.data[0]['data']
            
            if cloud_data:
                # 1. Update the Master Database
                st.session_state.app_db = cloud_data
                
                # 2. Force-update every widget key
                for section, content in cloud_data.items():
                    if isinstance(content, dict):
                        for key, value in content.items():
                            widget_id = f"{section}_{key}"
                            st.session_state[widget_id] = value
                
                init_session_state()
        else:
            pass
            
    except Exception as e:
        st.error(f"Sync Error: {e}")


# ==========================================
# 4. SMART INPUT WIDGET
# ==========================================
def cloud_input(label, section, key, input_type="number", step=None):
    """Creates an input linked to both Session State and App DB."""
    if 'app_db' not in st.session_state:
        init_session_state()
    if section not in st.session_state.app_db:
        st.session_state.app_db[section] = {}
    
    # Construct the unique widget ID with underscore
    widget_id = f"{section}_{key}"
    
    # Get value (DB > Widget State > Default)
    db_val = st.session_state.app_db[section].get(key)
    
    if widget_id not in st.session_state:
        if db_val is not None:
            st.session_state[widget_id] = db_val
    
    current_val = st.session_state.get(widget_id)
    if current_val is None:
        current_val = 0.0 if input_type == "number" else ""

    # Render Widget
    if input_type == "number":
        val = st.number_input(
            label, 
            value=float(current_val), 
            step=step, 
            key=widget_id,
            on_change=sync_widget,
            args=(f"{section}:{key}",)
        )
    else:
        val = st.text_input(
            label, 
            value=str(current_val), 
            key=widget_id,
            on_change=sync_widget,
            args=(f"{section}:{key}",)
        )
        
    return val
