import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import time
import os
import base64
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

BUILD_DATA = {
    "Single Family (Custom)": {"fsr": 0.6, "cost": 450, "sell_months": 6},
    "Duplex / Semi-Detached": {"fsr": 0.8, "cost": 380, "sell_months": 6},
    "Multiplex / Missing Middle": {"fsr": 1.2, "cost": 320, "sell_months": 12},
    "Townhouse (Woodframe)": {"fsr": 1.4, "cost": 300, "sell_months": 12},
    "Mid-Rise Condo (Woodframe)": {"fsr": 2.5, "cost": 330, "sell_months": 18},
    "High-Rise Condo (Concrete)": {"fsr": 5.0, "cost": 450, "sell_months": 18},
    "Commercial / Mixed-Use": {"fsr": 3.0, "cost": 350, "sell_months": 18}
}

CITY_OPTIONS = {
    "BC": ["Vancouver", "Burnaby", "Surrey", "Richmond", "Coquitlam", "Langley", "New Westminster", "North Vancouver", "Victoria", "Kelowna", "Other"],
    "Ontario": ["Toronto", "Mississauga", "Brampton", "Ottawa", "Hamilton", "London", "Markham", "Vaughan", "Other"],
    "Alberta": ["Calgary", "Edmonton", "Red Deer", "Lethbridge", "Other"],
    "Manitoba": ["Winnipeg", "Brandon", "Other"],
    "Quebec": ["Montreal", "Quebec City", "Laval", "Gatineau", "Other"],
    "Nova Scotia": ["Halifax", "Dartmouth", "Other"],
    "New Brunswick": ["Moncton", "Fredericton", "Saint John", "Other"],
    "Saskatchewan": ["Saskatoon", "Regina", "Other"]
}

# Initialize new DB variables
if 'land_residual' not in st.session_state.app_db:
    st.session_state.app_db['land_residual'] = {}

defaults = {
    'pre_const_months': 12.0,
    'dcc_per_unit': 25000.0,
    'cac_per_unit': 15000.0,
    'regional_dcc_flat': 0.0,
    'dp_fee_flat': 25000.0,
    'bp_fee_pct': 1.5,
    'avg_unit_sf': 850.0,
    'soft_cost_pct': 10.0,
    'province': 'BC',
    'city': 'Vancouver'
}
for key, val in defaults.items():
    if key not in st.session_state.app_db['land_residual']:
        st.session_state.app_db['land_residual'][key] = val

# --- 4. INLINE LOGO & TITLE ---
def get_inline_logo(img_name="logo.png", width=75):
    # Check root directory first, then fallback to looking one folder up
    img_path = img_name
    if not os.path.exists(img_path):
        img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), img_name)
        
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{encoded}" style="width: {width}px; flex-shrink: 0;">'
    return "<span style='font-size: 50px;'>🔥</span>"

logo_html = get_inline_logo(width=75)

st.markdown(f"""
    <div style='display: flex; align-items: center; justify-content: flex-start; gap: 15px; margin-top: -20px; margin-bottom: 25px;'>
        {logo_html}
        <h1 style='margin: 0 !important; padding: 0 !important; line-height: 1 !important;'>Land Residual Model</h1>
    </div>
""", unsafe_allow_html=True)

prof = st.session_state.app_db.get('profile', {})
p1_name = prof.get('p1_name', "Investor")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD};">
    <p style="color: {SLATE_ACCENT}; font-size: 1.05em; line-height: 1.4; margin-bottom: 15px;">
        Welcome, <b>{p1_name}</b>. This tool determines the maximum price you can pay for land while protecting your target returns.
    </p>
    <div style="background-color: white; padding: 18px; border-radius: 8px; border: 1px solid #eee; margin-bottom: 5px;">
        <h4 style="margin-top:0; color: {PRIMARY_GOLD}; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 12px;">The Residual Logic</h4>
        <p style="color: {SLATE_ACCENT}; font-size: 0.95em; line-height: 1.6; margin-bottom: 0;">
            <b style="color: {CHARCOAL}; font-size: 1.05em;">Projected Gross Revenue</b><br>
            <span style="color: #6C757D; font-size: 0.9em;">Value as if you sold the completed project in today’s market</span><br>
            <span style="display: block; margin-top: 8px;"></span>
            <b style="color: {CHARCOAL}; font-size: 1.05em;">Less: Total Development Costs</b><br>
            <span style="color: #6C757D; font-size: 0.9em;">Including construction hard costs (material, labor, etc), soft costs (municipal and consulting fees), and interest on the loan</span><br>
            <span style="display: block; margin-top: 8px;"></span>
            <b style="color: {CHARCOAL}; font-size: 1.05em;">Less: Developer’s Profit</b><br>
            <span style="color: #6C757D; font-size: 0.9em;">Your required margin for taking on the risk (usually 15%-20% of gross revenue)</span><br>
            <hr style="margin: 12px 0; border: 0; border-top: 2px solid {PRIMARY_GOLD}; width: 60px;">
            <b style="color: {CHARCOAL}; font-size: 1.1em;">= Residual Land Value</b><br>
            <span style="color: #DC2626; font-size: 0.9em; font-weight: 500;">Whatever capital is left over is the true value of the dirt. Pay a dollar more, and it comes straight out of your profit.</span>
        </p>
    </div>
</div>
""", unsafe_allow_html=True)



# --- 5. INPUTS ---
st.write("")
st.subheader("1. Site & Highest and Best Use")

loc_c1, loc_c2 = st.columns(2)
with loc_c1:
    prov_opts = list(CITY_OPTIONS.keys())
    curr_prov = st.session_state.app_db['land_residual'].get('province', 'BC')
    idx = prov_opts.index(curr_prov) if curr_prov in prov_opts else 0
    province = st.selectbox("Province", prov_opts, index=idx)
    st.session_state.app_db['land_residual']['province'] = province

with loc_c2:
    city_opts = CITY_OPTIONS.get(province, ["Other"])
    curr_city = st.session_state.app_db['land_residual'].get('city', city_opts[0])
    city_idx = city_opts.index(curr_city) if curr_city in city_opts else 0
    city = st.selectbox("Municipality / City", city_opts, index=city_idx)
    st.session_state.app_db['land_residual']['city'] = city

z_col1, z_col2, z_col3, z_col4 = st.columns(4)
with z_col1:
    lot_size = cloud_input("Lot Size (Sq.Ft.)", "land_residual", "lot_size", step=500)
with z_col2:
    prod_type = st.selectbox("Product Type", list(BUILD_DATA.keys()))
    active_defaults = BUILD_DATA[prod_type]
    sell_months = active_defaults["sell_months"]
with z_col3:
    fsr = st.number_input("Floor Space Ratio (FSR)", value=active_defaults["fsr"], step=0.1, key=f"fsr_{prod_type}")
with z_col4:
    avg_unit_sf = cloud_input("Avg Unit Size (SF)", "land_residual", "avg_unit_sf", step=50.0)

buildable_sf = lot_size * fsr
est_units = buildable_sf / avg_unit_sf if avg_unit_sf > 0 else 0
st.info(f"📐 **Buildable:** {buildable_sf:,.0f} SF | 🏘️ **Est. Units:** {est_units:,.1f} | ⏳ **Sales Velocity:** {sell_months} Month Sell-Out")

st.divider()

# --- REVENUE ---
st.subheader("2. Revenue Projections")
r_col1, r_col2 = st.columns(2)
with r_col1:
    sell_psf = cloud_input("Projected Sale Price ($/SF)", "land_residual", "sell_psf", step=50)
with r_col2:
    profit_margin = cloud_input("Target Profit Margin (%)", "land_residual", "profit_margin", step=1.0)

# --- COSTS ---
st.write("")
st.subheader("3. Development Costs")

st.markdown("**Construction & Consulting**")
c_col1, c_col2 = st.columns(2)
with c_col1:
    hard_cost_psf = st.number_input("Hard Costs ($/SF)", value=active_defaults["cost"], step=10, key=f"hc_{prod_type}")
with c_col2:
    soft_cost_pct = cloud_input("Soft Costs (% of Hard Cost)", "land_residual", "soft_cost_pct", step=1.0)
    st.caption("Architecture, Engineering, Marketing, Legal (Excludes City Fees)")

st.markdown("**Municipal Levies & Permits**")
fee_c1, fee_c2, fee_c3 = st.columns(3)
with fee_c1:
    dcc_per_unit = cloud_input("Municipal DCC ($/Unit)", "land_residual", "dcc_per_unit", step=1000.0)
    regional_dcc_flat = cloud_input("Regional DCC (Total $)", "land_residual", "regional_dcc_flat", step=10000.0)
with fee_c2:
    cac_per_unit = cloud_input("ACC / CACs ($/Unit)", "land_residual", "cac_per_unit", step=1000.0)
    dp_fee_flat = cloud_input("DP Fee (Total $)", "land_residual", "dp_fee_flat", step=1000.0)
with fee_c3:
    bp_fee_pct = cloud_input("BP Fee (% of Hard Cost)", "land_residual", "bp_fee_pct", step=0.1)

st.markdown("""
<div style="background-color: #F8F9FA; padding: 15px; border-radius: 8px; border-left: 4px solid #4A4E5A; font-size: 0.9em; color: #4A4E5A; margin-top: 10px;">
    <b>ℹ️ Municipal Fee Guide:</b><br>
    • <b>DCCs (Development Cost Charges):</b> Fees collected by the municipality to pay for new roads, water, and sewer infrastructure. Look up your city's <i>"DCC Bylaw Schedule"</i>.<br>
    • <b>Regional DCCs:</b> Additional levies by regional bodies (e.g., Metro Vancouver or TransLink) for regional water/sewer/transit. Found on the regional district's website.<br>
    • <b>ACC/CACs (Amenity Cost Charges / Contributions):</b> Charges for parks, libraries, and daycares. Often triggered by rezoning. Check the city's <i>"Community Amenity Policy"</i>.<br>
    • <b>DP (Development Permit) & BP (Building Permit):</b> Application fees. DP is usually a flat base fee plus a minor area charge. BP is typically 1% to 2% of the estimated hard construction cost.
</div>
""", unsafe_allow_html=True)

# --- FINANCING ---
st.write("")
st.subheader("4. Financing")
f_col1, f_col2, f_col3, f_col4 = st.columns(4)
with f_col1:
    finance_rate = cloud_input("Loan Rate (%)", "land_residual", "finance_rate", step=0.25)
    st.markdown(f"<div style='margin-top:-12px; margin-bottom:12px; font-size:0.8em; color:#6C757D;'>Default: Prime + 2% ({current_prime + 2}%)</div>", unsafe_allow_html=True)
with f_col2:
    ltc_pct = cloud_input("Loan-to-Cost %", "land_residual", "ltc_pct", step=5.0)
with f_col3:
    pre_const_months = cloud_input("Pre-Build (Mo)", "land_residual", "pre_const_months", step=1.0)
with f_col4:
    project_months = cloud_input("Build (Mo)", "land_residual", "project_months", step=1.0)


# --- 6. CALCULATIONS ---
gdv = buildable_sf * sell_psf
target_profit = gdv * (profit_margin / 100)

total_hard = buildable_sf * hard_cost_psf
pure_soft_costs = total_hard * (soft_cost_pct / 100)

# Calculate City Fees based on inputs
total_dcc = est_units * dcc_per_unit
total_cac = est_units * cac_per_unit
total_regional_dcc = regional_dcc_flat
total_dp = dp_fee_flat
total_bp = total_hard * (bp_fee_pct / 100)

total_city_fees = total_dcc + total_cac + total_regional_dcc + total_dp + total_bp
total_soft_combined = pure_soft_costs + total_city_fees

pre_m = pre_const_months
build_m = project_months

# ADVANCED FINANCING LOGIC:
# Interest-only calculation using 60% average utilization during active draw phases
soft_interest = total_soft_combined * (finance_rate / 100) * ((pre_m / 12) * 0.6 + (build_m / 12))
hard_interest = total_hard * (finance_rate / 100) * ((build_m / 12) * 0.6)

finance_cost = soft_interest + hard_interest
total_construction = total_hard + total_soft_combined

residual_land_value = gdv - target_profit - total_construction - finance_cost

# Capital Stack
total_project_cost = gdv - target_profit
bank_loan = total_project_cost * (ltc_pct / 100)
equity_required = total_project_cost - bank_loan
roe = (target_profit / equity_required) * 100 if equity_required > 0 else 0


# --- 7. PRO FORMA (Moved Up) ---
st.divider()
st.subheader("📄 Full Pro Forma Breakdown")

df_pf = pd.DataFrame([
    {"Item": "Gross Development Value (GDV)", "Value": format_money(gdv)},
    {"Item": "(-) Target Profit", "Value": format_money(-target_profit)},
    {"Item": "(-) Hard Construction Costs", "Value": format_money(-total_hard)},
    {"Item": "(-) Consulting & Soft Costs", "Value": format_money(-pure_soft_costs)},
    {"Item": "(-) City Fees: Municipal DCCs", "Value": format_money(-total_dcc)},
    {"Item": "(-) City Fees: Regional DCCs", "Value": format_money(-total_regional_dcc)},
    {"Item": "(-) City Fees: ACC/CACs", "Value": format_money(-total_cac)},
    {"Item": "(-) City Fees: DP & BP Permits", "Value": format_money(-(total_dp + total_bp))},
    {"Item": f"(-) Financing Costs ({int(pre_m) + int(build_m)} Mo)", "Value": format_money(-finance_cost)},
    {"Item": "RESIDUAL LAND VALUE", "Value": format_money(residual_land_value)}
])
st.table(df_pf.set_index("Item"))


# --- 8. RESULTS / ACQUISITION VERDICT ---
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
    pre_m_int = int(pre_m)
    const_m_int = int(build_m)
    total_timeline = pre_m_int + const_m_int + sell_months
    
    monthly_soft = total_soft_combined / pre_m_int if pre_m_int > 0 else 0
    monthly_hard = total_hard / const_m_int if const_m_int > 0 else 0
    monthly_fin_pre = soft_interest / pre_m_int if pre_m_int > 0 else 0
    monthly_fin_const = hard_interest / const_m_int if const_m_int > 0 else 0
    monthly_rev = gdv / sell_months if sell_months > 0 else 0

    cf_months = [0]
    cumulative_cash = [-residual_land_value]
    
    for m in range(1, total_timeline + 1):
        if m <= pre_m_int:
            net = -(monthly_soft + monthly_fin_pre) 
        elif m <= pre_m_int + const_m_int:
            net = -(monthly_hard + monthly_fin_const) 
        else:
            net = monthly_rev 
            
        cf_months.append(m)
        cumulative_cash.append(cumulative_cash[-1] + net)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cf_months, y=cumulative_cash, fill='tozeroy', line=dict(color=PRIMARY_GOLD, width=3)))
    
    fig.add_vline(x=pre_m_int, line_dash="dash", line_color="gray", annotation_text="Permits Complete", annotation_position="top right")
    fig.add_vline(x=pre_m_int + const_m_int, line_dash="dash", line_color="gray", annotation_text="Build Complete", annotation_position="top right")
    
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
            t_hard_sens = buildable_sf * c
            t_bp_sens = t_hard_sens * (bp_fee_pct / 100)
            t_city_sens = total_dcc + total_cac + total_regional_dcc + total_dp + t_bp_sens
            t_soft_sens = (t_hard_sens * (soft_cost_pct/100)) + t_city_sens
            
            # Using 60% utilization for the sensitivity matrix as well
            s_int = t_soft_sens * (finance_rate / 100) * ((pre_m / 12) * 0.6 + (build_m / 12))
            h_int = t_hard_sens * (finance_rate / 100) * ((build_m / 12) * 0.6)
            
            rlv = (buildable_sf * s) - (buildable_sf * s * (profit_margin/100)) - t_hard_sens - t_soft_sens - s_int - h_int
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

show_disclaimer()

# --- FOOTER ---
st.markdown("""
    <div style="text-align: center; color: #adb5bd; font-size: 0.85em; margin-top: 50px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        &copy; 2026 FIRE Calculator. All rights reserved. <br>
        <span style="font-size: 0.9em; font-style: italic;">Empowering Canadian professionals to build wealth.</span>
    </div>
""", unsafe_allow_html=True)
