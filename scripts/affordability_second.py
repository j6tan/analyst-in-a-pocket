import streamlit as st
import pandas as pd
import os
import json

# --- 1. THEME & STYLING ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

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

# --- 2. PERSISTENCE ---
defaults = {
    "down_payment": 200000.0,
    "is_rental": True,
    "manual_rent": 0.0,
    "contract_rate": float(intel['rates'].get('five_year_fixed_uninsured', 4.49)),
    "annual_prop_tax": 4200.0,
    "strata_condo": 450.0,
    "insurance_mo": 100.0,
    "repair_maint_mo": 150.0,
    "vacancy_months": 1,
    "mgmt_fee_percent": 5.0
}

if "aff_second_store" not in st.session_state:
    st.session_state.aff_second_store = defaults
else:
    for k, v in defaults.items():
        if k not in st.session_state.aff_second_store:
            st.session_state.aff_second_store[k] = v

store = st.session_state.aff_second_store

# --- 3. STORYTELLING HEADER ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): 
        st.image("logo.png", width=140)
with header_col2:
    st.title("The Portfolio Expansion Map")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 20px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em; letter-spacing: -0.5px;">🏢 The Scenario: Building Beyond the Primary Home</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        <b>{p1}</b> and <b>{p2}</b> have already secured their primary residence and have successfully built up liquid capital. 
        Now, you are exploring if that capital can be deployed to acquire a rental property—turning idle savings into a cash-flowing asset. 
        Below, we test the math to see how an investment property fits into your total household ecosystem.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 4. INPUTS ---
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Capital Deployment")
    down_payment = st.number_input("Available Cash for Down Payment ($)", value=float(store['down_payment']), step=5000.0)
    store['down_payment'] = down_payment
    
    contract_rate = st.number_input("Assumed Investment Mortgage Rate (%)", value=float(store['contract_rate']), step=0.1)
    store['contract_rate'] = contract_rate
    
    stress_rate = max(5.25, contract_rate + 2.0)
    st.markdown(f"<p style='color: #6c757d; font-size: 0.85em; margin-top: -10px;'>🛡️ Bank Qualifying Rate: <b>{stress_rate:.2f}%</b></p>", unsafe_allow_html=True)

    manual_rent = st.number_input("Projected Monthly Rental Income ($)", value=float(store['manual_rent']) if store['manual_rent'] > 0 else (down_payment/0.2 * (scraped_yield_val/100))/12)
    store['manual_rent'] = manual_rent
    
    v_months = st.slider("Vacancy Provision (Months/Year)", 0, 3, int(store['vacancy_months']))
    store['vacancy_months'] = v_months

    realized_rent = (manual_rent * (12 - v_months)) / 12
    st.markdown(f"<p style='color: #1e40af; font-size: 0.95em; font-weight: 600; margin-top: -5px;'>Effective Gross Income: ${realized_rent:,.0f}/mo</p>", unsafe_allow_html=True)

with col2:
    st.subheader("🏙️ Rental Carrying Costs")
    tax_ann = st.number_input("Annual Property Tax ($)", value=float(store['annual_prop_tax']))
    strata_mo = st.number_input("Monthly Strata ($)", value=float(store['strata_condo']))
    ins_mo = st.number_input("Monthly Insurance ($)", value=float(store['insurance_mo']))
    rm_mo = st.number_input("Monthly Repairs & Maint. ($)", value=float(store['repair_maint_mo']))
    mgmt_pct = st.number_input("Management Fee (%)", value=float(store['mgmt_fee_percent']))
    
    tax_mo = tax_ann / 12
    mgmt_mo = manual_rent * (mgmt_pct / 100)
    total_rental_opex = tax_mo + strata_mo + ins_mo + rm_mo + mgmt_mo

    m_bal = prof.get('m_bal', 0)
    m_rate_primary = (prof.get('m_rate', 4.5)/100)/12
    p_mtg = (m_bal * m_rate_primary) / (1 - (1 + m_rate_primary)**-300) if m_bal > 0 else 0
    primary_tax_heat = (prof.get('prop_taxes', 4200)/12) + 125.0
    total_obligation = p_mtg + primary_tax_heat

    st.markdown(f"""
    <div style="background-color: #f8fafc; padding: 10px 15px; border-radius: 5px; border: 1px dotted #64748b; margin-top: 10px;">
        <span style="color: #475569;">Monthly Operating Expenses: </span>
        <span style="color: #475569; font-weight: 500;">${total_rental_opex:,.0f}</span>
    </div>
    """, unsafe_allow_html=True)

# --- 5. MATH ENGINE ---
t4_monthly = (prof.get('p1_t4', 0) + prof.get('p2_t4', 0)) / 12
i_stress = (stress_rate / 100) / 12
stress_factor = i_stress / (1 - (1 + i_stress)**-300)
personal_debts = prof.get('car_loan',0) + prof.get('student_loan',0) + prof.get('cc_pmt',0) + (prof.get('loc_balance',0)*0.03)

rent_offset = realized_rent * 0.80 
qualifying_room = (t4_monthly * 0.44) + rent_offset - total_obligation - personal_debts - (tax_mo + strata_mo + 125.0)

if qualifying_room > 0:
    max_loan = qualifying_room / stress_factor
    final_purchase = max_loan + down_payment
    final_loan = final_purchase - down_payment
    i_contract = (contract_rate/100)/12
    new_mtg_pmt = (final_loan * i_contract) / (1 - (1 + i_contract)**-300)

    # --- 6. TOP LEVEL STATS ---
    st.divider()
    r1, r2, r3 = st.columns(3)
    r1.metric("Maximum Acquisition", f"${final_purchase:,.0f}")
    r2.metric("Required Financing", f"${final_loan:,.0f}")
    r3.metric("Stabilized Rent", f"${realized_rent:,.0f}")

    # --- 7. CASH FLOW TABLES ---
    st.subheader("📝 Monthly Household Cash Flow")
    net_t4 = (t4_monthly * 12 * 0.7) / 12
    total_in = net_t4 + realized_rent
    total_out = total_obligation + personal_debts + new_mtg_pmt + total_rental_opex
    
    c_in, c_out = st.columns(2)
    c_in.table(pd.DataFrame([{"Item": "Net Employment Income", "Amount": f"${net_t4:,.0f}"}, {"Item": "Realized Rental Income", "Amount": f"${realized_rent:,.0f}"}]))
    c_out.table(pd.DataFrame([{"Item": "Current Home & Personal Debt", "Amount": f"${total_obligation + personal_debts:,.0f}"}, {"Item": "New Rental Mortgage", "Amount": f"${new_mtg_pmt:,.0f}"}, {"Item": "Rental OpEx", "Amount": f"${total_rental_opex:,.0f}"}]))

    # --- 8. STRATEGY METRICS ---
    st.divider()
    rental_net_mo = realized_rent - total_rental_opex - new_mtg_pmt
    cash_on_cash = (rental_net_mo * 12) / down_payment if down_payment > 0 else 0
    savings_rate = ((total_in - total_out) / total_in) * 100 if total_in > 0 else 0

    m1, m2, m3 = st.columns(3)
    with m1:
        color = "#16a34a" if rental_net_mo > 0 else "#dc2626"
        st.markdown(f"<b style='font-size: 1.1em;'>Asset Self-Sufficiency</b>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='color:{color}; margin-top: 2px; margin-bottom: 0;'>${rental_net_mo:,.0f}<small>/mo</small></h2>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<b style='font-size: 1.1em;'>Cash-on-Cash Return</b>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='margin-top: 2px; margin-bottom: 0;'>{cash_on_cash:.2f}%</h2>", unsafe_allow_html=True)
    with m3:
        s_color = "#16a34a" if savings_rate > 15 else "#ca8a04" if savings_rate > 5 else "#dc2626"
        st.markdown(f"<b style='font-size: 1.1em;'>Household Safety Margin</b>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='color:{s_color}; margin-top: 2px; margin-bottom: 0;'>{savings_rate:.1f}%</h2>", unsafe_allow_html=True)

    # --- 9. TIGHTENED DIAGNOSIS BOX ---
    st.markdown("---")
    if savings_rate < 8:
        status, t_color, b_color = "⚠️ HIGH RISK", "#dc2626", "#FFF5F5"
        msg = "The household margin is thin. One major repair or vacancy month creates a deficit."
    elif rental_net_mo < 0:
        status, t_color, b_color = "💸 NEGATIVE CASH FLOW", "#8b5cf6", "#F5F3FF"
        msg = "The asset is not self-sustaining. Your T4 income is subsidizing this investment."
    else:
        status, t_color, b_color = "✅ STRATEGIC SURPLUS", "#16a34a", "#F0FDF4"
        msg = "This asset is self-sustaining and you maintain a healthy household safety buffer."

    st.markdown(f"""
    <div style="background-color: {b_color}; padding: 8px 15px; border-radius: 8px; border: 1.5px solid {t_color}; text-align: center; max-width: 650px; margin: 0 auto; line-height: 1.1;">
        <h3 style="color: {t_color}; margin: 0; font-size: 1.25em;">{status}</h3>
        <p style="color: {SLATE_ACCENT}; font-size: 0.95em; margin: 3px 0;">{msg}</p>
        <p style="font-size: 1.1em; color: #475569; margin: 5px 0 0 0; padding-top: 5px; border-top: 1px solid {t_color}33;">
            Net Monthly Household Surplus: <b style="color: {SLATE_ACCENT};">${(total_in - total_out):,.0f}</b>
        </p>
    </div>
    """, unsafe_allow_html=True)

else:
    st.error("🛑 Qualifying Room: $0. Total debt load exceeds maximum bank ratios.")

# --- 12. LEGAL DISCLAIMER ---
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

st.caption("Analyst in a Pocket | Strategic Debt Planning & Equity Strategy")