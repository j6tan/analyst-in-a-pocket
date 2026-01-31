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

# --- 3. DYNAMIC LTT/PTT CALCULATOR (Fixed for Ontario) ---
def calculate_ltt_and_fees(price, province_val, is_fthb, is_toronto=False):
    tax_rules = intel.get("tax_rules", {})
    if not tax_rules: return 0.0, 0.0
    rebates = tax_rules.get("rebates", {})
    
    # Surgical Fix: Ensure "Ontario" matches regardless of profile input formatting
    lookup_key = "Ontario" if "Ontario" in str(province_val) else str(province_val).strip()
    prov_rules = tax_rules.get(lookup_key, [])
    
    total_prov_tax, prev_h = 0.0, 0.0
    for rule in prov_rules:
        # Cast to float to avoid JSON string errors
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
        elif lookup_key == "BC":
            f_lim = float(rebates.get("BC_FTHB_Threshold", 835000))
            p_lim = float(rebates.get("BC_FTHB_Partial_Limit", 860000))
            if price <= f_lim: total_rebate = total_prov_tax
            elif price <= p_lim: total_rebate = total_prov_tax * ((p_lim - price) / (p_lim - f_lim))

    return (total_prov_tax + total_muni_tax), total_rebate

def calculate_min_downpayment(price):
    if price >= 1000000: return price * 0.20
    elif price <= 500000: return price * 0.05
    else: return (500000 * 0.05) + ((price - 500000) * 0.10)

# --- 4. THE ULTIMATE SOLVER ---
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
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 5px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.5em;">{story_headline}</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">{story_body}</p>
</div>
""", unsafe_allow_html=True)

# --- 6. PERSISTENCE ---
t4_sum = float(prof.get('p1_t4', 0) + prof.get('p2_t4', 0))
bonus_sum = float(prof.get('p1_bonus', 0) + prof.get('p1_commission', 0) + prof.get('p2_bonus', 0))
rental_sum = float(prof.get('inv_rental_income', 0))
debt_sum = float(prof.get('car_loan', 0) + prof.get('student_loan', 0) + prof.get('cc_pmt', 0))

TAX_DEFAULTS = {"BC": 0.0031, "Ontario": 0.0076, "Alberta": 0.0064}
prov_tax_rate = TAX_DEFAULTS.get(province, 0.0075)

def get_defaults(t4, bonus, rental, debt, tax_rate):
    rate_val = float(intel['rates'].get('five_year_fixed_uninsured', 4.49))
    stress_val = max(5.25, rate_val + 2.0)
    qual_income = t4 + bonus + (rental * 0.80)
    max_p, min_d = solve_max_affordability(qual_income, debt, stress_val, tax_rate)
    return min_d, (max_p * tax_rate), (max_p * 0.0002)

if "aff_v_complete" not in st.session_state:
    d_dp, d_tx, d_ht = get_defaults(t4_sum, bonus_sum, rental_sum, debt_sum, prov_tax_rate)
    st.session_state.aff_v_complete = {
        "t4": t4_sum, "bonus": bonus_sum, "rental": rental_sum, "monthly_debt": debt_sum,
        "down_payment": d_dp, "prop_taxes": d_tx, "heat": d_ht, "is_fthb": False, "is_toronto": False
    }
store = st.session_state.aff_v_complete

# --- 7. INPUTS & ENGINE ---
col_1, col_2, col_3 = st.columns([1.2, 1.2, 1.5])
with col_1:
    st.subheader("💰 Income Summary")
    store['t4'] = st.number_input("Combined T4 Income", value=store['t4'], key="c_t4")
    store['bonus'] = st.number_input("Total Additional Income", value=store['bonus'], key="c_bonus")
    store['rental'] = st.number_input("Joint Rental Income", value=store['rental'], key="c_rental")
    total_qualifying = store['t4'] + store['bonus'] + (store['rental'] * 0.80)
    st.markdown(f"""<div style="margin-top: 10px;"><span style="font-size: 1.15em; color: {SLATE_ACCENT}; font-weight: bold;">Qualifying Income: </span><span style="font-size: 1.25em; color: black; font-weight: bold;">${total_qualifying:,.0f}</span></div>""", unsafe_allow_html=True)

with col_2:
    st.subheader("💳 Debt & Status")
    p_type = st.selectbox("Property Type", ["House / Freehold", "Condo / Townhome"], key="c_type")
    store['monthly_debt'] = st.number_input("Monthly Debts", value=store['monthly_debt'], key="c_debt")
    store['is_fthb'] = st.checkbox("First-Time Home Buyer?", value=store['is_fthb'], key="c_fthb")
    if province == "Ontario":
        store['is_toronto'] = st.checkbox("Within Toronto City Limits?", value=store['is_toronto'], key="c_toronto")

with col_3:
    st.info("""
    **💡 Underwriting Insights:**
    * **T4:** Banks use **100%** of base salary.
    * **Additional Income:** Usually a **2-year average**.
    * **Rental:** Typically 'haircut' to **80%**.
    """)

with st.sidebar:
    st.header("⚙️ Underwriting")
    c_rate = st.number_input("Bank Contract Rate %", value=4.49, step=0.01)
    s_rate = max(5.25, c_rate + 2.0)
    st.warning(f"**Qualifying Rate:** {s_rate:.2f}%")
    store['down_payment'] = st.number_input("Down Payment ($)", value=store['down_payment'])
    store['prop_taxes'] = st.number_input("Annual Property Taxes", value=store['prop_taxes'])
    store['heat'] = st.number_input("Monthly Heat", value=store['heat'])
    strata = st.number_input("Monthly Strata", value=400.0) if p_type == "Condo / Townhome" else 0

# --- 8. CALCULATION LOGIC ---
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
        
    total_tax, total_rebate = calculate_ltt_and_fees(max_purchase, province, store['is_fthb'], store['is_toronto'])
    
    # Cost Itemization
    legals, title, appraisal = 1500, 500, 350
    total_cash_required = store['down_payment'] + total_tax - total_rebate + legals + title + appraisal

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Max Purchase Power", f"${max_purchase:,.0f}")
    m2.metric("Max Loan Amount", f"${loan_amt:,.0f}")
    m3.metric("Stress Test P&I", f"${max_pi_stress:,.0f}")
    
    r_c1, r_c2 = st.columns([2, 1.2])
    with r_c1:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=max_purchase, gauge={'axis': {'range': [0, max_purchase*1.5]}, 'bar': {'color': PRIMARY_GOLD}}))
        fig.update_layout(height=350, margin=dict(t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)
    with r_c2:
        st.subheader("⚖️ Cash-to-Close")
        breakdown = [
            {"Item": "Down Payment", "Cost": store['down_payment']},
            {"Item": "Land Transfer Tax", "Cost": total_tax},
            {"Item": "FTHB Rebate", "Cost": -total_rebate},
            {"Item": "Legal Fees", "Cost": legals},
            {"Item": "Title / Appraisal", "Cost": (title + appraisal)}
        ]
        st.table(pd.DataFrame(breakdown).assign(Cost=lambda x: x['Cost'].map('${:,.0f}'.format)))
        st.markdown(f"""
        <div style="background-color: {PRIMARY_GOLD}; color: white; padding: 10px 15px; border-radius: 8px; text-align: center; border: 1px solid #B49A57;">
            <p style="margin: 0; font-size: 0.9em; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">Total Cash Required</p>
            <p style="margin: 0; font-size: 1.6em; font-weight: 800; line-height: 1.2;">${total_cash_required:,.0f}</p>
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
