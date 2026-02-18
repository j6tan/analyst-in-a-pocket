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
    
    defaults = ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver', 'budget', 'affordability_second', 'sales_proceeds', 'simple_mortgage', 'buy_vs_rent']
    for section in defaults:
        if section not in st.session_state.app_db:
            st.session_state.app_db[section] = {}

# --- 3. DATABASE SAVING ---
def trigger_auto_save():
    """Forces a Cloud Save. Call this manually for Selectboxes/Radios."""
    if st.session_state.get('is_logged_in') and st.session_state.get('username') and supabase:
        try:
            supabase.table('user_vault').upsert({
                'id': st.session_state.username, 
                'data': st.session_state.app_db
            }).execute()
        except Exception as e:
            print(f"Auto-Save Error: {e}")

def sync_widget(key_path):
    """
    Standard Callback: Updates app_db from Widget -> Saves to Cloud.
    """
    if 'app_db' not in st.session_state:
        init_session_state()
        
    if ':' in key_path:
        section, key = key_path.split(":")
        widget_id = f"{section}_{key}"
        
        if widget_id in st.session_state:
            if section not in st.session_state.app_db:
                st.session_state.app_db[section] = {}
            
            # Update DB from Widget
            st.session_state.app_db[section][key] = st.session_state[widget_id]
            
            # Save to Cloud
            trigger_auto_save()

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

# --- 5. SMART INPUT HELPER (AGGRESSIVE RESYNC) ---
def cloud_input(label, section, key, input_type="number", step=None, **kwargs):
    if 'app_db' not in st.session_state: init_session_state()
    if section not in st.session_state.app_db: st.session_state.app_db[section] = {}
    
    widget_id = f"{section}_{key}"
    db_val = st.session_state.app_db[section].get(key)
    
    # 1. Initialize State if missing
    if widget_id not in st.session_state:
        if db_val is not None:
             st.session_state[widget_id] = db_val
        else:
             st.session_state[widget_id] = 0.0 if input_type == "number" else ""

    # 2. AGGRESSIVE RESYNC:
    # If the widget (session_state) is 0, but the Database has a real number,
    # we OVERWRITE the session state to match the database immediately.
    try:
        current_val = float(st.session_state.get(widget_id, 0))
    except (ValueError, TypeError):
        current_val = 0.0

    try:
        db_val_float = float(db_val) if db_val is not None and str(db_val) != "" else 0.0
    except (ValueError, TypeError):
        db_val_float = 0.0
    
    if input_type == "number" and current_val == 0.0 and db_val_float != 0.0:
        st.session_state[widget_id] = db_val_float

    # 3. RENDER WIDGET
    # We DO NOT use 'value=' to avoid the Duplicate Error.
    # Instead, we rely on the session_state update above to populate the widget.
    if input_type == "number":
        st.number_input(
            label, 
            step=step, 
            key=widget_id, 
            on_change=sync_widget, args=(f"{section}:{key}",),
            **kwargs 
        )
    else:
        st.text_input(
            label, 
            key=widget_id, 
            on_change=sync_widget, args=(f"{section}:{key}",),
            **kwargs
        )
        
    return st.session_state[widget_id]
