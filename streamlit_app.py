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

# --- 1. SESSION STATE SETUP ---
if 'current_link_token' not in st.session_state:
    st.session_state['current_link_token'] = None
if 'plaid_step' not in st.session_state:
    st.session_state['plaid_step'] = 'connect'  # Options: 'connect', 'link_ready'

# --- 2. INITIALIZE PLAID CLIENT (ROBUST VERSION) ---
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

# --- 3. HELPER FUNCTIONS ---
def generate_new_link():
    """Generates a fresh Link Token and locks the UI to this token."""
    try:
        request = LinkTokenCreateRequest(
            user={'client_user_id': 'user_123'},
            client_name="Analyst in a Pocket",
            products=[Products('liabilities')],
            country_codes=[CountryCode('CA')],
            language='en',
            hosted_link={} 
        )
        response = client.link_token_create(request)
        
        st.session_state['current_link_token'] = response['link_token']
        st.session_state['link_url'] = response['hosted_link_url']
        st.session_state['plaid_step'] = 'link_ready'
        st.rerun()
    except Exception as e:
        st.error(f"Error creating link: {e}")

def reset_plaid_flow():
    """Resets the flow so user can try again."""
    st.session_state['current_link_token'] = None
    st.session_state['plaid_step'] = 'connect'
    st.rerun()

def sync_plaid_data():
    token = st.session_state.get('current_link_token')
    if not token:
        st.error("No token found. Please start over.")
        reset_plaid_flow()
        return

    try:
        # Get Session Details from Plaid
        request = LinkTokenGetRequest(link_token=token)
        response = client.link_token_get(request)
        res = response.to_dict()

        # --- THE HANDSHAKE FIX ---
        # We need to extract the public_token from the session results
        public_token = None
        
        # Check primary results path
        if res.get('results', {}).get('item_add_results'):
            public_token = res['results']['item_add_results'][0].get('public_token')
        
        # Fallback: check session history (sometimes needed in Sandbox)
        if not public_token and res.get('sessions'):
            for s in res['sessions']:
                if s.get('status') == 'success' and s.get('public_token'):
                    public_token = s['public_token']
                    break

        if not public_token:
            last_status = res['sessions'][-1].get('status', 'No Activity') if res.get('sessions') else "No Activity"
            st.warning(f"Connection incomplete. Last Status: '{last_status}'.")
            return

        # Exchange public token for access token
        exchange = client.item_public_token_exchange(
            ItemPublicTokenExchangeRequest(public_token=public_token)
        )
        access_token = exchange['access_token']

        # Fetch the data
        liab = client.liabilities_get(LiabilitiesGetRequest(access_token=access_token))
        debts = liab.to_dict().get('liabilities', {})
        
        if debts.get('credit'):
            bal = sum(cc.get('last_statement_balance', 0) for cc in debts['credit'])
            st.session_state.user_profile['cc_pmt'] = round(bal * 0.03, 2)
        
        if debts.get('student'):
            pmt = sum(s.get('last_payment_amount', 0) for s in debts['student'])
            st.session_state.user_profile['student_loan'] = float(pmt)

        st.success("✅ Bank Data Pulled Successfully!")
        st.session_state['plaid_step'] = 'connect'
        st.rerun()

    except Exception as e:
        st.error(f"Sync Error: {e}")

# --- 4. CONFIG & GLOBAL VARS ---
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

# --- 5. NAVIGATION ---
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

# --- 6. PAGE UI ---
if selection == "👤 Client Profile":
    h1, h2 = st.columns([1, 5], vertical_alignment="center")
    with h1:
        if os.path.exists("logo.png"): st.image("logo.png", width=140)
    with h2:
        st.title("General Client Information")

    st.subheader("💾 Profile
