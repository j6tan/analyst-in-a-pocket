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
        with open(path, "r") as f:
            return json.load(f)
    return {"rates": {"five_year_fixed_uninsured": 4.49}}

intel = load_market_intel()

# --- 3. DYNAMIC LTT/PTT CALCULATOR ---
def calculate_ltt_and_fees(price, province, city, is_fthb):
    tax_rules = intel.get("tax_rules", {})
    if not tax_rules: return 0, 0
    rebates = tax_rules.get("rebates", {})
    prov_rules = tax_rules.get(province, [])
    total_prov_tax, prev_h = 0, 0
    for rule in prov_rules:
        if price > prev_h:
            taxable = min(price, rule["threshold"]) - prev_h
            total_prov_tax += taxable * rule["rate"]
            prev_h = rule["threshold"]
    total_mun_tax = 0
    if province == "Ontario" and city == "Toronto":
        mun_rules = tax_rules.get("Toronto_Municipal", [])
        prev_h_mun = 0
        for rule in mun_rules:
            if price > prev_h_mun:
                taxable_mun = min(price, rule["threshold"]) - prev_h_mun
                total_mun_tax += taxable_mun * rule["rate"]
                prev_h_mun = rule["threshold"]
    total_rebate = 0
    if is_fthb:
        if province == "Ontario":
            total_rebate += min(total_prov_tax, rebates.get("ON_FTHB_Max", 4000))
            if city == "Toronto": total_rebate += min(total_mun_tax, rebates.get("Toronto_FTHB_Max", 4475))
        elif province == "BC":
            if price <= rebates.get("BC_FTHB_Threshold", 500000): total_rebate = total_prov_tax
            elif price <= rebates.get("BC_FTHB_Partial_Limit", 525000): total_rebate = total_prov_tax * ((525000 - price) / 25000)
    return (total_prov_tax + total_mun_tax), total_rebate

def calculate_min_downpayment(price):
    if price >= 1000000: return price * 0.20
    elif price <= 500000: return price * 0.05
    else: return (500000 * 0.05) + ((price - 500000) * 0.10)

# --- 4. THE ULTIMATE SOLVER ---
def solve_max_affordability(income_annual, debts_monthly, stress_rate, tax_rate):
    m_inc = income_annual / 12
    HEAT_FACTOR = 0.0002
    TAX_FACTOR = tax_rate / 12
    ALPHA = HEAT_FACTOR + TAX_FACTOR
    r_mo = (stress_rate / 100) / 12
    K = (r_mo * (1 + r_mo)**300) / ((1 + r_mo)**300 - 1) if r_mo > 0 else 1/300
    budget = min(m_inc * 0.39, (m_inc * 0.44) - debts_monthly)
    p3 = budget / (0.80 * K + ALPHA)
    p2 = (budget - (25000 * K)) / (0.90 * K + ALPHA)
    p1 = budget / (0.95 * K + ALPHA)
    if p3 >= 1000000: fp, fd = p3, p3 * 0.20
    elif p2 >= 500000: fp = p2; fd = (500000 * 0.05) + ((fp - 500000) * 0.10)
    else: fp, fd = p1, p1 * 0.05
    return fp, fd

# --- 5. HEADER & STORY ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("Mortgage Affordability Analysis")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 5px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.5em;">{household}: Strategic Affordability</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">{story_body if 'story_body' in locals() else "Mapping purchase power across Canada's dynamic markets."}</p>
</div>
""", unsafe_allow_html=True)

# --- 6. PERSISTENCE INITIALIZATION (FIXED AUTO-RECALC) ---
t4_sum = float(prof.get('p1_t4', 0) + prof.get('p2_t4', 0))
bonus_sum = float(prof.get('p1_bonus', 0) + prof.get('p1_commission', 0) + prof.get('p2_bonus', 0))
rental_sum = float(prof.get('inv_rental_income', 0))
debt_sum = float(prof.get('car_loan', 0) + prof.get('student_loan', 0) + prof.get('cc_pmt', 0))
current_hash = hash(str(prof))

def get_defaults(t4, bonus, rental, debt, prov, city):
    rate_val = float(intel['rates'].get('five_year_fixed_uninsured', 4.49))
    stress_val = max(5.25, rate_val + 2.0)
    qual_income = t4 + bonus + (rental * 0.80)
    p_key = prov if prov in ["Ontario", "BC", "Alberta", "Quebec", "Manitoba", "Saskatchewan"] else "Atlantic"
    city_rates = intel.get("city_tax_data", {}).get(p_key, {})
    t_rate = city_rates.get(city, 0.0075) 
    max_price, min_down = solve_max_affordability(qual_income, debt, stress_val, t_rate)
    return min_down, (max_price * t_rate), (max_price * 0.0002)

# Initial Setup
if "aff_store" not in st.session_state:
    # Set a smart default city based on province
    default_city = "Vancouver" if province == "BC" else "Toronto"
    d_dp, d_tx, d_ht = get_defaults(t4_sum, bonus_sum, rental_sum, debt_sum, province, default_city)
    st.session_state.aff_store = {
        "t4": t4_sum, "bonus": bonus_sum, "rental": rental_sum, "monthly_debt": debt_sum,
        "down_payment": d_dp, "prop_taxes": d_tx, "heat": d_ht,
        "contract_rate": 4.49, "city": default_city, "prop_type": "House / Freehold", "is_fthb": False,
        "last_synced_profile": current_hash
    }

# Change Detection: If User swiped the City dropdown
if "w_city" in st.session_state and st.session_state.w_city != st.session_state.aff_store['city']:
    st.session_state.aff_store['city'] = st.session_state.w_city
    d_dp, d_tx, d_ht = get_defaults(t4_sum, bonus_sum, rental_sum, debt_sum, province, st.session_state.w_city)
    st.session_state.aff_store.update({"down_payment": d_dp, "prop_taxes": d_tx, "heat": d_ht})

store = st.session_state.aff_store

# --- 7. INPUTS ---
col1, col2, col3 = st.columns([1.2, 1.2, 1.5])
with col1:
    st.subheader("💰 Income Summary")
    t4 = st.number_input("Combined T4 Income", value=store['t4'], key="w_t4")
    bonus = st.number_input("Total Additional Income", value=store['bonus'], key="w_bonus")
    rental = st.number_input("Joint Rental Income", value=store['rental'], key="w_rental")
    total_qualifying = t4 + bonus + (rental * 0.80)

with col2:
    st.subheader("💳 Debt & Status")
    p_key = province if province in ["Ontario", "BC", "Alberta", "Quebec", "Manitoba", "Saskatchewan"] else "Atlantic"
    city_options = list(intel.get("city_tax_data", {}).get(p_key, {}).keys())
    if "Other" not in city_options: city_options.append("Other")
    try: c_idx = city_options.index(store['city'])
    except: c_idx = 0
    st.selectbox("Property City", city_options, index=c_idx, key="w_city")
    prop_type = st.selectbox("Property Type", ["House / Freehold", "Condo / Townhome"], key="w_prop_type")
    monthly_debt = st.number_input("Monthly Debts", value=store['monthly_debt'], key="w_debt")
    is_fthb = st.checkbox("First-Time Home Buyer?", value=store['is_fthb'], key="w_fthb")

with col3:
    st.info("""
    **💡 Underwriting Insights:**
    * **T4:** Banks use **100%** of base salary.
    * **Additional Income:** Usually a **2-year average**.
    * **Rental:** Typically 'haircut' to **80%**.
    """)

with st.sidebar:
    st.header("⚙️ Underwriting")
    contract_rate = st.number_input("Bank Contract Rate %", step=0.01, value=store['contract_rate'], key="w_rate")
    stress_rate = max(5.25, contract_rate + 2.0)
    st.warning(f"**Qualifying Stress Rate:** {stress_rate:.2f}%")
    down_payment = st.number_input("Down Payment ($)", value=store['down_payment'], key="w_dp")
    taxes = st.number_input("Annual Property Taxes", value=store['prop_taxes'], key="w_taxes")
    heat = st.number_input("Monthly Heat", value=store['heat'], key="w_heat")
    strata = st.number_input("Monthly Strata", value=400.0) if prop_type == "Condo / Townhome" else 0

# --- 8. CALCULATION LOGIC ---
monthly_inc = total_qualifying / 12
gds_max = (monthly_inc * 0.39) - heat - (taxes/12) - (strata*0.5)
tds_max = (monthly_inc * 0.44) - heat - (taxes/12) - (strata*0.5) - monthly_debt
max_pi_stress = min(gds_max, tds_max)

if max_pi_stress > 0:
    i_stress = (stress_rate/100)/12
    loan_amt = max_pi_stress * (1 - (1+i_stress)**-300) / i_stress
    max_purchase = loan_amt + down_payment
    min_required = calculate_min_downpayment(max_purchase)
    
    if down_payment < min_required - 1:
        st.error(f"### 🛑 Down Payment Too Low. Legal min for ${max_purchase:,.0f} is ${min_required:,.0f}")
        st.stop()
        
    total_ltt, total_rebate = calculate_ltt_and_fees(max_purchase, province, store['city'], is_fthb)
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Max Purchase", f"${max_purchase:,.0f}")
    m2.metric("Max Loan", f"${loan_amt:,.0f}")
    m3.metric("Stress Test P&I", f"${max_pi_stress:,.0f}")
    
    r1, r2 = st.columns([2, 1.2])
    with r1:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=max_purchase, gauge={'axis': {'range': [0, max_purchase*1.5]}, 'bar': {'color': PRIMARY_GOLD}}))
        fig.update_layout(height=350, margin=dict(t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)
    with r2:
        st.subheader("⚖️ Cash-to-Close")
        breakdown = [{"Item": "Total LTT", "Cost": total_ltt}, {"Item": "FTHB Rebate", "Cost": -total_rebate}, {"Item": "Legal/Fees", "Cost": 2350}]
        df_costs = pd.DataFrame(breakdown)
        st.table(df_costs.assign(Cost=lambda x: x['Cost'].map('${:,.0f}'.format)))
else: st.error("Approval amount is $0.")

st.markdown("---")
st.markdown("""
<div style='background-color: #f8f9fa; padding: 16px 20px; border-radius: 5px; border: 1px solid #dee2e6;'>
    <p style='font-size: 12px; color: #6c757d; line-height: 1.6; margin-bottom: 0;'>
        <strong>⚠️ Errors and Omissions Disclaimer:</strong><br>
        This tool is for <strong>informational and educational purposes only</strong>. Figures are based on mathematical estimates and historical data. 
        This does not constitute financial, legal, or tax advice. Consult with a professional before making significant financial decisions.
    </p>
</div>
""", unsafe_allow_html=True)
st.caption("Analyst in a Pocket | Strategic Equity Strategy")
