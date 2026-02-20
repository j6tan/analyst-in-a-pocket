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

# --- 3. DATABASE INITIALIZATION ---
if 'app_db' not in st.session_state:
    st.session_state.app_db = {}

if 'land_residual' not in st.session_state.app_db:
    st.session_state.app_db['land_residual'] = {
        'lot_size': 6000,
        'sell_psf': 1100,
        'soft_cost_pct': 20.0,
        'profit_margin': 15.0,
        'finance_rate': 7.5,
        'project_years': 2.0
    }

prof = st.session_state.app_db.get('profile', {})
name1 = prof.get('p1_name') or "Primary Client"
name2 = prof.get('p2_name') or ""
household = f"{name1} and {name2}" if name2 else name1

# --- 4. MARKET INTEL (Load from JSON with Sell-Out Periods) ---
def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f: return json.load(f)
        except: pass
    return {}

intel = load_market_intel()
# Includes the dynamic sell-out periods you requested
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
        By stripping away hard costs, soft costs, financing, and your target profit, we calculate the <b>Maximum Land Price</b>. Furthermore, our cash flow trajectory maps exactly when your capital is most exposed before project sell-out.
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
    # Auto-fill FSR based on product type, but allow override
    default_fsr = BUILD_COSTS[prod_type].get("fsr", 1.0)
    fsr = st.number_input("Floor Space Ratio (FSR/FAR)", value=default_fsr, step=0.1, help="Multiplier that determines max buildable square footage.")

buildable_sf = lot_size * fsr
st.info(f"📐 **Max Buildable Area:** {buildable_sf:,.0f} Sq.Ft. | ⏳ **Estimated Sell-Out:** {BUILD_COSTS[prod_type].get('sell_months', 12)} Months")

st.divider()

st.subheader("2. Financial Underwriting")
f_col1, f_col2, f_col3 = st.columns(3)

with f_col1:
    st.markdown("**Revenue Assumptions**")
    sell_psf = cloud_input("Projected Sale Price ($/SF)", "land_residual", "sell_psf", step=50)
    profit_margin = cloud_input("Target Profit Margin (%)", "land_residual", "profit_margin", step=1.0)
    st.caption(f"Industry standard: 15% - 20% of Gross Revenue")

with f_col2:
    st.markdown("**Construction Assumptions**")
    default_hard = BUILD_COSTS[prod_type].get("cost", 300)
    hard_cost_psf = st.number_input("Hard Costs ($/SF)", value=default_hard, step=10, help="Labor & materials. Industry averages.")
    soft_cost_pct = cloud_input("Soft Costs (%)", "land_residual", "soft_cost_pct", step=1.0)
    st.caption("Permits, DCCs, architects, marketing. % of Hard Costs.")

with f_col3:
    st.markdown("**Financing Assumptions**")
    finance_rate = cloud_input("Construction Loan Rate (%)", "land_residual", "finance_rate", step=0.5)
    project_years = cloud_input("Construction Duration (Years)", "land_residual", "project_years", step=0.5)
    st.caption("Time to build before sell-out phase begins.")

# --- 7. CALCULATIONS ---
# 1. Gross Realization
gdv = buildable_sf * sell_psf

# 2. Profit
target_profit = gdv * (profit_margin / 100)

# 3. Construction
total_hard = buildable_sf * hard_cost_psf
total_soft = total_hard * (soft_cost_pct / 100)
total_construction = total_hard + total_soft

# 4. Financing (Simplified linear draw assumption over construction period)
finance_cost = (total_construction * 0.5) * (finance_rate / 100) * project_years

# 5. The Residual Land Value
residual_land_value = gdv - target_profit - total_construction - finance_cost
rlv_per_buildable = residual_land_value / buildable_sf if buildable_sf > 0 else 0

# 6. Cash Flow Trajectory (S-Curve)
const_months = int(project_years * 12)
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
        net_mo -= (monthly_const_spend + monthly_finance) # Burning cash building
    if m > const_months:
        net_mo += monthly_revenue # Selling units
    
    cf_months.append(m)
    cumulative_cash.append(cumulative_cash[-1] + net_mo)

peak_exposure = min(cumulative_cash)

# --- 8. OUTPUT DASHBOARD ---
st.divider()
st.subheader("📊 The Verdict: Project Feasibility")

if residual_land_value <= 0:
    st.error(f"❌ **Project is unviable.** Under these assumptions, the land has negative value (${residual_land_value:,.0f}). You would need the seller to pay you to develop this lot.")
else:
    # Top Line Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Max Land Purchase Price", f"${residual_land_value/1000000:.2f}M", help=f"${residual_land_value:,.0f} exact")
    m2.metric("Peak Capital Exposure", f"${peak_exposure/1000000:.2f}M", delta="Max Cash/Debt Needed", delta_color="inverse")
    m3.metric("Projected Developer Profit", f"${target_profit/1000000:.2f}M", delta=f"{profit_margin}% Margin")
    m4.metric("Land Cost per Buildable SF", f"${rlv_per_buildable:,.0f}/SF")

    st.write("")
    
    # CUMULATIVE CASH FLOW CHART
    df_cf = pd.DataFrame({"Month": cf_months, "Cumulative Position": cumulative_cash})
    
    fig = go.Figure()
    
    # Add the zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Break Even", annotation_position="top left")
    
    # Add the trajectory area chart
    fig.add_trace(go.Scatter(
        x=df_cf["Month"], 
        y=df_cf["Cumulative Position"], 
        fill='tozeroy',
        mode='lines',
        name='Capital Position',
        line=dict(color=PRIMARY_GOLD, width=3),
        fillcolor='rgba(206, 179, 111, 0.2)'
    ))
    
    # Add Peak Exposure Marker
    fig.add_annotation(
        x=const_months,
        y=peak_exposure,
        text=f"Peak Exposure (-${abs(peak_exposure)/1000000:.1f}M)",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=2,
        arrowcolor=CHARCOAL,
        ax=-50,
        ay=-40,
        font=dict(color=DANGER_RED, size=12)
    )

    fig.update_layout(
        title=f"Cumulative Cash Flow Timeline ({total_months} Months)",
        xaxis_title="Timeline (Months)",
        yaxis_title="Net Capital Position ($)",
        height=450,
        margin=dict(t=50, b=40, l=0, r=0),
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(gridcolor="#E5E7EB"),
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Detailed Table
    with st.expander("📄 View Detailed Pro Forma"):
        df_proforma = pd.DataFrame([
            {"Line Item": "Gross Development Value (GDV)", "Amount": f"${gdv:,.0f}", "% of GDV": "100.0%"},
            {"Line Item": "Target Developer Profit", "Amount": f"-${target_profit:,.0f}", "% of GDV": f"{profit_margin:.1f}%"},
            {"Line Item": "Total Hard Costs", "Amount": f"-${total_hard:,.0f}", "% of GDV": f"{(total_hard/gdv)*100:.1f}%"},
            {"Line Item": "Total Soft Costs", "Amount": f"-${total_soft:,.0f}", "% of GDV": f"{(total_soft/gdv)*100:.1f}%"},
            {"Line Item": "Estimated Finance Costs", "Amount": f"-${finance_cost:,.0f}", "% of GDV": f"{(finance_cost/gdv)*100:.1f}%"},
            {"Line Item": "RESIDUAL LAND VALUE", "Amount": f"${residual_land_value:,.0f}", "% of GDV": f"{(residual_land_value/gdv)*100:.1f}%"}
        ])
        st.table(df_proforma.set_index("Line Item"))

show_disclaimer()
