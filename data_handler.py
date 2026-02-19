import streamlit as st
from supabase import create_client, Client

# --- 1. CONNECTION ---
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

# --- 2. SESSION MANAGEMENT ---
def init_session_state():
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    
    defaults = ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver', 'budget', 'affordability_second', 'sales_proceeds', 'simple_mortgage', 'buy_vs_rent', 'rental_vs_stock', 'renewal_analysis']
    for section in defaults:
        if section not in st.session_state.app_db:
            st.session_state.app_db[section] = {}

# --- 3. AUTO-SAVE ---
def trigger_auto_save():
    if st.session_state.get('is_logged_in') and st.session_state.get('username') and supabase:
        try:
            supabase.table('user_vault').upsert({
                'id': st.session_state.username, 
                'data': st.session_state.app_db
            }).execute()
        except Exception as e:
            print(f"Auto-Save Error: {e}")

def sync_widget(key_path):
    if 'app_db' not in st.session_state: init_session_state()
    
    if ':' in key_path:
        section, key = key_path.split(":")
        widget_id = f"{section}_{key}"
        
        if widget_id in st.session_state:
            if section not in st.session_state.app_db:
                st.session_state.app_db[section] = {}
            st.session_state.app_db[section][key] = st.session_state[widget_id]
            trigger_auto_save()

# --- 4. DATA LOADER (PRIME THE PUMP) ---
def load_user_data(user_id):
    init_session_state()
    if not supabase: return

    try:
        response = supabase.table('user_vault').select('data').eq('id', user_id).execute()
        if response.data and len(response.data) > 0:
            cloud_data = response.data[0]['data']
            if cloud_data:
                st.session_state.app_db = cloud_data
                # PRIME SESSION STATE: Force cloud values into widget keys immediately
                for section, content in cloud_data.items():
                    if isinstance(content, dict):
                        for key, value in content.items():
                            widget_id = f"{section}_{key}"
                            st.session_state[widget_id] = value
                st.toast(f"✅ Data Loaded", icon="📂")
    except Exception as e:
        st.error(f"Sync Error: {e}")

# --- 5. SMART INPUT (THE FIX) ---
def cloud_input(label, section, key, input_type="number", step=None, **kwargs):
    if 'app_db' not in st.session_state: init_session_state()
    if section not in st.session_state.app_db: st.session_state.app_db[section] = {}
    
    widget_id = f"{section}_{key}"
    db_val = st.session_state.app_db[section].get(key)
    
    # --- FORCE-FEED ENGINE ---
    # 1. Get what the widget THINKS the value is
    current_state = st.session_state.get(widget_id)
    
    # 2. Sanitize Database Value
    db_float = 0.0
    try:
        if db_val is not None and str(db_val).strip() != "":
            db_float = float(db_val)
    except: pass

    # 3. Sanitize Current State
    state_float = 0.0
    try:
        if current_state is not None and str(current_state).strip() != "":
            state_float = float(current_state)
    except: pass

    # 4. THE OVERWRITE RULE:
    # If the widget says "0" (empty/default) BUT the database has a real number...
    # We OVERWRITE the session state memory directly.
    if input_type == "number" and state_float == 0.0 and db_float != 0.0:
        st.session_state[widget_id] = db_float
    elif input_type == "text" and (current_state is None or str(current_state) == "") and db_val:
        st.session_state[widget_id] = str(db_val)

    # 5. RENDER
    # We do NOT use 'value=' here because we set st.session_state[widget_id] above.
    # Streamlit will automatically pick up the forced value.
    if input_type == "number":
        # Final safety: ensure key exists
        if widget_id not in st.session_state: st.session_state[widget_id] = 0.0
        
        st.number_input(
            label, step=step, key=widget_id, 
            on_change=sync_widget, args=(f"{section}:{key}",),
            **kwargs 
        )
    else:
        if widget_id not in st.session_state: st.session_state[widget_id] = ""
        st.text_input(
            label, key=widget_id, 
            on_change=sync_widget, args=(f"{section}:{key}",),
            **kwargs
        )
        
    return st.session_state[widget_id]
