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
BARISTA_BROWN = "#A88A68" # A warm "latte" color for Barista FIRE

# --- 3. DATA INIT ---
prof = st.session_state.app_db.get('profile', {})
rc_data = st.session_state.app_db.get('retire_calc', {})

if 'coast_fire' not in st.session_state.app_db:
    st.session_state.app_db['coast_fire'] = {}
cf_data = st.session_state.app_db['coast_fire']

p1_raw = prof.get('p1_name', '').strip() if isinstance(prof.get('p1_name'), str) else ''
p2_raw = prof.get('p2_name', '').strip() if isinstance(prof.get('p2_name'), str) else ''
greeting_names = f"{p1_raw} & {p2_raw}" if p1_raw and p2_raw else (p1_raw or "Primary Client")

# Inject safe defaults
if not cf_data.get('initialized'):
    cf_data['current_age'] = rc_data.get('current_age', 35)
    cf_data['target_age'] = 65
    cf_data['current_portfolio'] = rc_data.get('starting_assets', 150000.0)
    cf_data['target_spend'] = rc_data.get('target_spend', 80000.0)
    cf_data['expected_return'] = rc_data.get('annual_return', 7.0)
    cf_data['swr'] = rc_data.get('swr', 4.0)
    cf_data['initialized'] = True

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
        <h1 style='margin: 0 !important; padding: 0 !important; line-height: 1 !important;'>Coast & Barista FIRE</h1>
    </div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">☕ Downshifting the Rat Race</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Welcome back, <b>{greeting_names}</b>. You don't always need millions in the bank to quit your stressful job. If you have enough invested today, you can stop saving forever and let compounding do the heavy lifting while you work a lower-stress job you actually enjoy.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. INPUT VARIABLES ---
c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("⏳ Timeline")
    current_age = cloud_input("Current Age", "coast_fire", "current_age", step=1)
    target_age = cloud_input("Traditional Retirement Age", "coast_fire", "target_age", step=1)
    years_to_grow = max(1, target_age - current_age)

with c2:
    st.subheader("💰 The Money")
    current_portfolio = cloud_input("Current Invested Portfolio ($)", "coast_fire", "current_portfolio", step=5000)
    target_spend = cloud_input("Target Annual Spend in Retirement ($)", "coast_fire", "target_spend", step=5000)

with c3:
    st.subheader("📈 The Market")
    expected_return = cloud_input("Expected Annual Return (%)", "coast_fire", "expected_return", step=0.1)
    swr = cloud_input("Safe Withdrawal Rate (%)", "coast_fire", "swr", step=0.1)

# --- 6. CORE MATH ENGINE ---
r = expected_return / 100
swr_rate = swr / 100

# 1. The Ultimate Target
fire_number = target_spend / swr_rate

# 2. Coast FIRE Math (What you need today to hit FIRE tomorrow with $0 added)
coast_number = fire_number / ((1 + r) ** years_to_grow)

# 3. Barista FIRE Math (Bridging the gap)
projected_portfolio = current_portfolio * ((1 + r) ** years_to_grow)
projected_income = projected_portfolio * swr_rate
income_shortfall = max(0, target_spend - projected_income)

has_hit_coast = current_portfolio >= coast_number

# --- 7. VISUALS & DASHBOARD ---
st.divider()

if has_hit_coast:
    status_headline = "🎉 YOU HAVE REACHED COAST FIRE!"
    status_color = "#5cb85c"
    status_text = f"Congratulations! You can stop investing today. Without adding a single penny, your current portfolio of <b>${current_portfolio:,.0f}</b> will naturally compound to exceed your <b>${fire_number:,.0f}</b> goal by age {target_age}. You only need to earn enough to cover your daily living expenses!"
else:
    status_headline = "☕ YOU ARE IN BARISTA FIRE TERRITORY"
    status_color = BARISTA_BROWN
    status_text = f"If you stopped investing today, your portfolio would grow to <b>${projected_portfolio:,.0f}</b> by age {target_age}. It will generate <b>${projected_income:,.0f}/yr</b>, leaving a small shortfall. You just need a fun, part-time job to cover the gap!"

st.markdown(f"""
<div style="text-align: center; margin-bottom: 30px;">
    <h2 style="color: {status_color}; margin-bottom: 5px;">{status_headline}</h2>
    <p style="font-size: 1.1em; color: {SLATE_ACCENT}; max-width: 800px; margin: 0 auto;">{status_text}</p>
</div>
""", unsafe_allow_html=True)

col_a, col_b = st.columns(2)

with col_a:
    coast_glow = f"0 0 15px 4px {PRIMARY_GOLD}" if has_hit_coast else "none"
    st.markdown(f"""
    <div style="background-color: {OFF_WHITE}; padding: 20px; border-radius: 10px; border: 2px solid {PRIMARY_GOLD}; box-shadow: {coast_glow}; text-align: center; height: 100%;">
        <h3 style="margin-top:0; color: {PRIMARY_GOLD};">Coast FIRE Milestone</h3>
        <p style="color: {SLATE_ACCENT}; margin-bottom: 5px; font-size: 0.9em;"><i>The exact amount you need invested <b>today</b> to never invest again.</i></p>
        <h2 style="color: {CHARCOAL}; margin-top: 15px; margin-bottom: 5px;">${coast_number:,.0f}</h2>
        <div style="color: {'#5cb85c' if has_hit_coast else '#d9534f'}; font-weight: bold; margin-top: 10px;">
            {'✅ Coast Goal Achieved' if has_hit_coast else f'⚠️ Shortfall: -${(coast_number - current_portfolio):,.0f}'}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_b:
    barista_glow = f"0 0 15px 4px {BARISTA_BROWN}" if not has_hit_coast else "none"
    st.markdown(f"""
    <div style="background-color: {OFF_WHITE}; padding: 20px; border-radius: 10px; border: 2px solid {BARISTA_BROWN}; box-shadow: {barista_glow}; text-align: center; height: 100%;">
        <h3 style="margin-top:0; color: {BARISTA_BROWN};">Barista FIRE Gap</h3>
        <p style="color: {SLATE_ACCENT}; margin-bottom: 5px; font-size: 0.9em;"><i>The part-time income required at age {target_age} if you stop saving now.</i></p>
        <h2 style="color: {CHARCOAL}; margin-top: 15px; margin-bottom: 5px;">${income_shortfall:,.0f} / yr</h2>
        <div style="color: {'#5cb85c' if has_hit_coast else BARISTA_BROWN}; font-weight: bold; margin-top: 10px;">
            {'✅ No part-time work needed!' if has_hit_coast else '☕ Perfect for a low-stress job'}
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- THE CHART (COAST TRAJECTORY) ---
st.write("")
st.subheader("📈 The Coasting Trajectory (Zero New Contributions)")

years_list = list(range(int(years_to_grow) + 1))
ages = [int(current_age) + y for y in years_list]
portfolio_balances = [current_portfolio * ((1 + r) ** y) for y in years_list]
coast_target_line = [fire_number for _ in years_list]

fig = go.Figure()

# Portfolio Growth Line
fig.add_trace(go.Scatter(
    x=ages, y=portfolio_balances, mode='lines', 
    name='Your "Coasting" Portfolio', 
    line=dict(color=PRIMARY_GOLD, width=4)
))

# Ultimate FIRE Target Line
fig.add_trace(go.Scatter(
    x=ages, y=coast_target_line, mode='lines', 
    name=f'Ultimate Target (${fire_number:,.0f})', 
    line=dict(color=SLATE_ACCENT, width=2, dash='dash')
))

fig.update_layout(
    xaxis=dict(title="Your Age"),
    yaxis_title="Portfolio Value ($)",
    height=450,
    margin=dict(t=20, b=20, l=0, r=20),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# THE IRONCLAD RULE EXPLANATION
st.info("""
**💡 The Coast FIRE Philosophy:** Coasting isn't about retiring to a beach today. It is about realizing that your past investments have secured your traditional retirement. By removing the burden of saving $2,000+ a month for retirement, you can radically reduce your current work hours, take a lower-paying dream job, or start a business, knowing your future is already fully funded.
""")

show_disclaimer()

# --- FOOTER ---
st.markdown("""
    <div style="text-align: center; color: #adb5bd; font-size: 0.85em; margin-top: 50px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        &copy; 2026 FIRE Calculator. All rights reserved. <br>
        <span style="font-size: 0.9em; font-style: italic;">Empowering Canadian professionals to build wealth.</span>
    </div>
""", unsafe_allow_html=True)
