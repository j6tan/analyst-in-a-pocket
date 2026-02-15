import streamlit as st
from supabase import create_client

# --- 1. CONNECTION ---
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# --- 2. THE UNIVERSAL SYNC FUNCTION ---
def sync_widget(widget_key):
    """
    Splits a key like 'profile:p1_t4' and saves the entire state to Supabase.
    """
    if widget_key not in st.session_state:
        return
        
    category, data_key = widget_key.split(":")
    new_value = st.session_state[widget_key]
    
    # Update local memory
    if 'app_db' in st.session_state:
        st.session_state.app_db[category][data_key] = new_value
        
        # PUSH TO CLOUD
        if st.session_state.get("is_logged_in", False):
            username = st.session_state.get("username")
            try:
                # UPSERT ensures the row is created if it doesn't exist
                supabase.table("user_vault").upsert({
                    "id": username, 
                    "data": st.session_state.app_db
                }).execute()
                st.toast(f"✅ Saved to Cloud")
            except Exception as e:
                print(f"Cloud Sync Error: {e}")

# --- 3. THE SMART INPUT HELPER ---
def cloud_input(label, category, key, input_type="number", **kwargs):
    """Generates an input wired to the sync_widget."""
    widget_id = f"{category}:{key}"
    
    # Ensure category exists in app_db
    if category not in st.session_state.app_db:
        st.session_state.app_db[category] = {}
        
    current_val = st.session_state.app_db[category].get(key, 0.0 if input_type=="number" else "")
    
    if input_type == "number":
        return st.number_input(label, value=float(current_val), key=widget_id, 
                               on_change=sync_widget, args=(widget_id,), **kwargs)
    elif input_type == "text":
        return st.text_input(label, value=str(current_val), key=widget_id, 
                             on_change=sync_widget, args=(widget_id,), **kwargs)
