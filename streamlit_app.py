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
    # CHECKPOINT 1: Session Memory
    token = st.session_state.get('current_link_token')
    if not token:
        st.error("❌ Checkpoint 1 Failed: The app has forgotten the link token (Session State cleared).")
        return
    st.info(f"📡 Checkpoint 1: Token found in memory (...{token[-10:]})")

    try:
        # Request session status from Plaid
        request = LinkTokenGetRequest(link_token=token)
        response = client.link_token_get(request)
        res = response.to_dict()

        # CHECKPOINT 2: Plaid Activity
        sessions = res.get('sessions', [])
        if not sessions:
            st.error("❌ Checkpoint 2 Failed: Plaid says you never even opened the link. Did you click it?")
            return
        st.info(f"📡 Checkpoint 2: Plaid detected {len(sessions)} session(s).")

        # CHECKPOINT 3: Completion Status
        last_status = sessions[-1].get('status', 'unknown')
        if last_status != 'success':
            st.warning(f"❌ Checkpoint 3 Failed: Bank login started, but status is '{last_status}'. You must reach the final 'Success' screen.")
            return
        st.info("📡 Checkpoint 3: Plaid confirms 'Success' status achieved!")

        # CHECKPOINT 4: Handshake Token Extraction
        public_token = None
        if res.get('results', {}).get('item_add_results'):
            public_token = res['results']['item_add_results'][0].get('public_token')
        
        if not public_token:
            # Try finding it in session history if results is empty
            for s in sessions:
                if s.get('status') == 'success' and s.get('public_token'):
                    public_token = s['public_token']
                    break
        
        if not public_token:
            st.error("❌ Checkpoint 4 Failed: Login was successful, but Plaid did not provide a Public Token. This is an API sync delay.")
            return
        st.success("📡 Checkpoint 4: Handshake key (Public Token) captured!")

        # FINAL STEP: Exchange and Pull
        exchange = client.item_public_token_exchange(
            ItemPublicTokenExchangeRequest(public_token=public_token)
        )
        access_token = exchange['access_token']
        st.info("📡 Final Step: Access Token received. Fetching debts...")

        liab = client.liabilities_get(LiabilitiesGetRequest(access_token=access_token))
        debts = liab.to_dict().get('liabilities', {})
        
        # (Your existing data update logic here...)
        st.success("🎉 ALL SYSTEMS GO: Bank Data Pulled!")

    except Exception as e:
        st.error(f"⚠️ System Error during handshake: {str(e)}")

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

    st.subheader("💾 Profile Management")
    u1, u2 = st.columns(2)
    with u1:
        uf = st.file_uploader("Upload Existing Profile", type=["json"])
        if uf:
            st.session_state.user_profile.update(json.load(uf))
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
    h1, h2 = st.columns([1, 2])
    with h1:
        st.session_state.user_profile['housing_status'] = st.radio("Current Status", ["Renting", "Owning"], index=0 if st.session_state.user_profile['housing_status'] == "Renting" else 1)
    with h2:
        if st.session_state.user_profile['housing_status'] == "Renting":
            st.session_state.user_profile['rent_pmt'] = st.number_input("Monthly Rent ($)", value=float(st.session_state.user_profile.get('rent_pmt', 0.0)))
        else:
            s1, s2 = st.columns(2)
            with s1:
                st.session_state.user_profile['m_bal'] = st.number_input("Current Mortgage Balance ($)", value=float(st.session_state.user_profile.get('m_bal', 0.0)))
                st.session_state.user_profile['m_rate'] = st.number_input("Current Interest Rate (%)", value=float(st.session_state.user_profile.get('m_rate', 0.0)))
            with s2:
                st.session_state.user_profile['m_amort'] = st.number_input("Remaining Amortization (Years)", value=int(st.session_state.user_profile.get('m_amort', 25)))
                st.session_state.user_profile['prop_taxes'] = st.number_input("Annual Property Taxes ($)", value=float(st.session_state.user_profile.get('prop_taxes', 4200.0)))
                st.session_state.user_profile['heat_pmt'] = st.number_input("Estimated Monthly Heating ($)", value=float(st.session_state.user_profile.get('heat_pmt', 125.0)))

    st.divider()
    st.subheader("💳 Monthly Liabilities")

    p_col1, p_col2 = st.columns(2)
    
    with p_col1:
        if st.session_state['plaid_step'] == 'connect':
            if st.button("🔗 1. Connect Bank"):
                generate_new_link()
        elif st.session_state['plaid_step'] == 'link_ready':
            url = st.session_state.get('link_url', '#')
            st.success("Session Created!")
            st.markdown(f"👉 **[CLICK HERE TO LOGIN]({url})**")
            if st.button("Cancel / Start Over"):
                reset_plaid_flow()

    with p_col2:
        if st.session_state['plaid_step'] == 'link_ready':
            st.info("After 'Success', wait 5 seconds and click:")
            if st.button("🔄 2. Pull Data"):
                sync_plaid_data()

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

