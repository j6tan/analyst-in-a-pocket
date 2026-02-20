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
DANGER_RED = "#DC2626"

def format_money(val):
    sign = "-" if val < 0 else ""
    val = abs(val)
    if val >= 1_000_000: return f"{sign}${val/1_000_000:,.2f}M"
    return f"{sign}${val:,.0f}"

# --- 3. MARKET INTEL & VELOCITY MAPPING ---
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

# Fixed velocity rules per your requirements: 
# single/duplex (6mo), multiple/townhouse (12mo), condo/high-rise (18mo)
BUILD_DATA = {
    "Single Family (Custom)": {"fsr": 0.6, "cost": 450, "sell_months": 6},
    "Duplex / Semi-Detached": {"fsr": 0.8, "cost": 380, "sell_months": 6},
    "Multiplex / Missing Middle": {"fsr": 1.2, "cost": 320, "sell_months": 12},
    "Townhouse (Woodframe)": {"fsr": 1.4, "cost": 300, "sell_months": 12},
    "Mid-Rise Condo (Woodframe)": {"fsr": 2.5, "cost": 330, "sell_months": 18},
    "High-Rise Condo (Concrete)": {"fsr": 5.0, "cost": 450, "sell_months": 18},
    "Commercial / Mixed-Use": {"fsr": 3.0, "cost": 350, "sell_months": 18}
}

# --- 4. BALANCED HEADER ---
st.title("🏗️ Land Residual Model")

prof = st.session_state.app_db.get('profile', {})
p1_name = prof.get('p1_name', "Dori")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD};">
    <p style="color: {SLATE_ACCENT}; font-size: 1.05em; line-height: 1.4; margin-bottom: 15px;">
        Welcome, <b>{p1_name}</b>. This tool determines the maximum price you can pay for land while protecting your target returns.
    </p>
    
    <div style="background-color: white; padding: 18px; border-radius: 8px; border: 1px solid #eee; margin-bottom: 5px;">
        <h4 style="margin-top:0; color: {PRIMARY_GOLD}; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 12px;">The Residual Logic</h4>
        <p style="color: {SLATE_ACCENT}; font-size: 1em; line-height: 1.8; margin-bottom: 0;">
            <b>End Value</b> (Total Projected Revenue) <br>
            <span style="color: #A0A0A0; font-size: 0.85em;">&mdash; MINUS &mdash;</span> <b>Target Profit</b> (Your Required Yield) <br>
            <span style="color: #A0A0A0; font-size: 0.85em;">&mdash; MINUS &mdash;</span> <b>Development Costs</b> (Hard, Soft & Finance) <br>
            <hr style="margin: 10px 0; border: 0; border-top: 2px solid {PRIMARY_GOLD}; width: 50px;">
            <b style="color: {CHARCOAL}; font-size: 1.1em;">= MAXIMUM LAND PURCHASE PRICE</b>
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
    # Key update forces reset when home type changes
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
    # FIXED Syntax Error here: f"hc_{prod_type}"
    hard_cost_psf = st.number_input("Hard Costs ($/SF)", value=active_defaults["cost"], step=10, key=f"hc_{prod_type}")
    city_fees_psf = cloud_input("City Fees ($/SF)", "land_residual", "city_fees_psf", step=5.0)
    soft_cost_pct = cloud_input("Soft Costs (%)", "land_residual", "soft_cost_pct", step=1.0)

with f_col3:
    finance_rate = cloud_input("Loan Rate (%)", "land_residual", "finance_rate", step=0.25)
    st.caption(f"Bank Prime + 2% Rate: {current_prime + 2}%")
    ltc_pct = cloud_input("Loan-to-Cost %", "land_residual", "ltc_pct", step=5.0)
    project_months = cloud_input("Build Duration (Months)", "land_residual", "project_months", step=1.0)

# --- 6. CALCULATIONS ---
gdv = buildable_sf * sell_psf
target_profit = gdv * (profit_margin / 100)
total_hard = buildable_sf * hard_cost_psf
total_city_fees = buildable_sf * city_fees_psf
total_soft = (total_hard * (soft_cost_pct / 100)) + total_city_fees
total_construction = total_hard + total_soft

# Finance costs on average draw
finance_cost = (total_construction * 0.5) * (finance_rate / 100) * (project_months / 12)

residual_land_value = gdv - target_profit - total_construction - finance_cost

# Capital Stack
total_project_cost = gdv - target_profit
bank_loan = total_project_cost * (ltc_pct / 100)
equity_required = total_project_cost - bank_loan
roe = (target_profit / equity_required) * 100 if equity_required > 0 else 0

# --- 7. RESULTS ---
st.divider()
st.subheader("📊 Acquisition Verdict")

if residual_land_value <= 0:
    st.error(f"⚠️ **Unviable Deal:** Land value is negative ({format_money(residual_land_value)}). Costs exceed revenue.")
else:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Max Land Price", format_money(residual_land_value))
    m2.metric("Equity Needed", format_money(equity_required))
    m3.metric("Projected Profit", format_money(target_profit))
    m4.metric("ROE", f"{roe:.1f}%")

    # --- S-CURVE CASH FLOW ---
    const_months = int(project_months)
    total_timeline = const_months + sell_months
    monthly_rev = gdv / sell_months if sell_months > 0 else 0
    monthly_out = (total_construction + finance_cost) / const_months if const_months > 0 else 0

    cf_months = [0]
    cumulative_cash = [-residual_land_value]
    for m in range(1, total_timeline + 1):
        net = -monthly_out if m <= const_months else monthly_rev
        cf_months.append(m)
        cumulative_cash.append(cumulative_cash[-1] + net)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cf_months, y=cumulative_cash, fill='tozeroy', line=dict(color=PRIMARY_GOLD, width=3)))
    fig.update_layout(title=f"Capital Timeline ({total_timeline} Months)", xaxis_title="Timeline (Months)", height=350, plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

    # --- SENSITIVITY HEATMAP ---
    st.subheader("🌡️ Risk Matrix: Price vs Cost Sensitivity")
    sale_steps = [sell_psf * 0.9, sell_psf * 0.95, sell_psf, sell_psf * 1.05, sell_psf * 1.1]
    cost_steps = [hard_cost_psf * 0.9, hard_cost_psf * 0.95, hard_cost_psf, hard_cost_psf * 1.05, hard_cost_psf * 1.1]
    
    z_data, text_data = [], []
    for c in cost_steps:
        row, t_row = [], []
        for s in sale_steps:
            t_const = (buildable_sf * c) + (buildable_sf * c * (soft_cost_pct/100)) + total_city_fees
            rlv = (buildable_sf * s) - (buildable_sf * s * (profit_margin/100)) - t_const - (t_const * 0.5 * (finance_rate/100) * (project_months/12))
            row.append(rlv)
            t_row.append(format_money(rlv))
        z_data.append(row)
        text_data.append(t_row)

    fig2 = go.Figure(data=go.Heatmap(
        z=z_data, x=[f"${s:,.0f}" for s in sale_steps], y=[f"${c:,.0f}" for c in cost_steps],
        colorscale="RdYlGn", text=text_data, texttemplate="%{text}", hoverinfo="text"
    ))
    fig2.update_layout(xaxis_title="Final Sale Price ($/SF)", yaxis_title="Hard Costs ($/SF)", height=450)
    st.plotly_chart(fig2, use_container_width=True)

    # --- DETAILED PRO FORMA ---
    with st.expander("📄 Full Pro Forma Breakdown"):
        df_pf = pd.DataFrame([
            {"Item": "Gross Development Value (GDV)", "Value": format_money(gdv)},
            {"Item": "(-) Target Profit", "Value": format_money(-target_profit)},
            {"Item": "(-) Hard Construction Costs", "Value": format_money(-total_hard)},
            {"Item": "(-) Soft Costs & Fees", "Value": format_money(-total_soft)},
            {"Item": "(-) Financing Costs", "Value": format_money(-finance_cost)},
            {"Item": "RESIDUAL LAND VALUE", "Value": format_money(residual_land_value)}
        ])
        st.table(df_pf.set_index("Item"))

show_disclaimer()
