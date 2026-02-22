import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import os
import base64
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, load_user_data, init_session_state

# --- 1. UNIVERSAL AUTO-LOADER ---
init_session_state()
if st.session_state.get('username') and not st.session_state.app_db.get('profile', {}).get('p1_name'):
    with st.spinner("🔄 restoring your data..."):
        load_user_data(st.session_state.username)
        time.sleep(0.1)
        st.rerun()

inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 2. THEME VARIABLES ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"

# --- 3. DATA INIT & SMART GREETING ---
prof = st.session_state.app_db.get('profile', {})
rc_data = st.session_state.app_db.get('retire_calc', {})

if 'tfsa_rrsp' not in st.session_state.app_db:
    st.session_state.app_db['tfsa_rrsp'] = {}
tr_data = st.session_state.app_db['tfsa_rrsp']

# Smart Name Formatting
p1_raw = prof.get('p1_name', '').strip() if isinstance(prof.get('p1_name'), str) else ''
p2_raw = prof.get('p2_name', '').strip() if isinstance(prof.get('p2_name'), str) else ''
greeting_names = f"{p1_raw} & {p2_raw}" if p1_raw and p2_raw else (p1_raw or "Primary Client")

# Estimate current income
current_t4 = float(prof.get('p1_t4', 0)) + float(prof.get('p1_bonus', 0)) + float(prof.get('p1_commission', 0))
if current_t4 == 0: current_t4 = 90000.0

# Estimate retirement income (from Retire Calc target spend, or default)
retire_inc = float(rc_data.get('monthly_income', 5000)) * 12

# Simple Marginal Tax Estimator (Rough Canadian Averages)
def get_estimated_tax_rate(income):
    if income <= 55867: return 20.0
    elif income <= 111733: return 31.0
    elif income <= 173205: return 40.0
    elif income <= 246752: return 46.0
    else: return 53.0

# Inject safe defaults
if not tr_data.get('initialized'):
    tr_data['current_income'] = current_t4
    tr_data['retire_income'] = retire_inc
    tr_data['invest_amt'] = 10000.0
    tr_data['years'] = 20.0
    tr_data['expected_return'] = 7.0
    tr_data['initialized'] = True

# --- 4. INLINE LOGO & TITLE ---
def get_inline_logo(img_name="logo.png", width=75):
    img_path = img_name
    if not os.path.exists(img_path):
        img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), img_name)
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{encoded}" style="width: {width}px; flex-shrink: 0;">'
    return "<span style='font-size: 50px;'>🔥</span>"

logo_html = get_inline_logo(width=75)

st.markdown(f"""
    <div style='display: flex; align-items: center; justify-content: flex-start; gap: 15px; margin-top: -20px; margin-bottom: 25px;'>
        {logo_html}
        <h1 style='margin: 0 !important; padding: 0 !important; line-height: 1 !important;'>TFSA vs. RRSP Optimizer</h1>
    </div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">🍁 The Ultimate Tax Showdown</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Welcome back, <b>{greeting_names}</b>. Should your next dollar go into your TFSA or your RRSP? To make this a fair fight, this calculator assumes that if you use an RRSP, you <b>reinvest your tax refund</b> right back into the market.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. INPUT VARIABLES ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("💼 The Tax Variables")
    current_income = cloud_input("Current Annual Income ($)", "tfsa_rrsp", "current_income", step=5000, help="Used to calculate your tax bracket today.")
    retire_income = cloud_input("Expected Retirement Income ($)", "tfsa_rrsp", "retire_income", step=5000, help="Used to calculate your tax bracket when you withdraw the money.")
    
    # Auto-calculate rates
    curr_rate = get_estimated_tax_rate(current_income)
    ret_rate = get_estimated_tax_rate(retire_income)
    
    st.info(f"**Estimated Marginal Rates:**\n* Today: **{curr_rate}%**\n* In Retirement: **{ret_rate}%**")

with col2:
    st.subheader("📈 The Investment Variables")
    invest_amt = cloud_input("After-Tax Cash to Invest ($)", "tfsa_rrsp", "invest_amt", step=1000, help="How much cash is sitting in your bank account right now ready to deploy?")
    years = cloud_input("Years to Grow", "tfsa_rrsp", "years", step=1)
    expected_return = cloud_input("Expected Annual Return (%)", "tfsa_rrsp", "expected_return", step=0.1)

# --- 6. CORE MATH ENGINE ---
# 1. TFSA Math (Simple)
tfsa_deposit = invest_amt
tfsa_future_value = tfsa_deposit * ((1 + (expected_return / 100)) ** years)
tfsa_net = tfsa_future_value # Tax-free withdrawal

# 2. RRSP Math (The Gross-Up)
# If you have $10,000 after-tax, its pre-tax equivalent is: $10,000 / (1 - marginal_tax_rate)
# This perfectly mimics depositing $10k, getting a refund, reinvesting it, getting a refund on the refund, etc.
rrsp_deposit = invest_amt / (1 - (curr_rate / 100)) if curr_rate < 100 else invest_amt
rrsp_future_value = rrsp_deposit * ((1 + (expected_return / 100)) ** years)
rrsp_taxes_owed = rrsp_future_value * (ret_rate / 100)
rrsp_net = rrsp_future_value - rrsp_taxes_owed

# The Verdict
diff = abs(rrsp_net - tfsa_net)
if rrsp_net > tfsa_net:
    winner = "RRSP"
    winner_color = "#5cb85c" # Green
elif tfsa_net > rrsp_net:
    winner = "TFSA"
    winner_color = PRIMARY_GOLD
else:
    winner = "TIE (Mathematically Identical)"
    winner_color = CHARCOAL

# --- 7. VISUALS & DASHBOARD ---
st.divider()

st.markdown(f"""
<div style="text-align: center; margin-bottom: 30px;">
    <h2 style="color: {SLATE_ACCENT}; margin-bottom: 5px;">🏆 The Winner is the <span style="color: {winner_color};">{winner}</span></h2>
    <p style="font-size: 1.1em; color: {SLATE_ACCENT};">By choosing the {winner}, you will have <b>${diff:,.0f} more</b> in after-tax wealth.</p>
</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    st.markdown(f"""
    <div style="background-color: {OFF_WHITE}; padding: 20px; border-radius: 10px; border: 2px solid {PRIMARY_GOLD}; text-align: center; height: 100%;">
        <h3 style="margin-top:0; color: {CHARCOAL};">TFSA Strategy</h3>
        <p style="color: {SLATE_ACCENT}; margin-bottom: 5px;">Starting Deposit (After-Tax): <b>${tfsa_deposit:,.0f}</b></p>
        <p style="color: {SLATE_ACCENT}; margin-bottom: 5px;">Taxes Owed at Retirement: <b>$0</b></p>
        <h2 style="color: {PRIMARY_GOLD}; margin-top: 15px;">Net: ${tfsa_net:,.0f}</h2>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div style="background-color: {OFF_WHITE}; padding: 20px; border-radius: 10px; border: 2px solid #5cb85c; text-align: center; height: 100%;">
        <h3 style="margin-top:0; color: {CHARCOAL};">RRSP Strategy</h3>
        <p style="color: {SLATE_ACCENT}; margin-bottom: 5px; font-size: 0.9em;"><i>*Assumes tax refund is reinvested</i></p>
        <p style="color: {SLATE_ACCENT}; margin-bottom: 5px;">Starting Deposit (Grossed-Up): <b>${rrsp_deposit:,.0f}</b></p>
        <p style="color: #d9534f; margin-bottom: 5px;">Taxes Owed at Retirement: <b>-${rrsp_taxes_owed:,.0f}</b></p>
        <h2 style="color: #5cb85c; margin-top: 15px;">Net: ${rrsp_net:,.0f}</h2>
    </div>
    """, unsafe_allow_html=True)

# THE CHART
st.write("")
st.subheader("📊 Net Wealth Projection")
chart_data = pd.DataFrame({
    "Strategy": ["TFSA (Tax-Free Growth)", "RRSP (Tax-Deferred + Refund)"],
    "Net After-Tax Wealth": [tfsa_net, rrsp_net]
})

fig = go.Figure(data=[
    go.Bar(
        x=chart_data["Strategy"], 
        y=chart_data["Net After-Tax Wealth"],
        marker_color=[PRIMARY_GOLD, '#5cb85c'],
        text=chart_data["Net After-Tax Wealth"].apply(lambda x: f"${x:,.0f}"),
        textposition='auto',
        width=0.4
    )
])

fig.update_layout(
    yaxis_title="Net Walk-Away Wealth ($)",
    height=400,
    margin=dict(t=20, b=20, l=0, r=0),
    plot_bgcolor="white"
)
st.plotly_chart(fig, use_container_width=True)

# THE IRONCLAD RULE EXPLANATION
st.info("""
**💡 The Ironclad Rule of Canadian Investing:** If your tax bracket is **higher** today than it will be in retirement, the **RRSP** wins. 
If your tax bracket is **lower** today than it will be in retirement, the **TFSA** wins. 
If your tax bracket stays exactly the **same**, they tie!
""")

# --- 8. ERRORS & OMISSIONS DISCLAIMER ---
show_disclaimer()

# --- FOOTER ---
st.markdown("""
    <div style="text-align: center; color: #adb5bd; font-size: 0.85em; margin-top: 50px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        &copy; 2026 FIRE Calculator. All rights reserved. <br>
        <span style="font-size: 0.9em; font-style: italic;">Empowering Canadian professionals to build wealth.</span>
    </div>
""", unsafe_allow_html=True)
