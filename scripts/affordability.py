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

# --- DATA RETRIEVAL: MARKET INTEL ---
def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"rates": {"five_year_fixed_uninsured": 4.49}}

intel = load_market_intel()

# --- 3. PROVINCIAL & MUNICIPAL LTT CALCULATOR ---
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

# --- 4. HEADER & STORY ---
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
    story_body = f"Scaling up or relocating is a strategic play. We’ve analyzed your current income to determine how much house your wealth can truly buy in today's <b>{province}</b> market. <br><br><i>Note: This model assumes an <b>upgrade scenario</b> where your current property is sold; existing mortgage balances are not factored into this specific qualification limit.</i>"

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 15px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.5em;">{story_headline}</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        {story_body}
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. PERSISTENCE INITIALIZATION ---
if "aff_store" not in st.session_state:
    st.session_state.aff_store = {
        "t4": float(prof.get('p1_t4', 0) + prof.get('p2_t4', 0)),
        "bonus": float(prof.get('p1_bonus', 0) + prof.get('p1_commission', 0) + prof.get('p2_bonus', 0)),
        "rental": float(prof.get('inv_rental_income', 0)),
        "monthly_debt": float(prof.get('car_loan', 0) + prof.get('student_loan', 0) + prof.get('cc_pmt', 0)),
        "down_payment": 100000.0,
        "prop_taxes": float(prof.get('prop_taxes', 4200)),
        "contract_rate": float(intel['rates'].get('five_year_fixed_uninsured', 4.49)),
        "heat": float(prof.get('heat_pmt', 125.0)),
        "strata": 400.0,
        "city": "Outside Toronto",
        "prop_type": "House / Freehold",
        "is_fthb": False
    }

store = st.session_state.aff_store

# --- 6. INPUTS & ENGINE ---
col_1, col_2, col_3 = st.columns([1.2, 1.2, 1.5])

with col_1:
    st.subheader("💰 Income Summary")
    
    t4 = st.number_input("Combined T4 Income", value=store['t4'], key="w_t4")
    store['t4'] = t4 
    
    bonus = st.number_input("Total Additional Income", value=store['bonus'], key="w_bonus")
    store['bonus'] = bonus
    
    rental = st.number_input("Joint Rental Income", value=store['rental'], key="w_rental")
    store['rental'] = rental
    
    total_qualifying = t4 + bonus + (rental * 0.80)
    
    st.markdown(f"""
        <div style="margin-top: 10px;">
            <span style="font-size: 1.15em; color: {SLATE_ACCENT}; font-weight: bold;">Qualifying Income: </span>
            <span style="font-size: 1.25em; color: black; font-weight: bold;">${total_qualifying:,.0f}</span>
        </div>
    """, unsafe_allow_html=True)

with col_2:
    st.subheader("💳 Debt & Status")
    target_city = "Outside Toronto"
    if province == "Ontario":
        city_options = ["Toronto", "Other/Outside Toronto"]
        try: city_idx = city_options.index(store['city'])
        except: city_idx = 0
        
        target_city = st.selectbox("Property City", city_options, index=city_idx, key="w_city")
        store['city'] = target_city
    
    prop_options = ["House / Freehold", "Condo / Townhome"]
    try: prop_idx = prop_options.index(store['prop_type'])
    except: prop_idx = 0
    
    prop_type = st.selectbox("Property Type", prop_options, index=prop_idx, key="w_prop_type")
    store['prop_type'] = prop_type
    
    monthly_debt = st.number_input("Monthly Debts", value=store['monthly_debt'], key="w_debt")
    store['monthly_debt'] = monthly_debt
    
    is_fthb = st.checkbox("First-Time Home Buyer?", value=store['is_fthb'], key="w_fthb")
    store['is_fthb'] = is_fthb

with col_3:
    st.info("""
    **💡 Underwriting Insights:**
    * **T4:** Banks use **100%** of base salary.
    * **Additional Income:** Usually a **2-year average**.
    * **Rental:** Typically 'haircut' to **80%**.
    """)
    loc_balance = float(prof.get('loc_balance', 0))
    if loc_balance > 0:
        loc_impact = loc_balance * 0.03
        st.metric("LOC Qualifying Hit", f"-${loc_impact:,.0f}", delta_color="inverse")

with st.sidebar:
    st.header("⚙️ Underwriting")
    
    # --- MARKET SYNC BUTTON ---
    if st.button("🔄 Sync Market Rates"):
        store['contract_rate'] = float(intel['rates'].get('five_year_fixed_uninsured', 4.49))
        st.rerun()
    
    contract_rate = st.number_input("Bank Contract Rate %", step=0.01, value=store['contract_rate'], key="w_rate")
    store['contract_rate'] = contract_rate
    
    stress_rate = max(5.25, contract_rate + 2.0)
    st.warning(f"**Qualifying Stress Rate:** {stress_rate:.2f}%")
    
    down_payment = st.number_input("Down Payment ($)", value=store['down_payment'], key="w_dp")
    store['down_payment'] = down_payment
    
    taxes = st.number_input("Annual Property Taxes", value=store['prop_taxes'], key="w_taxes")
    store['prop_taxes'] = taxes
    
    heat = st.number_input("Monthly Heat", value=store['heat'], key="w_heat")
    store['heat'] = heat
    
    if prop_type == "Condo / Townhome":
        strata = st.number_input("Monthly Strata", value=store['strata'], key="w_strata")
        store['strata'] = strata
    else:
        strata = 0

# --- IMPROVED GDS/TDS LOGIC ---
monthly_inc = total_qualifying / 12
loc_pmt = prof.get('loc_balance', 0) * 0.03

# Fixed Logic: Uses heat and taxes from inputs which are primed by the Profile page
gds_max = (monthly_inc * 0.39) - heat - (taxes/12) - (strata * 0.5)
tds_max = (monthly_inc * 0.44) - heat - (taxes/12) - (strata * 0.5) - (monthly_debt + loc_pmt)
max_pi_stress = min(gds_max, tds_max)

if max_pi_stress > 0:
    i_stress = (stress_rate/100)/12
    loan_amt = max_pi_stress * (1 - (1+i_stress)**-(25*12)) / i_stress
    i_contract = (contract_rate/100)/12
    actual_pi = (loan_amt * i_contract) / (1 - (1 + i_contract)**-300) 
    
    max_purchase = loan_amt + down_payment
    
    min_required = calculate_min_downpayment(max_purchase)
    if down_payment < min_required:
        st.error("### 🛑 Down Payment Too Low")
        st.warning(f"Based on a \${max_purchase:,.0f} purchase price, the legal minimum down payment is \${min_required:,.0f}. You are currently short \${min_required - down_payment:,.0f}.")
        st.stop()

    total_ltt, total_rebate = calculate_ltt_and_fees(max_purchase, province, target_city, is_fthb)

    st.session_state['max_purchase_power'] = float(max_purchase)
    st.session_state['affordability_down_payment'] = float(down_payment)

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Max Purchase Power", f"${max_purchase:,.0f}")
    with m2: st.metric("Max Loan Amount", f"${loan_amt:,.0f}")
    with m3: st.metric("Actual Monthly P&I", f"${actual_pi:,.0f}")
    with m4: st.metric("Stress Test P&I", f"${max_pi_stress:,.0f}")

    r1, r2 = st.columns([2, 1.2])
    with r1:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=max_purchase, gauge={'axis': {'range': [0, max_purchase*1.5]}, 'bar': {'color': PRIMARY_GOLD}}))
        fig.update_layout(height=350, margin=dict(t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with r2:
        st.subheader("⚖️ Cash-to-Close")
        breakdown = [
            {"Item": "Total Land Transfer Tax", "Cost": total_ltt},
            {"Item": "FTHB Rebate/Exemption", "Cost": -total_rebate},
            {"Item": "Legal Fees & Disbursements", "Cost": 1850},
            {"Item": "Title Insurance", "Cost": 500},
            {"Item": "Prepaid Adjustments", "Cost": 1200},
            {"Item": "Appraisal Fee", "Cost": 450}
        ]
        df_costs = pd.DataFrame(breakdown)
        st.table(df_costs.assign(Cost=df_costs['Cost'].map('${:,.0f}'.format)))
        st.metric("Total Liquidity Required", f"${(down_payment + df_costs['Cost'].sum()):,.0f}")
else:
    st.error("Approval amount is $0. Please check income vs debt levels.")

# --- FOOTER ---
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
