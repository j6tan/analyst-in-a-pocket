import streamlit as st
import json
import os

# --- 1. DATA PERSISTENCE LOGIC ---
DB_FILE = "user_profile_db.json"

def load_profile():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    # Default values if no file exists
    return {
        "p1_name": "", "p2_name": "",
        "p1_t4": 0.0, "p1_bonus": 0.0, "p1_commission": 0.0, "p1_pension": 0.0,
        "p2_t4": 0.0, "p2_bonus": 0.0, "p2_commission": 0.0, "p2_pension": 0.0,
        "inv_rental_income": 0.0,
        "car_loan": 0.0, "student_loan": 0.0, "cc_pmt": 0.0, "loc_pmt": 0.0, "loc_balance": 0.0,
        "housing_status": "Renting", "province": "Ontario",
        "m_bal": 0.0, "m_rate": 0.0, "m_amort": 25, "prop_taxes": 4200.0, "rent_pmt": 0.0,
        "heat_pmt": 125.0, "is_pro": False
    }

# --- 2. INITIALIZE SESSION ---
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = load_profile()

if 'is_pro' not in st.session_state:
    st.session_state.is_pro = st.session_state.user_profile.get("is_pro", False)

# --- 3. DEV TOOLS (Sidebar Toggle) ---
with st.sidebar:
    st.title("🛠️ Dev Tools")
    st.session_state.is_pro = st.checkbox("Simulate Paid Account", value=st.session_state.is_pro)
    st.divider()
