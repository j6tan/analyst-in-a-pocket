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

# --- 1. SESSION STATE SETUP ---
if 'current_link_token' not in st.session_state:
    st.session_state['current_link_token'] = None
if 'plaid_step' not in st.session_state:
    st.session_state['plaid_step'] = 'connect' 

# --- 2. INITIALIZE PLAID CLIENT ---
try:
    if "PLAID_CLIENT_ID" not in st.secrets or "PLAID_SECRET" not in st.secrets:
        st.error("❌ Missing Plaid Credentials in Streamlit Secrets!")
        st.stop()

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

# --- 3. THE HANDSHAKE LOGIC ---

def run_handshake():
    """The core logic that exchanges the public token for actual debt data."""
    token = st.session_state.get('current_link_token')
    try:
        # 1. Ask Plaid for the results of the session
        request = LinkTokenGetRequest(link_token=token)
        response = client.link_token_get(request)
        res = response.to_dict()
        
        # 2. Extract the Public Token (The Handshake)
        public_token = None
        if res.get('results', {}).get('item_add_results'):
            public_token = res['results']['item_add_results'][0].get('public_token')
        elif res.get('sessions'):
            for s in res['sessions']:
                if s.get('status') == 'success' and s.get('public_token'):
                    public_token = s['public_token']
                    break
        
        if not public_token:
            st.warning("⚠️ No successful login detected yet. Please finish the login in the other tab.")
            return

        # 3. Exchange for Access Token
        exchange = client.item_public_token_exchange(ItemPublicTokenExchangeRequest(public_token=public_token))
        access_token = exchange['access_token']

        # 4. Fetch Liabilities
        liab = client.liabilities_get(LiabilitiesGetRequest(access_token=access_token))
        debts = liab.to_dict().get('liabilities', {})
        
        # 5. Update Profile
        if debts.get('credit'):
            bal = sum(cc.get('last_statement_balance', 0) for cc in debts['credit'])
            st.session_state.user_profile['cc_pmt'] = round(bal * 0.03, 2)
        
        if debts.get('student'):
            pmt = sum(s.get('last_payment_amount', 0) for s in debts['student'])
            st.session_state.user_profile['student_loan'] = float(pmt)

        st.success("✅ Data Pulled! Your liabilities have been updated.")
        st.session_state['plaid_step'] = 'connect' # Reset for next time
        st.rerun()

    except Exception as e:
        st.error(f"Handshake Error: {e}")

@st.fragment
def plaid_interface():
    """Isolates the Plaid flow to prevent the main app from refreshing/breaking."""
    if st.session_state['plaid_step'] == 'connect':
        if st.button("🔗 Auto-Fill Liabilities (Connect Bank)", use_container_width=True):
            try:
                # Use UUID to ensure every session is unique and fresh
                request = LinkTokenCreateRequest(
                    user={'client_user_id': str(uuid.uuid4())},
                    client_name="Analyst in a Pocket",
                    products=[Products('liabilities')],
                    country_codes=[CountryCode('CA')],
                    language='en',
                    hosted_link={} 
                )
                response = client.link_token_create(request)
                st.session_state['current_link_token'] = response['link_token']
                st.session_state['link_url'] = response['hosted_link_url']
                st.session_state['plaid_step'] = 'sync_ready'
                st.rerun()
            except Exception as e:
                st.error(f"Link Error: {e}")

    else:
        st.info("🔓 Bank Login Session Ready")
        st.markdown(f'<a href="{st.session_state["link_url"]}" target="_blank" style="text-decoration: none;"><div style="background-color: #007bff; color: white; padding: 10px; text-align: center; border-radius: 5px; font-weight: bold;">Step 1: Click Here to Log In</div></a>', unsafe_allow_html=True)
        st.write("")
        if st.button("Step 2: Sync My Data 🔄", type="primary", use_container_width=True):
            run_handshake()
        
        if st.button("Cancel", use_container_width=True):
            st.session_state['plaid_step'] = 'connect'
            st.rerun()

# --- 4. CONFIG & NAVIGATION ---
# (Rest of your script remains UNTOUCHED)
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

# (Existing Navigation Logic...)
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

if selection == "👤 Client Profile":
    # (Original Headers and Income sections remain here)
    h1, h2 = st.columns([1, 5], vertical_alignment="center")
    with h1:
        if os.path.exists("logo.png"): st.image("logo.png", width=140)
    with h2:
        st.title("General Client Information")

    # ... [Keep Profile Management and Household Income sections exactly as they were] ...
    
    # --- UI PLACEMENT FOR NEW PLAID ZONE ---
    st.divider()
    st.subheader("💳 Monthly Liabilities")
    
    # This replaces the old p_col1/p_col2 blocks
    plaid_interface()

    # (Original Liability number inputs remain here)
    l1, l2, l3 = st.columns(3)
    # ... [Keep l1, l2, l3 logic] ...
