import streamlit as st
import json
import os
import uuid
import plaid
import time
import streamlit.components.v1 as components # Required for the Bridge
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.link_token_get_request import LinkTokenGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.liabilities_get_request import LiabilitiesGetRequest

# --- 1. SHARED MAILBOX ---
@st.cache_resource
def get_global_token_store():
    return {}

token_store = get_global_token_store()

# --- 2. SESSION STATE SETUP ---
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

# --- 4. THE PLAID INTERFACE FUNCTION (PATCHED) ---
@st.fragment
def plaid_interface():
    # A. Generate Link Token if not present
    if 'link_token' not in st.session_state:
        try:
            request = LinkTokenCreateRequest(
                user={'client_user_id': str(uuid.uuid4())},
                client_name="Analyst in a Pocket",
                products=[Products('liabilities')],
                country_codes=[CountryCode('CA')],
                language='en'
            )
            response = client.link_token_create(request)
            st.session_state.link_token = response['link_token']
        except Exception as e:
            st.error(f"Plaid Init Error: {e}")
            return

    # B. The Javascript Bridge (Handles UI Popup)
    # This component emits a string value back to Streamlit on success
    res_token = components.html(f"""
        <html>
        <head>
            <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
        </head>
        <body style="margin: 0; padding: 0;">
            <button id="link-button" style="
                background-color: #2e7d32; 
                color: white; 
                border: none; 
                padding: 12px; 
                border-radius: 8px; 
                font-weight: bold; 
                width: 100%; 
                cursor: pointer;
                font-family: sans-serif;">
                🔗 Connect Bank Account
            </button>
            <div id="error-msg" style="color: red; font-size: 11px; font-family: sans-serif; margin-top: 5px; display: none;"></div>

            <script type="text/javascript">
                const btn = document.getElementById('link-button');
                const errDiv = document.getElementById('error-msg');

                try {{
                    const handler = Plaid.create({{
                        token: '{st.session_state.link_token}',
                        onSuccess: function(public_token, metadata) {{
                            window.parent.postMessage({{
                                type: 'streamlit:setComponentValue',
                                value: public_token
                            }}, '*');
                        }},
                        onExit: function(err, metadata) {{
                            if (err != null) {{
                                errDiv.style.display = 'block';
                                errDiv.innerText = 'Plaid Error: ' + err.display_message;
                            }}
                        }}
                    }});

                    btn.onclick = function() {{
                        handler.open();
                    }};
                }} catch (e) {{
                    errDiv.style.display = 'block';
                    errDiv.innerText = 'Bridge Error: ' + e.message;
                }}
            </script>
        </body>
        </html>
    """, height=70)

    # C. Handle Data Pull (Only runs if res_token is the string returned from JS)
    if isinstance(res_token, str) and res_token.strip() != "":
        with st.spinner("⏳ Fetching bank data..."):
            try:
                # Exchange public_token for access_token
                exchange = client.item_public_token_exchange(
                    ItemPublicTokenExchangeRequest(public_token=res_token)
                )
                access_token = exchange['access_token']

                # Fetch Liabilities
                res = client.liabilities_get(
                    LiabilitiesGetRequest(access_token=access_token)
                )
                debts = res.to_dict().get('liabilities', {})

                # Update Profile (CC Balances & Student Loans)
                if debts.get('credit'):
                    bal = sum(cc.get('last_statement_balance', 0) for cc in debts['credit'])
                    st.session_state.user_profile['cc_pmt'] = round(bal * 0.03, 2)
                
                if debts.get('student'):
                    pmt = sum(s.get('last_payment_amount', 0) for s in debts['student'])
                    st.session_state.user_profile['student_loan'] = float(pmt)

                st.success("✅ Bank Data Synced!")
                # Reset token for a clean slate
                del st.session_state['link_token']
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Sync failed: {e}")

# --- 5. APP CONFIG ---
st.set_page_config(layout="wide", page_title="Analyst in a Pocket", page_icon="📊")

# --- 6. NAVIGATION ---
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
