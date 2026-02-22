import streamlit as st
import pandas as pd
import os
import base64
import json
import math
import time
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, load_user_data, init_session_state, supabase

# --- 1. UNIVERSAL AUTO-LOADER (The Fix for Blank Pages) ---
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

# --- 1. THEME & STYLING ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
CRIMSON_RED = "#A52A2A"
DARK_GREEN = "#1B4D3E"

def custom_round_up(n):
    if n <= 0: return 0.0
    digits = int(math.log10(n)) + 1
    step = {1:10, 2:10, 3:10, 4:100, 5:100, 6:1000, 7:10000}.get(digits, 50000)
    return float(math.ceil(n / step) * step)

# --- 2. DATA RETRIEVAL ---
prof = st.session_state.app_db.get('profile', {})
current_res_prov = prof.get('province', 'BC')
p1_name = prof.get('p1_name', 'Primary Client')
p2_name = prof.get('p2_name', '')

def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f: return json.load(f)
    return {"rates": {"five_year_fixed_uninsured": 4.26}, "provincial_yields": {"BC": 3.8}}

intel = load_market_intel()

# --- 3. PERSISTENCE ---
if 'affordability_second' not in st.session_state.app_db:
    st.session_state.app_db['affordability_second'] = {}
aff_sec = st.session_state.app_db['affordability_second']

# Initialize defaults if empty
if aff_sec.get('target_price', 0) == 0:
    aff_sec.update({"down_payment": 200000, "target_price": 600000, "contract_rate": 4.26, "manual_rent": 2500, "vacancy_months": 1.0, "annual_prop_tax": 3000, "strata_mo": 400, "insurance_mo": 100, "rm_mo": 150, "asset_province": current_res_prov, "use_case": "Rental Property", "mgmt_pct": 5.0, "is_vanc": False})

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
        <h1 style='margin: 0 !important; padding: 0 !important; line-height: 1 !important;'>The Portfolio Expansion Map</h1>
    </div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 20px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">🏢 Strategic Brief: Capital Deployment</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        <b>{p1_name} {f'and {p2_name}' if p2_name else ''}</b> are evaluating the next step. 
        Whether deploying into a <b>self-sustaining rental asset</b> or a <b>vacation home</b>, 
        this map determines viability within your household ecosystem.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. SELECTORS ---
ts_col1, ts_col2 = st.columns(2)
with ts_col1:
    prov_options = ["BC", "Alberta", "Ontario", "Manitoba", "Quebec", "Saskatchewan", "Nova Scotia", "New Brunswick"]
    asset_province = st.selectbox("Asset Location (Province):", options=prov_options, index=prov_options.index(aff_sec.get('asset_province', current_res_prov)), key="affordability_second:asset_province", on_change=sync_widget, args=("affordability_second:asset_province",))
with ts_col2:
    use_case = st.selectbox("Use of the Second Home:", ["Rental Property", "Family Vacation Home"], index=0 if aff_sec.get('use_case') == "Rental Property" else 1, key="affordability_second:use_case", on_change=sync_widget, args=("affordability_second:use_case",))
    is_rental = True if use_case == "Rental Property" else False

# --- 6. CORE CALCULATION PREP ---
def get_f(k, d=0.0):
    try: return float(prof.get(k, d))
    except: return d

m_inc = (get_f('p1_t4') + get_f('p1_bonus') + get_f('p2_t4') + get_f('p2_bonus') + (get_f('inv_rental_income') * 0.80)) / 12
m_bal = get_f('m_bal')
m_rate_p = (get_f('m_rate', 4.0) / 100) / 12
primary_mtg = (m_bal * m_rate_p) / (1 - (1 + m_rate_p)**-300) if m_bal > 0 else 0
primary_carrying = (get_f('prop_taxes', 4200) / 12) + get_f('heat_pmt', 125)
p_debts = get_f('car_loan') + get_f('student_loan') + get_f('cc_pmt') + (get_f('loc_balance') * 0.03)

# --- 7. INPUTS ---
st.divider()
c_left, c_right = st.columns(2)

with c_left:
    st.subheader("💰 Capital Requirement")
    f_dp = cloud_input("Available Down Payment ($)", "affordability_second", "down_payment", step=5000)
    f_price = cloud_input("Purchase Price ($)", "affordability_second", "target_price", step=5000)

    # --- LIVE MAX QUALIFYING POWER ---
    calc_rate = float(aff_sec.get('contract_rate', 4.26))
    calc_rent = float(aff_sec.get('manual_rent', 0.0))
    stress_rate = max(5.25, calc_rate + 2.0)
    r_stress = (stress_rate / 100) / 12
    stress_k = (r_stress * (1 + r_stress)**300) / ((1 + r_stress)**300 - 1)
    
    rent_offset = (calc_rent * 0.80) if is_rental else 0
    qual_room = (m_inc * 0.44) + rent_offset - primary_mtg - primary_carrying - p_debts - (float(aff_sec.get('annual_prop_tax', 0)) / 12)
    
    max_by_income = (qual_room / stress_k) + f_dp if qual_room > 0 else f_dp
    max_by_dp = f_dp / 0.20
    max_buying_power = custom_round_up(min(max_by_income, max_by_dp))
    limit_reason = "Income Test" if max_by_income < max_by_dp else "20% Down Payment rule"

    st.markdown(f"""
        <div style="background-color: #E9ECEF; padding: 12px; border-radius: 8px; border: 1px solid #DEE2E6; margin-top: 10px; margin-bottom: 20px;">
            <p style="margin: 0; font-size: 0.8em; color: {SLATE_ACCENT}; font-weight: bold;">Max Qualified Buying Power</p>
            <p style="margin: 0; font-size: 1.4em; color: {SLATE_ACCENT}; font-weight: 800;">${max_buying_power:,.0f}</p>
            <p style="margin: 0; font-size: 0.75em; color: #6C757D;">Limited by: <b>{limit_reason}</b></p>
        </div>
    """, unsafe_allow_html=True)

    f_rate = cloud_input("Mortgage Contract Rate (%)", "affordability_second", "contract_rate", step=0.1)
    if is_rental:
        f_rent = cloud_input("Monthly Projected Rent ($)", "affordability_second", "manual_rent", step=100)
        f_vacancy = cloud_input("Vacancy (no. of months)", "affordability_second", "vacancy_months", step=1)
    else: f_rent, f_vacancy = 0, 0

with c_right:
    st.subheader("🏙️ Carrying Costs")
    f_tax = cloud_input("Annual Property Tax ($)", "affordability_second", "annual_prop_tax", step=100)
    f_strata = cloud_input("Monthly Strata ($)", "affordability_second", "strata_mo", step=10)
    f_ins = cloud_input("Monthly Insurance ($)", "affordability_second", "insurance_mo", step=10)
    f_rm = cloud_input("Repairs & Maintenance (Monthly)", "affordability_second", "rm_mo", step=10)
    bc_extra = 0
    if asset_province == "BC" and not is_rental:
        st.markdown("---")
        vanc_check = st.checkbox("Property in Vancouver?", value=aff_sec.get('is_vanc', False), key="affordability_second:is_vanc", on_change=sync_widget, args=("affordability_second:is_vanc",))
        bc_extra = ((f_price * 0.005) + (f_price * 0.03 if vanc_check else 0)) / 12

    mgmt_fee = (f_rent * (st.slider("Mgmt Fee %", 0.0, 12.0, float(aff_sec.get('mgmt_pct', 5.0)), key="affordability_second:mgmt_pct", on_change=sync_widget, args=("affordability_second:mgmt_pct",)) / 100)) if is_rental else 0
    total_opex_mo = (f_tax / 12) + f_strata + f_ins + f_rm + bc_extra + mgmt_fee

# --- 9. ANALYSIS ---
target_loan = max(0, f_price - f_dp)
r_contract = (f_rate / 100) / 12
new_p_i = (target_loan * r_contract) / (1 - (1 + r_contract)**-300) if target_loan > 0 else 0
realized_rent = (f_rent * (12 - f_vacancy)) / 12 if is_rental else 0
asset_net = realized_rent - total_opex_mo - new_p_i
net_h_inc = (get_f('p1_t4') + get_f('p1_bonus') + get_f('p2_t4') + get_f('p2_bonus') + get_f('inv_rental_income')) * 0.75 / 12
overall_cash_flow = (net_h_inc + realized_rent) - (primary_mtg + primary_carrying + p_debts + new_p_i + total_opex_mo)
safety_margin = (overall_cash_flow / (net_h_inc + realized_rent) * 100) if (net_h_inc + realized_rent) > 0 else 0

st.subheader("📝 Monthly Cash Flow Breakdown")
col_b1, col_b2 = st.columns(2)
with col_b1:
    st.markdown("**Household Ecosystem**")
    st.table(pd.DataFrame([{"Item": "Net Household Income", "Amount": f"${net_h_inc:,.0f}"}, {"Item": "Primary Home & Debts", "Amount": f"-${primary_mtg + primary_carrying + p_debts:,.0f}"}, {"Item": "Monthly Surplus", "Amount": f"${net_h_inc - (primary_mtg + primary_carrying + p_debts):,.0f}"}]))
with col_b2:
    st.markdown("**Secondary Asset Impact**")
    st.table(pd.DataFrame([{"Item": "Realized Rent", "Amount": f"${realized_rent:,.0f}"}, {"Item": "OpEx & New Mortgage", "Amount": f"-${total_opex_mo + new_p_i:,.0f}"}, {"Item": "Net Asset Cash Flow", "Amount": f"${asset_net:,.0f}"}]))

st.divider()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Asset Net Cash", f"${asset_net:,.0f}/mo", delta=None)
m2.metric("Cash-on-Cash", f"{(asset_net * 12 / f_dp * 100) if f_dp > 0 else 0:.1f}%")
m3.metric("Safety Margin", f"{safety_margin:.1f}%")
m4.metric("Overall Surplus", f"${overall_cash_flow:,.0f}")

# --- 11. STRATEGIC VERDICT ---
st.subheader("🎯 Strategic Verdict & Resilience Analysis")

b_data = st.session_state.app_db.get('budget', {})
lifestyle_spend = sum([b_data.get(k, 0.0) for k in ['groceries', 'dining', 'childcare', 'pets', 'gas_transit', 'car_ins_maint', 'utilities', 'shopping', 'entertainment', 'health', 'misc']])
true_net = overall_cash_flow - lifestyle_spend
household_expense_ratio = ((primary_mtg + primary_carrying + p_debts + lifestyle_spend + new_p_i + total_opex_mo) / (net_h_inc + realized_rent)) * 100

is_neg_carry = is_rental and asset_net < 0
is_unsustainable = overall_cash_flow < 0
is_lifestyle_deficit = true_net < 0

if is_unsustainable:
    v_status, v_color, v_bg = "❌ Critical Risk: Financial Overexposure", "#dc2626", "#FEF2F2"
    v_insight = "Fixed debts exceed income. Lender rejection is highly likely."
elif is_lifestyle_deficit:
    v_status, v_color, v_bg = "⚠️ Lifestyle Risk: House Poor Warning", "#ca8a04", "#FFFBEB"
    v_insight = f"Bank approved, but you must cut ${abs(true_net):,.0f}/mo from personal spending to avoid a deficit."
elif is_neg_carry:
    v_status, v_color, v_bg = "🟡 Strategic Play: Negative Carry", "#4A4E5A", "#F8F9FA"
    v_insight = "Asset loses cash monthly. This is a pure growth play requiring personal subsidy."
else:
    v_status, v_color, v_bg = "✅ Wealth Accelerator: High Resilience", "#16a34a", "#F0FDF4"
    v_insight = "Acquisition fits comfortably within income, debt, and lifestyle targets."

ratio_text_color = "#dc2626" if household_expense_ratio > 80 else "#16a34a"

st.markdown(f"""
<div style='background-color: {v_bg}; padding: 25px; border-radius: 12px; border: 2px solid {v_color}; color: #2E2B28;'>
    <h4 style='color: {v_color}; margin-top: 0; font-size: 1.3em;'>{v_status}</h4>
    <p style='font-size: 1.1em; font-weight: 500;'>{v_insight}</p>
    <hr style='border: 0; border-top: 1px solid #ddd; margin: 15px 0;'>
    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 20px;'>
        <div>
            <p style='margin: 0; font-size: 0.85em; color: #666;'>TRUE NET POSITION</p>
            <p style='margin: 0; font-size: 1.4em; font-weight: bold; color: {'#dc2626' if true_net < 0 else '#16a34a'};'>${true_net:,.0f}<small>/mo</small></p>
            <p style='margin: 5px 0; font-size: 0.8em; color: #666;'>Actual 'take home' after all debts and lifestyle costs.</p>
        </div>
        <div>
            <p style='margin: 0; font-size: 0.85em; color: #666;'>TOTAL EXPENSE RATIO</p>
            <p style='margin: 0; font-size: 1.4em; font-weight: bold; color: {ratio_text_color};'>{household_expense_ratio:.1f}%</p>
            <p style='margin: 5px 0; font-size: 0.85em; font-weight: 600; color: {ratio_text_color};'>
                { "High Risk: Above 80%" if household_expense_ratio > 80 else "Healthy: Below 80%"}
            </p>
            <p style='margin: 0; font-size: 0.8em; color: #6C757D;'>Ideal range: 50% - 70%</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.write("")
col_s1, col_s2 = st.columns(2)

with col_s1:
    st.markdown("### 💡 Strategic Insights")
    if is_lifestyle_deficit:
        st.error(f"**Trade-off:** Must cut **${abs(true_net)*12:,.0f}/yr** from lifestyle to sustain equity growth.")
    if is_neg_carry:
        st.warning("**Growth Play:** Requires **~3.5% annual appreciation** to offset monthly carry losses.")
    if not is_lifestyle_deficit and not is_unsustainable:
        st.success("**High Resilience:** Consider shortening amortization to accelerate equity build.")

with col_s2:
    st.markdown("### 🛡️ Stress Test")
    job_loss_months = (f_dp / (lifestyle_spend + primary_mtg + primary_carrying + new_p_i + total_opex_mo)) if f_dp > 0 else 0
    st.write(f"**Liquidity:** Capital can float all costs for **{job_loss_months:.1f} months** if income hits zero.")
    rate_shock = (target_loan * 0.02 / 12)
    st.write(f"**Rate Shock:** A +2% rate spike reduces monthly net by **${rate_shock:,.0f}**.")
    st.caption("⚠️ *Note: All surpluses are pre-lifestyle. Accuracy depends on your 'Monthly Budget' inputs.*")

show_disclaimer()

