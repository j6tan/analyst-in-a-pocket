import streamlit as st
from supabase import create_client

# --- 1. CONNECTION ---
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# --- 2. THE DEFAULT STRUCTURE ---
# This ensures that even if Supabase is empty, your app doesn't crash
DEFAULTS = {
    "profile": {
        "p1_name": "Investor", "province": "Ontario", "is_pro": False,
        "p1_t4": 0.0, "p1_bonus": 0.0, "p2_t4": 0.0, "housing_status": "Renting"
    },
    "smith": {
        "mortgage_amt": 500000.0, "amortization": 25, "mortgage_rate": 5.0
    },
    "mortgage": {
        "price": 800000.0, "down": 160000.0, "amort": 25
    }
}

def init_session_state():
    """
    Called by streamlit_app.py at startup.
    Ensures app_db exists in memory.
    """
    if "app_db" not in st.session_state:
        st.session_state.app_db = DEFAULTS
    if "is_logged_in" not in st.session_state:
        st.session_state.is_logged_in = False

# --- 3. THE UNIVERSAL SYNC FUNCTION ---
def sync_widget(widget_key):
    if widget_key not in st.session_state:
        return
        
    category, data_key = widget_key.split(":")
    new_value = st.session_state[widget_key]
    
    if 'app_db' in st.session_state:
        st.session_state.app_db[category][data_key] = new_value
        
        if st.session_state.get("is_logged_in", False):
            username = st.session_state.get("username")
            try:
                # UPSERT creates the record if 'dori' doesn't exist yet
                supabase.table("user_vault").upsert({
                    "id": username, 
                    "data": st.session_state.app_db
                }).execute()
                st.toast(f"✅ Saved to Cloud")
            except Exception as e:
                print(f"Cloud Sync Error: {e}")

# --- 4. THE SMART INPUT HELPER ---
def cloud_input(label, category, key, input_type="number", **kwargs):
    widget_id = f"{category}:{key}"
    
    # Safety check to prevent crashes if a category is missing
    if category not in st.session_state.app_db:
        st.session_state.app_db[category] = {}
        
    current_val = st.session_state.app_db[category].get(key, 0.0 if input_type=="number" else "")
    
    if input_type == "number":
        return st.number_input(label, value=float(current_val), key=widget_id, 
                               on_change=sync_widget, args=(widget_id,), **kwargs)
    elif input_type == "text":
        return st.text_input(label, value=str(current_val), key=widget_id, 
                             on_change=sync_widget, args=(widget_id,), **kwargs)
