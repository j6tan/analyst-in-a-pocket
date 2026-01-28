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

if 'show_plaid' not in st.session_state:
    st.session_state.show_plaid = False

# --- 2. INITIALIZE PLAID CLIENT ---
try:
    configuration = plaid.Configuration(
        host=plaid.Environment.Sandbox,
        api_key={
            'clientId': st.secrets["PLAID_CLIENT_ID"],
            'secret': st.secrets["PLAID_SECRET"],
        }
    )
    api_client = plaid_api.ApiClient(configuration)
    client = plaid_api.PlaidApi(api_client)
except Exception as e:
    st.error(f"Configuration Error: {e}")
    st.stop()

# --- 3. THE PLAID INTERFACE ---
def plaid_interface():
    # Button to toggle the interface
    if st.button("🔗 Sync Bank Liabilities (Plaid)", use_container_width=True):
        st.session_state.show_plaid = True
        st.rerun()

    if st.session_state.show_plaid:
        try:
            # Generate token once per session trigger
            request = LinkTokenCreateRequest(
                user={'client_user_id': str(uuid.uuid4())},
                client_name="Analyst in a Pocket",
                products=[Products('liabilities')],
                country_codes=[CountryCode('CA')],
                language='en'
            )
            response = client.link_token_create(request)
            link_token = response['link_token']
            
            html_code = f"""
                <div style="text-align:center; padding: 15px; border: 2px solid #2e7d32; border-radius: 10px; background: #f1f8e9;">
                    <p style="margin-bottom:10px; font-family:sans-serif;">✅ <b>Plaid Ready</b></p>
                    <button id='plaid-open' style="background:#2e7d32; color:white; border:none; padding:12px 24px; border-radius:5px; cursor:pointer; font-weight:bold;">
                        LAUNCH SECURE BANK LOGIN
                    </button>
                    <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
                    <script>
                        const handler = Plaid.create({{
                            token: '{link_token}',
                            onSuccess: (public_token, metadata) => {{
                                window.parent.postMessage({{
                                    type: 'streamlit:setComponentValue',
                                    value: public_token
                                }}, '*');
                            }},
                            onExit: (err, metadata) => {{ 
                                console.log('User closed Plaid'); 
                            }}
                        }});
                        document.getElementById('plaid-open').onclick = () => handler.open();
                    </script>
                </div>
            """
            # This positional-only call is what fixed your IframeMixin error
            res_token = components.html(html_code, height=120)

            # C. Handle the Token Exchange ONLY if we got a value back
            if res_token and len(res_token) > 10:
                with st.spinner("🔄 Fetching Debt Data..."):
                    exchange = client.item_public_token_exchange(ItemPublicTokenExchangeRequest(public_token=res_token))
                    res = client.liabilities_get(LiabilitiesGetRequest(access_token=exchange['access_token']))
                    debts = res.to_dict().get('liabilities', {})
                    
                    if debts.get('credit'):
                        bal = sum(cc.get('last_statement_balance', 0) for cc in debts['credit'])
                        st.session_state.user_profile['cc_pmt'] = round(bal * 0.03, 2)
                    
                    if debts.get('student'):
                        pmt = sum(s.get('last_payment_amount', 0) for s in debts['student'])
                        st.session_state.user_profile['student_loan'] = float(pmt)
                    
                    st.session_state.show_plaid = False # Close the interface
                    st.success("✅ Bank Data Synced!")
                    time.sleep(1)
                    st.rerun()

            if st.button("Cancel Sync"):
                st.session_state.show_plaid = False
                st.rerun()

        except Exception as e:
            st.error(f"Plaid Error: {e}")
            st.session_state.show_plaid = False

# --- 4. APP CONFIG ---
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
    st.title("General Client Information")

    st.subheader("👥 Household Income Details")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.user_profile['p1_name'] = st.text_input("Full Name", value=st.session_state.user_profile['p1_name'])
        st.session_state.user_profile['p1_t4'] = st.number_input("T4 Income", value=float(st.session_state.user_profile['p1_t4']))
    
    with c2:
        st.session_state.user_profile['p2_name'] = st.text_input("Full Name ", value=st.session_state.user_profile['p2_name'])
        st.session_state.user_profile['p2_t4'] = st.number_input("T4 Income ", value=float(st.session_state.user_profile['p2_t4']))

    st.divider()
    st.subheader("💳 Monthly Liabilities")

    # Call the Plaid trigger
    plaid_interface()

    l1, l2, l3 = st.columns(3)
    with l1:
        st.session_state.user_profile['car_loan'] = st.number_input("Car Loan Payments", value=float(st.session_state.user_profile['car_loan']))
        st.session_state.user_profile['student_loan'] = st.number_input("Student Loan Payments", value=float(st.session_state.user_profile['student_loan']))
    with l2:
        st.session_state.user_profile['cc_pmt'] = st.number_input("Credit Card Payments", value=float(st.session_state.user_profile['cc_pmt']))
        st.session_state.user_profile['loc_balance'] = st.number_input("Total LOC Balance", value=float(st.session_state.user_profile['loc_balance']))
    with l3:
        prov_options = ["Ontario", "BC", "Alberta", "Quebec", "Manitoba", "Saskatchewan", "Nova Scotia", "NB", "PEI", "NL"]
        st.session_state.user_profile['province'] = st.selectbox("Province", prov_options, index=prov_options.index(st.session_state.user_profile.get('province', 'Ontario')))

    profile_json = json.dumps(st.session_state.user_profile, indent=4)
    st.download_button("💾 Download Profile", data=profile_json, file_name="client_profile.json", mime="application/json")

# --- 7. HANDLE OTHER PAGES ---
else:
    file_path = os.path.join("scripts", tools[selection])
    if os.path.exists(file_path):
        exec(open(file_path, encoding="utf-8").read(), globals())
