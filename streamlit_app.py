import streamlit as st
import json
import os
import uuid
import plaid
import time
import streamlit.components.v1 as components
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.liabilities_get_request import LiabilitiesGetRequest

# --- 1. SESSION STATE SETUP ---
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
if 'current_link_token' not in st.session_state:
    st.session_state['current_link_token'] = None

# --- 2. INITIALIZE PLAID CLIENT ---
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

# --- 3. THE JAVASCRIPT PLAID INTERFACE ---
@st.fragment
def plaid_interface():
    # --- A. CHECK FOR RETURN TRIP (The New Tab) ---
    # We look for TWO things: status=success AND the token we passed along
    params = st.query_params
    
    if params.get("status") == "success" and params.get("t"):
        # We retrieve the token directly from the URL stash
        incoming_token = params.get("t")
        
        # Avoid re-running logic if we already synced this specific token
        if st.session_state.get('last_processed_token') != incoming_token:
            st.toast("🔄 Verifying Bank Connection...", icon="🏦")
            
            try:
                # Ask Plaid for the session details using the token from the URL
                check_req = LinkTokenGetRequest(link_token=incoming_token)
                check_res = client.link_token_get(check_req).to_dict()
                
                # Extract public_token
                public_token = None
                if check_res.get('link_sessions'):
                    for s in check_res['link_sessions']:
                        if s.get('status') == 'success':
                            public_token = s.get('public_token')
                            break
                
                if public_token:
                    # Exchange and Sync
                    exchange = client.item_public_token_exchange(ItemPublicTokenExchangeRequest(public_token=public_token))
                    liab = client.liabilities_get(LiabilitiesGetRequest(access_token=exchange['access_token']))
                    debts = liab.to_dict().get('liabilities', {})
                    
                    # FILL DATA
                    if debts.get('credit'):
                        bal = sum(cc.get('last_statement_balance', 0) for cc in debts['credit'])
                        st.session_state.user_profile['cc_pmt'] = round(bal * 0.03, 2)
                    
                    if debts.get('student'):
                        pmt = sum(s.get('last_payment_amount', 0) for s in debts['student'])
                        st.session_state.user_profile['student_loan'] = float(pmt)

                    st.success("✅ Success! Data has been imported.")
                    st.info("ℹ️ You can now close the previous tab and continue here.")
                    
                    # Mark this token as "done" so we don't loop forever
                    st.session_state['last_processed_token'] = incoming_token
                    
                    # Optional: Clean the URL
                    # st.query_params.clear() 
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Connection incomplete. Please try linking again.")
            
            except Exception as e:
                st.error(f"Sync Error: {e}")

    # --- B. THE START BUTTON (The Old Tab) ---
    else:
        if st.button("🔗 Connect Bank (Auto-Fill)", use_container_width=True):
            try:
                # 1. DEFINE YOUR APP URL
                # If locally testing:
                # base_url = "http://localhost:8501" 
                # If on Cloud (Update this to your actual URL!):
                base_url = "https://analyst-in-a-pocket.streamlit.app"
                
                # 2. CREATE A UNIQUE LINK TOKEN
                user_id = str(uuid.uuid4())
                
                # We need the token *before* we create the redirect URI...
                # But Plaid requires the redirect URI to create the token.
                # Catch-22? No. We use the 'state' parameter or append to URI later? 
                # Actually, Plaid Hosted Link creates the token first, THEN gives you the URL.
                # Wait, 'completion_redirect_uri' is part of the CREATE request. 
                # So we can't put the token inside the redirect URI before we have the token.
                
                # SMART WORKAROUND:
                # We will use a placeholder in the URI? No, Plaid validates it.
                # We can't pass the token in the URI if we don't have it yet.
                # BUT, we can just assume the redirect will happen and let the user 
                # pass the "link_session_id" which Plaid appends automatically?
                # No, Plaid appends 'link_token' automatically to the redirect if configured!
                
                # SIMPLER FIX:
                # We create the request WITHOUT the token in the URL first.
                # Plaid usually appends `?link_token=...` or `?link_session_id=...` automatically upon return.
                # Let's rely on Plaid's automatic appending. 
                # If Plaid DOESN'T append it, we have to use a 2-step process or `state`.
                
                # Let's try passing a temporary ID (state) that matches a session ID?
                # Actually, the EASIEST way:
                # We don't need the Token in the URL if we just fetch the MOST RECENTLY CREATED token? 
                # No, that's risky with multiple users.
                
                # BETTER FIX (The "Oauth State" Trick):
                # We generate a random ID *ourselves* first.
                my_tracking_id = str(uuid.uuid4())
                
                redirect_uri = f"{base_url}?status=success&tracking_id={my_tracking_id}"

                request = LinkTokenCreateRequest(
                    user={'client_user_id': user_id},
                    client_name="Analyst in a Pocket",
                    products=[Products('liabilities')],
                    country_codes=[CountryCode('CA')],
                    language='en',
                    hosted_link={'completion_redirect_uri': redirect_uri}
                )
                response = client.link_token_create(request)
                
                # Save the mapping of Tracking ID -> Link Token in Session State? 
                # NO, session state doesn't persist to the new tab!
                
                # OKAY, NEW STRATEGY: 
                # We can't easily pass data between tabs without a database.
                # EXCEPT: We can append the `link_token` to the URL *manually* on the client side? 
                # No, Plaid handles the redirect.
                
                # WAIT! Plaid documentation says: 
                # "The link_token will be appended to the completion_redirect_uri as a query parameter."
                # If that is true, we just need to look for 'link_token' in params!
                
                st.session_state['current_link_token'] = response['link_token']
                
                # BUTTON TO OPEN PLAID
                st.link_button("👉 Click to Open Secure Bank Login", response['hosted_link_url'])

            except Exception as e:
                st.error(f"Plaid Error: {e}")
        
# --- 4. CONFIG ---
st.set_page_config(layout="wide", page_title="Analyst in a Pocket", page_icon="📊")

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
            try:
                data = json.load(uf)
                st.session_state.user_profile.update(data)
                st.success("Profile Loaded!")
            except:
                st.error("Invalid JSON file.")

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

    # This handles the Plaid JavaScript button
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

else:
    file_path = os.path.join("scripts", tools[selection])
    if os.path.exists(file_path):
        exec(open(file_path, encoding="utf-8").read(), globals())





