import streamlit as st
from style_utils import inject_global_css
from data_handler import cloud_input

# 1. Inject the Wealthsimple-inspired Editorial CSS
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

st.title("👤 General Client Information")
st.info("Your information is saved automatically to your Cloud Vault.")

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
    # Note: Radio buttons require a slightly different helper if you have many, 
    # but for now, we'll keep the direct update logic for the radio specifically.
    from data_handler import sync_widget
    status_options = ["Renting", "Owning"]
    curr_status = st.session_state.app_db['profile'].get('housing_status', 'Renting')
    
    st.radio(
        "Current Status", 
        status_options, 
        index=status_options.index(curr_status),
        key="profile:housing_status",
        on_change=sync_widget,
        args=("profile:housing_status",)
    )

with h_data:
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
    prov_options = ["Ontario", "BC", "Alberta", "Quebec", "Manitoba", "Saskatchewan", "Nova Scotia", "NB", "PEI", "NL"]
    curr_prov = st.session_state.app_db['profile'].get('province', 'Ontario')
    
    st.selectbox(
        "Province", 
        prov_options, 
        index=prov_options.index(curr_prov),
        key="profile:province",
        on_change=sync_widget,
        args=("profile:province",)
    )

st.success("✅ Financial Passport updated and synchronized with Cloud Vault.")
