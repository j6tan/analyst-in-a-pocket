import streamlit as st

def show_main_dashboard():
    st.title("🚀 Analyst in a Pocket: FIRE Dashboard")
    
    # --- SECTION 1: FOUNDATIONS ---
    st.header("🏠 Foundations & Budgeting")
    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        with st.container(border=True):
            st.subheader("Budget Tracker")
            st.write("Manage monthly cashflow and savings rate.")
            if st.button("Open Tracker", key="btn_budget"):
                st.session_state.current_page = "budget" # Logic to switch pages
                
    with f_col2:
        with st.container(border=True):
            st.subheader("Simple Affordability")
            st.write("Quick check on home purchase limits.")
            st.button("Calculate", key="btn_afford")

    # --- SECTION 2: BUYING/SELLING ---
    st.divider()
    st.header("💰 Buying & Selling Process")
    b_col1, b_col2, b_col3 = st.columns(3)
    
    # ... Similar logic for Buying/Selling tools ...

    # --- SECTION 3: ADVANCED (TIER 2) ---
    st.divider()
    st.header("🚀 Advanced Wealth Strategy (Pro)")
    a_col1, a_col2 = st.columns(2)
    
    with a_col1:
        # Use a grayed-out style or "locked" visual for Pro tools
        with st.container(border=True):
            st.subheader("🇨🇦 Smith Maneuver 🔒")
            st.caption("Strategic tax-deductible mortgage conversion.")
            st.button("Upgrade to Unlock", key="btn_smith", type="primary")

    with a_col2:
        with st.container(border=True):
            st.subheader("🏘️ Rental Analyzer 🔒")
            st.caption("Deep-dive into Cap Rates and ROI.")
            st.button("Upgrade to Unlock", key="btn_rental", type="primary")
