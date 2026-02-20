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

# DYNAMIC CURRENCY FORMATTER
def format_money(val):
    sign = "-" if val < 0 else ""
    val = abs(val)
    if val >= 1_000_000:
        return f"{sign}${val/1_000_000:,.2f}M"
    else:
        return f"{sign}${val:,.0f}"

# --- 3. DATABASE INITIALIZATION ---
if 'app_db' not in st.session_state:
    st.session_state.app_db = {}

if 'land_residual' not in st.session_state.app_db:
    st.session_state.app_db['land_residual'] = {
        'lot_size': 6000,
        'sell_psf': 1100,
        'soft_cost_pct': 15.0,
        'city_fees_psf': 40.0, # NEW: City Fees
        'profit_margin': 15.0,
        'finance_rate': 7.5,
        'project_months': 24.0,
        'ltc_pct': 65.0 # NEW: Loan to Cost
    }

prof = st.session_state.app_db.get('profile', {})
name1 = prof.get('p1_name') or "Primary Client"
name2 = prof.get('p2_name') or ""
household = f"{name1} and {name2}" if name2 else name1

# --- 4. MARKET INTEL ---
def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f: return json.load(f)
        except: pass
    return {}

intel = load_market_intel()
default_costs = {
    "Single Family (Custom)": {"fsr": 0.6, "cost": 400, "sell_months": 6},
    "Multiplex / Missing Middle": {"fsr": 1.0, "cost": 320, "sell_months": 6},
    "Townhouse (Woodframe)": {"fsr": 1.2, "cost": 280, "sell_months": 12},
    "Mid-Rise Condo (Woodframe)": {"fsr": 2.5, "cost": 330, "sell_months": 18},
    "High-Rise Condo (Concrete)": {"fsr": 5.0, "cost": 420, "sell_months": 18},
    "Commercial / Retail": {"fsr": 3.0, "cost": 350, "sell_months": 18}
}
BUILD_COSTS = intel.get("build_costs", default_costs)

# --- 5. STORYTELLING HEADER ---
st.title("🏗️ Land Residual Valuation")
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">📐 Strategic Brief: Highest & Best Use</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Welcome to the development lab, <b>{household}</b>. The true value of dirt isn't based on what is sitting on it today—it's based on what you can build on it tomorrow. 
        By stripping away hard costs, city fees, financing, and your required profit, we calculate the <b>Maximum Land Price</b>. Review your capital stack and stress-test the deal in the sensitivity matrix below.
    </p>
</div>
""", unsafe_allow_html=True)


# --- 6. INPUTS ---
st.subheader("1. Zoning & Highest and Best Use")
z_col1, z_col2, z_col3 = st.columns(3)

with z_col1:
    lot_size = cloud_input("Lot Size (Sq.Ft.)", "land_residual", "lot_size", step=500)
with z_col2:
    prod_type = st.selectbox("Proposed Product Type", list(BUILD_COSTS.keys()))
with z_col3:
    default_fsr = BUILD_COSTS[prod_type].get("fsr", 1.0)
    fsr = st.number_input("Floor Space Ratio (FSR/FAR)", value=default_fsr, step=0.1, help="Multiplier that determines max buildable square footage.")

buildable_sf = lot_size * fsr
st.info(f"📐 **Max Buildable Area:** {buildable_sf:,.0f} Sq.Ft. | ⏳ **Estimated Sell-Out:** {BUILD_COSTS[prod_type].get('sell_months', 12)} Months")

st.divider()

st.subheader("2. Financial Underwriting")
f_col1, f_col2, f_col3 = st.columns(3)

with f_col1:
    st.markdown("**Revenue & Profit**")
    sell_psf = cloud_input("Projected Sale Price ($/SF)", "land_residual", "sell_psf", step=50)
    profit_margin = cloud_input("Target Profit Margin (%)", "land_residual", "profit_margin", step=1.0)
    st.caption(f"Margin based on Gross Development Value")

with f_col2:
    st.markdown("**Construction & Fees**")
    default_hard = BUILD_COSTS[prod_type].get("cost", 300)
    hard_cost_psf = st.number_input("Hard Costs ($/SF)", value=default_hard, step=10, help="Labor & materials. Industry averages.")
    
    # NEW: City Fees broken out from general soft costs
    c2_1, c2_2 = st.columns(2)
    with c2_1:
        city_fees_psf = cloud_input("City Fees ($/SF)", "land_residual", "city_fees_psf", step=5.0)
    with c2_2:
        soft_cost_pct = cloud_input("Soft Costs (%)", "land_residual", "soft_cost_pct", step=1.0)
    st.caption("City Fees (DCCs/CACs) + General Soft Costs (% of Hard Costs)")

with f_col3:
    st.markdown("**Capital Stack**")
    c3_1, c3_2 = st.columns(2)
    with c3_1:
        finance_rate = cloud_input("Bank Loan Rate (%)", "land_residual", "finance_rate", step=0.5)
    with c3_2:
        ltc_pct = cloud_input("Loan-to-Cost (LTC) %", "land_residual", "ltc_pct", step=5.0)
    project_months = cloud_input("Construction Duration (Months)", "land_residual", "project_months", step=1.0)
    st.caption("LTC determines how much Developer Cash is required.")

# --- 7. CALCULATIONS ---
# 1. Gross Realization
gdv = buildable_sf * sell_psf

# 2. Profit
target_profit = gdv * (profit_margin / 100)

# 3. Construction
total_hard = buildable_sf * hard_cost_psf
total_city_fees = buildable_sf * city_fees_psf
total_soft = (total_hard * (soft_cost_pct / 100)) + total_city_fees
total_construction = total_hard + total_soft

# 4. Financing
finance_cost = (total_construction * 0.5) * (finance_rate / 100) * (project_months / 12)

# 5. The Residual Land Value
residual_land_value = gdv - target_profit - total_construction - finance_cost
rlv_per_buildable = residual_land_value / buildable_sf if buildable_sf > 0 else 0

# 6. Capital Stack (Equity vs Debt)
total_project_cost = gdv - target_profit # Total Cost equals Land + Hard + Soft + Finance
bank_loan = total_project_cost * (ltc_pct / 100)
equity_required = total_project_cost - bank_loan
return_on_equity = (target_profit / equity_required) * 100 if equity_required > 0 else 0
equity_multiple = (target_profit + equity_required) / equity_required if equity_required > 0 else 0

# 7. Cash Flow Trajectory (S-Curve)
const_months = int(project_months)
sell_months = BUILD_COSTS[prod_type].get("sell_months", 12)
total_months = const_months + sell_months

monthly_const_spend = total_construction / const_months if const_months > 0 else 0
monthly_finance = finance_cost / const_months if const_months > 0 else 0 
monthly_revenue = gdv / sell_months if sell_months > 0 else 0

cf_months = [0]
cumulative_cash = [-residual_land_value] # Month 0 is buying the dirt

for m in range(1, total_months + 1):
    net_mo = 0
    if m <= const_months:
        net_mo -= (monthly_const_spend + monthly_finance) 
    if m > const_months:
        net_mo += monthly_revenue 
    
    cf_months.append(m)
    cumulative_cash.append(cumulative_cash[-1] + net_mo)

peak_exposure = min(cumulative_cash)

# --- 8. OUTPUT DASHBOARD ---
st.divider()
st.subheader("📊 The Verdict: Project Feasibility")

if residual_land_value <= 0:
    st.error(f"❌ **Project is unviable.** Under these assumptions, the land has negative value ({format_money(residual_land_value)}). You would need the seller to pay you to develop this lot.")
else:
    # --- METRICS ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Max Land Purchase Price", format_money(residual_land_value), help=f"${residual_land_value:,.0f} exact")
    m2.metric("Developer Cash Required", format_money(equity_required), delta=f"Based on {ltc_pct}% Bank LTC", delta_color="off")
    m3.metric("Projected Developer Profit", format_money(target_profit), delta=f"{profit_margin}% Margin")
    m4.metric("Return on Equity (ROE)", f"{return_on_equity:.1f}%", help=f"Equity Multiple: {equity_multiple:.2f}x")

    st.write("")
    
    # --- CUMULATIVE CASH FLOW CHART ---
    df_cf = pd.DataFrame({"Month": cf_months, "Cumulative Position": cumulative_cash})
    fig1 = go.Figure()
    fig1.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Break Even", annotation_position="top left")
    fig1.add_trace(go.Scatter(
        x=df_cf["Month"], y=df_cf["Cumulative Position"], fill='tozeroy', mode='lines', name='Capital Position',
        line=dict(color=PRIMARY_GOLD, width=3), fillcolor='rgba(206, 179, 111, 0.2)'
    ))
    fig1.add_annotation(
        x=const_months, y=peak_exposure, text=f"Peak Capital Needed: {format_money(peak_exposure)}",
        showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor=CHARCOAL,
        ax=-50, ay=-40, font=dict(color=DANGER_RED, size=12)
    )
    fig1.update_layout(
        title=f"Capital Exposure Timeline ({total_months} Months)",
        xaxis_title="Timeline (Months)", yaxis_title="Net Capital Position ($)",
        height=400, margin=dict(t=50, b=40, l=0, r=0), plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(gridcolor="#E5E7EB"), hovermode="x unified"
    )
    st.plotly_chart(fig1, use_container_width=True)

    # --- SENSITIVITY MATRIX (THE HEATMAP) ---
    st.subheader("🌡️ Risk Matrix: Sale Price vs Hard Costs")
    st.caption("How much is the land worth if construction costs inflate or market prices drop?")
    
    # Generate 5x5 grid of variations
    sale_steps = [sell_psf - 100, sell_psf - 50, sell_psf, sell_psf + 50, sell_psf + 100]
    cost_steps = [hard_cost_psf - 20, hard_cost_psf - 10, hard_cost_psf, hard_cost_psf + 10, hard_cost_psf + 20]
    
    z_data = []
    text_data = []
    for c in cost_steps:
        row = []
        t_row = []
        for s in sale_steps:
            # Recalculate everything for this specific cell
            t_h = buildable_sf * c
            t_s = (t_h * (soft_cost_pct/100)) + (buildable_sf * city_fees_psf)
            t_c = t_h + t_s
            f_c = (t_c * 0.5) * (finance_rate/100) * (project_months/12)
            g = buildable_sf * s
            p = g * (profit_margin/100)
            rlv = g - p - t_c - f_c
            row.append(rlv)
            t_row.append(format_money(rlv))
        z_data.append(row)
        text_data.append(t_row)
        
    fig2 = go.Figure(data=go.Heatmap(
        z=z_data,
        x=[f"${s}/SF" for s in sale_steps],
        y=[f"${c}/SF" for c in cost_steps],
        colorscale="RdYlGn",
        text=text_data,
        texttemplate="%{text}",
        hoverinfo="skip"
    ))
    
    fig2.update_layout(
        xaxis_title="Final Sale Price ($/SF)",
        yaxis_title="Hard Construction Costs ($/SF)",
        height=400,
        margin=dict(t=20, b=40, l=0, r=0)
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Detailed Table
    with st.expander("📄 View Detailed Pro Forma"):
        df_proforma = pd.DataFrame([
            {"Line Item": "Gross Development Value (GDV)", "Amount": f"${gdv:,.0f}", "% of GDV": "100.0%"},
            {"Line Item": "Target Developer Profit", "Amount": f"-${target_profit:,.0f}", "% of GDV": f"{profit_margin:.1f}%"},
            {"Line Item": "Total Hard Costs", "Amount": f"-${total_hard:,.0f}", "% of GDV": f"{(total_hard/gdv)*100:.1f}%"},
            {"Line Item": "City Fees (DCCs/CACs)", "Amount": f"-${total_city_fees:,.0f}", "% of GDV": f"{(total_city_fees/gdv)*100:.1f}%"},
            {"Line Item": "General Soft Costs", "Amount": f"-${(total_soft - total_city_fees):,.0f}", "% of GDV": f"{((total_soft - total_city_fees)/gdv)*100:.1f}%"},
            {"Line Item": "Estimated Finance Costs", "Amount": f"-${finance_cost:,.0f}", "% of GDV": f"{(finance_cost/gdv)*100:.1f}%"},
            {"Line Item": "RESIDUAL LAND VALUE", "Amount": f"${residual_land_value:,.0f}", "% of GDV": f"{(residual_land_value/gdv)*100:.1f}%"}
        ])
        st.table(df_proforma.set_index("Line Item"))

show_disclaimer()
