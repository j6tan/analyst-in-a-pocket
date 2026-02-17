import streamlit as st
from supabase import create_client, Client

# ==========================================
# 1. ROBUST CONNECTION & DEBUGGER
# ==========================================
@st.cache_resource
def init_supabase():
    """
    Attempts to connect to Supabase and debugs secrets if they fail.
    """
    # 1. Try to get keys (Safe .get() method never crashes)
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")

    # 2. Fallback for nested [supabase] section (Just in case)
    if not url and "supabase" in st.secrets:
        url = st.secrets["supabase"].get("SUPABASE_URL")
        key = st.secrets["supabase"].get("SUPABASE_KEY")

    # 3. Connection Logic
    if url and key:
        try:
            return create_client(url, key)
        except Exception as e:
            print(f"Supabase Client Error: {e}")
            return None
    else:
        # DEBUGGING: This prints to your Manage App -> Logs console
        print(f"⚠️ Secrets Missing. Available keys: {list(st.secrets.keys())}")
        return None

# Initialize Client
supabase = init_supabase()


# ==========================================
# 2. SESSION STATE MANAGEMENT
# ==========================================
def init_session_state():
    """Creates the database folder structure if missing."""
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    
    # Define all required data sections
    defaults = ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver']
    for section in defaults:
        if section not in st.session_state.app_db:
            st.session_state.app_db[section] = {}


# ==========================================
# 3. WIDGET SYNC (Fixes "AttributeError")
# ==========================================
def sync_widget(key_path):
    """
    Saves widget data to the database safely.
    """
    if 'app_db' not in st.session_state:
        init_session_state()
        
    if ':' in key_path:
        section, key = key_path.split(":")
        
        # Construct the widget key (underscore format)
        widget_id = f"{section}_{key}"
        
        # Only update if the widget exists in session state
        if widget_id in st.session_state:
            if section not in st.session_state.app_db:
                st.session_state.app_db[section] = {}
            st.session_state.app_db[section][key] = st.session_state[widget_id]


# ==========================================
# 4. DEEP DATA LOADER (Fixes "Blank Data")
# ==========================================
def load_user_data(user_id):
    """
    Downloads data for 'user_id' and forces the screen to update.
    """
    init_session_state()
    
    if not supabase:
        st.error("⚠️ Offline: Could not find SUPABASE_URL in secrets.")
        return

    try:
        # 1. Fetch data (Try exact match first)
        response = supabase.table('user_data').select('data').eq('user_id', user_id).execute()
        
        # 2. Case-Insensitive Fallback (e.g. 'Dori' vs 'dori')
        if not response.data:
            response = supabase.table('user_data').select('data').ilike('user_id', user_id).execute()

        # 3. Load Data
        if response.data and len(response.data) > 0:
            cloud_data = response.data[0]['data']
            
            if cloud_data:
                # Update Master DB
                st.session_state.app_db = cloud_data
                
                # FORCE UPDATE WIDGETS
                # This explicitly overwrites the text boxes with cloud data
                for section, content in cloud_data.items():
                    if isinstance(content, dict):
                        for key, value in content.items():
                            widget_id = f"{section}_{key}"
                            st.session_state[widget_id] = value
                
                init_session_state()
                st.toast(f"✅ Loaded data for {user_id}!", icon="📂")
        else:
            st.toast(f"⚠️ No data found for user: {user_id}", icon="🤷")
            
    except Exception as e:
        st.error(f"Sync Error: {e}")


# ==========================================
# 5. SMART INPUT HELPER
# ==========================================
def cloud_input(label, section, key, input_type="number", step=None):
    if 'app_db' not in st.session_state:
        init_session_state()
    if section not in st.session_state.app_db:
        st.session_state.app_db[section] = {}
    
    widget_id = f"{section}_{key}"
    
    # Priority: DB Value > Widget Value > Default
    db_val = st.session_state.app_db[section].get(key)
    
    # Initialize widget state from DB if new
    if widget_id not in st.session_state and db_val is not None:
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
