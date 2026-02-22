import streamlit as st
import os
import base64
from style_utils import inject_global_css, show_disclaimer
from data_handler import load_user_data, init_session_state

# --- 1. SESSION INITIALIZATION ---
init_session_state()

# Load from the cloud exactly ONCE to prevent screen-wiping
if st.session_state.get('username') and not st.session_state.get('brrrr_sync_complete'):
    load_user_data(st.session_state.username)
    st.session_state['brrrr_sync_complete'] = True
    st.rerun()

inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- HELPER: SAFE FLOAT CONVERSION ---
# This completely prevents the TypeError by catching None or empty strings
def safe_float(val, default=0.0):
    try:
        if val is None or str(val).strip() == "":
            return float(default)
        return float(val)
    except (ValueError, TypeError):
        return float(default)

# --- HELPER: STICKY WIDGET STATE ---
db = st.session_state.get('app_db', {})

input_defaults = {
    "brrrr_buy_price_widget": ("brrrr_buy_price", 125000.0),
    "brrrr_rehab_budget_widget": ("brrrr_rehab_budget", 40000.0),
    "brrrr_arv_widget": ("brrrr_arv", 225000.0),
    "brrrr_holding_widget": ("brrrr_holding", 5000.0),
    "brrrr_rent_widget": ("brrrr_rent", 1850.0),
    "brrrr_refi_rate_widget": ("brrrr_refi_rate", 4.0),
    "brrrr_refi_costs_widget": ("brrrr_refi_costs", 4000.0),
    "brrrr_ltv_widget": ("brrrr_ltv", 75)
}

# Pre-fill Streamlit's session state only if it's completely empty.
# This makes your typing "sticky" and immune to database lag.
for widget_key, (db_key, default_val) in input_defaults.items():
    if widget_key not in st.session_state:
        db_val = db.get(db_key, default_val)
        if isinstance(default_val, float):
            st.session_state[widget_key] = safe_float(db_val, default_val)
        else:
            st.session_state[widget_key] = int(safe_float(db_val, default_val))

# --- 2. THEME & LOGO ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
SLATE_ACCENT = "#4A4E5A"
WARNING_AMBER = "#D97706"

def get_logo():
    img_path = "logo.png"
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{encoded}" style="width: 75px;">'
    return "🏘️"

st.markdown(f"<div style='display: flex; align-items: center; gap: 15px;'>{get_logo()} <h1 style='margin:0;'>FIRE Calculator: BRRRR Engine</h1></div>", unsafe_allow_html=True)

# --- 3. THE INPUTS ---
st.header("🛠️ Phase 1: Buy & Rehab")
col1, col2 = st.columns(2)

with col1:
    buy_price = st.number_input("Purchase Price ($)", step=1000.0, key="brrrr_buy_price_widget")
    rehab_budget = st.number_input("Rehab Costs ($)", step=1000.0, key="brrrr_rehab_budget_widget")
    
with col2:
    arv = st.number_input("After Repair Value (ARV) ($)", step=1000.0, key="brrrr_arv_widget")
    holding = st.number_input("Holding & Closing ($)", step=1000.0, key="brrrr_holding_widget")

st.header("🏦 Phase 2: Rent & Refi")
col3, col4 = st.columns(2)

with col3:
    monthly_rent = st.number_input("Monthly Rent ($)", step=50.0, key="brrrr_rent_widget")
    refi_ltv_pct = st.slider("Refinance LTV (%)", 50, 85, key="brrrr_ltv_widget")
    refi_ltv = refi_ltv_pct / 100.0

with col4:
    refi_rate = st.number_input("Refi Interest Rate (%)", step=0.1, key="brrrr_refi_rate_widget")
    refi_costs = st.number_input("Refi Closing Costs ($)", step=500.0, key="brrrr_refi_costs_widget")

# UPDATE DATABASE SILENTLY 
for widget_key, (db_key, _) in input_defaults.items():
    st.session_state.app_db[db_key] = st.session_state[widget_key]

# --- 4. MATH ENGINE ---
total_invested = buy_price + rehab_budget + holding

new_loan = 0.0
net_proceeds = 0.0
cash_left = total_invested
monthly_piti = 0.0
opex = monthly_rent * 0.25 
monthly_net = monthly_rent - opex
dscr = 0.0

if arv > 0:
    new_loan = round(arv * refi_ltv, -3)
    net_proceeds = round(new_loan - refi_costs, -3)
    cash_left = round(total_invested - net_proceeds, -3)

    if refi_rate > 0:
        r_monthly = (refi_rate / 100.0) / 12.0
        monthly_piti = (new_loan * r_monthly) / (1 - (1 + r_monthly)**-360)
    else:
        monthly_piti = new_loan / 360.0
    
    monthly_net = round(monthly_rent - monthly_piti - opex, 0)
    dscr = ((monthly_rent - opex) * 12) / (monthly_piti * 12) if monthly_piti > 0 else 99.0

# --- 5. RESULTS ---
st.divider()
r1, r2, r3 = st.columns(3)
r1.metric("Cash Left", f"${max(0, cash_left):,.0f}")
r2.metric("Equity Created", f"${round(arv - new_loan, -3):,.0f}")
r3.metric("Monthly Net", f"${monthly_net:,.0f}")



if arv > 0:
    if monthly_net < 0:
        st.markdown(f"""
        <div style="background-color: {WARNING_AMBER}15; padding: 20px; border-radius: 10px; border: 1px solid {WARNING_AMBER}; margin-top: 20px;">
            <h4 style="color: {WARNING_AMBER}; margin-top: 0;">📋 Deal Analysis</h4>
            <p style="color: {SLATE_ACCENT};"><b>DSCR: {dscr:.2f}</b>. Lenders usually want 1.20+. This negative cash flow can slow your portfolio velocity.</p>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 15px;">
                <div style="background: white; padding: 10px; border-radius: 5px; border: 1px solid {WARNING_AMBER}30; text-align: center;">
                    <span style="font-size: 1.2em;">📉</span><br><b style="color: {CHARCOAL};">Lower LTV</b><br><span style="font-size: 0.85em; color: {SLATE_ACCENT};">Try {max(50, refi_ltv_pct - 10)}%</span>
                </div>
                <div style="background: white; padding: 10px; border-radius: 5px; border: 1px solid {WARNING_AMBER}30; text-align: center;">
                    <span style="font-size: 1.2em;">🛠️</span><br><b style="color: {CHARCOAL};">Cut OpEx</b><br><span style="font-size: 0.85em; color: {SLATE_ACCENT};">Self-manage</span>
                </div>
                <div style="background: white; padding: 10px; border-radius: 5px; border: 1px solid {WARNING_AMBER}30; text-align: center;">
                    <span style="font-size: 1.2em;">💰</span><br><b style="color: {CHARCOAL};">Value Add</b><br><span style="font-size: 0.85em; color: {SLATE_ACCENT};">Increase Rent</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif cash_left <= 0:
        st.success("✨ **The Perfect BRRRR:** You've recovered your initial capital with positive cash flow.")

show_disclaimer()
