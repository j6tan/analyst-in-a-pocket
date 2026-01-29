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

# --- 3. HELPERS ---
def calculate_ltt_and_fees(price, province, city, is_fthb):
    ltt_prov, ltt_mun, rebate_prov, rebate_mun = 0, 0, 0, 0
    if province == "Ontario":
        if price <= 55000: ltt_prov = price * 0.005
        elif price <= 250000: ltt_prov = 275 + (price - 55000) * 0.01
        elif price <= 400000: ltt_prov = 2225 + (price - 250000) * 0.015
        elif price <= 2000000: ltt_prov = 4475 + (price - 400000) * 0.02
        else: ltt_prov = 36475 + (price - 2000000) * 0.025
        if is_fthb: rebate_prov = min(ltt_prov, 4000)
        if city == "Toronto":
            if price <= 55000: ltt_mun = price * 0.005
            elif price <= 250000: ltt_mun = 275 + (price - 55000) * 0.01
            elif price <= 400000: ltt_mun = 2225 + (price - 250000) * 0.015
            elif price <= 2000000: ltt_mun = 4475 + (price - 400000) * 0.02
            else: ltt_mun = 36475 + (price - 2000000) * 0.025
            if is_fthb: rebate_mun = min(ltt_mun, 4475)
    elif province == "BC":
        if price <= 200000: ltt_prov = price * 0.01
        elif price <= 2000000: ltt_prov = 2000 + (price - 200000) * 0.02
        else: ltt_prov = 38000 + (price - 2000000) * 0.03
        if is_fthb:
            if price <= 500000: rebate_prov = ltt_prov
            elif price <= 525000: 
                rebate_prov = ltt_prov * ((525000 - price) / 25000)
    return (ltt_prov + ltt_mun), (rebate_prov + rebate_mun)

def calculate_min_downpayment(price):
    if price >= 1000000: return price * 0.20
    elif price <= 500000: return price * 0.05
    else: return (500000 * 0.05) + ((price - 500000) * 0.10)

# --- 4. HEADER ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("Mortgage Affordability Analysis")

# --- 5. DYNAMIC CALCULATION ENGINE (PRE-UI) ---
# We calculate the qualifying power first to drive the dynamic defaults
t4_inc = float(prof.get('p1_t4', 0) + prof.get('p2_t4', 0))
bonus_inc = float(prof.get('p1_bonus', 0) + prof.get('p1_commission', 0) + prof.get('p2_bonus', 0))
rental_inc = float(prof.get('inv_rental_income', 0))
total_qualifying = t4_inc + bonus_inc + (rental_inc * 0.80)
monthly_inc = total_qualifying / 12

# Stress Rate
c_rate = float(intel['rates'].get('five_year_fixed_uninsured', 4.49))
s_rate = max(5.25, c_rate + 2.0)

# Estimated Purchase Power for Scaling (Rough 4.5x multiplier for defaults)
est_purchase = total_qualifying * 4.5

# --- 6. INITIALIZATION ---
if "aff_store" not in st.session_state:
    st.session_state.aff_store = {
        "t4": t4_inc,
        "bonus": bonus_inc,
        "rental": rental_inc,
        "monthly_debt": float(prof.get('car_loan', 0) + prof.get('student_loan', 0) + prof.get('cc_pmt', 0)),
        "down_payment": est_purchase * 0.20, # Dynamic 20%
        "prop_taxes": est_purchase * 0.0075, # Dynamic 0.75% (Standard)
        "contract_rate": c_rate,
        "heat": est_purchase * 0.0002, # Dynamic Monthly Heat
        "strata": 400.0,
        "city": "Outside Toronto",
        "prop_type": "House / Freehold",
        "is_fthb": False
    }

store = st.session_state.aff_store

# --- 7. UI LAYOUT ---
col_1, col_2, col_3 = st.columns([1.2, 1.2, 1.5])

with col_1:
    st.subheader("💰 Income Summary")
    store['t4'] = st.number_input("Combined T4 Income", value=store['t4'])
    store['bonus'] = st.number_input("Total Additional Income", value=store['bonus'])
    store['rental'] = st.number_input("Joint Rental Income", value=store['rental'])
    
    st.markdown(f"**Qualifying Income:** <span style='font-size:1.2em; color:black;'>${total_qualifying:,.0f}</span>", unsafe_allow_html=True)

with col_2:
    st.subheader("💳 Debt & Status")
    if province == "Ontario":
        store['city'] = st.selectbox("Property City", ["Outside Toronto", "Toronto"], index=0 if store['city'] == "Outside Toronto" else 1)
    store['prop_type'] = st.selectbox("Property Type", ["House / Freehold", "Condo / Townhome"], index=0 if store['prop_type'] == "House / Freehold" else 1)
    store['monthly_debt'] = st.number_input("Monthly Debts", value=store['monthly_debt'])
    store['is_fthb'] = st.checkbox("First-Time Home Buyer?", value=store['is_fthb'])

with col_3:
    st.info("**Heuristic Scaling Active:** Down payment, Taxes, and Heat are automatically scaling based on qualifying power.")
    loc_balance = float(prof.get('loc_balance', 0))
    if loc_balance > 0:
        st.metric("LOC Impact", f"-${(loc_balance * 0.03):,.0f}")

with st.sidebar:
    st.header("⚙️ Underwriting")
    if st.button("🔄 Sync Market Rates"):
        store['contract_rate'] = c_rate
        st.rerun()
    
    store['contract_rate'] = st.number_input("Bank Contract Rate %", step=0.01, value=store['contract_rate'])
    st.warning(f"**Stress Rate:** {s_rate:.2f}%")
    
    # User can still override these, but they start at your requested %
    store['down_payment'] = st.number_input("Down Payment ($)", value=store['down_payment'])
    store['prop_taxes'] = st.number_input("Annual Property Taxes", value=store['prop_taxes'])
    store['heat'] = st.number_input("Monthly Heat", value=store['heat'])
    
    if store['prop_type'] == "Condo / Townhome":
        store['strata'] = st.number_input("Monthly Strata", value=store['strata'])
    else:
        store['strata'] = 0

# --- 8. FINAL MATH ---
loc_pmt = prof.get('loc_balance', 0) * 0.03
gds_max = (monthly_inc * 0.39) - store['heat'] - (store['prop_taxes']/12) - (store['strata'] * 0.5)
tds_max = (monthly_inc * 0.44) - store['heat'] - (store['prop_taxes']/12) - (store['strata'] * 0.5) - (store['monthly_debt'] + loc_pmt)
max_pi_stress = min(gds_max, tds_max)

if max_pi_stress > 0:
    i_stress = (s_rate/100)/12
    loan_amt = max_pi_stress * (1 - (1+i_stress)**-(25*12)) / i_stress
    i_contract = (store['contract_rate']/100)/12
    actual_pi = (loan_amt * i_contract) / (1 - (1 + i_contract)**-300) 
    
    max_purchase = loan_amt + store['down_payment']
    
    # Result Metrics
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Max Purchase Power", f"${max_purchase:,.0f}")
    with m2: st.metric("Max Loan Amount", f"${loan_amt:,.0f}")
    with m3: st.metric("Actual Monthly P&I", f"${actual_pi:,.0f}")
    with m4: st.metric("Down Payment %", f"{ (store['down_payment']/max_purchase)*100:.1f}%")

    r1, r2 = st.columns([2, 1.2])
    with r1:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=max_purchase, gauge={'axis': {'range': [0, max_purchase*1.5]}, 'bar': {'color': PRIMARY_GOLD}}))
        fig.update_layout(height=350, margin=dict(t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with r2:
        st.subheader("⚖️ Cash-to-Close")
        total_ltt, total_rebate = calculate_ltt_and_fees(max_purchase, province, store['city'], store['is_fthb'])
        costs = [{"Item": "LTT", "Cost": total_ltt}, {"Item": "Rebate", "Cost": -total_rebate}, {"Item": "Legal/Title", "Cost": 2350}]
        df_costs = pd.DataFrame(costs)
        st.table(df_costs.assign(Cost=df_costs['Cost'].map('${:,.0f}'.format)))
        st.metric("Total Liquidity", f"${(store['down_payment'] + df_costs['Cost'].sum()):,.0f}")
