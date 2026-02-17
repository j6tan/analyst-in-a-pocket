import streamlit as st
from supabase import create_client, Client

# ==========================================
# 1. BULLETPROOF CONNECTION (Forever Fix #1)
# ==========================================
def init_supabase():
    """
    Connects to Supabase safely. 
    Never crashes, even if secrets are missing or formatted differently.
    """
    try:
        # Attempt 1: Standard Streamlit Cloud Secrets
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")

        # Attempt 2: Nested TOML Secrets (Common in local development)
        if not url and "supabase" in st.secrets:
            url = st.secrets["supabase"].get("SUPABASE_URL")
            key = st.secrets["supabase"].get("SUPABASE_KEY")

        # Only connect if we found both keys
        if url and key:
            return create_client(url, key)
        
        return None # Return None instead of crashing
    except Exception:
        return None

# Initialize the client immediately
supabase = init_supabase()


# ==========================================
# 2. SESSION STATE & WIDGET MANAGEMENT
# ==========================================
def init_session_state():
    """Ensures the internal database structure exists."""
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    
    # Define all required sections here
    defaults = ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver']
    for section in defaults:
        if section not in st.session_state.app_db:
            st.session_state.app_db[section] = {}

def sync_widget(key_path):
    """
    Updates the database when a user changes a specific input.
    Usage: on_change=sync_widget, args=("profile:p1_name",)
    """
    if 'app_db' not in st.session_state:
        init_session_state()
        
    if ':' in key_path:
        section, key = key_path.split(":")
        # Update the master DB with the new widget value
        st.session_state.app_db[section][key] = st.session_state[key_path]


# ==========================================
# 3. DEEP SYNC DATA LOADER (Forever Fix #2)
# ==========================================
def load_user_data(user_id):
    """
    Downloads user data AND forces the UI widgets to update.
    """
    init_session_state()
    
    if not supabase:
        st.warning("⚠️ Cloud Disconnected: Please check secrets.toml")
        return

    try:
        # Fetch data from Supabase
        response = supabase.table('user_data').select('data').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            cloud_data = response.data[0]['data']
            
            if cloud_data:
                # 1. Update the Master Database
                st.session_state.app_db = cloud_data
                
                # 2. DEEP SYNC: Force-update every widget key
                # This fixes the "Blank Data" issue by pushing data into the widgets
                for section, content in cloud_data.items():
                    if isinstance(content, dict):
                        for key, value in content.items():
                            # Widget keys are formatted as "section_key" (e.g., profile_p1_name)
                            widget_id = f"{section}_{key}"
                            st.session_state[widget_id] = value
                
                # 3. Re-verify structure
                init_session_state()
                st.toast("✅ Data Synced Successfully!", icon="🔄")
                
        else:
            # New user or empty row
            pass
            
    except Exception as e:
        st.error(f"Sync Error: {e}")


# ==========================================
# 4. SMART INPUT WIDGET
# ==========================================
def cloud_input(label, section, key, input_type="number", step=None):
    """
    Creates an input that is linked to both the Session State and the App DB.
    """
    # 1. Ensure DB exists
    if 'app_db' not in st.session_state:
        init_session_state()
    if section not in st.session_state.app_db:
        st.session_state.app_db[section] = {}
    
    # 2. Construct the unique widget ID
    widget_id = f"{section}_{key}"
    
    # 3. Get the value (Priority: Widget State > DB Value > Default)
    # We prefer the DB value if the widget state is missing (first load)
    db_val = st.session_state.app_db[section].get(key)
    
    if widget_id not in st.session_state:
        if db_val is not None:
            st.session_state[widget_id] = db_val
    
    # 4. Handle defaults for None values
    current_val = st.session_state.get(widget_id)
    if current_val is None:
        current_val = 0.0 if input_type == "number" else ""

    # 5. Render the Widget
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
