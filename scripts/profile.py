import streamlit as st
import time
import os
import base64
from style_utils import inject_global_css
from data_handler import cloud_input, load_user_data, supabase, sync_widget, init_session_state

# --- 1. UNIVERSAL AUTO-LOADER (CRITICAL) ---
init_session_state()
# If we have a username but the DB is empty, FORCE A LOAD
if st.session_state.get('username') and not st.session_state.app_db.get('profile', {}).get('p1_name'):
    with st.spinner("🔄 restoring your data..."):
        load_user_data(st.session_state.username)
        time.sleep(0.1)
        st.rerun()

# 2. Inject Style
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 3. INLINE LOGO & TITLE ---
def get_inline_logo(img_name="logo.png", width=75):
    # Check root directory first, then fallback to looking one folder up
    img_path = img_name
    if not os.path.exists(img_path):
        img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), img_name)
        
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{encoded}" style="width: {width}px; flex-shrink: 0;">'
    return "<span style='font-size: 50px;'>🔥</span>"

logo_html = get_inline_logo(width=75)

st.markdown(f"""
    <div style='display: flex; align-items: center; justify-content: flex-start; gap: 15px; margin-top: -20px; margin-bottom: 25px;'>
        {logo_html}
        <h1 style='margin: 0 !important; padding: 0 !important; line-height: 1 !important;'>General Client Information</h1>
    </div>
""", unsafe_allow_html=True)


# --- SECTION 1: INCOME ---
st.subheader("👥 Household Income Details")
c1, c2 = st.columns(2)
with c1:
    st.markdown("### Primary Client")
    # TEXT INPUTS for Names
    cloud_input("Full Name", "profile", "p1_name", input_type="text")
    # INTEGER INPUTS for Salary (step=1000)
    cloud_input("T4 (Employment Income)", "profile", "p1_t4", step=1000)
    cloud_input("Bonuses / Performance Pay", "profile", "p1_bonus", step=500)
    cloud_input("Commissions", "profile", "p1_commission", step=500)
    cloud_input("Pension / CPP / OAS", "profile", "p1_pension", step=100)
with c2:
    st.markdown("### Co-Owner / Partner")
    cloud_input("Full Name ", "profile", "p2_name", input_type="text")
    cloud_input("T4 (Employment Income) ", "profile", "p2_t4", step=1000)
    cloud_input("Bonuses / Performance Pay ", "profile", "p2_bonus", step=500)
    cloud_input("Commissions ", "profile", "p2_commission", step=500)
    cloud_input("Pension / CPP / OAS ", "profile", "p2_pension", step=100)

cloud_input("Joint Rental Income (Current Portfolio)", "profile", "inv_rental_income", step=100)
st.divider()

# --- SECTION 2: HOUSING ---
st.subheader("🏠 Housing & Property Details")
h_toggle, h_data = st.columns([1, 2])

with h_toggle:
    status_options = ["Renting", "Owning"]
    # Manual sync for Radio Button
    curr_status = st.session_state.app_db['profile'].get('housing_status', 'Renting')
    if curr_status not in status_options: curr_status = "Renting"
    
    st.radio(
        "Current Status", 
        status_options, 
        index=status_options.index(curr_status),
        key="profile_housing_status", 
        on_change=sync_widget,
        args=("profile:housing_status",)
    )

with h_data:
    if st.session_state.app_db['profile'].get('housing_status') == "Renting":
        cloud_input("Monthly Rent ($)", "profile", "rent_pmt", step=50)
    else:
        sub_c1, sub_c2 = st.columns(2)
        with sub_c1:
            cloud_input("Current Mortgage Balance ($)", "profile", "m_bal", step=1000)
            # FLOAT for Rate (step=0.1)
            cloud_input("Current Interest Rate (%)", "profile", "m_rate", step=0.1)
        with sub_c2:
            cloud_input("Remaining Amortization (Years)", "profile", "m_amort", step=1.0)
            cloud_input("Annual Property Taxes ($)", "profile", "prop_taxes", step=100)
            cloud_input("Estimated Monthly Heating ($)", "profile", "heat_pmt", step=10)

st.divider()

# --- SECTION 3: LIABILITIES ---
st.subheader("💳 Monthly Liabilities")
l1, l2, l3 = st.columns(3)
with l1:
    cloud_input("Car Loan Payments (Monthly)", "profile", "car_loan", step=50)
    cloud_input("Student Loan Payments (Monthly)", "profile", "student_loan", step=50)
with l2:
    cloud_input("Credit Card Payments (Monthly)", "profile", "cc_pmt", step=50)
    cloud_input("Total LOC Balance ($)", "profile", "loc_balance", step=500)
with l3:
    prov_options = ["Ontario", "BC", "Alberta", "Quebec", "Manitoba", "Saskatchewan", "Nova Scotia", "NB", "PEI", "NL"]
    curr_prov = st.session_state.app_db['profile'].get('province', 'Ontario')
    if curr_prov not in prov_options: curr_prov = "Ontario"
    
    st.selectbox(
        "Province", 
        prov_options, 
        index=prov_options.index(curr_prov),
        key="profile_province",
        on_change=sync_widget,
        args=("profile:province",)
    )

st.success("✅ Profile Updated.")

# --- FOOTER ---
st.markdown("""
    <div style="text-align: center; color: #adb5bd; font-size: 0.85em; margin-top: 50px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        &copy; 2026 FIRE Calculator. All rights reserved. <br>
        <span style="font-size: 0.9em; font-style: italic;">Empowering Canadian professionals to build wealth.</span>
    </div>
""", unsafe_allow_html=True)
