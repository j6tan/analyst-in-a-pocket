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
RRSP_COLOR = "#706262"     
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"
WINNER_GLOW = "#FF9800"    

# --- 3. DATA INIT & SMART GREETING ---
prof = st.session_state.app_db.get('profile', {})
rc_data = st.session_state.app_db.get('retire_calc', {})

if 'tfsa_rrsp' not in st.session_state.app_db:
    st.session_state.app_db['tfsa_rrsp'] = {}
tr_data = st.session_state.app_db['tfsa_rrsp']

p1_raw = prof.get('p1_name', '').strip() if isinstance(prof.get('p1_name'), str) else ''
p2_raw = prof.get('p2_name', '').strip() if isinstance(prof.get('p2_name'), str) else ''
greeting_names = f"{p1_raw} & {p2_raw}" if p1_raw and p2_raw else (p1_raw or "Primary Client")

current_t4 = float(prof.get('p1_t4', 0)) + float(prof.get('p1_bonus', 0)) + float(prof.get('p1_commission', 0))
if current_t4 == 0: current_t4 = 90000.0

def get_marginal_tax_rate(income):
    if income <= 55867: return 20.0
    elif income <= 111733: return 31.0
    elif income <= 173205: return 40.0
    elif income <= 246752: return 46.0
    else: return 53.0

if not tr_data.get('initialized'):
    tr_data['current_income'] = current_t4
    tr_data['invest_amt'] = 10000.0
    tr_data['annual_invest'] = 5000.0
    tr_data['years'] = 20.0
    tr_data['expected_return'] = 7.0
    tr_data['initialized'] = True

# Ensure new variables exist to prevent errors
if 'base_income' not in tr_data: tr_data['base_income'] = 25000.0
if 'swr' not in tr_data: tr_data['swr'] = 4.0

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
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">🍁 The Decumulation Engine</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Welcome back, <b>{greeting_names}</b>. Real retirees don't cash out their portfolios on day one. This advanced FIRE calculator models your accumulation phase, and then simulates your <b>Annual Drawdown</b>, exposing exactly how RRSP withdrawals trigger income taxes and government benefit clawbacks.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. INPUT VARIABLES ---
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("💼 The Tax Variables")
    current_income = cloud_input("Current Annual Income ($)", "tfsa_rrsp", "current_income", step=5000, help="Determines the Marginal tax refund you get today.")
    base_income = cloud_input("Base Retirement Income ($)", "tfsa_rrsp", "base_income", step=2000, help="Your estimated CPP, OAS, Pensions, or part-time work.")
    curr_rate = get_marginal_tax_rate(current_income)
    st.info(f"Today's Marginal Refund Rate: **{curr_rate}%**")

with col2:
    st.subheader("📈 The Accumulation")
    invest_amt = cloud_input("Initial Lump Sum ($)", "tfsa_rrsp", "invest_amt", step=1000)
    annual_invest = cloud_input("Annual Contribution ($)", "tfsa_rrsp", "annual_invest", step=1000)
    years = cloud_input("Years to Grow", "tfsa_rrsp", "years", step=1)

with col3:
    st.subheader("🏖️ The Drawdown")
    expected_return = cloud_input("Expected Return (%)", "tfsa_rrsp", "expected_return", step=0.1)
    swr = cloud_input("Safe Withdrawal Rate (%)", "tfsa_rrsp", "swr", step=0.1, help="The percentage of the portfolio you will withdraw annually.")

# --- 6. CORE MATH ENGINE ---
r = expected_return / 100
t = int(years)
swr_rate = swr / 100

# Accumulation (Gross Values)
tfsa_gross = (invest_amt * ((1 + r) ** t)) + (annual_invest * (((1 + r) ** t - 1) / r)) if r > 0 else invest_amt + (annual_invest * t)

tax_factor = (1 - (curr_rate / 100)) if curr_rate < 100 else 1
rrsp_deposit = invest_amt / tax_factor
rrsp_annual = annual_invest / tax_factor
rrsp_gross = (rrsp_deposit * ((1 + r) ** t)) + (rrsp_annual * (((1 + r) ** t - 1) / r)) if r > 0 else rrsp_deposit + (rrsp_annual * t)

# Decumulation (Year 1 Retirement Drawdown)
tfsa_withdraw = tfsa_gross * swr_rate
rrsp_withdraw = rrsp_gross * swr_rate

def get_tax(income):
    if income <= 55867: return income * 0.20
    elif income <= 111733: return (55867 * 0.20) + ((income - 55867) * 0.31)
    elif income <= 173205: return (55867 * 0.20) + (55866 * 0.31) + ((income - 111733) * 0.40)
    elif income <= 246752: return (55867 * 0.20) + (55866 * 0.31) + (61472 * 0.40) + ((income - 173205) * 0.46)
    else: return (55867 * 0.20) + (55866 * 0.31) + (61472 * 0.40) + (73547 * 0.46) + ((income - 246752) * 0.53)

# Calculate exactly how much tax is generated BY the RRSP withdrawal
base_tax = get_tax(base_income)
total_tax = get_tax(base_income + rrsp_withdraw)
rrsp_income_tax = total_tax - base_tax

# Calculate Hidden Taxes (Clawbacks based on 2026 Thresholds)
OAS_THRESHOLD = 95323
GIS_THRESHOLD = 22488

oas_clawback = 0
if (base_income + rrsp_withdraw) > OAS_THRESHOLD:
    excess = (base_income + rrsp_withdraw) - max(OAS_THRESHOLD, base_income)
    oas_clawback = excess * 0.15

gis_clawback = 0
if base_income < GIS_THRESHOLD:
    gis_exposed = min(rrsp_withdraw, GIS_THRESHOLD - base_income)
    gis_clawback = gis_exposed * 0.50

total_hidden_tax = rrsp_income_tax + oas_clawback + gis_clawback
rrsp_net_spendable = rrsp_withdraw - total_hidden_tax
tfsa_net_spendable = tfsa_withdraw

# The Verdict
diff = abs(rrsp_net_spendable - tfsa_net_spendable)
tfsa_glow = "none"
rrsp_glow = "none"

if rrsp_net_spendable > tfsa_net_spendable:
    winner = "RRSP"
    winner_color = RRSP_COLOR 
    rrsp_glow = f"0 0 15px 4px {WINNER_GLOW}"
elif tfsa_net_spendable > rrsp_net_spendable:
    winner = "TFSA"
    winner_color = PRIMARY_GOLD
    tfsa_glow = f"0 0 15px 4px {WINNER_GLOW}"
else:
    winner = "TIE"
    winner_color = SLATE_ACCENT

# --- 7. VISUALS & DASHBOARD ---
st.divider()

st.markdown(f"""
<div style="text-align: center; margin-bottom: 30px;">
    <h2 style="color: {SLATE_ACCENT}; margin-bottom: 5px;">🏆 The Winner is the <span style="color: {winner_color};">{winner}</span></h2>
    <p style="font-size: 1.1em; color: {SLATE_ACCENT};">By choosing the {winner}, you generate <b>${diff:,.0f} more</b> in spendable cash every single year in retirement.</p>
</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    st.markdown(f"""
    <div style="background-color: {OFF_WHITE}; padding: 20px; border-radius: 10px; border: 2px solid {PRIMARY_GOLD}; box-shadow: {tfsa_glow}; text-align: center; height: 100%; transition: all 0.3s ease;">
        <h3 style="margin-top:0; color: {PRIMARY_GOLD};">TFSA Drawdown</h3>
        <p style="color: {SLATE_ACCENT}; margin-bottom: 5px;">Gross Annual Withdrawal: <b>${tfsa_withdraw:,.0f}</b></p>
        <p style="color: {SLATE_ACCENT}; margin-bottom: 5px;">Income Tax Hit: <b>$0</b></p>
        <p style="color: {SLATE_ACCENT}; margin-bottom: 5px;">OAS / GIS Clawback: <b>$0</b></p>
        <h2 style="color: {PRIMARY_GOLD}; margin-top: 15px;">Net Spendable: ${tfsa_net_spendable:,.0f} / yr</h2>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div style="background-color: {OFF_WHITE}; padding: 20px; border-radius: 10px; border: 2px solid {RRSP_COLOR}; box-shadow: {rrsp_glow}; text-align: center; height: 100%; transition: all 0.3s ease;">
        <h3 style="margin-top:0; color: {RRSP_COLOR};">RRSP Drawdown</h3>
        <p style="color: {SLATE_ACCENT}; margin-bottom: 5px;">Gross Annual Withdrawal: <b>${rrsp_withdraw:,.0f}</b></p>
        <p style="color: #d9534f; margin-bottom: 5px;">Income Tax Hit: <b>-${rrsp_income_tax:,.0f}</b></p>
        <p style="color: #d9534f; margin-bottom: 5px;">OAS / GIS Clawback: <b>-${(oas_clawback + gis_clawback):,.0f}</b></p>
        <h2 style="color: {RRSP_COLOR}; margin-top: 15px;">Net Spendable: ${rrsp_net_spendable:,.0f} / yr</h2>
    </div>
    """, unsafe_allow_html=True)

# --- THE CHART (ACCUMULATION & DECUMULATION) ---
st.write("")
st.subheader("📈 The Lifecycle: Accumulation & Decumulation")

years_list = list(range(t + 1))
tfsa_balances = []
rrsp_balances = []

# Accumulation Phase
for y in years_list:
    if r > 0:
        t_val = (invest_amt * ((1 + r) ** y)) + (annual_invest * (((1 + r) ** y - 1) / r))
        r_val = (rrsp_deposit * ((1 + r) ** y)) + (rrsp_annual * (((1 + r) ** y - 1) / r))
    else:
        t_val = invest_amt + (annual_invest * y)
        r_val = rrsp_deposit + (rrsp_annual * y)
    
    tfsa_balances.append(t_val)
    rrsp_balances.append(r_val)

# Decumulation Phase (Next 10 Years)
for d in range(1, 11):
    years_list.append(t + d)
    prev_tfsa = tfsa_balances[-1]
    prev_rrsp = rrsp_balances[-1]
    
    # Balance decreases by withdrawal, remainder grows by expected return
    tfsa_new = (prev_tfsa - tfsa_withdraw) * (1 + r) if (prev_tfsa - tfsa_withdraw) > 0 else 0
    rrsp_new = (prev_rrsp - rrsp_withdraw) * (1 + r) if (prev_rrsp - rrsp_withdraw) > 0 else 0
    
    tfsa_balances.append(tfsa_new)
    rrsp_balances.append(rrsp_new)

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=years_list, y=tfsa_balances, mode='lines', name='TFSA Balance', 
    line=dict(color=PRIMARY_GOLD, width=4)
))

fig.add_trace(go.Scatter(
    x=years_list, y=rrsp_balances, mode='lines', name='RRSP Balance', 
    line=dict(color=RRSP_COLOR, width=4) 
))

# Add a vertical line to mark Retirement Day
fig.add_vline(x=t, line_width=2, line_dash="dash", line_color=SLATE_ACCENT, annotation_text="Retirement Day", annotation_position="top left")

fig.update_layout(
    xaxis=dict(title="Years"),
    yaxis_title="Gross Portfolio Value ($)",
    height=450,
    margin=dict(t=30, b=20, l=0, r=40),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

st.info("""
**💡 The Clawback Trap:** Because TFSA withdrawals are invisible to the CRA, they do not trigger government clawbacks. RRSP withdrawals, however, are stacked directly on top of your Base Income. If that combined total pushes you over the OAS threshold, or kicks you out of GIS eligibility, your RRSP is subjected to massive "Hidden Taxes."
""")

show_disclaimer()
