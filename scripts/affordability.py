import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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

# --- 3. SIDEBAR CALCULATIONS ---
with st.sidebar:
    st.header("🛠️ Scenario Tuning")
    
    if 'aff_store' not in st.session_state:
        # Initial defaults
        st.session_state.aff_store = {
            'down_payment': 200000.0,
            'contract_rate': float(intel['rates'].get('five_year_fixed_uninsured', 4.49)),
            'prop_taxes': 4200.0,
            'heat_pmt': 125.0
        }
    
    store = st.session_state.aff_store

    # PATCHED: User can update Down Payment and values stay per actual input
    store['down_payment'] = st.number_input("Down Payment Capital ($)", value=float(store['down_payment']), step=1000.0)
    store['contract_rate'] = st.number_input("Mortgage Rate (%)", value=float(store['contract_rate']), step=0.01)
    store['prop_taxes'] = st.number_input("Annual Property Taxes ($)", value=float(store['prop_taxes']), step=10.0)
    store['heat_pmt'] = st.number_input("Monthly Heat Cost ($)", value=float(store['heat_pmt']), step=5.0)

# --- 4. QUALIFICATION LOGIC ---
def get_float(k, d=0.0):
    try: return float(prof.get(k, d))
    except: return d

p1_inc = get_float('p1_t4') + get_float('p1_bonus') + get_float('p1_commission')
p2_inc = get_float('p2_t4') + get_float('p2_bonus') + get_float('p2_commission')
rental_inc = get_float('inv_rental_income') * 0.80
total_gross_mo = (p1_inc + p2_inc + rental_inc) / 12

monthly_debts = (
    get_float('car_loan') + 
    get_float('student_loan') + 
    get_float('cc_pmt') + 
    (get_float('loc_balance') * 0.03)
)

stress_rate = max(5.25, store['contract_rate'] + 2.0)
r_stress = (stress_rate / 100) / 12
k_stress = (r_stress * (1 + r_stress)**300) / ((1 + r_stress)**300 - 1)

available_for_housing = (total_gross_mo * 0.44) - monthly_debts
monthly_taxes_heat = (store['prop_taxes'] / 12) + store['heat_pmt']
qualifying_mortgage_pmt = available_for_housing - monthly_taxes_heat

max_loan = qualifying_mortgage_pmt / k_stress if qualifying_mortgage_pmt > 0 else 0
max_purchase = max_loan + store['down_payment']

# PATCHED: Min Down Payment Calculation
def calculate_min_down(price):
    if price <= 500000: return price * 0.05
    elif price <= 999999.99: return (500000 * 0.05) + ((price - 500000) * 0.10)
    else: return price * 0.20

legal_min_down = calculate_min_down(max_purchase)

# --- 5. DISPLAY ---
st.title("The Opportunity Map")
st.markdown(f"### Analysis for {household}")

if max_purchase > 0:
    # PATCHED: Down Payment Check
    if store['down_payment'] < legal_min_down:
        st.error(f"🛑 **Down payment too low.** Based on a purchase price of ${max_purchase:,.0f}, the legal minimum requirement is **${legal_min_down:,.2f}**.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Max Purchase Power", f"${custom_round_up(max_purchase):,.0f}")
    col2.metric("Qualifying Mortgage", f"${max_loan:,.0f}")
    col3.metric("Stress Test Rate", f"{stress_rate:.2f}%")

    st.session_state['max_purchase_power'] = max_purchase
    st.session_state['affordability_down_payment'] = store['down_payment']

    # Closing & Carrying Costs
    land_transfer_tax = 12000 
    legal_fees = 1500.0
    total_cash_required = store['down_payment'] + land_transfer_tax + legal_fees

    r_contract = (store['contract_rate'] / 100) / 12
    actual_pmt = (max_loan * r_contract) / (1 - (1 + r_contract)**-300)
    total_monthly_expense = actual_pmt + monthly_taxes_heat

    st.divider()
    res_col1, res_col2 = st.columns(2)
    
    with res_col1:
        st.subheader("🏦 Mortgage & Equity")
        fig = go.Figure(go.Pie(
            labels=['Mortgage Amount', 'Your Down Payment'],
            values=[max_loan, store['down_payment']],
            hole=.4,
            marker_colors=[SLATE_ACCENT, PRIMARY_GOLD]
        ))
        fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=250)
        st.plotly_chart(fig, use_container_width=True)

    with res_col2:
        st.subheader("💰 Cash & Carrying Costs")
        
        st.markdown(f"""
        <div style="background-color: {OFF_WHITE}; padding: 10px 15px; border-radius: 8px; text-align: center; border: 1px solid #B49A57; margin-bottom: 10px;">
            <p style="margin: 0; font-size: 0.85em; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; color: {SLATE_ACCENT};">Total Cash Required at Closing</p>
            <p style="margin: 0; font-size: 1.6em; font-weight: 800; line-height: 1.2; color: {SLATE_ACCENT};">${total_cash_required:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background-color: {SLATE_ACCENT}; color: white; padding: 10px 15px; border-radius: 8px; text-align: center; border: 1px solid #33363F;">
            <p style="margin: 0; font-size: 0.85em; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">Estimated Monthly Ownership Expense</p>
            <p style="margin: 0; font-size: 1.6em; font-weight: 800; line-height: 1.2;">${total_monthly_expense:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

else: st.error("Approval amount is $0.")

# --- 6. LEGAL DISCLAIMER ---
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
