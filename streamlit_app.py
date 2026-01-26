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
    link_token = st.session_state.get('current_link_token')
    if not link_token:
        st.error("Session lost. Please click 'Connect Bank' again.")
        return

    try:
        get_request = LinkTokenGetRequest(link_token=link_token)
        get_response = client.link_token_get(get_request)
        
        # FIX 1: Accessing the results correctly using .to_dict()
        res = get_response.to_dict().get('results', {})
        item_results = res.get('item_add_results', [])
        
        if not item_results:
            st.error("No bank account was linked. Ensure you finish the Plaid login fully!")
            return

        public_token = item_results[0]['public_token']

        exchange_resp = client.item_public_token_exchange(
            ItemPublicTokenExchangeRequest(public_token=public_token)
        )
        access_token = exchange_resp['access_token']

        liabilities_resp = client.liabilities_get(
            LiabilitiesGetRequest(access_token=access_token)
        )
        liab_data = liabilities_resp.to_dict()
        
        # FIX 2: Correctly mapping the Sandbox data to your variables
        debts = liab_data.get('liabilities', {})
        
        # Credit Card Mapping
        credit = debts.get('credit', [])
        if credit:
            total_bal = sum(cc.get('last_statement_balance', 0) for cc in credit)
            st.session_state.user_profile['cc_pmt'] = round(total_bal * 0.03, 2)
            
        # Student Loan Mapping
        student = debts.get('student', [])
        if student:
            total_pmt = sum(s.get('last_payment_amount', 0) for s in student)
            st.session_state.user_profile['student_loan'] = float(total_pmt)

        st.success("✅ Data Synced!")
        st.rerun() # Forces the UI to show the new numbers
        
    except Exception as e:
        st.error(f"Sync Error: {e}")

# --- PLAID CLIENT SETUP ---
configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={'clientId': st.secrets["PLAID_CLIENT_ID"], 'secret': st.secrets["PLAID_SECRET"]}
)
api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

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

# --- YOUR ORIGINAL APP LOGIC BELOW ---
st.set_page_config(layout="wide", page_title="Analyst in a Pocket")

if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        "p1_name": "", "p1_t4": 0.0, "p1_bonus": 0.0, "p1_commission": 0.0, "p1_pension": 0.0,
        "p2_name": "", "p2_t4": 0.0, "p2_bonus": 0.0, "p2_commission": 0.0, "p2_pension": 0.0,
        "inv_rental_income": 0.0,
        "car_loan": 0.0, "student_loan": 0.0, "cc_pmt": 0.0, "loc_balance": 0.0,
        "housing_status": "Renting", "province": "Ontario", "rent_pmt": 0.0
    }

# (The rest of your original Profile UI goes here...)
st.title("General Client Information")

# Liabilities Section
st.divider()
st.subheader("💳 Monthly Liabilities")

if st.button("🔗 Connect Bank"):
    url = create_plaid_link()
    st.markdown(f"### [Click here to Login]({url})")

# THE PULL DATA BUTTON
if st.button("🔄 Pull Data from Bank"):
    sync_plaid_data()

# Your Input Boxes
l1, l2 = st.columns(2)
with l1:
    st.session_state.user_profile['car_loan'] = st.number_input("Car Loan", value=float(st.session_state.user_profile['car_loan']))
    st.session_state.user_profile['student_loan'] = st.number_input("Student Loan", value=float(st.session_state.user_profile['student_loan']))
with l2:
    st.session_state.user_profile['cc_pmt'] = st.number_input("CC Payments", value=float(st.session_state.user_profile['cc_pmt']))
