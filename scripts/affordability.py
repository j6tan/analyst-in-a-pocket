import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import json
import math
from style_utils import inject_global_css
from data_handler import cloud_input, sync_widget # ADDED FOR SYNC

# 1. Inject the Wealthsimple-inspired Editorial CSS
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 1. THEME & STYLING ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

# --- ROUNDING UTILITY ---
def custom_round_up(n):
    if n <= 0:
        return 0.0
    digits = int(math.log10(n)) + 1
    if digits <= 3:
        step = 10
    elif digits <= 5:
        step = 100
    elif digits == 6:
        step = 1000
    elif digits == 7:
        step = 10000
    else:
        step = 50000 
    return float(math.ceil(n / step) * step)

# --- 2. DATA RETRIEVAL ---
prof = st.session_state.app_db.get('profile', {})
province = prof.get('province', 'Ontario')
name1 = prof.get('p1_name', 'Primary Client')
name2 = prof.get('p2_name', '')
is_renter = prof.get('housing_status') == "Renting"

household = f"{name1} and {name2}" if name2 else name1

def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"rates": {"five_year_fixed_uninsured": 4.26}}

intel = load_market_intel()

# --- 3. DYNAMIC LTT/PTT CALCULATOR ---
def calculate_ltt_and_fees(price, province_val, is_fthb, is_toronto=False):
    tax_rules = intel.get("tax_rules", {})
    if not tax_rules: return 0, 0
    rebates = tax_rules.get("rebates", {})
    
    # 1. Provincial Tax
    prov_rules = tax_rules.get(province_val, [])
    total_prov_tax, prev_h = 0, 0
    for rule in prov_rules:
        if price > prev_h:
            taxable = min(price, rule["threshold"]) - prev_h
            total_prov_tax += taxable * rule["rate"]
            prev_h = rule["threshold"]
    
    # 2. Toronto Municipal Tax (Conditional)
    total_muni_tax = 0
    if is_toronto and province_val == "Ontario":
        muni_rules = tax_rules.get("Toronto_Municipal", [])
        prev_m = 0
        for rule in muni_rules:
            if price > prev_m:
                taxable = min(price, rule["threshold"]) - prev_m
                total_muni_tax += taxable * rule["rate"]
                prev_m = rule["threshold"]

    # 3. Rebate Logic
    total_rebate = 0
    if is_fthb:
        if province_val == "Ontario":
            total_rebate += min(total_prov_tax, rebates.get("ON_FTHB_Max", 4000))
            if is_toronto:
                total_rebate += min(total_muni_tax, rebates.get("Toronto_FTHB_Max", 4475))
        elif province_val == "BC":
            fthb_limit = rebates.get("BC_FTHB_Threshold", 835000)
            partial_limit = rebates.get("BC_FTHB_Partial_Limit", 860000)
            if price <= fthb_limit: total_rebate = total_prov_tax
            elif price <= partial_limit:
                total_rebate = total_prov_tax * ((partial_limit - price) / (partial_limit - fthb_limit))

    return total_prov_tax + total_muni_tax, total_rebate

def calculate_min_downpayment(price):
    if price >= 1000000: return price * 0.20
    elif price <= 500000: return price * 0.05
    else: return (500000 * 0.05) + ((price - 500000) * 0.10)

# --- 4. THE ULTIMATE SOLVER ---
def solve_max_affordability(income_annual, debts_monthly, stress_rate, tax_rate):
    m_inc = income_annual / 12
    HEAT_FACTOR, TAX_FACTOR = 0.0002, tax_rate / 12
    ALPHA = HEAT_FACTOR + TAX_FACTOR
    r_mo = (stress_rate / 100) / 12
    K = (r_mo * (1 + r_mo)**300) / ((1 + r_mo)**300 - 1) if r_mo > 0 else 1/300
    budget = min(m_inc * 0.39, (m_inc * 0.44) - debts_monthly)
    p3 = budget / (0.80 * K + ALPHA)
    p2 = (budget - (25000 * K)) / (0.90 * K + ALPHA)
    p1 = budget / (0.95 * K + ALPHA)
    if p3 >= 1000000: 
        fp, fd = p3, p3 * 0.20
    elif p2 >= 500000: 
        fp = min(p2, 999999) 
        fd = 25000 + (fp - 500000) * 0.10
    else: 
        fp = min(p1, 499999) 
        fd = fp * 0.05
    return fp, fd

# --- 5. HEADER & STORY ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("Mortgage Affordability Analysis")

if is_renter:
    story_headline = f"🚀 {household}: From Renting to Ownership"
    story_body = f"This is the moment where your monthly rent becomes an investment in your future. Based on your current profile, we're mapping out the exact math needed to secure your first home in <b>{province}</b>."
else:
    story_headline = f"📈 {household}: Planning Your Next Move"
    story_body = f"Scaling up or relocating is a strategic play. We’ve analyzed your current income to determine how much house your wealth can truly buy in today's <b>{province}</b> market."

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 5px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.5em;">{story_headline}</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">{story_body}</p>
</div>
""", unsafe_allow_html=True)

# --- 6. PERSISTENCE & DEFAULTS ---
# Using current values from st.session_state.app_db
t4_sum = float(prof.get('p1_t4', 0)) + float(prof.get('p2_t4', 0)) + float(prof.get('p1_pension', 0)) + float(prof.get('p2_pension', 0))
bonus_sum = float(prof.get('p1_bonus', 0)) + float(prof.get('p1_commission', 0)) + float(prof.get('p2_bonus', 0)) + float(prof.get('p2_commission', 0)) + float(prof.get('other_income', 0))
rental_sum = float(prof.get('inv_rental_income', 0))
debt_sum = (
    float(prof.get('car_loan', 0)) + 
    float(prof.get('student_loan', 0)) + 
    float(prof.get('cc_pmt', 0)) + 
    float(prof.get('support_pmt', 0)) + 
    float(prof.get('other_debt', 0)) + 
    (float(prof.get('loc_balance', 0)) * 0.03)
)

TAX_DEFAULTS = {"BC": 0.0031, "Ontario": 0.0076, "Alberta": 0.0064}
prov_tax_rate = TAX_DEFAULTS.get(province, 0.0075)
market_rate = float(intel['rates'].get('five_year_fixed_uninsured', 4.26))

# --- 7. UNDERWRITING ASSUMPTIONS (NOW DYNAMIC) ---
st.subheader("⚙️ Underwriting Assumptions")
uw_col1, uw_col2, uw_col3 = st.columns(3)
with uw_col1:
    c_rate = cloud_input("Bank Contract Rate %", "affordability", "bank_rate", step=0.01)
    s_rate = max(5.25, c_rate + 2.0)
    st.markdown(f"**Qualifying Rate:** {s_rate:.2f}%")
with uw_col2:
    f_dp = cloud_input("Down Payment ($)", "affordability", "down_payment", step=1000.0)
    f_ptax = cloud_input("Annual Property Taxes", "affordability", "prop_taxes", step=100.0)
with uw_col3:
    f_heat = cloud_input("Monthly Heat", "affordability", "heat", step=10.0)
    prop_type = st.selectbox("Property Type", ["House / Freehold", "Condo / Townhome"], 
                             index=0 if st.session_state.app_db['affordability'].get('prop_type') == "House / Freehold" else 1,
                             key="affordability:prop_type", on_change=sync_widget, args=("affordability:prop_type",))
    
    strata = 0
    if prop_type == "Condo / Townhome":
        strata = cloud_input("Monthly Strata", "affordability", "strata", step=10.0)

st.divider()

# --- 8. INPUTS & UI (NOW DYNAMIC) ---
col_1, col_2, col_3 = st.columns([1.2, 1.2, 1.5])
with col_1:
    st.subheader("💰 Income Summary")
    # Mapping these back to 'profile' so they update the main client data
    i_t4 = cloud_input("Combined T4 Income", "profile", "p1_t4", step=1000.0)
    i_bonus = cloud_input("Total Additional Income", "profile", "p1_bonus", step=500.0)
    i_rental = cloud_input("Joint Rental Income", "profile", "inv_rental_income", step=100.0)
    
    total_qualifying = i_t4 + i_bonus + (i_rental * 0.80)
    st.markdown(f"""<div style="margin-top: 10px;"><span style="font-size: 1.15em; color: {SLATE_ACCENT}; font-weight: bold;">Qualifying Income: </span><span style="font-size: 1.25em; color: black; font-weight: bold;">${total_qualifying:,.0f}</span></div>""", unsafe_allow_html=True)

with col_2:
    st.subheader("💳 Debt & Status")
    i_debt = cloud_input("Monthly Debts", "profile", "car_loan", step=50.0) # Using car_loan as the proxy for the sum
    
    # Checkbox uses sync_widget directly
    f_fthb = st.checkbox("First-Time Home Buyer?", 
                         value=st.session_state.app_db['affordability'].get('is_fthb', False),
                         key="affordability:is_fthb", on_change=sync_widget, args=("affordability:is_fthb",))
    
    f_toronto = False
    if province == "Ontario":
        f_toronto = st.checkbox("Within Toronto City Limits?", 
                                 value=st.session_state.app_db['affordability'].get('is_toronto', False),
                                 key="affordability:is_toronto", on_change=sync_widget, args=("affordability:is_toronto",))

with col_3:
    st.info("""
    **💡 Underwriting Insights:**
    * **T4:** Banks use **100%** of base salary.
    * **Additional Income:** Usually a **2-year average**.
    * **Rental:** Typically 'haircut' to **80%**.
    """)

# --- 9. CALCULATION LOGIC (IDENTICAL MATH) ---
monthly_inc = total_qualifying / 12
gds_max = (monthly_inc * 0.39) - f_heat - (f_ptax/12) - (strata*0.5)
tds_max = (monthly_inc * 0.44) - f_heat - (f_ptax/12) - (strata*0.5) - i_debt
max_pi_stress = min(gds_max, tds_max)

if max_pi_stress > 0:
    r_mo_stress = (s_rate/100)/12
    raw_loan_amt = max_pi_stress * (1 - (1+r_mo_stress)**-300) / r_mo_stress
    loan_amt = custom_round_up(raw_loan_amt)
    
    r_mo_contract = (c_rate/100)/12
    contract_pi = (loan_amt * r_mo_contract) / (1 - (1+r_mo_contract)**-300)
    
    max_purchase = loan_amt + f_dp
    
    # Store results for other pages
    st.session_state.aff_final = {'max_purchase': max_purchase, 'down_payment': f_dp}
    
    min_required = calculate_min_downpayment(max_purchase)
    is_dp_valid = f_dp >= (min_required - 1.0)
    
    if not is_dp_valid:
        st.error("#### 🛑 Down Payment Too Low")
        st.markdown(f"""
        <div style="background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; border: 1px solid #ffeeba;">
            The minimum requirement for a purchase price of <strong>${max_purchase:,.0f}</strong> is <strong>${min_required:,.0f}</strong>.
        </div>
        """, unsafe_allow_html=True)
        st.stop()
        
    total_tax, total_rebate = calculate_ltt_and_fees(max_purchase, province, f_fthb, f_toronto)
    legal_fees, title_ins, appraisal = 1500, 500, 350
    total_closing_costs = total_tax - total_rebate + legal_fees + title_ins + appraisal
    total_cash_required = f_dp + total_closing_costs
    monthly_home_cost = contract_pi + (f_ptax/12) + f_heat

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Max Purchase Power", f"${max_purchase:,.0f}")
    m2.metric("Max Loan Amount", f"${loan_amt:,.0f}")
    m3.metric("Contracted P&I", f"${contract_pi:,.0f}")
    m4.metric("Stress Test P&I", f"${max_pi_stress:,.0f}")
    
    r_c1, r_c2 = st.columns([2, 1.2])
    with r_c1:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=max_purchase, gauge={'axis': {'range': [0, max_purchase*1.5]}, 'bar': {'color': PRIMARY_GOLD}}))
        fig.update_layout(height=350, margin=dict(t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)
    with r_c2:
        st.subheader("⚖️ Cash-to-Close")
        breakdown = [
            {"Item": "Down Payment", "Cost": f_dp},
            {"Item": "Land Transfer Tax", "Cost": total_tax},
            {"Item": "FTHB Rebate", "Cost": -total_rebate},
            {"Item": "Legal / Title / Appraisal", "Cost": (legal_fees + title_ins + appraisal)}
        ]
        st.table(pd.DataFrame(breakdown).assign(Cost=lambda x: x['Cost'].map('${:,.0f}'.format)))
        
        st.markdown(f"""
        <div style="background-color: {PRIMARY_GOLD}; color: white; padding: 10px 15px; border-radius: 8px; text-align: center; border: 1px solid #B49A57; margin-bottom: 10px;">
            <p style="margin: 0; font-size: 0.85em; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">TOTAL CASH REQUIRED TO CLOSE</p>
            <p style="margin: 0; font-size: 1.6em; font-weight: 800; line-height: 1.2;">${total_cash_required:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="background-color: #C0C0C0; color: white; padding: 10px 15px; border-radius: 8px; text-align: center; border: 1px solid #A9A9A9;">
            <p style="margin: 0; font-size: 0.85em; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">MONTHLY HOME COST</p>
            <p style="margin: 0; font-size: 1.6em; font-weight: 800; line-height: 1.2;">${monthly_home_cost:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)
        
else: st.error("Approval amount is $0.")

st.markdown("---")
st.markdown("""
<div style='background-color: #f8f9fa; padding: 16px 20px; border-radius: 5px; border: 1px solid #dee2e6;'>
    <p style='font-size: 12px; color: #6c757d; line-height: 1.6; margin-bottom: 0;'>
        <strong>⚠️ Errors and Omissions Disclaimer:</strong><br>
        This tool is for <strong>informational and educational purposes only</strong>.
    </p>
</div>
""", unsafe_allow_html=True)
st.caption("Analyst in a Pocket | Strategic Equity Strategy")
