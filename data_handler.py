import streamlit as st
from supabase import create_client, Client

# --- 1. DEFAULT DATABASE (Fallback System) ---
DEFAULT_DB = {
    "profile": {
        "province": "BC", 
        "housing_status": "Renting",
        "p1_t4": 0, "p2_t4": 0, 
        "m_rate": 4.5, "m_amort": 25.0
    },
    "budget": {
        "groceries": 600, "dining": 300, 
        "utilities": 150, "gas_transit": 200
    },
    "affordability": {
        "bank_rate": 4.5, 
        "prop_taxes": 3000, "heat": 150
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
                            st.session_state[widget_id] = value
                            
                st.toast(f"✅ Data Loaded", icon="📂")
    except Exception as e:
        st.error(f"Sync Error: {e}")

# --- 6. SMART INPUT (INTEGER / FLOAT DETECTOR) ---
def cloud_input(label, section, key, input_type="number", step=None, **kwargs):
    init_session_state()
    if section not in st.session_state.app_db: st.session_state.app_db[section] = {}
    
    widget_id = f"{section}_{key}"
    
    # 1. FETCH SOURCES
    state_val = st.session_state.get(widget_id)
    db_val = st.session_state.app_db[section].get(key)
    default_val = DEFAULT_DB.get(section, {}).get(key)
    
    # 2. DETERMINE "TRUE" VALUE
    final_val = None
    if db_val is not None and str(db_val).strip() != "":
        final_val = db_val
    elif final_val is None:
        if default_val is not None:
            final_val = default_val

    # 3. TYPE ENFORCEMENT BASED ON STEP
    # If step is Float (0.1), we force Float.
    # If step is Int (100) or None, we force Int.
    if input_type == "number" and final_val is not None:
        try:
            is_float_mode = isinstance(step, float)
            
            if is_float_mode:
                final_val = float(final_val)
            else:
                final_val = int(float(final_val)) # Handle "100.0" -> 100
                
            # Update Session State if mismatched
            if state_val != final_val:
                st.session_state[widget_id] = final_val
        except:
            pass

    # 4. RENDER WIDGET
    if input_type == "number":
        # Default fallback
        if widget_id not in st.session_state: 
            st.session_state[widget_id] = 0.0 if isinstance(step, float) else 0
        
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
