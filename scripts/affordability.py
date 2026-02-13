import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import json
import math
from style_utils import inject_global_css

# 1. Inject the Wealthsimple-inspired Editorial CSS
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

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
prof = st.session_state.app_db.get('profile', {})
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
    if not tax_rules: return 0, 0
    rebates = tax_rules.get("rebates", {})
    
    # 1. Provincial Tax
    prov_rules = tax_rules.get(province_val, [])
    total_prov_tax, prev_h = 0, 0
    for rule in prov_rules:
        if price > prev_h:
            taxable = min(price, rule["threshold"]) - prev_h
            total_prov_tax += taxable * rule["rate"]
            prev_h = rule["threshold"]
    
    # 2. Toronto Municipal Tax (Conditional)
    total_muni_tax = 0
    if is_toronto and province_val == "Ontario":
        muni_rules = tax_rules.get("Toronto_Municipal", [])
        prev_m = 0
        for rule in muni_rules:
            if price > prev_m:
                taxable = min(price, rule["threshold"]) - prev_m
                total_muni_tax += taxable * rule["rate"]
                prev_m = rule["threshold"]

    # 3. Rebate Logic
    total_rebate = 0
    if is_fthb:
        if province_val == "Ontario":
            total_rebate += min(total_prov_tax, rebates.get("ON_FTHB_Max", 4000))
            if is_toronto:
                total_rebate += min(total_muni_tax, rebates.get("Toronto_FTHB_Max", 4475))
        elif province_val == "BC":
            fthb_limit = rebates.get("BC_FTHB_Threshold", 835000)
            partial_limit = rebates.get("BC_FTHB_Partial_Limit", 860000)
            if price <= fthb_limit: total_rebate = total_prov_tax
            elif price <= partial_limit:
                total_rebate = total_prov_tax * ((partial_limit - price) / (partial_limit - fthb_limit))

    return total_prov_tax + total_muni_tax, total_rebate

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
    # Updated logic for Lines 94-98
    if p3 >= 1000000: 
        fp, fd = p3, p3 * 0.20
    elif p2 >= 500000: 
        fp = min(p2, 999999) # Cap this tier so it doesn't cross the $1M cliff
        fd = 25000 + (fp - 500000) * 0.10
    else: 
        fp = min(p1, 499999) # Cap this tier so it doesn't cross the 5% cliff
        fd = fp * 0.05
    return fp, fd

def sync_aff_widgets():
    if 'f_dp' in st.session_state:
        st.session_state.aff_final['down_payment'] = st.session_state.f_dp
    if 'f_bonus' in st.session_state:
        st.session_state.aff_final['bonus'] = st.session_state.f_bonus
    if 'f_ptax' in st.session_state:
        st.session_state.aff_final['prop_taxes'] = st.session_state.f_ptax
    if 'f_heat' in st.session_state:
        st.session_state.aff_final['heat'] = st.session_state.f_heat

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
    story_body = f"Scaling up or relocating is a strategic play. We’ve analyzed your current income to determine how much house your wealth can truly buy in today's <b>{province}</b> market."

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 5px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.5em;">{story_headline}</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">{story_body}</p>
</div>
""", unsafe_allow_html=True)

if not is_renter:
    st.markdown(f"""
        <p style="font-size: 0.85em; color: {SLATE_ACCENT}; margin-top: 15px; margin-bottom: 15px; margin-left: 25px;">
            <i>Note: This model assumes an <b>upgrade scenario</b> where your current property is sold; existing mortgage balances are not factored into this specific qualification limit.</i>
        </p>
    """, unsafe_allow_html=True)

# --- 6. PERSISTENCE ---
# Capture all T4 and Pensions
t4_sum = float(prof.get('p1_t4', 0)) + float(prof.get('p2_t4', 0)) + float(prof.get('p1_pension', 0)) + float(prof.get('p2_pension', 0))

# Capture all Bonus, Commission, and Other
bonus_sum = float(prof.get('p1_bonus', 0)) + float(prof.get('p1_commission', 0)) + float(prof.get('p2_bonus', 0)) + float(prof.get('p2_commission', 0)) + float(prof.get('other_income', 0))

# Fixed key for rental income
rental_sum = float(prof.get('inv_rental_income', 0))

# Capture all Debts including 3% of LOC
debt_sum = (
    float(prof.get('car_loan', 0)) + 
    float(prof.get('student_loan', 0)) + 
    float(prof.get('cc_pmt', 0)) + 
    float(prof.get('support_pmt', 0)) + 
    float(prof.get('other_debt', 0)) + 
    (float(prof.get('loc_balance', 0)) * 0.03)
)
# INSERT THIS HERE: Pre-initialize widget keys to prevent 0.0 wipeouts
if 'f_dp' not in st.session_state:
    st.session_state.f_dp = 0.0
if 'f_ptax' not in st.session_state:
    st.session_state.f_ptax = 0.0
if 'f_heat' not in st.session_state:
    st.session_state.f_heat = 0.0
    
TAX_DEFAULTS = {"BC": 0.0031, "Ontario": 0.0076, "Alberta": 0.0064}
prov_tax_rate = TAX_DEFAULTS.get(province, 0.0075)
market_rate = float(intel['rates'].get('five_year_fixed_uninsured', 4.26))

def get_defaults(t4, bonus, rental, debt, tax_rate):
    rate_val = float(intel['rates'].get('five_year_fixed_uninsured', 4.26))
    stress_val = max(5.25, rate_val + 2.0)
    qual_income = t4 + bonus + (rental * 0.80)
    max_p, min_d = solve_max_affordability(qual_income, debt, stress_val, tax_rate)
    #apply custom rounding to the price first
    rounded_p = custom_round_up(max_p)
    #Calculate the legal minimum for that specific rounded price
    legal_min_dp = calculate_min_downpayment(rounded_p)
    #Add a solid $2,000 buffer to ensure it's never "just shy"
    #and round that DP up to the nearest $100
    safe_dp = math.ceil((legal_min_dp + 2000) / 100) * 100
    return float(safe_dp), custom_round_up(rounded_p * tax_rate), custom_round_up(rounded_p * 0.0002)

if "aff_final" not in st.session_state:
    # First time initialization
    d_dp, d_tx, d_ht = get_defaults(t4_sum, bonus_sum, rental_sum, debt_sum, prov_tax_rate)
    st.session_state.aff_final = {
        "t4": t4_sum, 
        "bonus": bonus_sum,
        "rental": rental_sum, 
        "monthly_debt": debt_sum,
        "down_payment": d_dp, 
        "prop_taxes": d_tx, 
        "heat": d_ht,
        "bank_rate": market_rate,
        "is_fthb": False, 
        "is_toronto": False
    }
    st.session_state.f_dp = d_dp
    st.session_state.f_ptax = d_tx
    st.session_state.f_heat = d_ht
    st.session_state.f_crate = market_rate
else:
    # Check if Profile data has actually changed
    has_changed = (
        st.session_state.aff_final.get('t4') != t4_sum or
        st.session_state.aff_final.get('bonus') != bonus_sum or
        st.session_state.aff_final.get('rental') != rental_sum or
        st.session_state.aff_final.get('monthly_debt') != debt_sum
    )

    # Sync basic basics
    st.session_state.aff_final.update({
        "t4": t4_sum, 
        "bonus": bonus_sum, 
        "rental": rental_sum, 
        "monthly_debt": debt_sum
    })
    
    if "user_has_overwritten" not in st.session_state or has_changed:
        new_dp, new_tx, new_ht = get_defaults(t4_sum, bonus_sum, rental_sum, debt_sum, prov_tax_rate)
        st.session_state.f_dp = new_dp
        st.session_state.f_ptax = new_tx
        st.session_state.f_heat = new_ht
        st.session_state.f_crate = market_rate
        st.session_state.user_has_overwritten = True
    else:
        # ENSURE f_dp and others are re-loaded from the store when you return
        st.session_state.f_dp = st.session_state.aff_final.get('down_payment', 0.0)
        st.session_state.f_ptax = st.session_state.aff_final.get('prop_taxes', 0.0)
        st.session_state.f_heat = st.session_state.aff_final.get('heat', 0.0)
        st.session_state.f_crate = st.session_state.aff_final.get('bank_rate', market_rate)

# Local helper to sync the UI back to the store
def sync_rate():
    st.session_state.aff_final['bank_rate'] = st.session_state.f_crate

# Set the local variable for the widgets
store = st.session_state.aff_final

# --- 7. UNDERWRITING ASSUMPTIONS (MOVED FROM SIDEBAR) ---
st.subheader("⚙️ Underwriting Assumptions")
uw_col1, uw_col2, uw_col3 = st.columns(3)
with uw_col1:
    c_rate = st.number_input(
        "Bank Contract Rate %", 
        step=0.01, 
        key="f_crate",
        on_change=sync_rate
    )
    s_rate = max(5.25, c_rate + 2.0)
    st.markdown(f"**Qualifying Rate:** {s_rate:.2f}%")
with uw_col2:
    store['down_payment'] = st.number_input("Down Payment ($)", key="f_dp", on_change=sync_aff_widgets)
    store['prop_taxes'] = st.number_input("Annual Property Taxes", key="f_ptax", on_change=sync_aff_widgets)
with uw_col3:
    store['heat'] = st.number_input("Monthly Heat", key="f_heat", on_change=sync_aff_widgets)
    prop_type = st.selectbox("Property Type", ["House / Freehold", "Condo / Townhome"], key="f_type")
    strata = st.number_input("Monthly Strata", value=400.0) if prop_type == "Condo / Townhome" else 0

st.divider()

# --- 8. INPUTS & UI ---
col_1, col_2, col_3 = st.columns([1.2, 1.2, 1.5])
with col_1:
    st.subheader("💰 Income Summary")
    store['t4'] = st.number_input("Combined T4 Income", value=store['t4'], key="f_t4", on_change=sync_aff_widgets)
    store['bonus'] = st.number_input("Total Additional Income", value=store['bonus'], key="f_bonus", on_change=sync_aff_widgets)
    store['rental'] = st.number_input("Joint Rental Income", value=store['rental'], key="f_rental", on_change=sync_aff_widgets)
    total_qualifying = store['t4'] + store['bonus'] + (store['rental'] * 0.80)
    st.markdown(f"""<div style="margin-top: 10px;"><span style="font-size: 1.15em; color: {SLATE_ACCENT}; font-weight: bold;">Qualifying Income: </span><span style="font-size: 1.25em; color: black; font-weight: bold;">${total_qualifying:,.0f}</span></div>""", unsafe_allow_html=True)

with col_2:
    st.subheader("💳 Debt & Status")
    store['monthly_debt'] = st.number_input("Monthly Debts", value=store['monthly_debt'], key="f_debt")
    store['is_fthb'] = st.checkbox("First-Time Home Buyer?", value=store['is_fthb'], key="f_fthb")
    if province == "Ontario":
        store['is_toronto'] = st.checkbox("Within Toronto City Limits?", value=store['is_toronto'], key="f_toronto")

with col_3:
    st.info("""
    **💡 Underwriting Insights:**
    * **T4:** Banks use **100%** of base salary.
    * **Additional Income:** Usually a **2-year average**.
    * **Rental:** Typically 'haircut' to **80%**.
    """)

# --- 9. CALCULATION LOGIC ---
monthly_inc = total_qualifying / 12
gds_max = (monthly_inc * 0.39) - store['heat'] - (store['prop_taxes']/12) - (strata*0.5)
tds_max = (monthly_inc * 0.44) - store['heat'] - (store['prop_taxes']/12) - (strata*0.5) - store['monthly_debt']
max_pi_stress = min(gds_max, tds_max)

if max_pi_stress > 0:
    # Stress Rate P&I
    r_mo_stress = (s_rate/100)/12
    raw_loan_amt = max_pi_stress * (1 - (1+r_mo_stress)**-300) / r_mo_stress
    # Applied rounding logic to loan size
    loan_amt = custom_round_up(raw_loan_amt)
    
    # Contract Rate P&I Calculation
    r_mo_contract = (c_rate/100)/12
    contract_pi = (loan_amt * r_mo_contract) / (1 - (1+r_mo_contract)**-300)
    
    max_purchase = loan_amt + store['down_payment']
    # Safety Cap: Shrink the loan if the rounded price exceeds what the DP supports
    st.session_state.aff_final['max_purchase'] = max_purchase
    st.session_state.aff_final['down_payment'] = store['down_payment']
    # Calculate requirements
    min_required = calculate_min_downpayment(max_purchase)
    is_dp_valid = store['down_payment'] >= (min_required - 1.0)
    
# 2. Validation Check
    if not is_dp_valid:
        st.error("#### 🛑 Down Payment Too Low")
    
        # Using HTML to ensure the font, colors, and $ symbols stay exactly as intended
        error_html = f"""
        <div style="background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; border: 1px solid #ffeeba; font-family: sans-serif;">
            The minimum requirement for a purchase price of 
            <strong>${max_purchase:,.0f}</strong> is 
            <strong>${min_required:,.0f}</strong>.
        </div>
        """
        st.markdown(error_html, unsafe_allow_html=True)
    
        st.stop()
        
    if is_dp_valid:
        total_tax, total_rebate = calculate_ltt_and_fees(max_purchase, province, store['is_fthb'], store.get('is_toronto', False))
    
    # Itemized Closing Costs
    legal_fees, title_ins, appraisal = 1500, 500, 350
    total_closing_costs = total_tax - total_rebate + legal_fees + title_ins + appraisal
    total_cash_required = store['down_payment'] + total_closing_costs
    
    # Monthly Home Cost calculation
    monthly_home_cost = contract_pi + (store['prop_taxes']/12) + store['heat']

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Max Purchase Power", f"${max_purchase:,.0f}")
    m2.metric("Max Loan Amount", f"${loan_amt:,.0f}")
    m3.metric("Contracted P&I", f"${contract_pi:,.0f}")
    m4.metric("Stress Test P&I", f"${max_pi_stress:,.0f}")
    
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
            {"Item": "Legal / Title / Appraisal", "Cost": (legal_fees + title_ins + appraisal)}
        ]
        st.table(pd.DataFrame(breakdown).assign(Cost=lambda x: x['Cost'].map('${:,.0f}'.format)))
        
        # TOTAL CASH REQUIRED TO CLOSE
        st.markdown(f"""
        <div style="background-color: {PRIMARY_GOLD}; color: white; padding: 10px 15px; border-radius: 8px; text-align: center; border: 1px solid #B49A57; margin-bottom: 10px;">
            <p style="margin: 0; font-size: 0.85em; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">TOTAL CASH REQUIRED TO CLOSE</p>
            <p style="margin: 0; font-size: 1.6em; font-weight: 800; line-height: 1.2;">${total_cash_required:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # MONTHLY HOME COST
        st.markdown(f"""
        <div style="background-color: #C0C0C0; color: white; padding: 10px 15px; border-radius: 8px; text-align: center; border: 1px solid #A9A9A9;">
            <p style="margin: 0; font-size: 0.85em; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">MONTHLY HOME COST</p>
            <p style="margin: 0; font-size: 1.6em; font-weight: 800; line-height: 1.2;">${monthly_home_cost:,.0f}</p>
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
st.caption("Analyst in a Pocket | Strategic Equity Strategy")






























