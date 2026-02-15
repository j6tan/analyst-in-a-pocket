import streamlit as st
from supabase import create_client

# --- 1. CLOUD CONNECTION ---
@st.cache_resource
def init_supabase():
    """Establishes connection using your Streamlit Secrets."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# --- 2. THE MASTER DATA STRUCTURE (DEFAULTS) ---
# This is critical. It defines the 'map' of your app's memory.
DEFAULTS = {
    "profile": {
        "p1_name": "Primary Client", "p2_name": "", "province": "Ontario",
        "p1_t4": 0.0, "p1_bonus": 0.0, "p1_commission": 0.0, "p1_pension": 0.0,
        "p2_t4": 0.0, "p2_bonus": 0.0, "p2_commission": 0.0, "p2_pension": 0.0,
        "inv_rental_income": 0.0, "housing_status": "Renting",
        "car_loan": 0.0, "student_loan": 0.0, "cc_pmt": 0.0, "loc_balance": 0.0
    },
    "affordability": {
        "down_payment": 50000.0, "rate": 4.25, "amort": 25, "stress_rate": 6.25,
        "condo_fees": 0.0, "prop_taxes": 4000.0, "heat": 125.0, "is_fthb": False,
        "is_toronto": False, "prop_type": "House / Freehold", "strata": 0.0,
        "bank_rate": 4.26
    },
    "mortgage": {
        "price": 800000.0, "down": 160000.0, "amort": 25, "rate": 5.0
    }
}

# --- 3. SESSION INITIALIZATION ---
def init_session_state():
    """Bootstraps the app's memory on startup."""
    if "app_db" not in st.session_state:
        st.session_state.app_db = DEFAULTS
    if "is_logged_in" not in st.session_state:
        st.session_state.is_logged_in = False

# --- 4. DATA LOADING (LOGIN) ---
def load_user_data(username):
    """Fetches user record from Supabase or creates a new one."""
    try:
        response = supabase.table("user_vault").select("data").eq("id", username).execute()
        if response.data:
            st.session_state.app_db = response.data[0]['data']
            st.toast(f"☁️ {username.capitalize()}'s data synced")
        else:
            # New user logic
            st.session_state.app_db = DEFAULTS
            supabase.table("user_vault").insert({"id": username, "data": DEFAULTS}).execute()
            st.toast("🆕 Created new Cloud Vault")
    except Exception as e:
        st.error(f"Cloud Load Error: {e}")

# --- 5. THE UNIVERSAL SYNC SYSTEM ---
def sync_widget(widget_key):
    """The engine that makes changes 'stick' to Supabase."""
    if widget_key not in st.session_state:
        return
        
    category, data_key = widget_key.split(":")
    new_value = st.session_state[widget_key]
    
    # Update local state
    if 'app_db' in st.session_state:
        st.session_state.app_db[category][data_key] = new_value
        
        # Immediate Cloud Push
        if st.session_state.get("is_logged_in", False):
            username = st.session_state.get("username")
            try:
                # Use upsert to handle both updates and first-time inserts
                supabase.table("user_vault").upsert({
                    "id": username, 
                    "data": st.session_state.app_db
                }).execute()
                st.toast(f"✅ Saved {data_key}")
            except Exception as e:
                print(f"Cloud Sync Error: {e}")

# --- 6. THE SMART INPUT HELPER ---
def cloud_input(label, category, key, input_type="number", **kwargs):
    """Generates a UI widget that is automatically cloud-synced."""
    widget_id = f"{category}:{key}"
    
    # Safety Check: Ensure the structure exists
    if category not in st.session_state.app_db:
        st.session_state.app_db[category] = {}
        
    current_val = st.session_state.app_db[category].get(key, 0.0 if input_type=="number" else "")
    
    if input_type == "number":
        return st.number_input(label, value=float(current_val), key=widget_id, 
                               on_change=sync_widget, args=(widget_id,), **kwargs)
    elif input_type == "text":
        return st.text_input(label, value=str(current_val), key=widget_id, 
                             on_change=sync_widget, args=(widget_id,), **kwargs)
