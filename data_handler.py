import streamlit as st
from supabase import create_client, Client

# --- 1. DEFAULT DATABASE (Fallback System) ---
# If Supabase is empty or keys are missing, these values will load.
DEFAULT_DB = {
    "profile": {
        "province": "BC",
        "housing_status": "Renting",
        "p1_t4": 0.0,
        "p2_t4": 0.0,
        "m_rate": 4.5,
        "m_amort": 25.0,
        "p1_name": "Client",
    },
    "budget": {
        "groceries": 600.0,
        "dining": 300.0,
        "utilities": 150.0,
        "gas_transit": 200.0,
        "misc": 100.0
    },
    "affordability": {
        "bank_rate": 4.5,
        "prop_taxes": 3000.0,
        "heat": 150.0
    }
}

# --- 2. CONNECTION ---
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

# --- 3. SESSION MANAGEMENT ---
def init_session_state():
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    
    defaults = ['profile', 'affordability', 'mortgage_scenario', 'smith_maneuver', 'budget', 'affordability_second', 'sales_proceeds', 'simple_mortgage', 'buy_vs_rent', 'rental_vs_stock', 'renewal_analysis']
    for section in defaults:
        if section not in st.session_state.app_db:
            st.session_state.app_db[section] = {}

# --- 4. AUTO-SAVE ---
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
            val = st.session_state[widget_id]
            # Ensure we save as standard types to avoid JSON issues
            if isinstance(val, (int, float)):
                val = float(val)
            
            if section not in st.session_state.app_db:
                st.session_state.app_db[section] = {}
            st.session_state.app_db[section][key] = val
            trigger_auto_save()

# --- 5. DATA LOADER ---
def load_user_data(user_id):
    init_session_state()
    if not supabase: return

    try:
        response = supabase.table('user_vault').select('data').eq('id', user_id).execute()
        if response.data and len(response.data) > 0:
            cloud_data = response.data[0]['data']
            if cloud_data:
                st.session_state.app_db = cloud_data
                
                # PRIME SESSION STATE 
                for section, content in cloud_data.items():
                    if isinstance(content, dict):
                        for key, value in content.items():
                            widget_id = f"{section}_{key}"
                            
                            # Pre-convert to float to help widgets
                            if isinstance(value, int):
                                value = float(value)
                                
                            st.session_state[widget_id] = value
                            
                st.toast(f"✅ Data Loaded", icon="📂")
    except Exception as e:
        st.error(f"Sync Error: {e}")

# --- 6. SMART INPUT (THE FIX) ---
def cloud_input(label, section, key, input_type="number", step=None, **kwargs):
    init_session_state()
    if section not in st.session_state.app_db: st.session_state.app_db[section] = {}
    
    widget_id = f"{section}_{key}"
    
    # 1. FETCH SOURCES
    state_val = st.session_state.get(widget_id)
    db_val = st.session_state.app_db[section].get(key)
    default_val = DEFAULT_DB.get(section, {}).get(key) # Fallback
    
    # 2. DETERMINE "TRUE" VALUE (Priority: DB > Default)
    final_val = None
    
    # Priority A: Database Value
    if db_val is not None and str(db_val).strip() != "":
        try:
            final_val = float(db_val) if input_type == "number" else str(db_val)
        except: pass
        
    # Priority B: Default Value (Only if DB is empty/missing)
    if final_val is None:
        if default_val is not None:
            final_val = float(default_val) if input_type == "number" else str(default_val)

    # 3. TYPE ENFORCEMENT (STRICT)
    # This logic forces the session state to match the widget type exactly.
    if final_val is not None:
        should_update = False
        
        if input_type == "number":
             final_val = float(final_val) # Ensure Float
             
             # Case 1: State is missing
             if state_val is None: 
                 should_update = True
             # Case 2: State is wrong Type (e.g. Int instead of Float)
             elif not isinstance(state_val, float): 
                 should_update = True
             # Case 3: Values differ
             elif state_val != final_val: 
                 should_update = True
        else:
             final_val = str(final_val)
             if state_val != final_val: 
                 should_update = True
                 
        if should_update:
            st.session_state[widget_id] = final_val

    # 4. RENDER WIDGET
    if input_type == "number":
        # Final safety: if still missing, default to 0.0
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
