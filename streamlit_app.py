import streamlit as st
import json
import os
import uuid 
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.link_token_get_request import LinkTokenGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.liabilities_get_request import LiabilitiesGetRequest

# --- 1. SESSION STATE & DEBUG SETUP ---
if 'current_link_token' not in st.session_state:
    st.session_state['current_link_token'] = None
if 'plaid_step' not in st.session_state:
    st.session_state['plaid_step'] = 'connect'
if 'unique_user_id' not in st.session_state:
    st.session_state['unique_user_id'] = str(uuid.uuid4())

# --- 2. INITIALIZE PLAID CLIENT ---
configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': st.secrets["PLAID_CLIENT_ID"],
        'secret': st.secrets["PLAID_SECRET"],
    }
)
api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

# --- 3. HELPER FUNCTIONS ---
def generate_new_link():
    """Generates a fresh Link Token and redirects user."""
    try:
        user_id = st.session_state['unique_user_id']
        
        # Determine the redirect URI (Local or Public)
        # Sandbox allows http://localhost:8501, but Production/Dev requires HTTPS
        redirect_uri = "http://localhost:8501" 
        
        request = LinkTokenCreateRequest(
            user={'client_user_id': user_id},
            client_name="Analyst in a Pocket",
            products=[Products('liabilities')],
            country_codes=[CountryCode('CA')],
            language='en',
            redirect_uri=redirect_uri, # <--- CRITICAL FOR MULTI-USER/OAUTH
            hosted_link={
                "completion_redirect_uri": redirect_uri # <--- AUTOMATIC RETURN
            } 
        )
        response = client.link_token_create(request)
        
        st.session_state['current_link_token'] = response['link_token']
        st.session_state['link_url'] = response['hosted_link_url']
        st.session_state['plaid_step'] = 'link_ready'
        st.rerun()
        
    except Exception as e:
        st.error(f"Error creating link: {e}")

def sync_plaid_data():
    """Exchanges tokens and pulls liability data into the user profile."""
    token = st.session_state.get('current_link_token')
    
    if not token:
        st.error("Session expired or token missing. Please try again.")
        st.session_state['plaid_step'] = 'connect'
        return

    try:
        # Retrieve the public_token from the completed session
        request = LinkTokenGetRequest(link_token=token)
        response = client.link_token_get(request)
        res = response.to_dict()

        public_token = None
        # Check primary results
        if res.get('results', {}).get('item_add_results'):
            public_token = res['results']['item_add_results'][0].get('public_token')
        # Check sessions backup
        elif res.get('sessions'):
            for s in res['sessions']:
                if s.get('status') == 'success' and s.get('public_token'):
                    public_token = s['public_token']
                    break

        if not public_token:
            st.warning("Plaid hasn't finished the connection yet. Please wait 5 seconds and try again.")
            return

        # Exchange Public -> Access Token
        exchange = client.item_public_token_exchange(
            ItemPublicTokenExchangeRequest(public_token=public_token)
        )
        access_token = exchange['access_token']

        # Fetch Liabilities (Debts)
        liab = client.liabilities_get(LiabilitiesGetRequest(access_token=access_token))
        debts = liab.to_dict().get('liabilities', {})
        
        # Automate data mapping to Client Profile
        if debts.get('credit'):
            # Estimate 3% min payment on total CC balance
            total_bal = sum(cc.get('last_statement_balance', 0) for cc in debts['credit'])
            st.session_state.user_profile['cc_pmt'] = round(total_bal * 0.03, 2)
        
        if debts.get('student'):
            total_pmt = sum(s.get('last_payment_amount', 0) for s in debts['student'])
            st.session_state.user_profile['student_loan'] = float(total_pmt)

        st.success("✅ Bank Data Integrated Successfully!")
        st.session_state['plaid_step'] = 'connect' 
        st.rerun()

    except Exception as e:
        st.error(f"Technical Sync Error: {e}")

# ... (Navigation and UI logic remains unchanged)

# --- UPDATED PLAID UI SECTION ---
st.divider()
st.subheader("💳 Monthly Liabilities")

p_col1, p_col2 = st.columns(2)

with p_col1:
    if st.session_state['plaid_step'] == 'connect':
        st.write("Link your bank to pull liabilities automatically.")
        if st.button("🔗 Connect Bank Account"):
            generate_new_link()
    
    elif st.session_state['plaid_step'] == 'link_ready':
        url = st.session_state.get('link_url', '#')
        st.info("Plaid link is active.")
        st.markdown(f'<a href="{url}" target="_self" style="text-decoration:none;"><div style="background-color:#007bff;color:white;padding:10px;text-align:center;border-radius:5px;">👉 Log into Bank</div></a>', unsafe_allow_html=True)
        
        if st.button("Cancel Connection"):
            st.session_state['plaid_step'] = 'connect'
            st.rerun()

with p_col2:
    if st.session_state['plaid_step'] == 'link_ready':
        st.write("Step 2: After bank login is finished...")
        if st.button("🔄 Import Bank Data"):
            with st.spinner("Talking to Plaid..."):
                sync_plaid_data()
