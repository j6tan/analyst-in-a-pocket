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

# --- 1. SHARED MAILBOX (Fixes the "Empty Page" / New Tab issue) ---
@st.cache_resource
def get_global_token_store():
    return {}

token_store = get_global_token_store()

# --- 2. SESSION STATE SETUP (Original Structure) ---
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

# --- 3. INITIALIZE PLAID CLIENT ---
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

# --- 4. THE PLAID INTERFACE FUNCTION ---
@st.fragment
def plaid_interface():
    # Initialize a status tracker in the session state
    if 'plaid_status' not in st.session_state:
        st.session_state['plaid_status'] = 'idle'

    # 1. HANDLE REDIRECT (This is what the "New Tab" sees)
    if "req_id" in st.query_params:
        st.success("✅ **Bank Login Verified!**")
        st.info("You can now close this tab and return to the original window to sync your data.")
        return

    # 2. THE MAIN UI (What you see in your original tab)
    if st.session_state['plaid_status'] == 'idle':
        if st.button("🔗 Connect Bank Account", use_container_width=True):
            try:
                # We create a unique ID to track this specific attempt
                req_id = str(uuid.uuid4())
                # MUST match your Plaid Dashboard "Allowed Redirect URIs"
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
                
                # Save the link token in the session so we can check it later
                st.session_state['active_link_token'] = response['link_token']
                st.session_state['plaid_status'] = 'waiting'
                
                # Create a big clickable link
                st.markdown(f"""
                    <a href="{response['hosted_link_url']}" target="_blank" style="text-decoration: none;">
                        <div style="background-color: #2e7d32; color: white; padding: 15px; text-align: center; border-radius: 8px; font-weight: bold; margin-bottom: 10px; cursor: pointer;">
                            👉 STEP 1: CLICK TO LOGIN (Opens New Tab)
                        </div>
                    </a>
                """, unsafe_allow_html=True)
                st.rerun()
            except Exception as e:
                st.error(f"Plaid Init Error: {e}")

    # 3. THE SYNC STEP (The original tab waits for you here)
    elif st.session_state['plaid_status'] == 'waiting':
        st.markdown("---")
        st.warning("⏳ **Step 2: Pull the Data**")
        st.write("Once you have finished the login in the other tab, click the button below.")
        
        if st.button("📥 Sync My Liabilities Now", type="primary", use_container_width=True):
            with st.spinner("Checking with Plaid..."):
                try:
                    token = st.session_state.get('active_link_token')
                    # We ask Plaid: "Did that token we gave the user result in a success?"
                    check_res = client.link_token_get(LinkTokenGetRequest(link_token=token)).to_dict()
                    
                    public_token = None
                    if check_res.get('link_sessions'):
                        for s in check_res['link_sessions']:
                            if s.get('status') == 'success':
                                public_token = s.get('public_token')
                                break
                    
                    if public_token:
                        # Success! Now exchange for real data
                        exchange = client.item_public_token_exchange(ItemPublicTokenExchangeRequest(public_token=public_token))
                        liab = client.liabilities_get(LiabilitiesGetRequest(access_token=exchange['access_token']))
                        debts = liab.to_dict().get('liabilities', {})
                        
                        # Update your CC and Student Loan fields
                        if debts.get('credit'):
                            bal = sum(cc.get('last_statement_balance', 0) for cc in debts['credit'])
                            st.session_state.user_profile['cc_pmt'] = round(bal * 0.03, 2)
                        
                        if debts.get('student'):
                            pmt = sum(s.get('last_payment_amount', 0) for s in debts['student'])
                            st.session_state.user_profile['student_loan'] = float(pmt)

                        st.success("✅ Liabilities Updated!")
                        st.session_state['plaid_status'] = 'idle'
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Plaid doesn't show a successful login yet. Make sure you reached the final 'Success' screen in the other tab.")
                except Exception as e:
                    st.error(f"Sync Error: {e}")
        
        if st.button("Cancel & Reset"):
            st.session_state['plaid_status'] = 'idle'
            st.rerun()

# --- 5. APP CONFIG ---
st.set_page_config(layout="wide", page_title="Analyst in a Pocket", page_icon="📊")

# --- 6. NAVIGATION (Your Original Logic) ---
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

# --- 7. PAGE UI ---
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

    # The Plaid Interface Call
    plaid_interface()

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

# --- 8. HANDLE OTHER PAGES ---
else:
    file_path = os.path.join("scripts", tools[selection])
    if os.path.exists(file_path):
        exec(open(file_path, encoding="utf-8").read(), globals())



