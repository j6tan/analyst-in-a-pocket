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

prof = st.session_state.get('user_profile', {})
province = prof.get('province', 'BC')
p1 = prof.get('p1_name', 'Client A')
p2 = prof.get('p2_name', 'Client B')
household = f"{p1} & {p2}".strip(" & ")

def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"rates": {"five_year_fixed_uninsured": 4.49}, "provincial_yields": {}}

intel = load_market_intel()
scraped_yield_val = intel.get("provincial_yields", {}).get(province, 3.8)

# DYNAMIC DEFAULT LOGIC
qual_purchase_baseline = 542682.0 
tax_rate = 0.0031 if province == "BC" else 0.0064 if province == "Alberta" else 0.0076

# --- 2. PERSISTENCE ---
if "aff_second_store" not in st.session_state:
    st.session_state.aff_second_store = {
        "down_payment": 200000.0,
        "is_rental": True,
        "target_price": 500000.0,
        "manual_rent": 0.0,
        "contract_rate": float(intel['rates'].get('five_year_fixed_uninsured', 4.49)),
        "annual_prop_tax": qual_purchase_baseline * tax_rate,
        "strata_mo": qual_purchase_baseline * 0.0008,
        "insurance_mo": qual_purchase_baseline * 0.0002,
        "repair_maint_mo": qual_purchase_baseline * 0.0003,
        "vacancy_months": 1.0,
        "mgmt_fee_percent": 5.0,
        "bc_spec_tax": 0.0,
        "vancouver_empty_tax": 0.0
    }

store = st.session_state.aff_second_store

# --- 3. STORYTELLING HEADER ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("The Portfolio Expansion Map")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 20px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em; letter-spacing: -0.5px;">🏢 Scenario Analysis: Secondary Home Acquisition</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Exploring the deployment of capital for either a <b>Rental Asset</b> or a <b>Secondary Family Residence</b> in {province}. 
        We test the household ecosystem for long-term viability and cash-flow impact.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 4. MATH ENGINE & SAFETY CHECKS (LINE 95 FIX) ---
# Using .get() with defaults to prevent KeyError if the profile is empty
t4_monthly = (prof.get('p1_t4', 0) + prof.get('p2_t4', 0)) / 12
personal_debts = (prof.get('car_loan', 0) + 
                 prof.get('student_loan', 0) + 
                 prof.get('cc_pmt', 0) + 
                 (prof.get('loc_balance', 0) * 0.03))

m_bal = prof.get('m_bal', 0)
m_rate_primary = (prof.get('m_rate', 4.5) / 100) / 12
p_mtg = (m_bal * m_rate_primary) / (1 - (1 + m_rate_primary)**-300) if m_bal > 0 else 0
primary_tax_heat = (prof.get('prop_taxes', 4200) / 12) + 125.0
total_obligation = p_mtg + primary_tax_heat

# Initial Max Estimation
temp_stress = max(5.25, store['contract_rate'] + 2.0)
i_stress = (temp_stress / 100) / 12
stress_factor = i_stress / (1 - (1 + i_stress)**-300)

rent_est = (qual_purchase_baseline * (scraped_yield_val / 100)) / 12
rent_offset_est = rent_est * 0.80 if store['is_rental'] else 0
qual_room_est = (t4_monthly * 0.44) + rent_offset_est - total_obligation - personal_debts - ((qual_purchase_baseline * tax_rate / 12) + 400.0)

max_purchase_limit = (qual_room_est / stress_factor) + store['down_payment'] if qual_room_est > 0 else store['down_payment']
max_purchase_limit = custom_round_up(max_purchase_limit)

# --- 5. INPUTS ---
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Capital & Use Case")
    store['is_rental'] = st.toggle("Rental Property Use Case", value=store['is_rental'])
    store['down_payment'] = st.number_input("Down Payment Capital ($)", value=float(store['down_payment']), step=5000.0)
    store['target_price'] = st.number_input("Target Purchase Price ($)", 
                                           value=min(float(store['target_price']), max_purchase_limit), 
                                           max_value=max_purchase_limit)
    store['contract_rate'] = st.number_input("Mortgage Interest Rate (%)", value=float(store['contract_rate']), step=0.1)
    
    if store['is_rental']:
        auto_rent_calc = (store['target_price'] * (scraped_yield_val / 100)) / 12
        display_rent = auto_rent_calc if store['manual_rent'] == 0 else store['manual_rent']
        store['manual_rent'] = st.number_input("Projected Monthly Rent ($)", value=float(display_rent))
        store['vacancy_months'] = st.number_input("Vacancy Months / Year", 0.0, 12.0, float(store['vacancy_months']))
        realized_rent = (store['manual_rent'] * (12 - store['vacancy_months'])) / 12
    else:
        realized_rent = 0.0
        st.info("ℹ️ Household income must support 100% of this property's carrying costs.")

with col2:
    st.subheader("🏙️ Carrying Costs")
    store['annual_prop_tax'] = st.number_input("Annual Property Tax ($)", value=float(store['annual_prop_tax']))
    store['strata_mo'] = st.number_input("Monthly Strata ($)", value=float(store['strata_mo']))
    store['insurance_mo'] = st.number_input("Monthly Insurance ($)", value=float(store['insurance_mo']))
    
    if province == "BC":
        with st.expander("🌲 BC-Specific Taxes"):
            store['bc_spec_tax'] = st.number_input("Annual Speculation & Vacancy Tax ($)", value=float(store['bc_spec_tax']))
            store['vancouver_empty_tax'] = st.number_input("Annual Empty Homes Tax ($)", value=float(store['vancouver_empty_tax']))
    
    tax_mo = (store['annual_prop_tax'] + store.get('bc_spec_tax', 0) + store.get('vancouver_empty_tax', 0)) / 12
    mgmt_mo = (store['manual_rent'] * (store['mgmt_fee_percent'] / 100)) if store['is_rental'] else 0
    total_rental_opex = tax_mo + store['strata_mo'] + store['insurance_mo'] + mgmt_mo

# --- 6. FINAL MATH ENGINE ---
target_loan = store['target_price'] - store['down_payment']
i_contract = (store['contract_rate'] / 100) / 12
new_mtg_pmt = (target_loan * i_contract) / (1 - (1 + i_contract)**-300) if target_loan > 0 else 0

# --- 7. TOP LEVEL STATS ---
st.divider()
r1, r2, r3 = st.columns(3)
r1.metric("Target Acquisition", f"${store['target_price']:,.0f}")
r2.metric("Qualified Max", f"${max_purchase_limit:,.0f}")
r3.metric("Required Financing", f"${target_loan:,.0f}")

# --- 8. CASH FLOW TABLES ---
st.subheader("📝 Monthly Household Cash Flow")
net_t4 = (t4_monthly * 12 * 0.7) / 12 # Estimated Net after tax
asset_net = realized_rent - total_rental_opex - new_mtg_pmt

c_in, c_out = st.columns(2)
with c_in:
    st.markdown("**Household Ecosystem**")
    st.table(pd.DataFrame([
        {"Item": "Net Household Income (T4+)", "Amount": f"${net_t4:,.0f}"},
        {"Item": "Primary Home & Personal Debt", "Amount": f"-${total_obligation + personal_debts:,.0f}"},
        {"Item": "Current Monthly Surplus", "Amount": f"${net_t4 - (total_obligation + personal_debts):,.0f}"}
    ]))
with c_out:
    st.markdown("**Secondary Asset Impact**")
    st.table(pd.DataFrame([
        {"Item": "Realized Rental Income", "Amount": f"${realized_rent:,.0f}"},
        {"Item": "OpEx & New Mortgage", "Amount": f"-${total_rental_opex + new_mtg_pmt:,.0f}"},
        {"Item": "Net Asset Cash Flow", "Amount": f"${asset_net:,.0f}"}
    ]))

# --- 9. STRATEGY METRICS ---
st.divider()
cash_on_cash = (asset_net * 12) / store['down_payment'] if store['down_payment'] > 0 else 0
total_in = net_t4 + realized_rent
total_out = total_obligation + personal_debts + new_mtg_pmt + total_rental_opex
overall_cash_flow = total_in - total_out
savings_rate = (overall_cash_flow / total_in) * 100 if total_in > 0 else 0

m1, m2, m3, m4 = st.columns(4)
with m1:
    color = "#16a34a" if asset_net >= 0 else "#dc2626"
    st.markdown(f"<b style='font-size: 0.9em;'>Asset Self-Sufficiency</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:{color}; margin-top: 0;'>${asset_net:,.0f}<small>/mo</small></h3>", unsafe_allow_html=True)
with m2:
    st.markdown(f"<b style='font-size: 0.9em;'>Cash-on-Cash</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0;'>{cash_on_cash:.2f}%</h3>", unsafe_allow_html=True)
with m3:
    s_color = "#16a34a" if savings_rate > 15 else "#ca8a04" if savings_rate > 5 else "#dc2626"
    st.markdown(f"<b style='font-size: 0.9em;'>Household Safety Margin</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:{s_color}; margin-top: 0;'>{savings_rate:.1f}%</h3>", unsafe_allow_html=True)
with m4:
    st.markdown(f"<b style='font-size: 0.9em;'>Overall Cash Flow</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0;'>${overall_cash_flow:,.0f}<small>/mo</small></h3>", unsafe_allow_html=True)

st.divider()
st.caption("Analyst in a Pocket | Strategic Portfolio Expansion Tool")
