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
# SMART MATCH: Clean the province string to prevent $0 tax errors
province_raw = prof.get('province', 'Ontario')
province = str(province_raw).strip() 
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

# --- 3. DYNAMIC LTT/PTT CALCULATOR (Fixed for Ontario) ---
def calculate_ltt_and_fees(price, province_val, city_val, is_fthb):
    ltt_prov, ltt_mun, rebate_prov, rebate_mun = 0.0, 0.0, 0.0, 0.0
    
    # Clean strings for strict comparison
    p_clean = str(province_val).strip()
    c_clean = str(city_val).strip()

    if p_clean == "Ontario":
        # Provincial Tax Brackets
        if price <= 55000: ltt_prov = price * 0.005
        elif price <= 250000: ltt_prov = 275 + (price - 55000) * 0.01
        elif price <= 400000: ltt_prov = 2225 + (price - 250000) * 0.015
        elif price <= 2000000: ltt_prov = 4475 + (price - 400000) * 0.02
        else: ltt_prov = 36475 + (price - 2000000) * 0.025
        
        if is_fthb: rebate_prov = min(ltt_prov, 4000.0)
        
        # Municipal Tax Brackets (Toronto)
        if c_clean == "Toronto":
            if price <= 55000: ltt_mun = price * 0.005
            elif price <= 250000: ltt_mun = 275 + (price - 55000) * 0.01
            elif price <= 400000: ltt_mun = 2225 + (price - 250000) * 0.015
            elif price <= 2000000: ltt_mun = 4475 + (price - 400000) * 0.02
            else: ltt_mun = 36475 + (price - 2000000) * 0.025
            
            if is_fthb: rebate_mun = min(ltt_mun, 4475.0)

    elif p_clean == "BC":
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
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">{story_body}</p>
</div>
""", unsafe_allow_html=True)

# --- 5. PERSISTENCE ---
if "aff_v_final" not in st.session_state:
    st.session_state.aff_v_final = {
        "t4": float(prof.get('p1_t4', 0) + prof.get('p2_t4', 0)),
        "bonus": float(prof.get('p1_bonus', 0) + prof.get('p1_commission', 0) + prof.get('p2_bonus', 0)),
        "rental": float(prof.get('inv_rental_income', 0)),
        "monthly_debt": float(prof.get('car_loan', 0) + prof.get('student_loan', 0) + prof.get('cc_pmt', 0)),
        "down_payment": 100000.0, "prop_taxes": 5000.0, "heat": 125.0, "contract_rate": 4.49,
        "is_fthb": False, "city": "Other/Outside Toronto", "prop_type": "House / Freehold"
    }
store = st.session_state.aff_v_final

# --- 6. INPUTS & ENGINE ---
col_1, col_2, col_3 = st.columns([1.2, 1.2, 1.5])
with col_1:
    st.subheader("💰 Income Summary")
    store['t4'] = st.number_input("Combined T4 Income", value=store['t4'], key="f_t4")
    store['bonus'] = st.number_input("Total Additional Income", value=store['bonus'], key="f_bonus")
    store['rental'] = st.number_input("Joint Rental Income", value=store['rental'], key="f_rental")
    total_qualifying = store['t4'] + store['bonus'] + (store['rental'] * 0.80)
    st.markdown(f"""<div style="margin-top: 10px;"><span style="font-size: 1.15em; color: {SLATE_ACCENT}; font-weight: bold;">Qualifying Income: </span><span style="font-size: 1.25em; color: black; font-weight: bold;">${total_qualifying:,.0f}</span></div>""", unsafe_allow_html=True)

with col_2:
    st.subheader("💳 Debt & Status")
    store['prop_type'] = st.selectbox("Property Type", ["House / Freehold", "Condo / Townhome"], key="f_type")
    store['monthly_debt'] = st.number_input("Monthly Debts", value=store['monthly_debt'], key="f_debt")
    store['is_fthb'] = st.checkbox("First-Time Home Buyer?", value=store['is_fthb'], key="f_fthb")
    if province == "Ontario":
        store['city'] = st.selectbox("Property City", ["Toronto", "Other/Outside Toronto"], key="f_city")

with col_3:
    st.info("""
    **💡 Underwriting Insights:**
    * **T4:** Banks use **100%** of base salary.
    * **Additional Income:** Usually a **2-year average**.
    * **Rental:** Typically 'haircut' to **80%**.
    """)

with st.sidebar:
    st.header("⚙️ Underwriting")
    c_rate = st.number_input("Bank Contract Rate %", value=store['contract_rate'], step=0.01)
    s_rate = max(5.25, c_rate + 2.0)
    st.warning(f"**Qualifying Rate:** {s_rate:.2f}%")
    store['down_payment'] = st.number_input("Down Payment ($)", value=store['down_payment'])
    store['prop_taxes'] = st.number_input("Annual Property Taxes", value=store['prop_taxes'])
    store['heat'] = st.number_input("Monthly Heat", value=store['heat'])
    strata = st.number_input("Monthly Strata", value=400.0) if store['prop_type'] == "Condo / Townhome" else 0

# --- 7. CALCULATION LOGIC ---
monthly_inc = total_qualifying / 12
gds_max = (monthly_inc * 0.39) - store['heat'] - (store['prop_taxes']/12) - (strata*0.5)
tds_max = (monthly_inc * 0.44) - store['heat'] - (store['prop_taxes']/12) - (strata*0.5) - store['monthly_debt']
max_pi_stress = min(gds_max, tds_max)

if max_pi_stress > 0:
    r_mo = (s_rate/100)/12
    loan_amt = max_pi_stress * (1 - (1+r_mo)**-300) / r_mo
    max_purchase = loan_amt + store['down_payment']
    min_required = calculate_min_downpayment(max_purchase)
    
    if store['down_payment'] < min_required - 1.0: 
        st.error(f"### 🛑 Down Payment Too Low. Legal min for ${max_purchase:,.0f} is ${min_required:,.0f}")
        st.stop()
        
    total_tax, total_rebate = calculate_ltt_and_fees(max_purchase, province, store.get('city', 'Other'), store['is_fthb'])
    
    # Costs Itemization
    legals, title, appraisal = 1500, 500, 350
    total_closing = total_tax - total_rebate + legals + title + appraisal
    total_cash_required = store['down_payment'] + total_closing

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Max Purchase Power", f"${max_purchase:,.0f}")
    m2.metric("Max Loan Amount", f"${loan_amt:,.0f}")
    m3.metric("Stress Test P&I", f"${max_pi_stress:,.0f}")
    
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
            {"Item": "Closing Fees*", "Cost": (legals + title + appraisal)}
        ]
        st.table(pd.DataFrame(breakdown).assign(Cost=lambda x: x['Cost'].map('${:,.0f}'.format)))
        st.markdown(f"""
        <div style="background-color: {PRIMARY_GOLD}; color: white; padding: 10px 15px; border-radius: 8px; text-align: center; border: 1px solid #B49A57;">
            <p style="margin: 0; font-size: 0.9em; font-weight: bold; text-transform: uppercase;">Total Cash Required</p>
            <p style="margin: 0; font-size: 1.6em; font-weight: 800;">${total_cash_required:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)
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
st.caption("Analyst in a Pocket | Strategic Debt Planning & Equity Strategy")
