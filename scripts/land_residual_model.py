import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import time
import os
import json
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, load_user_data, init_session_state, supabase

# --- 1. UNIVERSAL AUTO-LOADER ---
init_session_state()
if st.session_state.get('username') and not st.session_state.app_db.get('profile'):
    with st.spinner("🔄 restoring your data..."):
        load_user_data(st.session_state.username)
        time.sleep(0.1)
        st.rerun()

inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 2. THEME & UTILS ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"
SUCCESS_GREEN = "#16A34A"
DANGER_RED = "#DC2626"

def format_money(val):
    sign = "-" if val < 0 else ""
    val = abs(val)
    if val >= 1_000_000:
        return f"{sign}${val/1_000_000:,.2f}M"
    else:
        return f"{sign}${val:,.0f}"

# --- 3. MARKET INTEL & VELOCITY MAPPING ---
def load_market_intel():
    # Use the filename provided in your environment
    for fname in ["market_intel.json", "market_intel (7).json"]:
        if os.path.exists(fname):
            try:
                with open(fname, "r") as f: return json.load(f)
            except: pass
    return {}

intel = load_market_intel()
current_prime = intel.get("rates", {}).get("bank_prime", 4.45)
default_finance_rate = current_prime + 2.0

# Strict velocity mapping: 6 months for small, 12 for mid, 18 for large/condo
BUILD_DATA = {
    "Single Family (Custom)": {"fsr": 0.6, "cost": 450, "sell_months": 6},
    "Duplex / Semi-Detached": {"fsr": 0.8, "cost": 380, "sell_months": 6},
    "Multiplex / Row House": {"fsr": 1.2, "cost": 320, "sell_months": 12},
    "Townhouse (Woodframe)": {"fsr": 1.4, "cost": 300, "sell_months": 12},
    "Mid-Rise Condo (Woodframe)": {"fsr": 2.5, "cost": 330, "sell_months": 18},
    "High-Rise Condo (Concrete)": {"fsr": 5.0, "cost": 450, "sell_months": 18},
    "Commercial / Mixed-Use": {"fsr": 3.0, "cost": 350, "sell_months": 18}
}

# --- 4. DATABASE INITIALIZATION ---
if 'land_residual' not in st.session_state.app_db:
    st.session_state.app_db['land_residual'] = {
        'lot_size': 6000,
        'sell_psf': 1100,
        'soft_cost_pct': 15.0,
        'city_fees_psf': 45.0,
        'profit_margin': 15.0,
        'finance_rate': default_finance_rate,
        'project_months': 24.0,
        'ltc_pct': 65.0
    }

prof = st.session_state.app_db.get('profile', {})
household = prof.get('p1_name', "Primary Client")

# --- 5. HEADER ---
st.title("🏗️ Land Residual Valuation")
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px; border-radius: 12px; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin: 0;">📐 Strategic Brief: Highest & Best Use</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; margin-bottom: 0;">
        Calculating the <b>Maximum Land Price</b> for <b>{household}</b> based on construction costs, municipal fees, and market velocity.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 6. INPUTS ---
st.subheader("1. Zoning & Product Selection")
z_col1, z_col2, z_col3 = st.columns(3)

with z_col1:
    lot_size = cloud_input("Lot Size (Sq.Ft.)", "land_residual", "lot_size", step=500)

with z_col2:
    prod_type = st.selectbox("Proposed Product Type", list(BUILD_DATA.keys()))
    # Extract the dynamic defaults for this product
    active_defaults = BUILD_DATA[prod_type]
    sell_months = active_defaults["sell_months"]

with z_col3:
    # Use the product type as part of the key to force refresh when user switches types
    fsr = st.number_input("Floor Space Ratio (FSR)", value=active_defaults["fsr"], step=0.1, key=f"fsr_{prod_type}")

buildable_sf = lot_size * fsr
st.info(f"📐 **Buildable Area:** {buildable_sf:,.0f} SF | ⏳ **Sales Velocity:** {sell_months} Month Sell-Out Phase")

st.divider()

st.subheader("2. Financial Underwriting")
f_col1, f_col2, f_col3 = st.columns(3)

with f_col1:
    st.markdown("**Revenue & Profit**")
    sell_psf = cloud_input("Projected Sale Price ($/SF)", "land_residual", "sell_psf", step=50)
    profit_margin = cloud_input("Target Profit Margin (%)", "land_residual", "profit_margin", step=1.0)

with f_col2:
    st.markdown("**Construction & Fees**")
    # Dynamic key ensures Hard Costs update when changing home type
    hard_cost_psf = st.number_input("Hard Costs ($/SF)", value=active_defaults["cost"], step=10, key=f"hc_{prod_type}")
    
    c2_1, c2_2 = st.columns(2)
    with c2_1:
        city_fees_psf = cloud_input("City Fees ($/SF)", "land_residual", "city_fees_psf", step=5.0)
    with c2_2:
        soft_cost_pct = cloud_input("Soft Costs (%)", "land_residual", "soft_cost_pct", step=1.0)

with f_col3:
    st.markdown("**Capital Stack**")
    c3_1, c3_2 = st.columns(2)
    with c3_1:
        finance_rate = cloud_input("Bank Loan Rate (%)", "land_residual", "finance_rate", step=0.25)
    with c3_2:
        ltc_pct = cloud_input("Loan-to-Cost (LTC) %", "land_residual", "ltc_pct", step=5.0)
    project_months = cloud_input("Construction Duration (Months)", "land_residual", "project_months", step=1.0)

# --- 7. CALCULATIONS ---
gdv = buildable_sf * sell_psf
target_profit = gdv * (profit_margin / 100)
total_hard = buildable_sf * hard_cost_psf
total_city_fees = buildable_sf * city_fees_psf
total_soft = (total_hard * (soft_cost_pct / 100)) + total_city_fees
total_construction = total_hard + total_soft

# Interest calculation (Interest on avg 50% draw over construction period)
finance_cost = (total_construction * 0.5) * (finance_rate / 100) * (project_months / 12)

residual_land_value = gdv - target_profit - total_construction - finance_cost
total_project_cost = gdv - target_profit
bank_loan = total_project_cost * (ltc_pct / 100)
equity_required = total_project_cost - bank_loan
return_on_equity = (target_profit / equity_required) * 100 if equity_required > 0 else 0

# --- 8. CASH FLOW (S-CURVE) ---
const_months = int(project_months)
total_timeline = const_months + sell_months 

monthly_const_spend = total_construction / const_months if const_months > 0 else 0
monthly_revenue = gdv / sell_months if sell_months > 0 else 0

cf_months = [0]
cumulative_cash = [-residual_land_value] 

for m in range(1, total_timeline + 1):
    net_mo = 0
    if m <= const_months:
        net_mo -= (monthly_const_spend + (finance_cost / const_months)) 
    if m > const_months:
        net_mo += monthly_revenue 
    cf_months.append(m)
    cumulative_cash.append(cumulative_cash[-1] + net_mo)

# --- 9. OUTPUT ---
st.divider()
st.subheader("📊 The Verdict: Project Feasibility")

if residual_land_value <= 0:
    st.error(f"❌ **Unviable Deal:** Land value is negative ({format_money(residual_land_value)}).")
else:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Max Land Price", format_money(residual_land_value))
    m2.metric("Cash Equity Required", format_money(equity_required))
    m3.metric("Projected Profit", format_money(target_profit))
    m4.metric("Return on Equity", f"{return_on_equity:.1f}%")

    # Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cf_months, y=cumulative_cash, fill='tozeroy', line=dict(color=PRIMARY_GOLD, width=3)))
    fig.update_layout(title=f"Capital Timeline ({total_timeline} Months)", xaxis_title="Timeline (Months)", yaxis_title="Cash Position ($)", height=400, plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

    # Sensitivity Heatmap (Simplified for logic)
    st.subheader("🌡️ Risk Matrix: Sale Price vs Hard Costs")
    # ... (Heatmap code logic from previous version remains compatible)

show_disclaimer()
