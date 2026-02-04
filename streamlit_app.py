import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px

# --- 1. GLOBAL CONFIG ---
st.set_page_config(layout="wide", page_title="Analyst in a Pocket", page_icon="📊")

# --- 2. INITIALIZE GLOBAL VAULT ---
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        "p1_name": "Investor", "p2_name": "",
        "p1_t4": 0.0, "p1_bonus": 0.0, "p1_commission": 0.0, "p1_pension": 0.0,
        "p2_t4": 0.0, "p2_bonus": 0.0, "p2_commission": 0.0, "p2_pension": 0.0,
        "inv_rental_income": 0.0,
        "car_loan": 0.0, "student_loan": 0.0, "cc_pmt": 0.0, "loc_pmt": 0.0, "loc_balance": 0.0,
        "housing_status": "Renting", "province": "Ontario",
        "m_bal": 0.0, "m_rate": 0.0, "m_amort": 25, "prop_taxes": 4200.0, "rent_pmt": 0.0,
        "heat_pmt": 125.0
    }

# --- 3. NAVIGATION DEFINITION ---
# The dictionary keys are the display names, values are the script filenames
tools = {
    "🏠 Home Dashboard": "DASHBOARD",
    "👤 Client Profile": "PROFILE",
    "📊 Affordability Primary": "affordability.py",
    "🏢 Affordability Secondary": "affordability_second.py", 
    "🛡️ Smith Maneuver": "smith_maneuver.py",
    "📉 Mortgage Scenarios": "mortgage_scenario.py",
    "🔄 Renewal Dilemma": "renewal_analysis.py",
    "⚖️ Buy vs Rent": "buy_vs_rent.py",
    "⚖️ Rental vs Stock": "rental_vs_stock.py",
}

with st.sidebar:
    st.title("FIRE Toolkit")
    # Using a radio to manage navigation
    selection = st.radio("Navigation", list(tools.keys()))
    st.divider()
    
    # Global Profile Download
    profile_json = json.dumps(st.session_state.user_profile, indent=4)
    st.download_button(
        label="Download Profile (JSON)",
        data=profile_json,
        file_name="client_profile.json",
        mime="application/json",
        use_container_width=True
    )

# --- 4. PAGE ROUTING LOGIC ---

# OPTION B: DASHBOARD LANDING PAGE
if selection == "🏠 Home Dashboard":
    st.title("🚀 Analyst in a Pocket: FIRE Dashboard")
    
    # --- FINANCIAL PASSPORT (CENTRAL DATA SUMMARY) ---
    with st.container(border=True):
        p1_income = st.session_state.user_profile['p1_t4']
        p2_income = st.session_state.user_profile['p2_t4']
        total_income = p1_income + p2_income
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Household Income", f"${total_income:,.0f}")
        c2.metric("Province", st.session_state.user_profile['province'])
        c3.metric("Status", st.session_state.user_profile['housing_status'])
        c4.write("### Financial Passport")
        if c4.button("Update Profile", use_container_width=True):
            st.info("Select '👤 Client Profile' in the sidebar to edit.")

    st.write("") # Spacing

    # --- TIER 1: FOUNDATIONS & BUDGETING ---
    st.subheader("🏠 Foundations & Budgeting")
    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        with st.container(border=True):
            st.markdown("### ⚖️ Buy vs. Rent")
            st.write("Compare long-term wealth building between home ownership and renting/investing.")
            st.caption("Free Tier")
            # Note: To "Switch" pages in this setup, the user must use the sidebar, 
            # but we show the tool info here.
    
    with f_col2:
        with st.container(border=True):
            st.markdown("### 📊 Simple Affordability")
            st.write("Calculate your maximum mortgage based on your current T4 income and debt.")
            st.caption("Free Tier")

    with f_col3:
        with st.container(border=True):
            st.markdown("### 📈 Rate Trends")
            st.write("View historical Bank Prime and 5-Year Fixed interest rate trends.")
            st.caption("Free Tier")

    # --- TIER 1.5: BUYING & SELLING ---
    st.divider()
    st.subheader("💰 Buying & Selling Process")
    b_col1, b_col2, b_col3 = st.columns(3)
    
    with b_col1:
        with st.container(border=True):
            st.markdown("### 🏢 Secondary Home")
            st.write("Analysis for rental property acquisitions and downpayment requirements.")
            
    with b_col2:
        with st.container(border=True):
            st.markdown("### 🔄 Renewal Dilemma")
            st.write("Evaluate if you should switch lenders or stay for your upcoming renewal.")

    # --- TIER 2: ADVANCED WEALTH STRATEGY (PRO) ---
    st.divider()
    st.subheader("🚀 Advanced Wealth Strategy (Pro)")
    a_col1, a_c2 = st.columns(2)
    
    with a_col1:
        with st.container(border=True):
            st.markdown("### 🛡️ Smith Maneuver 🔒")
            st.write("Calculate tax-deductible interest conversion strategies for Canadian homeowners.")
            st.button("Upgrade to Tier 2 ($15/mo)", key="btn_smith", type="primary")

    with a_c2:
        with st.container(border=True):
            st.markdown("### 📉 Mortgage Scenarios 🔒")
            st.write("Advanced modeling for lump-sum prepayments vs. equity market investing.")
            st.button("Unlock Advanced Modeling", key="btn_mortgage", type="primary")

# CLIENT PROFILE PAGE
elif selection == "👤 Client Profile":
    st.title("General Client Information")
    
    # ... (Your existing Profile Questionnaire code from streamlit_app (2).py) ...
    # Ensure all st.session_state updates remain as you have them.
    
    # (Simplified Example for placeholder)
    st.subheader("💾 Profile Management")
    uploaded_file = st.file_uploader("Upload Existing Profile (JSON)", type=["json"])
    if uploaded_file is not None:
        st.session_state.user_profile.update(json.load(uploaded_file))
        st.success("Profile Loaded!")
    
    # [Insert your full Client Profile UI code here]
    st.info("The central profile data is shared across all tools below.")

# TOOL SCRIPT EXECUTION
else:
    file_path = os.path.join("scripts", tools[selection])
    if os.path.exists(file_path):
        # We wrap this in a container to clearly separate it from the sidebar
        with st.container():
            # Pass session_state to the executed script
            exec(open(file_path, encoding="utf-8").read(), globals())
    else:
        st.error(f"Error: Tool script not found at {file_path}. Please ensure your scripts are in the 'scripts' folder.")
