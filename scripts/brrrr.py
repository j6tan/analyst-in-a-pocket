import streamlit as st
import os
import base64
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, load_user_data, init_session_state

# --- 1. SESSION INITIALIZATION ---
init_session_state()

# We only load from the cloud ONCE at the start. 
# This prevents the cloud from overwriting your screen while you type.
if st.session_state.get('username') and not st.session_state.get('brrrr_sync_complete'):
    load_user_data(st.session_state.username)
    st.session_state['brrrr_sync_complete'] = True
    st.rerun()

inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 2. THEME & LOGO ---
PRIMARY_GOLD = "#CEB36F"
SLATE_ACCENT = "#4A4E5A"
WARNING_AMBER = "#D97706"

def get_logo():
    img_path = "logo.png"
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{encoded}" style="width: 75px;">'
    return "🏘️"

st.markdown(f"<div style='display: flex; align-items: center; gap: 15px;'>{get_logo()} <h1 style='margin:0;'>The BRRRR Engine</h1></div>", unsafe_allow_html=True)

# --- 3. THE "STICKY" INPUTS ---
# We define these variables first. If they exist in session_state, we use them.
# This is the "Anchor" that stops the values from jumping to zero.

st.header("🛠️ Phase 1: Buy & Rehab")
col1, col2 = st.columns(2)

with col1:
    # We use st.number_input with a manual key for maximum stability
    buy_price = st.number_input("Purchase Price ($)", value=float(st.session_state.app_db.get('brrrr_buy_price', 0)), key="input_buy")
    rehab_budget = st.number_input("Rehab Costs ($)", value=float(st.session_state.app_db.get('brrrr_rehab_budget', 0)), key="input_rehab")
    
with col2:
    arv = st.number_input("After Repair Value (ARV) ($)", value=float(st.session_state.app_db.get('brrrr_arv', 0)), key="input_arv")
    holding = st.number_input("Holding & Closing ($)", value=float(st.session_state.app_db.get('brrrr_holding', 0)), key="input_holding")

st.header("🏦 Phase 2: Rent & Refi")
col3, col4 = st.columns(2)

with col3:
    monthly_rent = st.number_input("Monthly Rent ($)", value=float(st.session_state.app_db.get('brrrr_rent', 0)), key="input_rent")
    refi_ltv_pct = st.slider("Refinance LTV (%)", 50, 85, 75, key="input_ltv")
    refi_ltv = refi_ltv_pct / 100

with col4:
    refi_rate = st.number_input("Refi Interest Rate (%)", value=float(st.session_state.app_db.get('brrrr_refi_rate', 4.0)), key="input_rate")
    refi_costs = st.number_input("Refi Closing Costs ($)", value=float(st.session_state.app_db.get('brrrr_refi_costs', 4000)), key="input_refi_costs")

# UPDATE DATABASE (Background sync)
# This saves your data without interrupting the UI flow
st.session_state.app_db['brrrr_buy_price'] = buy_price
st.session_state.app_db['brrrr_rehab_budget'] = rehab_budget
st.session_state.app_db['brrrr_arv'] = arv
st.session_state.app_db['brrrr_holding'] = holding
st.session_state.app_db['brrrr_rent'] = monthly_rent
st.session_state.app_db['brrrr_refi_rate'] = refi_rate
st.session_state.app_db['brrrr_refi_costs'] = refi_costs

# --- 4. MATH ENGINE ---
total_invested = buy_price + rehab_budget + holding

if arv > 0 and refi_rate > 0:
    new_loan = round(arv * refi_ltv, -3)
    net_proceeds = round(new_loan - refi_costs, -3)
    cash_left = round(total_invested - net_proceeds, -3)

    # Mortgage formula
    r_monthly = (refi_rate / 100) / 12
    monthly_piti = (new_loan * r_monthly) / (1 - (1 + r_monthly)**-360)
    
    opex = monthly_rent * 0.25 
    monthly_net = round(monthly_rent - monthly_piti - opex, 0)
    dscr = ((monthly_rent - opex) * 12) / (monthly_piti * 12) if monthly_piti > 0 else 0

    # --- 5. RESULTS ---
    st.divider()
    r1, r2, r3 = st.columns(3)
    r1.metric("Cash Left", f"${max(0, cash_left):,.0f}")
    r2.metric("Equity Created", f"${round(arv - new_loan, -3):,.0f}")
    r3.metric("Monthly Net", f"${monthly_net:,.0f}")

    if monthly_net < 0:
        st.warning(f"⚠️ Cash Flow is negative. DSCR is {dscr:.2f}. You may struggle to get your next loan.")

show_disclaimer()
