import streamlit as st
import json
import os
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.link_token_get_request import LinkTokenGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.liabilities_get_request import LiabilitiesGetRequest

def sync_plaid_data():
    if 'current_link_token' not in st.session_state:
        st.error("No active session found. Please click the connect button first.")
        return

    try:
        # 1. Get the session status to find the 'public_token'
        get_request = LinkTokenGetRequest(link_token=st.session_state['current_link_token'])
        get_response = client.link_token_get(get_request)
        public_token = get_response['sessions'][0]['public_token']

        # 2. Exchange for access_token and fetch debt
        exchange_resp = client.item_public_token_exchange(ItemPublicTokenExchangeRequest(public_token=public_token))
        liabilities_resp = client.liabilities_get(LiabilitiesGetRequest(access_token=exchange_resp['access_token']))

        # 3. AUTO-MAPPING: Link Plaid data to your specific UI boxes
        # Plaid Sandbox 'user_good' usually has a student loan and a credit card
        liabilities = liabilities_resp['liabilities']
        
        # Mapping Credit Card Minimum Payments
        if liabilities.get('credit'):
            total_cc = sum(cc.get('last_payment_amount', 0) for cc in liabilities['credit'])
            st.session_state.user_profile['cc_pmt'] = float(total_cc)

        # Mapping Student/Car Loans
        if liabilities.get('student'):
            total_student = sum(s.get('last_payment_amount', 0) for s in liabilities['student'])
            st.session_state.user_profile['student_loan'] = float(total_student)

        st.success("✅ Bank Data Synced Successfully!")
        st.rerun() # Refresh the UI to show the new numbers in the boxes
    except Exception as e:
        st.error(f"Sync failed: {e}")

# --- 1. INITIALIZE PLAID CLIENT ---
configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': st.secrets["PLAID_CLIENT_ID"],
        'secret': st.secrets["PLAID_SECRET"],
    }
)
api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

def create_plaid_link():
    # 1. You MUST define 'request' here first!
    plaid_request = LinkTokenCreateRequest(
        user={'client_user_id': st.session_state.get('user_id', 'user_123')},
        client_name="Analyst in a Pocket",
        products=[Products('liabilities')],
        country_codes=[CountryCode('CA')],
        language='en',
        hosted_link={} 
    )
    
    # 2. Now 'request' is defined and can be passed to the client
    response = client.link_token_create(plaid_request)
    
    st.session_state['current_link_token'] = response['link_token']
    return response['hosted_link_url']

# --- 1. GLOBAL CONFIG ---
st.set_page_config(layout="wide", page_title="Analyst in a Pocket", page_icon="📊")

# --- 2. INITIALIZE GLOBAL VAULT ---
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        "p1_name": "", "p2_name": "",
        "p1_t4": 0.0, "p1_bonus": 0.0, "p1_commission": 0.0, "p1_pension": 0.0,
        "p2_t4": 0.0, "p2_bonus": 0.0, "p2_commission": 0.0, "p2_pension": 0.0,
        "inv_rental_income": 0.0,
        "car_loan": 0.0, "student_loan": 0.0, "cc_pmt": 0.0, "loc_pmt": 0.0, "loc_balance": 0.0,
        "housing_status": "Renting", "province": "Ontario",
        "m_bal": 0.0, "m_rate": 0.0, "m_amort": 25, "prop_taxes": 4200.0, "rent_pmt": 0.0,
        "heat_pmt": 125.0 # Added for more accurate TDS calculations
    }

# --- 3. NAVIGATION ---
# Added "🏢 Investment Qual" to the tools dictionary
tools = {
    "👤 Client Profile": "MAIN",
    "📊 Affordability Primary": "affordability.py",
    "🏢 Affordability Secondary": "affordability_second.py", 
    "🛡️ Smith Maneuver": "smith_maneuver.py",
    "📉 Mortgage Scenarios": "mortgage_scenario.py",
    "🔄 Renewal Dilemma": "renewal_analysis.py",
    "⚖️ Buy vs Rent": "buy_vs_rent.py",
    "⚖️ Rental vs Stock": "rental_vs_stock.py",
}
selection = st.sidebar.radio("Go to", list(tools.keys()))

# --- 4. PROFILE PAGE ---
if selection == "👤 Client Profile":
    header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
    with header_col1:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=140)
    with header_col2:
        st.title("General Client Information")

    st.subheader("💾 Profile Management")
    up_col1, up_col2 = st.columns(2)
    with up_col1:
        uploaded_file = st.file_uploader("Upload Existing Profile (JSON)", type=["json"])
        if uploaded_file is not None:
            st.session_state.user_profile.update(json.load(uploaded_file))
            st.success("Profile Loaded!")

    st.subheader("👥 Household Income Details")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Primary Client")
        st.session_state.user_profile['p1_name'] = st.text_input("Full Name", value=st.session_state.user_profile['p1_name'])
        st.session_state.user_profile['p1_t4'] = st.number_input("T4 (Employment Income)", value=float(st.session_state.user_profile['p1_t4']))
        st.session_state.user_profile['p1_bonus'] = st.number_input("Bonuses / Performance Pay", value=float(st.session_state.user_profile['p1_bonus']))
        st.session_state.user_profile['p1_commission'] = st.number_input("Commissions", value=float(st.session_state.user_profile['p1_commission']))
        st.session_state.user_profile['p1_pension'] = st.number_input("Pension / CPP / OAS", value=float(st.session_state.user_profile['p1_pension']))
    
    with c2:
        st.markdown("### Co-Owner / Partner")
        st.session_state.user_profile['p2_name'] = st.text_input("Full Name ", value=st.session_state.user_profile['p2_name'])
        st.session_state.user_profile['p2_t4'] = st.number_input("T4 (Employment Income) ", value=float(st.session_state.user_profile['p2_t4']))
        st.session_state.user_profile['p2_bonus'] = st.number_input("Bonuses / Performance Pay ", value=float(st.session_state.user_profile['p2_bonus']))
        st.session_state.user_profile['p2_commission'] = st.number_input("Commissions ", value=float(st.session_state.user_profile['p2_commission']))
        st.session_state.user_profile['p2_pension'] = st.number_input("Pension / CPP / OAS ", value=float(st.session_state.user_profile['p2_pension']))

    st.session_state.user_profile['inv_rental_income'] = st.number_input("Joint Rental Income (Current Portfolio)", value=float(st.session_state.user_profile['inv_rental_income']))

    st.divider()
    st.subheader("🏠 Housing & Property Details")
    h_toggle, h_data = st.columns([1, 2])
    with h_toggle:
        st.session_state.user_profile['housing_status'] = st.radio("Current Status", ["Renting", "Owning"], index=0 if st.session_state.user_profile['housing_status'] == "Renting" else 1)
    with h_data:
        if st.session_state.user_profile['housing_status'] == "Renting":
            st.session_state.user_profile['rent_pmt'] = st.number_input("Monthly Rent ($)", value=float(st.session_state.user_profile.get('rent_pmt', 0.0)))
        else:
            sub_c1, sub_c2 = st.columns(2)
            with sub_c1:
                st.session_state.user_profile['m_bal'] = st.number_input("Current Mortgage Balance ($)", value=float(st.session_state.user_profile.get('m_bal', 0.0)))
                st.session_state.user_profile['m_rate'] = st.number_input("Current Interest Rate (%)", value=float(st.session_state.user_profile.get('m_rate', 0.0)))
            with sub_c2:
                st.session_state.user_profile['m_amort'] = st.number_input("Remaining Amortization (Years)", value=int(st.session_state.user_profile.get('m_amort', 25)))
                st.session_state.user_profile['prop_taxes'] = st.number_input("Annual Property Taxes ($)", value=float(st.session_state.user_profile.get('prop_taxes', 4200.0)))
                # Added heating input for primary residence to feed Investment Tool
                st.session_state.user_profile['heat_pmt'] = st.number_input("Estimated Monthly Heating ($)", value=float(st.session_state.user_profile.get('heat_pmt', 125.0)))

    st.divider()
    st.subheader("💳 Monthly Liabilities")
    # --- PLAID INTEGRATION BUTTON ---
if st.button("🔗 Auto-Sync Liabilities via Bank"):
    try:
        link_url = create_plaid_link()
        st.success("Link Generated!")
        st.markdown(f"### [Click here to Securely Connect Bank]({link_url})")
        st.info("After connecting, Plaid will provide your debt data automatically.")
    except Exception as e:
        st.error(f"Plaid Error: {e}")

    l1, l2, l3 = st.columns(3)
    with l1:
        st.session_state.user_profile['car_loan'] = st.number_input("Car Loan Payments (Monthly)", value=float(st.session_state.user_profile['car_loan']))
        st.session_state.user_profile['student_loan'] = st.number_input("Student Loan Payments (Monthly)", value=float(st.session_state.user_profile['student_loan']))
    with l2:
        st.session_state.user_profile['cc_pmt'] = st.number_input("Credit Card Payments (Monthly)", value=float(st.session_state.user_profile['cc_pmt']))
        st.session_state.user_profile['loc_balance'] = st.number_input("Total LOC Balance ($)", value=float(st.session_state.user_profile['loc_balance']))
    with l3:
        prov_options = ["Ontario", "BC", "Alberta", "Quebec", "Manitoba", "Saskatchewan", "Nova Scotia", "NB", "PEI", "NL"]
        st.session_state.user_profile['province'] = st.selectbox("Province", prov_options, index=prov_options.index(st.session_state.user_profile.get('province', 'Ontario')))

    profile_json = json.dumps(st.session_state.user_profile, indent=4)
    st.download_button("💾 Download Profile", data=profile_json, file_name="client_profile.json", mime="application/json")

else:
    file_path = os.path.join("scripts", tools[selection])
    if os.path.exists(file_path):

        exec(open(file_path, encoding="utf-8").read(), globals())

if st.button("🔄 Pull Data from Bank"):
    sync_plaid_data()
    st.rerun() # Refresh the page to show the new numbers






