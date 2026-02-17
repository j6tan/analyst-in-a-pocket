import streamlit as st
import time
from style_utils import inject_global_css
from data_handler import cloud_input, load_user_data, supabase

# 1. Inject Style
inject_global_css()

# --- 2. SMART DATA LOADER (The Fix) ---
# This ensures that if you land here and data is missing, we fetch it immediately.
if 'app_db' not in st.session_state:
    st.session_state.app_db = {}

# Check if profile is empty (blank data)
profile_data = st.session_state.app_db.get('profile', {})
is_empty = not profile_data.get('p1_name')

if is_empty and st.session_state.get('user'):
    user = st.session_state.user
    # Handle user object vs dictionary
    user_id = user.id if hasattr(user, 'id') else user.get('id')
    
    with st.spinner("🔄 Fetching Dori's data from cloud..."):
        load_user_data(user_id)
        time.sleep(0.5) # Give state a moment to settle
        st.rerun() # Refresh page to show the data

# --- PAGE LAYOUT ---
if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

st.title("👤 General Client Information")

# Connection Status Indicator
if supabase:
    st.caption("🟢 Cloud Status: **Online & Synced**")
else:
    st.error("🔴 Cloud Status: **Offline** (Check Secrets)")

# --- SECTION 1: HOUSEHOLD INCOME DETAILS ---
st.subheader("👥 Household Income Details")
c1, c2 = st.columns(2)

with c1:
    st.markdown("### Primary Client")
    cloud_input("Full Name", "profile", "p1_name", input_type="text")
    cloud_input("T4 (Employment Income)", "profile", "p1_t4", step=1000.0)
    cloud_input("Bonuses / Performance Pay", "profile", "p1_bonus", step=500.0)
    cloud_input("Commissions", "profile", "p1_commission", step=500.0)
    cloud_input("Pension / CPP / OAS", "profile", "p1_pension", step=100.0)

with c2:
    st.markdown("### Co-Owner / Partner")
    cloud_input("Full Name ", "profile", "p2_name", input_type="text")
    cloud_input("T4 (Employment Income) ", "profile", "p2_t4", step=1000.0)
    cloud_input("Bonuses / Performance Pay ", "profile", "p2_bonus", step=500.0)
    cloud_input("Commissions ", "profile", "p2_commission", step=500.0)
    cloud_input("Pension / CPP / OAS ", "profile", "p2_pension", step=100.0)

# Joint Rental Income
cloud_input("Joint Rental Income (Current Portfolio)", "profile", "inv_rental_income", step=100.0)

st.divider()

# --- SECTION 2: HOUSING & PROPERTY ---
st.subheader("🏠 Housing & Property Details")
h_toggle, h_data = st.columns([1, 2])

with h_toggle:
    # Manual Sync for Radio Button
    from data_handler import sync_widget
    status_options = ["Renting", "Owning"]
    curr_status = st.session_state.app_db['profile'].get('housing_status', 'Renting')
    
    # Handle case where curr_status might be empty/None
    if curr_status not in status_options: curr_status = "Renting"
    
    st.radio(
        "Current Status", 
        status_options, 
        index=status_options.index(curr_status),
        key="profile:housing_status",
        on_change=sync_widget,
        args=("profile:housing_status",)
    )

with h_data:
    # Check the DB value directly for immediate UI update
    if st.session_state.app_db['profile'].get('housing_status') == "Renting":
        cloud_input("Monthly Rent ($)", "profile", "rent_pmt", step=50.0)
    else:
        sub_c1, sub_c2 = st.columns(2)
        with sub_c1:
            cloud_input("Current Mortgage Balance ($)", "profile", "m_bal", step=1000.0)
            cloud_input("Current Interest Rate (%)", "profile", "m_rate", step=0.1)
        with sub_c2:
            cloud_input("Remaining Amortization (Years)", "profile", "m_amort", step=1.0)
            cloud_input("Annual Property Taxes ($)", "profile", "prop_taxes", step=100.0)
            cloud_input("Estimated Monthly Heating ($)", "profile", "heat_pmt", step=10.0)

st.divider()

# --- SECTION 3: MONTHLY LIABILITIES ---
st.subheader("💳 Monthly Liabilities")
l1, l2, l3 = st.columns(3)
with l1:
    cloud_input("Car Loan Payments (Monthly)", "profile", "car_loan", step=50.0)
    cloud_input("Student Loan Payments (Monthly)", "profile", "student_loan", step=50.0)
with l2:
    cloud_input("Credit Card Payments (Monthly)", "profile", "cc_pmt", step=50.0)
    cloud_input("Total LOC Balance ($)", "profile", "loc_balance", step=500.0)
with l3:
    # Manual Sync for Selectbox
    prov_options = ["Ontario", "BC", "Alberta", "Quebec", "Manitoba", "Saskatchewan", "Nova Scotia", "NB", "PEI", "NL"]
    curr_prov = st.session_state.app_db['profile'].get('province', 'Ontario')
    if curr_prov not in prov_options: curr_prov = "Ontario"
    
    st.selectbox(
        "Province", 
        prov_options, 
        index=prov_options.index(curr_prov),
        key="profile:province",
        on_change=sync_widget,
        args=("profile:province",)
    )

st.success("✅ Financial Passport updated and synchronized with Cloud Vault.")
