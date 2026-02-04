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

# --- 4. OPTION C NAVIGATION (Grouped Sidebar) ---
pages = {
    "Overview": [
        st.Page("home.py", title="Home Dashboard", icon="🏠", default=True),
        st.Page("scripts/profile.py", title="Client Profile", icon="👤"),
    ],
    "🏠 Foundations & Budgeting": [
        st.Page("scripts/budget_tracker.py", title="Monthly Budget Tracker", icon="📊"),
        st.Page("scripts/affordability.py", title="Simple Affordability", icon="🤔"),
        st.Page("scripts/buy_vs_rent.py", title="Buy vs Rent", icon="⚖️"),
    ],
    "💰 Buying & Selling Process": [
        st.Page("scripts/buying_costs.py", title="House Buying Costs", icon="💸"),
        st.Page("scripts/selling_proceeds.py", title="Selling & Proceeds", icon="💰"),
        st.Page("scripts/mortgage_simple.py", title="Simple Mortgage Calc", icon="🧮"),
        st.Page("scripts/listing_comparison.py", title="Buying Analysis (Compare)", icon="🏘️"),
    ],
    "🚀 Advanced Wealth Strategy": [
        st.Page("scripts/mortgage_scenario.py", title="Mortgage Scenarios 🔒", icon="📈"),
        st.Page("scripts/smith_maneuver.py", title="Smith Maneuver 🔒", icon="🛡️"),
        st.Page("scripts/affordability_second.py", title="Secondary Property 🔒", icon="🏢"),
        st.Page("scripts/renewal_scenario.py", title="Renewal Scenario 🔒", icon="🔄"),
        st.Page("scripts/rental_vs_stock.py", title="Rental vs Stock 🔒", icon="📉"),
        st.Page("scripts/rental_analysis.py", title="Rental Analysis 🔒", icon="📋"),
        st.Page("scripts/refinance.py", title="Refinance 🔒", icon="🏦"),
    ],
    "🛠️ Developer Toolkit": [
        st.Page("scripts/land_residual.py", title="Land Residual", icon="🏗️"),
        st.Page("scripts/income_proforma.py", title="Income Proforma", icon="📈"),
        st.Page("scripts/comparable_analysis.py", title="Comparable Analysis", icon="📋"),
    ]
}

pg = st.navigation(pages)
pg.run()

