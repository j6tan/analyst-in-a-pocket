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

def format_money(val):
    sign = "-" if val < 0 else ""
    val = abs(val)
    if val >= 1_000_000: return f"{sign}${val/1_000_000:,.2f}M"
    return f"{sign}${val:,.0f}"

# --- 3. MARKET INTEL & VELOCITY ---
def load_market_intel():
    for fname in ["market_intel.json", "market_intel (7).json"]:
        if os.path.exists(fname):
            try:
                with open(fname, "r") as f: return json.load(f)
            except: pass
    return {}

intel = load_market_intel()
current_prime = intel.get("rates", {}).get("bank_prime", 4.45)
default_finance_rate = current_prime + 2.0

BUILD_DATA = {
    "Single Family (Custom)": {"fsr": 0.6, "cost": 450, "sell_months": 6},
    "Duplex / Semi-Detached": {"fsr": 0.8, "cost": 380, "sell_months": 6},
    "Multiplex / Row House": {"fsr": 1.2, "cost": 320, "sell_months": 12},
    "Townhouse (Woodframe)": {"fsr": 1.4, "cost": 300, "sell_months": 12},
    "Mid-Rise Condo (Woodframe)": {"fsr": 2.5, "cost": 330, "sell_months": 18},
    "High-Rise Condo (Concrete)": {"fsr": 5.0, "cost": 450, "sell_months": 18}
}

# --- 4. HEADER & EXTENDED STORYTELLING ---
st.title("🏗️ Land Residual Valuation")

prof = st.session_state.app_db.get('profile', {})
household = prof.get('p1_name', "Primary Client")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 30px; border-radius: 15px; border: 1px solid {BORDER_GREY}; border-left: 10px solid {PRIMARY_GOLD};">
    <h2 style="color: {CHARCOAL}; margin-top: 0;">📐 The Developer's Mandate: Highest & Best Use</h2>
    <p style="color: {SLATE_ACCENT}; font-size: 1.15em; line-height: 1.6;">
        Welcome back, <b>{household}</b>. In real estate development, we don't value land by looking at comparable sales—we value it by looking at <b>potential</b>. 
        This tool uses the <b>Residual Method of Valuation</b>. It works backward from the finished product's end value.
    </p>
    <div style="background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; margin: 20px 0;">
        <h4 style="margin-top:0; color: {PRIMARY_GOLD};">How the "Residual" logic works:</h4>
        <ol style="color: {SLATE_ACCENT}; font-size: 1.05em;">
            <li><b>Gross Realization:</b> We calculate the total revenue from selling the finished homes.</li>
            <li><b>Profit First:</b> We subtract your required 15-20% profit margin immediately (you don't work for free).</li>
            <li><b>The Hard Truth:</b> We subtract every dollar of construction, city fees, and architecture.</li>
            <li><b>The Residual:</b> Whatever is left over after all costs and profit are accounted for is the <b>Maximum Price</b> you can afford to pay for the land.</li>
        </ol>
    </div>
    <p style="color: {SLATE_ACCENT}; font-style: italic; font-size: 1em;">
        "If you pay more than the Residual Value, you are effectively eating into your own profit margin."
    </p>
</div>
""", unsafe_allow_html=True)



# --- 5. INPUTS ---
st.write("")
st.subheader("1. Site Potential & Product Velocity")
z_col1, z_col2, z_col3 = st.columns(3)

with z_col1:
    lot_size = cloud_input("Lot Size (Sq.Ft.)", "land_residual", "lot_size", step=500)
with z_col2:
    prod_type = st.selectbox("Proposed Product Type", list(BUILD_DATA.keys()))
    active_defaults = BUILD_DATA[prod_type]
    sell_months = active_defaults["sell_months"]
with z_col3:
    fsr = st.number_input("Floor Space Ratio (FSR)", value=active_defaults["fsr"], step=0.1, key=f"fsr_{prod_type}")

buildable_sf = lot_size * fsr
st.info(f"📐 **Max Buildable:** {buildable_sf:,.0f} SF | ⏳ **Market Velocity:** {sell_months} Month Sell-Out Phase")

st.divider()

st.subheader("2. Financial Underwriting & Capital Stack")
f_col1, f_col2, f_col3 = st.columns(3)

with f_col1:
    st.markdown("**Revenue Targets**")
    sell_psf = cloud_input("Projected Sale Price ($/SF)", "land_residual", "sell_psf", step=50)
    profit_margin = cloud_input("Target Profit Margin (%)", "land_residual", "profit_margin", step=1.0)

with f_col2:
    st.markdown("**Costs & City Fees**")
    hard_cost_psf = st.number_input("Hard Costs ($/SF)", value=active_defaults["cost"], step=10, key=f"hc_{prod_type}")
    city_fees_psf = cloud_input("City Fees ($/SF)", "land_residual", "city_fees_psf", step=5.0)
    soft_cost_pct = cloud_input("Soft Costs (%)", "land_residual", "soft_cost_pct", step=1.0)

with f_col3:
    st.markdown("**Financing (Debt)**")
    finance_rate = cloud_input("Bank Loan Rate (%)", "land_residual", "finance_rate", step=0.25)
    ltc_pct = cloud_input("Loan-to-Cost (LTC) %", "land_residual", "ltc_pct", step=5.0)
    project_months = cloud_input("Build Duration (Months)", "land_residual", "project_months", step=1.0)
    st.caption(f"Interest calculated on {finance_rate}% (Prime + 2%)")

# --- 6. CALCULATIONS ---
gdv = buildable_sf * sell_psf
target_profit = gdv * (profit_margin / 100)
total_hard = buildable_sf * hard_cost_psf
total_city_fees = buildable_sf * city_fees_psf
total_soft = (total_hard * (soft_cost_pct / 100)) + total_city_fees
total_construction = total_hard + total_soft
finance_cost = (total_construction * 0.5) * (finance_rate / 100) * (project_months / 12)

# THE RESIDUAL FORMULA
residual_land_value = gdv - target_profit - total_construction - finance_cost

# CAPITAL STACK
total_project_cost = gdv - target_profit
bank_loan = total_project_cost * (ltc_pct / 100)
equity_required = total_project_cost - bank_loan
roe = (target_profit / equity_required) * 100 if equity_required > 0 else 0

# --- 7. RESULTS ---
st.divider()
st.subheader("📊 Acquisition Verdict")

if residual_land_value <= 0:
    st.error(f"⚠️ **Deal is Dead:** At these costs, the land has zero value. You must lower costs or increase sale prices.")
else:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Max Purchase Price", format_money(residual_land_value))
    m2.metric("Developer Equity", format_money(equity_required))
    m3.metric("Projected Profit", format_money(target_profit))
    m4.metric("ROE", f"{roe:.1f}%")

    # Add a visual "Residual Ladder" chart here in future...
    
show_disclaimer()
