import streamlit as st
import pandas as pd
import os
import json
import math

# --- 1. THEME & STYLING ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

# --- ROUNDING UTILITY ---
def custom_round_up(n):
    if n <= 0: return 0.0
    digits = int(math.log10(n)) + 1
    if digits <= 3: step = 10
    elif digits <= 5: step = 100
    elif digits == 6: step = 1000
    elif digits == 7: step = 10000
    else: step = 50000 
    return float(math.ceil(n / step) * step)

# --- 2. DATA CROSS-REFERENCING ---
prof = st.session_state.get('user_profile', {})
province = prof.get('province', 'BC')
p1_name = prof.get('p1_name', 'Client A')
p2_name = prof.get('p2_name', 'Client B')
household = f"{p1_name} & {p2_name}".strip(" & ")

def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"rates": {"five_year_fixed_uninsured": 4.26}, "provincial_yields": {"BC": 3.8}}

intel = load_market_intel()
scraped_yield = intel.get("provincial_yields", {}).get(province, 3.8)

# --- 3. PERSISTENCE ---
if "aff_second_store" not in st.session_state:
    st.session_state.aff_second_store = {
        "down_payment": 200000.0,
        "is_rental": True,
        "target_price": 500000.0,
        "manual_rent": 0.0,
        "contract_rate": float(intel.get('rates', {}).get('five_year_fixed_uninsured', 4.26)),
        "annual_prop_tax": 4500.0,
        "strata_mo": 400.0,
        "insurance_mo": 100.0,
        "vacancy_months": 1.0,
        "bc_spec_tax": 0.0,
        "vancouver_empty_tax": 0.0
    }
store = st.session_state.aff_second_store

# --- 4. DEFENSIVE MATH ENGINE ---
# Income: Aggregates T4, Bonus, and Commissions with safety defaults
p1_annual = float(prof.get('p1_t4', 0) + prof.get('p1_bonus', 0) + prof.get('p1_commission', 0))
p2_annual = float(prof.get('p2_t4', 0) + prof.get('p2_bonus', 0) + prof.get('p2_commission', 0))
rental_income_existing = float(prof.get('inv_rental_income', 0))
total_income_annual = p1_annual + p2_annual + (rental_income_existing * 0.80)
m_inc = total_income_annual / 12

# Primary Residence: Calculates current debt load from profile
m_bal = float(prof.get('m_bal', 0))
m_rate_p = (float(prof.get('m_rate', 4.0)) / 100) / 12
primary_p_i = (m_bal * m_rate_p) / (1 - (1 + m_rate_p)**-300) if m_bal > 0 else 0
primary_carrying = (float(prof.get('prop_taxes', 4200)) / 12) + float(prof.get('heat_pmt', 125))

# Liabilities: Aggregates installment debts + 3% of Revolving LOC balance
p_debts = float(prof.get('car_loan', 0) + prof.get('student_loan', 0) + prof.get('cc_pmt', 0) + (prof.get('loc_balance', 0) * 0.03))

# MAX QUALIFICATION LOGIC
stress_rate = max(5.25, store.get('contract_rate', 4.26) + 2.0)
r_stress = (stress_rate / 100) / 12
stress_k = (r_stress * (1 + r_stress)**300) / ((1 + r_stress)**300 - 1)

rental_offset = (store.get('manual_rent', 0) * 0.80) if store.get('is_rental') else 0
qual_room = (m_inc * 0.44) + rental_offset - primary_p_i - primary_carrying - p_debts - (store.get('annual_prop_tax', 4500)/12)
max_loan = qual_room / stress_k if qual_room > 0 else 0
max_affordable = custom_round_up(max_loan + store.get('down_payment', 200000))

# --- 5. UI LAYOUT ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("Portfolio Expansion Map")

st.markdown(f"""<div style="background-color: {OFF_WHITE}; padding: 15px; border-radius: 10px; border-left: 8px solid {PRIMARY_GOLD};">
    <b>Scenario Analysis:</b> Buying a second property for {household} in {province}.
</div>""", unsafe_allow_html=True)

st.divider()
c_left, c_right = st.columns(2)

with c_left:
    st.subheader("🏠 Acquisition Strategy")
    store['is_rental'] = st.toggle("Rental Property Use Case", value=store.get('is_rental', True))
    store['down_payment'] = st.number_input("Down Payment Capital ($)", value=float(store.get('down_payment', 200000)), step=5000.0)
    
    # Target Price capped by dynamic Max affordability
    store['target_price'] = st.number_input(f"Target Purchase Price (Max: ${max_affordable:,.0f})", 
                                           value=min(float(store.get('target_price', 500000)), max_affordable), 
                                           max_value=max_affordable, step=5000.0)
    
    store['contract_rate'] = st.number_input("Mortgage Contract Rate (%)", value=float(store.get('contract_rate', 4.26)), step=0.1)
    
    if store['is_rental']:
        if store.get('manual_rent', 0) == 0: 
            store['manual_rent'] = (store['target_price'] * (scraped_yield/100)) / 12
        store['manual_rent'] = st.number_input("Monthly Projected Rent ($)", value=float(store.get('manual_rent')))
        store['vacancy_months'] = st.number_input("Vacancy Months / Year", 0.0, 12.0, value=float(store.get('vacancy_months', 1.0)))

with c_right:
    st.subheader("📑 Operating Expenses")
    store['annual_prop_tax'] = st.number_input("Annual Property Tax ($)", value=float(store.get('annual_prop_tax', 4500)))
    store['strata_mo'] = st.number_input("Monthly Strata ($)", value=float(store.get('strata_mo', 400)))
    store['insurance_mo'] = st.number_input("Monthly Insurance ($)", value=float(store.get('insurance_mo', 100)))
    
    bc_extra = 0
    if province == "BC":
        with st.expander("🌲 BC Vacancy & Empty Home Taxes"):
            store['bc_spec_tax'] = st.number_input("Speculation & Vacancy Tax ($)", value=float(store.get('bc_spec_tax', 0)))
            store['vancouver_empty_tax'] = st.number_input("Vancouver Empty Homes Tax ($)", value=float(store.get('vancouver_empty_tax', 0)))
            bc_extra = (store['bc_spec_tax'] + store['vancouver_empty_tax']) / 12

# --- 6. PERFORMANCE ANALYSIS ---
target_loan = max(0, store['target_price'] - store['down_payment'])
r_contract = (store['contract_rate'] / 100) / 12
new_p_i = (target_loan * r_contract) / (1 - (1 + r_contract)**-300) if target_loan > 0 else 0

# Vacancy impact on income
realized_rent = (store['manual_rent'] * (12 - store['vacancy_months'])) / 12 if store['is_rental'] else 0
total_opex = (store['annual_prop_tax'] / 12) + store['strata_mo'] + store['insurance_mo'] + bc_extra
asset_net = realized_rent - total_opex - new_p_i

# Overall Surplus (Estimated 75% of gross income is net-of-tax)
net_h_inc = (total_income_annual * 0.75) / 12
overall_cash_flow = (net_h_inc + realized_rent) - (primary_p_i + primary_carrying + p_debts + new_p_i + total_opex)

# --- 7. UNIFIED STRATEGY METRICS ---
st.divider()
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"<b style='font-size: 0.85em;'>Asset Self-Sufficiency</b>", unsafe_allow_html=True)
    color = "#16a34a" if asset_net >= 0 else "#dc2626"
    st.markdown(f"<h3 style='color:{color}; margin-top: 0;'>${asset_net:,.0f}<small>/mo</small></h3>", unsafe_allow_html=True)
with m2:
    coc = (asset_net * 12 / store['down_payment'] * 100) if store['down_payment'] > 0 else 0
    st.markdown(f"<b style='font-size: 0.85em;'>Cash-on-Cash Return</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0;'>{coc:.1f}%</h3>", unsafe_allow_html=True)
with m3:
    safety = (overall_cash_flow / (net_h_inc + realized_rent) * 100) if (net_h_inc + realized_rent) > 0 else 0
    st.markdown(f"<b style='font-size: 0.85em;'>Household Safety Margin</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0;'>{safety:.1f}%</h3>", unsafe_allow_html=True)
with m4:
    st.markdown(f"<b style='font-size: 0.85em;'>Monthly Overall Cash Flow</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0;'>${overall_cash_flow:,.0f}</h3>", unsafe_allow_html=True)

# --- 8. RESULTS SUMMARY ---
st.divider()
s1, s2, s3 = st.columns(3)
s1.metric("Target Acquisition", f"${store['target_price']:,.0f}")
s2.metric("Qualified Max", f"${max_affordable:,.0f}")
s3.metric("New Mtg Payment (P&I)", f"${new_p_i:,.0f}")

st.caption("Analyst in a Pocket | Portfolio Expansion & Secondary Home Strategy")
