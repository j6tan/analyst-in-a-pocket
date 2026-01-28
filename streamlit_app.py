import streamlit as st
import json
import os
import uuid
import plaid
import time
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.link_token_get_request import LinkTokenGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.liabilities_get_request import LiabilitiesGetRequest

# --- 1. THE "MAILBOX" (Solves the Empty Page Issue) ---
# This creates a shared dictionary that persists across different tabs.
@st.cache_resource
def get_global_token_store():
    return {}

token_store = get_global_token_store()

# --- 2. SETUP & CONFIG ---
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

# --- 3. INITIALIZE PLAID ---
try:
    configuration = plaid.Configuration(
        host=plaid.Environment.Sandbox,
        api_key={
            'clientId': st.secrets["PLAID_CLIENT_ID"],
            'secret': st.secrets["PLAID_SECRET"],
        }
    )
    api_client = plaid.ApiClient(configuration)
    client = plaid_api.PlaidApi(api_client)
except Exception as e:
    st.error(f"Configuration Error: {e}")
    st.stop()

# --- 4. THE SMART PLAID INTERFACE ---
@st.fragment
def plaid_interface():
    # A. HANDLE THE RETURN TRIP (New Tab)
    params = st.query_params
    if "req_id" in params:
        req_id = params["req_id"]
        stored_token = token_store.get(req_id)
        
        if stored_token:
            with st.spinner("⏳ Finalizing secure connection..."):
                # We try 3 times to find the success session (sometimes Plaid is slow)
                public_token = None
                for _ in range(3):
                    try:
                        check_res = client.link_token_get(LinkTokenGetRequest(link_token=stored_token)).to_dict()
                        if check_res.get('link_sessions'):
                            for s in check_res['link_sessions']:
                                if s.get('status') == 'success':
                                    public_token = s.get('public_token')
                                    break
                        if public_token: break
                        time.sleep(1) # Wait for Plaid to update
                    except:
                        pass

                if public_token:
                    try:
                        exchange = client.item_public_token_exchange(ItemPublicTokenExchangeRequest(public_token=public_token))
                        liab = client.liabilities_get(LiabilitiesGetRequest(access_token=exchange['access_token']))
                        debts = liab.to_dict().get('liabilities', {})
                        
                        # UPDATE YOUR PROFILE DATA
                        if debts.get('credit'):
                            bal = sum(cc.get('last_statement_balance', 0) for cc in debts['credit'])
                            st.session_state.user_profile['cc_pmt'] = round(bal * 0.03, 2)
                        
                        if debts.get('student'):
                            pmt = sum(s.get('last_payment_amount', 0) for s in debts['student'])
                            st.session_state.user_profile['student_loan'] = float(pmt)

                        st.success("✅ Data Synced!")
                        del token_store[req_id]
                        st.query_params.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Sync Error: {e}")
                else:
                    st.error("Connection incomplete. Plaid hasn't confirmed the login yet. Please try one more time.")

    # B. THE BUTTON (Original Tab)
    else:
        if st.button("🔗 Connect Bank Account", use_container_width=True):
            try:
                req_id = str(uuid.uuid4())
                # CHANGE THIS to your actual streamlit URL
                base_url = "https://analyst-in-a-pocket.streamlit.app" 
                redirect_uri = f"{base_url}?req_id={req_id}"

                request = LinkTokenCreateRequest(
                    user={'client_user_id': str(uuid.uuid4())},
                    client_name="Analyst in a Pocket",
                    products=[Products('liabilities')],
                    country_codes=[CountryCode('CA')],
                    language='en',
                    hosted_link={'completion_redirect_uri': redirect_uri}
                )
                response = client.link_token_create(request)
                
                # Save to shared mailbox
                token_store[req_id] = response['link_token']
                
                # Show Link
                st.link_button("👉 Click to Open Bank Login", response['hosted_link_url'])
            except Exception as e:
                st.error(f"Plaid Init Error: {e}")

    # B. START BUTTON (Standard View)
    else:
        if st.button("🔗 Connect Bank (Auto-Fill)", use_container_width=True):
            try:
                # 1. Create a unique ID for this specific transaction
                # We will use this to retrieve the token later
                req_id = str(uuid.uuid4())
                
                # 2. Define where to come back to (THIS app + the unique ID)
                # IMPORTANT: If on Cloud, change 'localhost' to your actual app URL!
                # e.g., https://analyst-in-a-pocket.streamlit.app
                base_url = "https://analyst-in-a-pocket.streamlit.app" 
                # base_url = "http://localhost:8501" # Uncomment for local testing
                
                redirect_uri = f"{base_url}?req_id={req_id}"

                # 3. Create the Link Token
                request = LinkTokenCreateRequest(
                    user={'client_user_id': str(uuid.uuid4())},
                    client_name="Analyst in a Pocket",
                    products=[Products('liabilities')],
                    country_codes=[CountryCode('CA')],
                    language='en',
                    hosted_link={'completion_redirect_uri': redirect_uri}
                )
                response = client.link_token_create(request)
                
                # 4. Put the token in the "Mailbox" so the new tab can find it
                token_store[req_id] = response['link_token']
                
                # 5. Send user to Plaid
                st.link_button("👉 Click to Log In at Bank", response['hosted_link_url'])
                
            except Exception as e:
                st.error(f"Plaid Error: {e}")

# --- 5. APP NAVIGATION & UI ---
tools = {
    "👤 Client Profile": "MAIN",
    "📊 Affordability Primary": "affordability.py",
    # ... add your other pages here ...
}
selection = st.sidebar.radio("Go to", list(tools.keys()))

if selection == "👤 Client Profile":
    st.title("General Client Information")
    
    # ... Your Input Fields (Names, T4, etc.) ...
    
    st.divider()
    st.subheader("💳 Monthly Liabilities")
    
    # RUN THE INTERFACE
    plaid_interface()

    l1, l2, l3 = st.columns(3)
    with l1:
        st.number_input("Car Loan Payments", key="car_loan", value=float(st.session_state.user_profile['car_loan']))
        st.number_input("Student Loan Payments", key="student_loan", value=float(st.session_state.user_profile['student_loan']))
    with l2:
        # These will update automatically after Plaid sync!
        st.number_input("Credit Card Payments", key="cc_pmt", value=float(st.session_state.user_profile['cc_pmt']))
        st.number_input("LOC Balance", key="loc_balance", value=float(st.session_state.user_profile['loc_balance']))
    with l3:
        st.selectbox("Province", ["Ontario", "BC", "Alberta"], key="province")

else:
    # Logic for other pages
    pass

