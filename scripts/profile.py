import streamlit as st
import json

# Internal function to save to the local JSON file
def sync_data():
    with open("user_profile_db.json", "w") as f:
        json.dump(st.session_state.user_profile, f, indent=4)

if st.button("⬅️ Back to Dashboard"):
    st.switch_page("home.py")

st.title("👤 General Client Information")
st.info("Your information is saved automatically to your local session.")

# --- SECTION 1: HOUSEHOLD INCOME DETAILS ---
st.subheader("👥 Household Income Details")
c1, c2 = st.columns(2)

with c1:
    st.markdown("### Primary Client")
    st.session_state.user_profile['p1_name'] = st.text_input("Full Name", value=st.session_state.user_profile.get('p1_name', ""), on_change=sync_data)
    st.session_state.user_profile['p1_t4'] = st.number_input("T4 (Employment Income)", value=float(st.session_state.user_profile.get('p1_t4', 0.0)), on_change=sync_data)
    st.session_state.user_profile['p1_bonus'] = st.number_input("Bonuses / Performance Pay", value=float(st.session_state.user_profile.get('p1_bonus', 0.0)), on_change=sync_data)
    st.session_state.user_profile['p1_commission'] = st.number_input("Commissions", value=float(st.session_state.user_profile.get('p1_commission', 0.0)), on_change=sync_data)
    st.session_state.user_profile['p1_pension'] = st.number_input("Pension / CPP / OAS", value=float(st.session_state.user_profile.get('p1_pension', 0.0)), on_change=sync_data)

with c2:
    st.markdown("### Co-Owner / Partner")
    st.session_state.user_profile['p2_name'] = st.text_input("Full Name ", value=st.session_state.user_profile.get('p2_name', ""), on_change=sync_data)
    st.session_state.user_profile['p2_t4'] = st.number_input("T4 (Employment Income) ", value=float(st.session_state.user_profile.get('p2_t4', 0.0)), on_change=sync_data)
    st.session_state.user_profile['p2_bonus'] = st.number_input("Bonuses / Performance Pay ", value=float(st.session_state.user_profile.get('p2_bonus', 0.0)), on_change=sync_data)
    st.session_state.user_profile['p2_commission'] = st.number_input("Commissions ", value=float(st.session_state.user_profile.get('p2_commission', 0.0)), on_change=sync_data)
    st.session_state.user_profile['p2_pension'] = st.number_input("Pension / CPP / OAS ", value=float(st.session_state.user_profile.get('p2_pension', 0.0)), on_change=sync_data)

# Joint Rental Income
st.session_state.user_profile['inv_rental_income'] = st.number_input("Joint Rental Income (Current Portfolio)", value=float(st.session_state.user_profile.get('inv_rental_income', 0.0)), on_change=sync_data)

st.divider()

# --- SECTION 2: HOUSING & PROPERTY ---
st.subheader("🏠 Housing & Property Details")
h_toggle, h_data = st.columns([1, 2])
with h_toggle:
    st.session_state.user_profile['housing_status'] = st.radio("Current Status", ["Renting", "Owning"], index=0 if st.session_state.user_profile.get('housing_status') == "Renting" else 1, on_change=sync_data)

with h_data:
    if st.session_state.user_profile['housing_status'] == "Renting":
        st.session_state.user_profile['rent_pmt'] = st.number_input("Monthly Rent ($)", value=float(st.session_state.user_profile.get('rent_pmt', 0.0)), on_change=sync_data)
    else:
        sub_c1, sub_c2 = st.columns(2)
        with sub_c1:
            st.session_state.user_profile['m_bal'] = st.number_input("Current Mortgage Balance ($)", value=float(st.session_state.user_profile.get('m_bal', 0.0)), on_change=sync_data)
            st.session_state.user_profile['m_rate'] = st.number_input("Current Interest Rate (%)", value=float(st.session_state.user_profile.get('m_rate', 0.0)), on_change=sync_data)
        with sub_c2:
            st.session_state.user_profile['m_amort'] = st.number_input("Remaining Amortization (Years)", value=int(st.session_state.user_profile.get('m_amort', 25)), on_change=sync_data)
            st.session_state.user_profile['prop_taxes'] = st.number_input("Annual Property Taxes ($)", value=float(st.session_state.user_profile.get('prop_taxes', 4200.0)), on_change=sync_data)
            st.session_state.user_profile['heat_pmt'] = st.number_input("Estimated Monthly Heating ($)", value=float(st.session_state.user_profile.get('heat_pmt', 125.0)), on_change=sync_data)

st.divider()

# --- SECTION 3: MONTHLY LIABILITIES ---
st.subheader("💳 Monthly Liabilities")
l1, l2, l3 = st.columns(3)
with l1:
    st.session_state.user_profile['car_loan'] = st.number_input("Car Loan Payments (Monthly)", value=float(st.session_state.user_profile.get('car_loan', 0.0)), on_change=sync_data)
    st.session_state.user_profile['student_loan'] = st.number_input("Student Loan Payments (Monthly)", value=float(st.session_state.user_profile.get('student_loan', 0.0)), on_change=sync_data)
with l2:
    st.session_state.user_profile['cc_pmt'] = st.number_input("Credit Card Payments (Monthly)", value=float(st.session_state.user_profile.get('cc_pmt', 0.0)), on_change=sync_data)
    st.session_state.user_profile['loc_balance'] = st.number_input("Total LOC Balance ($)", value=float(st.session_state.user_profile.get('loc_balance', 0.0)), on_change=sync_data)
with l3:
    prov_options = ["Ontario", "BC", "Alberta", "Quebec", "Manitoba", "Saskatchewan", "Nova Scotia", "NB", "PEI", "NL"]
    st.session_state.user_profile['province'] = st.selectbox("Province", prov_options, index=prov_options.index(st.session_state.user_profile.get('province', 'Ontario')), on_change=sync_data)

st.success("✅ Financial Passport updated and synchronized.")
