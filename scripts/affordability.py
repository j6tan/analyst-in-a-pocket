import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import json

# --- 1. THEME & STYLING ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

# --- ROUNDING LOGIC ---
def apply_rounding_rule(value):
    if value == 0: return 0
    s = str(int(abs(value)))
    n = len(s)
    if n <= 2: return round(value, -1)
    # Rule: Keep first two digits, zero out the rest (e.g., 1234 -> 1200)
    factor = 10 ** (n - 2)
    return float((value // factor) * factor)

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
    return {"rates": {"five_year_fixed_uninsured": 4.26}}

intel = load_market_intel()

# --- 3. DYNAMIC LTT/PTT CALCULATOR ---
def calculate_ltt_and_fees(price, province_val, is_fthb, is_toronto=False):
    tax_rules = intel.get("tax_rules", {})
    if not tax_rules: return 0.0, 0.0
    rebates = tax_rules.get("rebates", {})
    
    lookup_key = "Ontario" if "Ontario" in str(province_val) else str(province_val).strip()
    prov_rules = tax_rules.get(lookup_key, [])
    
    total_prov_tax, prev_h = 0.0, 0.0
    for rule in prov_rules:
        h, r = float(rule["threshold"]), float(rule["rate"])
        if price > prev_h:
            taxable = min(float(price), h) - prev_h
            total_prov_tax += taxable * r
            prev_h = h
    
    total_muni_tax = 0.0
    if is_toronto and lookup_key == "Ontario":
        muni_rules = tax_rules.get("Toronto_Municipal", [])
        prev_m = 0.0
        for rule in muni_rules:
            mh, mr = float(rule["threshold"]), float(rule["rate"])
            if price > prev_m:
                taxable_m = min(float(price), mh) - prev_m
                total_muni_tax += taxable_m * mr
                prev_m = mh

    total_rebate = 0.0
    if is_fthb:
        if lookup_key == "Ontario":
            total_rebate += min(total_prov_tax, float(rebates.get("ON_FTHB_Max", 4000)))
            if is_toronto:
                total_rebate += min(total_muni_tax, float(rebates.get("Toronto_FTHB_Max", 4475)))
    return (total_prov_tax + total_muni_tax), total_rebate

def calculate_min_downpayment(price):
    if price >= 1000000: return price * 0.20
    elif price <= 500000: return price * 0.05
    else: return (500000 * 0.05) + ((price - 500000) * 0.10)

# --- 4. HEADER & STORY ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("Mortgage Affordability Analysis")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 15px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.5em;">{household}: Planning Your Move</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">We've analyzed your current profile to determine how much house your wealth can truly buy in today's <b>{province}</b> market.</p>
</div>
""", unsafe_allow_html=True)

# --- 5. PERSISTENCE ---
if "aff_v_final_v2" not in st.session_state:
    st.session_state.aff_v_final_v2 = {
        "t4": float(prof.get('p1_t4', 0) + prof.get('p2_t4', 0)),
        "bonus": float(prof.get('p1_bonus', 0) + prof.get('p1_commission', 0) + prof.get('p2_bonus', 0)),
        "rental": float(prof.get('inv_rental_income', 0)),
        "monthly_debt": float(prof.get('car_loan', 0) + prof.get('student_loan', 0) + prof.get('cc_pmt', 0)),
        "down_payment": apply_rounding_rule(100000.0),
        "prop_taxes": apply_rounding_rule(5000.0),
        "heat": apply_rounding_rule(125.0),
        "contract_rate": float(intel['rates'].get('five_year_fixed_uninsured', 4.49)),
        "is_fthb": False, "is_toronto": False, "prop_type": "House / Freehold"
    }
store = st.session_state.aff_v_final_v2

# --- 6. INPUTS & ENGINE ---
col_1, col_2, col_3 = st.columns([1.2, 1.2, 1.5])
with col_1:
    st.subheader("💰 Income Summary")
    store['t4'] = st.number_input("Combined T4 Income", value=store['t4'])
    store['bonus'] = st.number_input("Total Additional Income", value=store['bonus'])
    store['rental'] = st.number_input("Joint Rental Income", value=store['rental'])
    total_qualifying = store['t4'] + store['bonus'] + (store['rental'] * 0.80)
    st.markdown(f"**Qualifying Income:** ${total_qualifying:,.0f}")

with col_2:
    st.subheader("💳 Debt & Status")
    store['prop_type'] = st.selectbox("Property Type", ["House / Freehold", "Condo / Townhome"])
    store['monthly_debt'] = st.number_input("Monthly Debts", value=store['monthly_debt'])
    store['is_fthb'] = st.checkbox("First-Time Home Buyer?", value=store['is_fthb'])
    if province == "Ontario":
        store['is_toronto'] = st.checkbox("Within Toronto City Limits?", value=store['is_toronto'])

with col_3:
    st.info("**💡 Underwriting Insights:**\n* T4: 100% of base.\n* Rental: Haircut to 80%.\n* Bonus: 2yr average used.")

with st.sidebar:
    st.header("⚙️ Underwriting")
    c_rate = st.number_input("Bank Contract Rate %", value=store['contract_rate'], step=0.01)
    s_rate = max(5.25, c_rate + 2.0)
    st.warning(f"**Qualifying Rate:** {s_rate:.2f}%")
    store['down_payment'] = st.number_input("Down Payment ($)", value=float(store['down_payment']))
    store['prop_taxes'] = st.number_input("Annual Property Taxes", value=float(store['prop_taxes']))
    store['heat'] = st.number_input("Monthly Heat", value=float(store['heat']))
    strata = st.number_input("Monthly Strata", value=400.0) if store['prop_type'] == "Condo / Townhome" else 0

# --- 7. LOGIC ---
monthly_inc = total_qualifying / 12
gds_max = (monthly_inc * 0.39) - store['heat'] - (store['prop_taxes']/12) - (strata*0.5)
tds_max = (monthly_inc * 0.44) - store['heat'] - (store['prop_taxes']/12) - (strata*0.5) - store['monthly_debt']
max_pi_stress = min(gds_max, tds_max)

if max_pi_stress > 0:
    r_mo_stress = (s_rate/100)/12
    loan_amt = apply_rounding_rule(max_pi_stress * (1 - (1+r_mo_stress)**-300) / r_mo_stress)
    max_purchase = round(loan_amt + store['down_payment'])
    
    r_mo_contract = (c_rate/100)/12
    contract_pi = (loan_amt * r_mo_contract) / (1 - (1+r_mo_contract)**-300)

    min_required = calculate_min_downpayment(max_purchase)
    if store['down_payment'] < min_required - 1.0: 
        st.error(f"#### 🛑 Down Payment Too Low")
        st.warning(f"Minimum Requirement for purchase price of **${max_purchase:,.0f}** is **${min_required:,.0f}**.")
        st.stop()
        
    total_tax, total_rebate = calculate_ltt_and_fees(max_purchase, province, store['is_fthb'], store.get('is_toronto', False))
    total_cash_required = store['down_payment'] + total_tax - total_rebate + 2350

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Max Purchase Power", f"${max_purchase:,.0f}")
    m2.metric("Max Loan Amount", f"${loan_amt:,.0f}")
    m3.metric("Stress Test P&I", f"${round(max_pi_stress):,.0f}")
    m4.metric("Contracted P&I", f"${round(contract_pi):,.0f}")
    st.caption(f"Note: Stress test P&I is using qualifying rate {s_rate:.2f}%")
    
    r_c1, r_c2 = st.columns([2, 1.2])
    with r_c1:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=max_purchase, gauge={'axis': {'range': [0, max_purchase*1.5]}, 'bar': {'color': PRIMARY_GOLD}}))
        st.plotly_chart(fig, use_container_width=True)
    with r_c2:
        st.subheader("⚖️ Cash-to-Close")
        breakdown = [
            {"Item": "Down Payment", "Cost": store['down_payment']},
            {"Item": "Land Transfer Tax", "Cost": total_tax},
            {"Item": "FTHB Rebate", "Cost": -total_rebate},
            {"Item": "Legal / Title / Appraisal", "Cost": 2350}
        ]
        st.table(pd.DataFrame(breakdown).assign(Cost=lambda x: x['Cost'].map('${:,.0f}'.format)))
        st.markdown(f"""<div style="background-color: {PRIMARY_GOLD}; color: white; padding: 10px 15px; border-radius: 8px; text-align: center; border: 1px solid #B49A57;"><p style="margin: 0; font-size: 0.9em; font-weight: bold; text-transform: uppercase;">Total Cash Required</p><p style="margin: 0; font-size: 1.6em; font-weight: 800;">${total_cash_required:,.0f}</p></div>""", unsafe_allow_html=True)
else: st.error("Approval amount is $0.")

st.markdown("---")
st.markdown("""
<div style='background-color: #f8f9fa; padding: 16px 20px; border-radius: 5px; border: 1px solid #dee2e6;'>
    <p style='font-size: 12px; color: #6c757d; line-height: 1.6; margin-bottom: 0;'>
        <strong>⚠️ Errors and Omissions Disclaimer:</strong> Figures are based on mathematical estimates and bank guidelines. Consult a professional before making financial decisions.
    </p>
</div>
""", unsafe_allow_html=True)
st.caption("Analyst in a Pocket | Strategic Debt Planning & Equity Strategy")
