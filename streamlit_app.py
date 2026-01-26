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

# --- 2. FUNCTIONS ---

def sync_plaid_data():
    link_token = st.session_state.get('current_link_token')
    if not link_token:
        st.error("Session lost. Please click 'Auto-Sync' again.")
        return

    try:
        # Get session results
        get_request = LinkTokenGetRequest(link_token=link_token)
        get_response = client.link_token_get(get_request)
        
        # FIX: Correct way to access public_token in Hosted Link
        # We access the 'results' attribute of the response object
        results = get_response.to_dict().get('results', {})
        item_add_results = results.get('item_add_results', [])
        
        if not item_add_results:
            st.warning("No bank account was linked yet. Please finish the Plaid process.")
            return
            
        public_token = item_add_results[0]['public_token']

        # Exchange for Access Token
        exchange_resp = client.item_public_token_exchange(
            ItemPublicTokenExchangeRequest(public_token=public_token)
        )
        access_token = exchange_resp['access_token']

        # Fetch Liabilities
        liabilities_resp = client.liabilities_get(
            LiabilitiesGetRequest(access_token=access_token)
        )
        data = liabilities_resp.to_dict()
        
        # MAPPING: Sandbox 'user_good' math
        liabilities = data.get('liabilities', {})
        
        # Credit Cards
        credit_accounts = liabilities.get('credit', [])
        if credit_accounts:
            total_cc_min = sum(acc.get('last_statement_balance', 0) for acc in credit_accounts)
            st.session_state.user_profile['cc_pmt'] = round(total_cc_min * 0.03, 2)
        
        # Student Loans (Common in Sandbox)
        student_loans = liabilities.get('student', [])
        if student_loans:
            total_student = sum(s.get('last_payment_amount', 0) for s in student_loans)
            st.session_state.user_profile['student_loan'] = float(total_student)

        st.success("✅ Data Synced!")
        
    except Exception as e:
        st.error(f"Sync Error: {e}")

def create_plaid_link():
    plaid_request = LinkTokenCreateRequest(
        user={'client_user_id': 'user_123'},
        client_name="Analyst in a Pocket",
        products=[Products('liabilities')],
        country_codes=[CountryCode('CA')],
        language='en',
        hosted_link={} 
    )
    response = client.link_token_create(plaid_request)
    st.session_state['current_link_token'] = response['link_token']
    return response['hosted_link_url']

# --- 3. PAGE CONFIG & SESSION STATE ---
st.set_page_config(layout="wide", page_title="Analyst in a Pocket", page_icon="📊")

if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        "p1_name": "", "p2_name": "",
        "p1_t4": 0.0, "p1_bonus": 0.0, "p1_commission": 0.0, "p1_pension": 0.0,
        "p2_t4": 0.0, "p2_bonus": 0.0, "p2_commission": 0.0, "p2_pension": 0.0,
        "inv_rental_income": 0.0,
        "car_loan": 0.0, "student_loan": 0.0, "cc_pmt": 0.0, "loc_pmt": 0.0, "loc_balance": 0.0,
        "housing_status": "Renting", "province": "Ontario",
        "m_bal": 0.0, "m_rate": 0.0, "m_amort": 25, "prop_taxes": 4200.0, "rent_pmt": 0.0,
        "heat_pmt": 125.0
    }

# --- 4. NAVIGATION ---
tools = {
    "👤 Client Profile": "MAIN",
    "📊 Affordability Primary": "affordability.py",
    # ... (other tools)
}
selection = st.sidebar.radio("Go to", list(tools.keys()))

# --- 5. UI LOGIC ---
if selection == "👤 Client Profile":
    st.title("General Client Information")

    # (Income sections same as before...)
    
    st.divider()
    st.subheader("💳 Monthly Liabilities")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔗 1. Connect Bank"):
            url = create_plaid_link()
            st.markdown(f"[Click here to login]({url})")
            
    with col_btn2:
        # Use on_click for immediate refresh
        st.button("🔄 2. Pull Data", on_click=sync_plaid_data)

    l1, l2, l3 = st.columns(3)
    with l1:
        st.session_state.user_profile['car_loan'] = st.number_input("Car Loan Payments", value=float(st.session_state.user_profile['car_loan']))
        st.session_state.user_profile['student_loan'] = st.number_input("Student Loan Payments", value=float(st.session_state.user_profile['student_loan']))
    with l2:
        st.session_state.user_profile['cc_pmt'] = st.number_input("Credit Card Payments", value=float(st.session_state.user_profile['cc_pmt']))
    
    # Download button at the bottom of the profile page
    profile_json = json.dumps(st.session_state.user_profile, indent=4)
    st.download_button("💾 Download Profile", data=profile_json, file_name="client_profile.json")

else:
    # Run sub-scripts
    file_path = os.path.join("scripts", tools[selection])
    if os.path.exists(file_path):
        exec(open(file_path, encoding="utf-8").read(), globals())
