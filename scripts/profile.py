import streamlit as st
from style_utils import inject_global_css
from data_handler import update_data

# 1. Inject Styles
inject_global_css()

# 2. Back Button
if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 3. DATA CONNECTION ---
# Connect to the 'profile' bucket in the Master Database
prof = st.session_state.app_db['profile']

# Helper function to save changes securely
def update_profile(key):
    # Sends data to data_handler (RAM for Guest, Cloud for Paid)
    # It looks for st.session_state["w_" + key]
    update_data('profile', key, st.session_state[f"w_{key}"])

st.title("👤 Client Profile & Financials")
st.info("Changes are saved automatically.")

# --- SECTION 1: PERSONAL & LOCATION ---
st.subheader("📍 Personal Details")
c1, c2 = st.columns(2)

with c1:
    st.text_input("Full Name", value=prof.get('p1_name', ""), key="w_p1_name", on_change=update_profile, args=("p1_name",))
    
    # PROVINCE SELECTOR (Fixed Index Lookup)
    prov_options = ["Ontario", "British Columbia", "Alberta", "Quebec", "Nova Scotia", "Manitoba", "Saskatchewan", "New Brunswick", "PEI", "Newfoundland"]
    curr_prov = prof.get('province', "Ontario")
    try:
        prov_index = prov_options.index(curr_prov)
    except ValueError:
        prov_index = 0
        
    st.selectbox("Province of Residence", options=prov_options, index=prov_index, key="w_province", on_change=update_profile, args=("province",))

with c2:
    st.text_input("Partner Name (Optional)", value=prof.get('p2_name', ""), key="w_p2_name", on_change=update_profile, args=("p2_name",))

st.divider()

# --- SECTION 2: INCOME SOURCES ---
st.subheader("💰 Annual Income Sources")
st.markdown("Please enter gross annual amounts (before tax).")

i1, i2 = st.columns(2)

with i1:
    st.markdown("#### Primary Client")
    st.number_input("T4 Employment Income", value=float(prof.get('p1_t4', 0.0)), step=1000.0, key="w_p1_t4", on_change=update_profile, args=("p1_t4",))
    st.number_input("Bonuses / Performance Pay", value=float(prof.get('p1_bonus', 0.0)), step=500.0, key="w_p1_bonus", on_change=update_profile, args=("p1_bonus",))
    st.number_input("Commission Income", value=float(prof.get('p1_commission', 0.0)), step=500.0, key="w_p1_commission", on_change=update_profile, args=("p1_commission",))
    st.number_input("Pension Income", value=float(prof.get('p1_pension', 0.0)), step=500.0, key="w_p1_pension", on_change=update_profile, args=("p1_pension",))

with i2:
    st.markdown("#### Partner / Joint")
    st.number_input("Partner T4 Income", value=float(prof.get('p2_t4', 0.0)), step=1000.0, key="w_p2_t4", on_change=update_profile, args=("p2_t4",))
    st.number_input("Partner Bonus/Commission", value=float(prof.get('p2_bonus', 0.0)), step=500.0, key="w_p2_bonus", on_change=update_profile, args=("p2_bonus",))
    st.number_input("Net Rental Income (Joint)", value=float(prof.get('rental_income', 0.0)), step=500.0, help="Net income after expenses but before tax.", key="w_rental_income", on_change=update_profile, args=("rental_income",))
    st.number_input("Other Household Income", value=float(prof.get('other_income', 0.0)), step=500.0, key="w_other_income", on_change=update_profile, args=("other_income",))

st.divider()

# --- SECTION 3: CURRENT HOUSING SITUATION ---
st.subheader("🏠 Current Housing Situation")

# FIX: We renamed the key to 'w_housing_status' so it matches the args=("housing_status",)
housing_mode = st.radio(
    "Do you currently Rent or Own?", 
    ["Rent", "Own"], 
    index=0 if prof.get('housing_status', 'Rent') == 'Rent' else 1, 
    key="w_housing_status", 
    on_change=update_profile, 
    args=("housing_status",)
)

h1, h2 = st.columns(2)

if housing_mode == "Rent":
    with h1:
        st.number_input("Current Monthly Rent ($)", value=float(prof.get('current_rent', 2000.0)), step=50.0, key="w_current_rent", on_change=update_profile, args=("current_rent",))
else:
    with h1:
        st.number_input("Current Mortgage Payment (Monthly)", value=float(prof.get('current_mortgage', 0.0)), step=50.0, key="w_current_mortgage", on_change=update_profile, args=("current_mortgage",))
        st.number_input("Property Taxes (Annual)", value=float(prof.get('prop_taxes', 4000.0)), step=100.0, key="w_prop_taxes", on_change=update_profile, args=("prop_taxes",))
    with h2:
        st.number_input("Condo Fees (Monthly)", value=float(prof.get('condo_fees', 0.0)), step=10.0, key="w_condo_fees", on_change=update_profile, args=("condo_fees",))
        st.number_input("Heating Costs (Monthly)", value=float(prof.get('heat_cost', 125.0)), step=10.0, key="w_heat_cost", on_change=update_profile, args=("heat_cost",))

st.divider()

# --- SECTION 4: DEBTS & LIABILITIES ---
st.subheader("💳 Monthly Liabilities")
st.markdown("Debts impacting your borrowing power (TDS Ratio).")

l1, l2, l3 = st.columns(3)
with l1:
    st.number_input("Car Loan Payments ($)", value=float(prof.get('car_loan', 0.0)), step=10.0, key="w_car_loan", on_change=update_profile, args=("car_loan",))
    st.number_input("Student Loan Payments ($)", value=float(prof.get('student_loan', 0.0)), step=10.0, key="w_student_loan", on_change=update_profile, args=("student_loan",))
with l2:
    st.number_input("Credit Card Payments ($)", value=float(prof.get('cc_pmt', 0.0)), step=10.0, help="Minimum monthly payment required.", key="w_cc_pmt", on_change=update_profile, args=("cc_pmt",))
    st.number_input("Total LOC Balance ($)", value=float(prof.get('loc_balance', 0.0)), step=100.0, help="Total outstanding balance.", key="w_loc_balance", on_change=update_profile, args=("loc_balance",))
with l3:
    st.number_input("Spousal/Child Support ($)", value=float(prof.get('support_pmt', 0.0)), step=10.0, key="w_support_pmt", on_change=update_profile, args=("support_pmt",))
    st.number_input("Other Monthly Debts ($)", value=float(prof.get('other_debt', 0.0)), step=10.0, key="w_other_debt", on_change=update_profile, args=("other_debt",))
