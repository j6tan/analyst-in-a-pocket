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

# --- 3. MARKET INTEL (Dynamic Velocity Mapping) ---
def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f: return json.load(f)
        except: pass
    return {}

intel = load_market_intel()
current_prime = intel.get("rates", {}).get("bank_prime", 4.45)
default_finance_rate = current_prime + 2.0

# UPDATED: Mapping sell-out velocity per your requirements
default_costs = {
    "Single Family (Custom)": {"fsr": 0.6, "cost": 400, "sell_months": 6},
    "Duplex": {"fsr": 0.8, "cost": 350, "sell_months": 6},
    "Multiplex / Missing Middle": {"fsr": 1.2, "cost": 320, "sell_months": 12},
    "Townhouse (Woodframe)": {"fsr": 1.4, "cost": 300, "sell_months": 12},
    "Mid-Rise Condo (Woodframe)": {"fsr": 2.5, "cost": 330, "sell_months": 18},
    "High-Rise Condo (Concrete)": {"fsr": 5.0, "cost": 420, "sell_months": 18},
    "Commercial / Retail": {"fsr": 3.0, "cost": 350, "sell_months": 18}
}
BUILD_COSTS = intel.get("build_costs", default_costs)

# --- 4. DATABASE INITIALIZATION ---
if 'app_db' not in st.session_state:
    st.session_state.app_db = {}

if 'land_residual' not in st.session_state.app_db:
    st.session_state.app_db['land_residual'] = {
        'lot_size': 6000,
        'sell_psf': 1100,
        'soft_cost_pct': 15.0,
        'city_fees_psf': 40.0,
        'profit_margin': 15.0,
        'finance_rate': default_finance_rate,
        'project_months': 24.0,
        'ltc_pct': 65.0
    }

prof = st.session_state.app_db.get('profile', {})
name1 = prof.get('p1_name') or "Primary Client"
name2 = prof.get('p2_name') or ""
household = f"{name1} and {name2}" if name2 else name1

# --- 5. STORYTELLING HEADER ---
st.title("🏗️ Land Residual Valuation")
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">📐 Strategic Brief: Highest & Best Use</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Welcome to the development lab, <b>{household}</b>. We determine the <b>Maximum Land Price</b> by accounting for all costs and your required profit margin.
        Velocity matters: our model now calculates interest and revenue flows based on your specific product type's sell-out window.
    </p>
</div>
""", unsafe_allow_html=True)


# --- 6. INPUTS ---
st.subheader("1. Zoning & Product Selection")
z_col1, z_col2, z_col3 = st.columns(3)

with z_col1:
    lot_size = cloud_input("Lot Size (Sq.Ft.)", "land_residual", "lot_size", step=500)
with z_col2:
    prod_type = st.selectbox("Proposed Product Type", list(BUILD_COSTS.keys()))
with z_col3:
    # FSR and Sell-Out auto-update based on selectbox
    default_fsr = BUILD_COSTS[prod_type].get("fsr", 1.0)
    sell_months = BUILD_COSTS[prod_type].get("sell_months", 12)
    fsr = st.number_input("Floor Space Ratio (FSR/FAR)", value=default_fsr, step=0.1)

buildable_sf = lot_size * fsr
st.info(f"📐 **Max Buildable Area:** {buildable_sf:,.0f} Sq.Ft. | ⏳ **Sales Velocity:** {sell_months} Month Sell-Out Phase")

st.divider()

st.subheader("2. Financial Underwriting")
f_col1, f_col2, f_col3 = st.columns(3)

with f_col1:
    st.markdown("**Revenue & Profit**")
    sell_psf = cloud_input("Projected Sale Price ($/SF)", "land_residual", "sell_psf", step=50)
    profit_margin = cloud_input("Target Profit Margin (%)", "land_residual", "profit_margin", step=1.0)

with f_col2:
    st.markdown("**Construction & Fees**")
    default_hard = BUILD_COSTS[prod_type].get("cost", 300)
    hard_cost_psf = st.number_input("Hard Costs ($/SF)", value=default_hard, step=10)
    
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
        st.caption(f"Prime + 2% (Current Prime: {current_prime}%)")
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

# Financing costs are heavily dependent on time
finance_cost = (total_construction * 0.5) * (finance_rate / 100) * (project_months / 12)

residual_land_value = gdv - target_profit - total_construction - finance_cost
rlv_per_buildable = residual_land_value / buildable_sf if buildable_sf > 0 else 0

total_project_cost = gdv - target_profit
bank_loan = total_project_cost * (ltc_pct / 100)
equity_required = total_project_cost - bank_loan
return_on_equity = (target_profit / equity_required) * 100 if equity_required > 0 else 0
equity_multiple = (target_profit + equity_required) / equity_required if equity_required > 0 else 0

# --- 8. CASH FLOW DYNAMICS ---
const_months = int(project_months)
total_timeline = const_months + sell_months # Now dynamically uses sell_months from the dict

monthly_const_spend = total_construction / const_months if const_months > 0 else 0
monthly_finance = finance_cost / const_months if const_months > 0 else 0 
monthly_revenue = gdv / sell_months if sell_months > 0 else 0

cf_months = [0]
cumulative_cash = [-residual_land_value] 

for m in range(1, total_timeline + 1):
    net_mo = 0
    if m <= const_months:
        net_mo -= (monthly_const_spend + monthly_finance) 
    if m > const_months:
        net_mo += monthly_revenue 
    
    cf_months.append(m)
    cumulative_cash.append(cumulative_cash[-1] + net_mo)

peak_exposure = min(cumulative_cash)

# --- 9. OUTPUT DASHBOARD ---
st.divider()
st.subheader("📊 The Verdict: Project Feasibility")

if residual_land_value <= 0:
    st.error(f"❌ **Project is unviable.** Under these assumptions, the land value is negative ({format_money(residual_land_value)}).")
else:
    # TOP LINE METRICS
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Max Land Price", format_money(residual_land_value))
    m2.metric("Cash Equity Required", format_money(equity_required))
    m3.metric("Projected Profit", format_money(target_profit))
    m4.metric("ROE", f"{return_on_equity:.1f}%")

    # S-CURVE CHART
    df_cf = pd.DataFrame({"Month": cf_months, "Cumulative Position": cumulative_cash})
    fig1 = go.Figure()
    fig1.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Break Even")
    fig1.add_trace(go.Scatter(
        x=df_cf["Month"], y=df_cf["Cumulative Position"], fill='tozeroy', mode='lines', 
        line=dict(color=PRIMARY_GOLD, width=3), fillcolor='rgba(206, 179, 111, 0.2)'
    ))
    fig1.add_annotation(
        x=const_months, y=peak_exposure, text=f"Peak Exposure: {format_money(peak_exposure)}",
        showarrow=True, arrowhead=2, arrowcolor=CHARCOAL, ax=-50, ay=-40, font=dict(color=DANGER_RED)
    )
    fig1.update_layout(title=f"Capital Timeline ({total_timeline} Months)", xaxis_title="Timeline (Months)", yaxis_title="Net Cash Position ($)", height=400, plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor="#E5E7EB"))
    st.plotly_chart(fig1, use_container_width=True)

    # RISK HEATMAP
    st.subheader("🌡️ Risk Matrix: Sale Price vs Hard Costs")
    sale_steps = [sell_psf - 100, sell_psf - 50, sell_psf, sell_psf + 50, sell_psf + 100]
    cost_steps = [hard_cost_psf - 20, hard_cost_psf - 10, hard_cost_psf, hard_cost_psf + 10, hard_cost_psf + 20]
    z_data, text_data = [], []
    for c in cost_steps:
        row, t_row = [], []
        for s in sale_steps:
            t_h = buildable_sf * c
            t_c = t_h + (t_h * (soft_cost_pct/100)) + (buildable_sf * city_fees_psf)
            rlv = (buildable_sf * s) - (buildable_sf * s * (profit_margin/100)) - t_c - ((t_c * 0.5) * (finance_rate/100) * (project_months/12))
            row.append(rlv)
            t_row.append(format_money(rlv))
        z_data.append(row)
        text_data.append(t_row)
    fig2 = go.Figure(data=go.Heatmap(z=z_data, x=[f"${s}/SF" for s in sale_steps], y=[f"${c}/SF" for c in cost_steps], colorscale="RdYlGn", text=text_data, texttemplate="%{text}"))
    fig2.update_layout(xaxis_title="Final Sale Price ($/SF)", yaxis_title="Hard Costs ($/SF)", height=400)
    st.plotly_chart(fig2, use_container_width=True)

    # PRO FORMA TABLE
    with st.expander("📄 View Detailed Pro Forma"):
        df_proforma = pd.DataFrame([
            {"Line Item": "Gross Development Value (GDV)", "Amount": f"${gdv:,.0f}"},
            {"Line Item": "Target Developer Profit", "Amount": f"-${target_profit:,.0f}"},
            {"Line Item": "Hard + Soft + City Fees", "Amount": f"-${total_construction:,.0f}"},
            {"Line Item": "Finance Costs", "Amount": f"-${finance_cost:,.0f}"},
            {"Line Item": "RESIDUAL LAND VALUE", "Amount": f"${residual_land_value:,.0f}"}
        ])
        st.table(df_proforma.set_index("Line Item"))

show_disclaimer()
