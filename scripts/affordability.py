import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import json
import math
from style_utils import inject_global_css, show_disclaimer # Added central disclaimer
from data_handler import cloud_input, sync_widget

inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 1. THEME & UTILS ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

def custom_round_up(n):
    if n <= 0: return 0.0
    digits = int(math.log10(n)) + 1
    step = {1:10, 2:10, 3:10, 4:100, 5:100, 6:1000, 7:10000}.get(digits, 50000)
    return float(math.ceil(n / step) * step)

# --- 2. DATA RETRIEVAL ---
prof = st.session_state.app_db.get('profile', {})
province = prof.get('province', 'Ontario')
name1 = prof.get('p1_name', 'Primary Client')
name2 = prof.get('p2_name', '')
is_renter = prof.get('housing_status') == "Renting"
household = f"{name1} and {name2}" if name2 else name1

# Market Intel & Tax Functions (Keeping your exact logic)
def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f: return json.load(f)
    return {"rates": {"five_year_fixed_uninsured": 4.26}}

intel = load_market_intel()

def calculate_ltt_and_fees(price, province_val, is_fthb, is_toronto=False):
    tax_rules = intel.get("tax_rules", {})
    if not tax_rules: return 0, 0
    prov_rules = tax_rules.get(province_val, [])
    total_prov_tax, prev_h = 0, 0
    for rule in prov_rules:
        if price > prev_h:
            taxable = min(price, rule["threshold"]) - prev_h
            total_prov_tax += taxable * rule["rate"]
            prev_h = rule["threshold"]
    total_muni_tax = 0
    if is_toronto and province_val == "Ontario":
        muni_rules = tax_rules.get("Toronto_Municipal", [])
        prev_m = 0
        for rule in muni_rules:
            if price > prev_m:
                taxable = min(price, rule["threshold"]) - prev_m
                total_muni_tax += taxable * rule["rate"]
                prev_m = rule["threshold"]
    
    rebates = tax_rules.get("rebates", {})
    total_rebate = 0
    if is_fthb:
        if province_val == "Ontario":
            total_rebate += min(total_prov_tax, rebates.get("ON_FTHB_Max", 4000))
            if is_toronto: total_rebate += min(total_muni_tax, rebates.get("Toronto_FTHB_Max", 4475))
        elif province_val == "BC":
            fthb_limit = rebates.get("BC_FTHB_Threshold", 835000)
            if price <= fthb_limit: total_rebate = total_prov_tax
    return total_prov_tax + total_muni_tax, total_rebate

def calculate_min_downpayment(price):
    if price >= 1000000: return price * 0.20
    elif price <= 500000: return price * 0.05
    else: return (500000 * 0.05) + ((price - 500000) * 0.10)

# --- 3. SUMMARIES & SMART DEFAULTS ---
t4_sum = float(prof.get('p1_t4', 0)) + float(prof.get('p2_t4', 0)) + float(prof.get('p1_pension', 0)) + float(prof.get('p2_pension', 0))
bonus_sum = float(prof.get('p1_bonus', 0)) + float(prof.get('p1_commission', 0)) + float(prof.get('p2_bonus', 0)) + float(prof.get('p2_commission', 0))
rental_sum = float(prof.get('inv_rental_income', 0))
debt_sum = float(prof.get('car_loan', 0)) + float(prof.get('student_loan', 0)) + float(prof.get('cc_pmt', 0)) + (float(prof.get('loc_balance', 0)) * 0.03)

if 'affordability' not in st.session_state.app_db:
    st.session_state.app_db['affordability'] = {}
aff = st.session_state.app_db['affordability']

# --- 4. HEADER ---
st.title("Mortgage Affordability Analysis")
st.markdown(f"""<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border-left: 8px solid {PRIMARY_GOLD};">
    <h3 style="margin-top:0;">🚀 {household}: From Renting to Ownership</h3>
    <p>Mapping out the math needed for <b>{province}</b>.</p>
</div>""", unsafe_allow_html=True)

# --- 5. INPUT SECTIONS (Restored UI) ---
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
                             index=0 if aff.get('prop_type') == "House / Freehold" else 1,
                             key="affordability:prop_type", on_change=sync_widget, args=("affordability:prop_type",))
    strata = cloud_input("Monthly Strata", "affordability", "strata", step=10.0) if prop_type == "Condo / Townhome" else 0

st.divider()

col_1, col_2, col_3 = st.columns([1.2, 1.2, 1.5])
with col_1:
    st.subheader("💰 Income Summary")
    i_t4 = cloud_input("Combined T4 Income", "affordability", "combined_t4", step=1000.0)
    i_bonus = cloud_input("Total Additional Income", "affordability", "combined_bonus", step=500.0)
    i_rental = cloud_input("Joint Rental Income", "affordability", "rental", step=100.0)
    total_qualifying = i_t4 + i_bonus + (i_rental * 0.80)
    st.markdown(f"**Qualifying Income:** ${total_qualifying:,.0f}")

with col_2:
    st.subheader("💳 Debt & Status")
    i_debt = cloud_input("Monthly Debts", "affordability", "combined_debt", step=50.0)
    f_fthb = st.checkbox("First-Time Home Buyer?", value=aff.get('is_fthb', False), key="affordability:is_fthb", on_change=sync_widget, args=("affordability:is_fthb",))
    f_toronto = st.checkbox("Toronto Limits?", key="affordability:is_toronto") if province == "Ontario" else False

with col_3:
    st.info("**💡 Underwriting Insights:** T4 100%, Bonus 2-yr avg, Rental 80% haircut.")

# --- 6. DASHBOARD CALCULATIONS & VISUALS ---
monthly_inc = total_qualifying / 12
gds_max = (monthly_inc * 0.39) - f_heat - (f_ptax/12) - (strata*0.5)
tds_max = (monthly_inc * 0.44) - f_heat - (f_ptax/12) - (strata*0.5) - i_debt
max_pi_stress = min(gds_max, tds_max)

if max_pi_stress > 0:
    r_mo_stress = (s_rate/100)/12
    raw_loan = max_pi_stress * (1 - (1+r_mo_stress)**-300) / r_mo_stress if r_mo_stress > 0 else max_pi_stress * 300
    loan_amt = custom_round_up(raw_loan)
    
    r_mo_contract = (c_rate/100)/12
    contract_pi = (loan_amt * r_mo_contract) / (1 - (1+r_mo_contract)**-300) if r_mo_contract > 0 else loan_amt / 300
    
    max_purchase = loan_amt + f_dp
    
    # Restored Dashboard Metrics
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Max Purchase", f"${max_purchase:,.0f}")
    m2.metric("Max Loan", f"${loan_amt:,.0f}")
    m3.metric("Contract P&I", f"${contract_pi:,.0f}")
    m4.metric("Stress P&I", f"${max_pi_stress:,.0f}")

    # Restored Gauge and Closing Costs Table
    r_c1, r_c2 = st.columns([2, 1.2])
    with r_c1:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=max_purchase, gauge={'axis': {'range': [0, max_purchase*1.5]}, 'bar': {'color': PRIMARY_GOLD}}))
        fig.update_layout(height=350, margin=dict(t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    with r_c2:
        st.subheader("⚖️ Cash-to-Close")
        total_tax, total_rebate = calculate_ltt_and_fees(max_purchase, province, f_fthb, f_toronto)
        total_closing = total_tax - total_rebate + 2350 # Legal/Title/Appraisal
        total_cash = f_dp + total_closing
        monthly_cost = contract_pi + (f_ptax/12) + f_heat + strata
        
        breakdown = [
            {"Item": "Down Payment", "Cost": f_dp},
            {"Item": "Land Transfer Tax", "Cost": total_tax},
            {"Item": "FTHB Rebate", "Cost": -total_rebate},
            {"Item": "Legal / Misc", "Cost": 2350}
        ]
        st.table(pd.DataFrame(breakdown).assign(Cost=lambda x: x['Cost'].map('${:,.0f}'.format)))
        
        # Restored Color Cards
        st.markdown(f"""
        <div style="background-color: {PRIMARY_GOLD}; color: white; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 10px;">
            <p style="margin: 0; font-size: 0.8em;">TOTAL CASH TO CLOSE</p>
            <p style="margin: 0; font-size: 1.5em; font-weight: 800;">${total_cash:,.0f}</p>
        </div>
        <div style="background-color: #C0C0C0; color: white; padding: 10px; border-radius: 8px; text-align: center;">
            <p style="margin: 0; font-size: 0.8em;">MONTHLY HOME COST</p>
            <p style="margin: 0; font-size: 1.5em; font-weight: 800;">${monthly_cost:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

else:
    st.error("Approval amount is $0.")

# --- CENTRALIZED DISCLAIMER ---
show_disclaimer()
