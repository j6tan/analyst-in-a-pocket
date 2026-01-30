import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import json

# --- 1. THEME & STYLING ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

# --- 2. DATA RETRIEVAL ---
prof = st.session_state.get('user_profile', {})
province = prof.get('province', 'Ontario')
name1 = prof.get('p1_name', 'Primary Client')
name2 = prof.get('p2_name', '')
is_renter = prof.get('housing_status') == "Renting"

household = f"{name1} and {name2}" if name2 else name1

def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f: return json.load(f)
    return {"rates": {"five_year_fixed_uninsured": 4.26}}

intel = load_market_intel()

# --- 3. DYNAMIC LTT/PTT CALCULATOR ---
def calculate_ltt_and_fees(price, province, is_fthb):
    tax_rules = intel.get("tax_rules", {})
    if not tax_rules: return 0, 0
    rebates = tax_rules.get("rebates", {})
    
    # 1. Provincial Tax
    prov_rules = tax_rules.get(province, [])
    total_prov_tax, prev_h = 0, 0
    for rule in prov_rules:
        if price > prev_h:
            taxable = min(price, rule["threshold"]) - prev_h
            total_prov_tax += taxable * rule["rate"]
            prev_h = rule["threshold"]
            
    # 2. Rebate Logic
    total_rebate = 0
    if is_fthb:
        if province == "Ontario":
            total_rebate += min(total_prov_tax, rebates.get("ON_FTHB_Max", 4000))
        elif province == "BC":
            if price <= rebates.get("BC_FTHB_Threshold", 835000): total_rebate = total_prov_tax
            elif price <= rebates.get("BC_FTHB_Partial_Limit", 860000): 
                total_rebate = total_prov_tax * ((860000 - price) / 25000)
    return total_prov_tax, total_rebate

def calculate_min_downpayment(price):
    if price >= 1000000: return price * 0.20
    elif price <= 500000: return price * 0.05
    else: return (500000 * 0.05) + ((price - 500000) * 0.10)

# --- 4. ULTIMATE SOLVER ---
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
    if p3 >= 1000000: fp, fd = p3, p3 * 0.20
    elif p2 >= 500000: fp = p2; fd = 25000 + (fp - 500000) * 0.10
    else: fp, fd = p1, p1 * 0.05
    return fp, fd

# --- 5. HEADER & STORY ---
st.title("Mortgage Affordability Analysis")
story_headline = f"🚀 {household}: From Renting to Ownership" if is_renter else f"📈 {household}: Planning Your Next Move"
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD};">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0;">{story_headline}</h3>
    <p style="color: {SLATE_ACCENT}; margin-bottom: 0;">Analyzing purchase power in <b>{province}</b> with live 2026 market rates.</p>
</div>
""", unsafe_allow_html=True)

# --- 6. PERSISTENCE ---
t4_sum = float(prof.get('p1_t4', 0) + prof.get('p2_t4', 0))
bonus_sum = float(prof.get('p1_bonus', 0) + prof.get('p1_commission', 0) + prof.get('p2_bonus', 0))
rental_sum = float(prof.get('inv_rental_income', 0))
debt_sum = float(prof.get('car_loan', 0) + prof.get('student_loan', 0) + prof.get('cc_pmt', 0))

# Provincial Tax Defaults
TAX_DEFAULTS = {"BC": 0.0031, "Ontario": 0.0076, "Alberta": 0.0064}
prov_tax_rate = TAX_DEFAULTS.get(province, 0.0075)

def get_defaults(t4, bonus, rental, debt, tax_rate):
    rate_val = float(intel['rates'].get('five_year_fixed_uninsured', 4.26))
    stress_val = max(5.25, rate_val + 2.0)
    qual_income = t4 + bonus + (rental * 0.80)
    max_p, min_d = solve_max_affordability(qual_income, debt, stress_val, tax_rate)
    return min_d, (max_p * tax_rate), (max_p * 0.0002)

if "aff_store" not in st.session_state:
    d_dp, d_tx, d_ht = get_defaults(t4_sum, bonus_sum, rental_sum, debt_sum, prov_tax_rate)
    st.session_state.aff_store = {"t4": t4_sum, "bonus": bonus_sum, "rental": rental_sum, "monthly_debt": debt_sum, "down_payment": d_dp, "prop_taxes": d_tx, "heat": d_ht, "is_fthb": False}

store = st.session_state.aff_store

# --- 7. INPUTS ---
col1, col2, col3 = st.columns([1.2, 1.2, 1.5])
with col1:
    st.subheader("💰 Income")
    store['t4'] = st.number_input("Combined T4", value=store['t4'])
    store['bonus'] = st.number_input("Bonus/Comm.", value=store['bonus'])
    store['rental'] = st.number_input("Rental Income", value=store['rental'])
    total_q = store['t4'] + store['bonus'] + (store['rental'] * 0.8)

with col2:
    st.subheader("💳 Debts")
    store['monthly_debt'] = st.number_input("Monthly Debts", value=store['monthly_debt'])
    store['is_fthb'] = st.checkbox("First-Time Buyer?", value=store['is_fthb'])
    prop_type = st.selectbox("Property Type", ["House / Freehold", "Condo / Townhome"])

with col3:
    st.info("**💡 Underwriting Insights:**\n* **T4:** 100% used.\n* **Bonus:** 2yr Avg.\n* **Rental:** Haircut to 80%.")

with st.sidebar:
    st.header("⚙️ Underwriting")
    rate = st.number_input("Contract Rate %", value=4.26, step=0.01)
    stress = max(5.25, rate + 2.0)
    st.warning(f"Qualifying at {stress:.2f}%")
    store['down_payment'] = st.number_input("Down Payment", value=store['down_payment'])
    store['prop_taxes'] = st.number_input("Annual Taxes", value=store['prop_taxes'])
    store['heat'] = st.number_input("Monthly Heat", value=store['heat'])
    strata = st.number_input("Monthly Strata", value=400.0) if "Condo" in prop_type else 0

# --- 8. RESULTS ---
monthly_inc = total_q / 12
gds = (monthly_inc * 0.39) - store['heat'] - (store['prop_taxes']/12) - (strata*0.5)
tds = (monthly_inc * 0.44) - store['heat'] - (store['prop_taxes']/12) - (strata*0.5) - store['monthly_debt']
max_pi = min(gds, tds)

if max_pi > 0:
    r_mo = (stress/100)/12
    loan = max_pi * (1 - (1+r_mo)**-300) / r_mo
    p_power = loan + store['down_payment']
    min_d = calculate_min_downpayment(p_power)
    
    if store['down_payment'] < min_d - 1:
        st.error(f"### 🛑 DP Too Low. Min for ${p_power:,.0f} is ${min_d:,.0f}")
        st.stop()
        
    ltt, rebate = calculate_ltt_and_fees(p_power, province, store['is_fthb'])
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Max Purchase", f"${p_power:,.0f}")
    m2.metric("Max Loan", f"${loan:,.0f}")
    m3.metric("Min Required DP", f"${min_d:,.0f}")
    
    breakdown = [{"Item": "Land Transfer Tax", "Cost": ltt}, {"Item": "FTHB Rebate", "Cost": -rebate}, {"Item": "Legal/Fees", "Cost": 2350}]
    st.table(pd.DataFrame(breakdown).assign(Cost=lambda x: x['Cost'].map('${:,.0f}'.format)))
else: st.error("Incomes do not support a mortgage.")

st.markdown("---")
st.markdown("<div style='background-color: #f8f9fa; padding: 16px; border-radius: 5px; font-size: 12px; color: #6c757d;'><strong>⚠️ Errors and Omissions Disclaimer:</strong> Figures are mathematical estimates based on historical data. Consult a professional.</div>", unsafe_allow_html=True)
st.caption("Analyst in a Pocket | Strategic Equity Strategy")
