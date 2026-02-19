import streamlit as st
from supabase import create_client, Client

# --- 1. DEFAULT DATABASE (Fallback) ---
DEFAULT_DB = {
    "profile": {
        "province": "BC", "housing_status": "Renting",
        "p1_name": "", "p2_name": "",
        "p1_t4": 0, "p2_t4": 0, "m_rate": 4.5, "m_amort": 25.0
    },
    "budget": {
        "groceries": 0, "dining": 0, "utilities": 0, "gas_transit": 0
    },
    "affordability": {
        "bank_rate": 4.5, "prop_taxes": 0, "heat": 0
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
        return None

supabase = init_supabase()

# --- 3. SESSION UTILS ---
def init_session_state():
    if 'app_db' not in st.session_state:
        st.session_state.app_db = {}
    
    defaults = ['profile', 'affordability', 'budget', 'affordability_second', 'mortgage_scenario', 'smith_maneuver', 'sales_proceeds', 'simple_mortgage', 'buy_vs_rent', 'rental_vs_stock', 'renewal_analysis']
    for section in defaults:
        if section not in st.session_state.app_db:
            st.session_state.app_db[section] = {}

def trigger_auto_save():
    if st.session_state.get('is_logged_in') and st.session_state.get('username') and supabase:
        try:
            supabase.table('user_vault').upsert({
                'id': st.session_state.username, 
                'data': st.session_state.app_db
            }).execute()
        except: pass

def sync_widget(key_path):
    if 'app_db' not in st.session_state: init_session_state()
    
    if ':' in key_path:
        section, key = key_path.split(":")
        widget_id = f"{section}_{key}"
        
        if widget_id in st.session_state:
            val = st.session_state[widget_id]
            # Save to DB
            if section not in st.session_state.app_db:
                st.session_state.app_db[section] = {}
            st.session_state.app_db[section][key] = val
            trigger_auto_save()

# --- 4. DATA LOADER ---
def load_user_data(user_id):
    init_session_state()
    if not supabase: return

    try:
        response = supabase.table('user_vault').select('data').eq('id', user_id).execute()
        if response.data and len(response.data) > 0:
            cloud_data = response.data[0]['data']
            if cloud_data:
                st.session_state.app_db = cloud_data
                st.toast(f"✅ Data Loaded", icon="📂")
    except Exception as e:
        st.error(f"Sync Error: {e}")

# --- 5. THE NUCLEAR CLOUD_INPUT ---
def cloud_input(label, section, key, input_type="number", step=None, **kwargs):
    init_session_state()
    
    # 1. Ensure DB Section Exists
    if section not in st.session_state.app_db: 
        st.session_state.app_db[section] = {}
    
    widget_id = f"{section}_{key}"
    
    # 2. Get the "Truth" from DB (or Default)
    db_val = st.session_state.app_db[section].get(key)
    if db_val is None:
        db_val = DEFAULT_DB.get(section, {}).get(key)

    # 3. PRE-SEED THE WIDGET VALUE
    # This is the "Nuclear Option." We calculate exactly what the widget *should* hold
    # and force it into session_state BEFORE the widget is drawn.
    
    final_val = None

    if input_type == "number":
        # DETERMINE IF INT OR FLOAT BASED ON STEP
        is_float_widget = isinstance(step, float) if step is not None else True
        
        # Sanitize the DB value
        if db_val is not None and str(db_val).strip() != "":
            try:
                if is_float_widget:
                    final_val = float(db_val)
                else:
                    final_val = int(float(db_val)) # Handle "100.0" -> 100
            except:
                final_val = 0.0 if is_float_widget else 0
        else:
            final_val = 0.0 if is_float_widget else 0
            
    else:
        # TEXT INPUT HANDLING
        if db_val is not None:
            final_val = str(db_val)
        else:
            final_val = ""

    # 4. FORCE UPDATE SESSION STATE
    # Only update if missing or different to avoid Streamlit loop warnings, 
    # but ensure the type is strictly enforced.
    if widget_id not in st.session_state or st.session_state[widget_id] != final_val:
        st.session_state[widget_id] = final_val

    # 5. RENDER THE WIDGET
    # We rely on the fact that st.session_state[widget_id] is now set correctly.
    if input_type == "number":
        st.number_input(
            label, step=step, key=widget_id, 
            on_change=sync_widget, args=(f"{section}:{key}",),
            **kwargs 
        )
    else:
        st.text_input(
            label, key=widget_id, 
            on_change=sync_widget, args=(f"{section}:{key}",),
            **kwargs
        )
        
    return st.session_state[widget_id]
