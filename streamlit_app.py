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
    # 1. Check if we still have the link_token in memory
    link_token = st.session_state.get('current_link_token')
    if not link_token:
        st.error("Session lost. Please click 'Connect Bank' again.")
        return

    try:
        # 2. Ask Plaid for the results of that session
        get_request = LinkTokenGetRequest(link_token=link_token)
        get_response = client.link_token_get(get_request)
        
        # --- THE FIX: Convert object to dictionary to find the token ---
        res_dict = get_response.to_dict()
        results = res_dict.get('results', {})
        item_add_results = results.get('item_add_results', [])
        
        if not item_add_results:
            st.warning("Plaid session found, but no bank was linked yet.")
            return

        public_token = item_add_results[0]['public_token']

        # 3. Exchange for an Access Token
        exchange_resp = client.item_public_token_exchange(
            ItemPublicTokenExchangeRequest(public_token=public_token)
        )
        access_token = exchange_resp['access_token']

        # 4. Fetch the Debt Data
        liabilities_resp = client.liabilities_get(
            LiabilitiesGetRequest(access_token=access_token)
        )
        liab_dict = liabilities_resp.to_dict()
        
        # 5. MAPPING TO YOUR CALCULATOR
        debts = liab_dict.get('liabilities', {})
        
        # Mapping Sandbox 'user_good' Credit Card data
        credit_accounts = debts.get('credit', [])
        if credit_accounts:
            total_bal = sum(acc.get('last_statement_balance', 0) for acc in credit_accounts)
            st.session_state.user_profile['cc_pmt'] = round(total_bal * 0.03, 2)
            
        # Mapping Sandbox Student Loans
        student_loans = debts.get('student', [])
        if student_loans:
            total_pmt = sum(s.get('last_payment_amount', 0) for s in student_loans)
            st.session_state.user_profile['student_loan'] = float(total_pmt)

        st.success("✅ Bank data fetched! Calculator updated.")
        st.rerun() # Refresh page to show the numbers
        
    except Exception as e:
        st.error(f"Sync Error: {e}")

# --- 1. INITIALIZE PLAID CLIENT ---
configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': st.secrets["PLAID_CLIENT_ID"],
        'secret': st.secrets["PLAID_SECRET"],
    }
)
api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

def create_plaid_link():
    plaid_request = LinkTokenCreateRequest(
        user={'client_user_id': st.session_state.get('user_id', 'user_123')},
        client_name="Analyst in a Pocket",
        products=[Products('liabilities')],
        country_codes=[CountryCode('CA')],
        language='en',
        hosted_link={} 
    )
    
    response = client.link_token_create(plaid_request)
    st.session_state['current_link_token'] = response['link_token']
    return response['hosted_link_url']

# --- 1. GLOBAL CONFIG ---
st.set_page_config(layout="wide", page_title="Analyst in a Pocket", page_icon="📊")

# --- 2. INITIALIZE GLOBAL VAULT ---
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

# --- 3. NAVIGATION ---
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

# --- 4. PROFILE PAGE ---
if selection == "👤 Client Profile":
    header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
    with header_col1:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=140)
    with header_col2:
        st.title("General Client Information")

    st.subheader("💾 Profile Management")
    up_col1, up_col2 = st.columns(2)
    with up_col1:
        uploaded_file = st.file_uploader("Upload Existing Profile (JSON)", type=["json"])
        if uploaded_file is not None:
            st.session_state.user_profile.update(json.load(uploaded_file))
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
    h_toggle, h_data = st.columns([1, 2])
    with h_toggle:
        st.session_state.user_profile['housing_status'] = st.radio("Current Status", ["Renting", "Owning"], index=0 if st.session_state.user_profile['housing_status'] == "Renting" else 1)
    with h_data:
        if st.session_state.user_profile['housing_status'] == "Renting":
            st.session_state.user_profile['rent_pmt'] = st.number_input("Monthly Rent ($)", value=float(st.session_state.user_profile.get('rent_pmt', 0.0)))
        else:
            sub_c1, sub_c2 = st.columns(2)
            with sub_c1:
                st.session_state.user_profile['m_bal'] = st.number_input("Current Mortgage Balance ($)", value=float(st.session_state.user_profile.get('m_bal', 0.0)))
                st.session_state.user_profile['m_rate'] = st.number_input("Current Interest Rate (%)", value=float(st.session_state.user_profile.get('m_rate', 0.0)))
            with sub_c2:
                st.session_state.user_profile['m_amort'] = st.number_input("Remaining Amortization (Years)", value=int(st.session_state.user_profile.get('m_amort', 25)))
                st.session_state.user_profile['prop_taxes'] = st.number_input("Annual Property Taxes ($)", value=float(st.session_state.user_profile.get('prop_taxes', 4200.0)))
                st.session_state.user_profile['heat_pmt'] = st.number_input("Estimated Monthly Heating ($)", value=float(st.session_state.user_profile.get('heat_pmt', 125.0)))

    st.divider()
    st.subheader("💳 Monthly Liabilities")

    # --- PLAID BUTTONS ---
    col_plaid1, col_plaid2 = st.columns(2)
    with col_plaid1:
        if st.button("🔗 1. Connect Bank"):
            try:
                link_url = create_plaid_link()
                st.markdown(f"### [Click here to Login]({link_url})")
            except Exception as e:
                st.error(f"Plaid Error: {e}")
    with col_plaid2:
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
