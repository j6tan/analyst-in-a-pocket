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

# --- 4. BALANCED HEADER ---
st.title("🏗️ Land Residual Model") # Smaller title

prof = st.session_state.app_db.get('profile', {})
household = prof.get('p1_name', "Primary Client")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD};">
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 15px;">
        Welcome, <b>{household}</b>. We value land by calculating the <b>Residual</b>—the maximum price you can pay for a property while still hitting your profit targets.
    </p>
    
    <div style="background-color: white; padding: 15px; border-radius: 8px; border: 1px solid #eee; margin-bottom: 10px;">
        <h4 style="margin-top:0; color: {PRIMARY_GOLD}; font-size: 1em; text-transform: uppercase; letter-spacing: 1px;">The Residual Logic</h4>
        <p style="color: {SLATE_ACCENT}; font-size: 0.95em; margin-bottom: 5px;">
            <b>End Value</b> (Revenue) <br>
            <span style="color: #888;">minus</span> <b>Target Profit</b> (15%+) <br>
            <span style="color: #888;">minus</span> <b>Total Costs</b> (Hard + Soft + Finance) <br>
            <hr style="margin: 8px 0; border: 0; border-top: 1px solid #ddd;">
            <b>= MAX LAND PRICE</b>
        </p>
    </div>
</div>
""", unsafe_allow_html=True)



# --- 5. INPUTS ---
st.write("")
st.subheader("1. Site & Product Velocity")
z_col1, z_col2, z_col3 = st.columns(3)

with z_col1:
    lot_size = cloud_input("Lot Size (Sq.Ft.)", "land_residual", "lot_size", step=500)
with z_col2:
    prod_type = st.selectbox("Product Type", list(BUILD_DATA.keys()))
    active_defaults = BUILD_DATA[prod_type]
    sell_months = active_defaults["sell_months"]
with z_col3:
    fsr = st.number_input("Floor Space Ratio (FSR)", value=active_defaults["fsr"], step=0.1, key=f"fsr_{prod_type}")

buildable_sf = lot_size * fsr
st.info(f"📐 **Buildable:** {buildable_sf:,.0f} SF | ⏳ **Sales Velocity:** {sell_months} Month Sell-Out")

st.divider()

st.subheader("2. Underwriting & Financing")
f_col1, f_col2, f_col3 = st.columns(3)

with f_col1:
    sell_psf = cloud_input("Sale Price ($/SF)", "land_residual", "sell_psf", step=50)
    profit_margin = cloud_input("Profit Margin (%)", "land_residual", "profit_margin", step=1.0)

with f_col2:
    hard_cost_psf = st.number_input("Hard Costs ($/SF)", value=active_defaults["cost"], step=10, key=f"hc_{prod_type}")
    city_fees_psf = cloud_input("City Fees ($/SF)", "land_residual", "city_fees_psf", step=5.0)
    soft_cost_pct = cloud_input("Soft Costs (%)", "land_residual", "soft_cost_pct", step=1.0)

with f_col3:
    finance_rate = cloud_input("Loan Rate (%)", "land_residual", "finance_rate", step=0.25)
    ltc_pct = cloud_input("Loan-to-Cost %", "land_residual", "ltc_pct", step=5.0)
    project_months = cloud_input("Build Months", "land_residual", "project_months", step=1.0)

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
    st.error(f"⚠️ **Unviable Deal:** Land value is negative. High costs or low revenue are eating your profit.")
else:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Max Land Price", format_money(residual_land_value))
    m2.metric("Equity Needed", format_money(equity_required))
    m3.metric("Projected Profit", format_money(target_profit))
    m4.metric("ROE", f"{roe:.1f}%")

show_disclaimer()
