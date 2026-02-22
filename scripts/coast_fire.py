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
BARISTA_BROWN = "#A88A68" 

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
        Welcome back, <b>{greeting_names}</b>. You don't always need millions in the bank to quit your stressful job. Use the tools below to see if your current portfolio can "Coast" or if you're ready for "Barista" freedom.
    </p>
</div>
""", unsafe_allow_html=True)

# --- NEW: FIRE DICTIONARY EXPANDER ---
with st.expander("📚 What are the different types of FIRE?"):
    st.markdown(f"""
    **🔥 Traditional FIRE:** You have saved 25x your annual expenses. You can safely withdraw 4% a year and never have to work again.
    
    **⚖️ Lean FIRE:** Traditional FIRE, but for minimalists. You live on a very strict, low-cost budget (usually under `$40,000`/yr), meaning you can retire much sooner with a smaller portfolio.
    
    **🍾 Fat FIRE:** The luxury route. You want a high-spending lifestyle in retirement (often `$100,000`\+ a year). It takes longer to achieve because you need a massive portfolio (`$2.5M`\+).
    
    **⛵ Coast FIRE:** You have invested enough *today* that it will naturally compound into your Traditional FIRE number by age 65. You can stop saving completely and just work enough to cover your current daily bills.
    
    **☕ Barista FIRE:** You quit the rat race *before* reaching your full FIRE number. You take a fun, low-stress, part-time job to cover your living expenses while your investments grow in the background.
    """)

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

# --- 6. CORE MATH ENGINE (ROUNDED) ---
r = expected_return / 100
swr_rate = swr / 100

# Calculate the "Big Three" Full FIRE Numbers
traditional_fire_num = round(target_spend / swr_rate, -3)
lean_fire_num = round((target_spend * 0.75) / swr_rate, -3)
fat_fire_num = round((target_spend * 1.5) / swr_rate, -3)

# Coast FIRE Math
coast_number = round(traditional_fire_num / ((1 + r) ** years_to_grow), -3)

# Barista Math
projected_portfolio = round(current_portfolio * ((1 + r) ** years_to_grow), -3)
projected_income = round(projected_portfolio * swr_rate, -3)
income_shortfall = round(max(0, target_spend - projected_income), -3)
coast_shortfall = round(max(0, coast_number - current_portfolio), -3)

has_hit_coast = current_portfolio >= coast_number
barista_threshold = 40000.0 
is_barista = not has_hit_coast and income_shortfall <= barista_threshold
is_accumulation = not has_hit_coast and income_shortfall > barista_threshold

# --- 7. VISUALS & DASHBOARD ---
st.divider()

if has_hit_coast:
    status_headline = "🎉 YOU HAVE REACHED COAST FIRE!"
    status_color = "#5cb85c"
    status_text = f"Congratulations! Your portfolio of <b>${current_portfolio:,.0f}</b> will naturally compound to exceed your <b>${traditional_fire_num:,.0f}</b> goal by age {target_age}."
elif is_barista:
    status_headline = "☕ YOU ARE IN BARISTA FIRE TERRITORY"
    status_color = BARISTA_BROWN
    status_text = f"If you stop investing now, your portfolio will generate <b>${projected_income:,.0f}/yr</b>. You just need a low-stress job to cover the <b>${income_shortfall:,.0f}</b> gap!"
else:
    status_headline = "🧱 THE ACCUMULATION PHASE"
    status_color = "#2B5C8F"
    status_text = f"Your portfolio would only generate <b>${projected_income:,.0f}/yr</b> if you stopped now. You're still in heavy accumulation mode—keep building that engine!"

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
        <h2 style="color: {CHARCOAL}; margin-top: 15px; margin-bottom: 5px;">${coast_number:,.0f}</h2>
        <div style="color: {'#5cb85c' if has_hit_coast else '#d9534f'}; font-weight: bold;">
            {'✅ Goal Achieved' if has_hit_coast else f'⚠️ Shortfall: -${coast_shortfall:,.0f}'}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_b:
    barista_glow = f"0 0 15px 4px {status_color}" if not has_hit_coast else "none"
    st.markdown(f"""
    <div style="background-color: {OFF_WHITE}; padding: 20px; border-radius: 10px; border: 2px solid {status_color}; box-shadow: {barista_glow}; text-align: center; height: 100%;">
        <h3 style="margin-top:0; color: {status_color};">The Income Gap</h3>
        <h2 style="color: {CHARCOAL}; margin-top: 15px; margin-bottom: 5px;">${income_shortfall:,.0f} / yr</h2>
        <div style="color: {'#5cb85c' if has_hit_coast else status_color}; font-weight: bold;">
            {'✅ No gap!' if has_hit_coast else ('☕ Barista Ready' if is_barista else '🧱 Keep Accumulating')}
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 8. THE FIRE LADDER (COAST PROGRESS) ---
st.write("")
st.subheader("🪜 Your Coasting Milestones")
st.caption("Are you done saving? This shows how much of your 'Save-No-More' number you have reached today.")
l1, l2, l3 = st.columns(3)

# Calculate the COAST version of each milestone
coast_lean = round(lean_fire_num / ((1 + r) ** years_to_grow), -3)
coast_trad = coast_number # We already have this (Traditional)
coast_fat = round(fat_fire_num / ((1 + r) ** years_to_grow), -3)

def coast_metric(col, label, coast_target, current):
    # Calculate progress toward the amount needed TODAY
    progress = int((current / coast_target) * 100)
    
    if progress >= 100:
        status_msg = "✅ COAST SECURED"
        d_color = "normal" 
    else:
        status_msg = f"{progress}% of Coast Goal"
        d_color = "inverse" # Shows red/warning if under 100%

    col.metric(label, f"${coast_target:,.0f}", status_msg, delta_color=d_color)

coast_metric(l1, "Lean Coast", coast_lean, current_portfolio)
coast_metric(l2, "Traditional Coast", coast_trad, current_portfolio)
coast_metric(l3, "Fat Coast", coast_fat, current_portfolio)

# --- 9. THE CHART ---
st.write("")
st.subheader("📈 Coasting Trajectory (Zero New Contributions)")
years_list = list(range(int(years_to_grow) + 1))
ages = [int(current_age) + y for y in years_list]
balances = [current_portfolio * ((1 + r) ** y) for y in years_list]

fig = go.Figure()
fig.add_trace(go.Scatter(x=ages, y=balances, name='Coasting Portfolio', line=dict(color=PRIMARY_GOLD, width=4)))
fig.add_trace(go.Scatter(x=ages, y=[traditional_fire_num]*len(ages), name='Traditional Target', line=dict(color=SLATE_ACCENT, dash='dash')))

fig.update_layout(xaxis_title="Age", yaxis_title="Portfolio Value ($)", height=400, margin=dict(t=20, b=20, l=0, r=20), hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

show_disclaimer()

# --- FOOTER ---
st.markdown("""
    <div style="text-align: center; color: #adb5bd; font-size: 0.85em; margin-top: 50px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        &copy; 2026 FIRE Calculator. All rights reserved. <br>
        <span style="font-size: 0.9em; font-style: italic;">Empowering Canadian professionals to build wealth.</span>
    </div>
""", unsafe_allow_html=True)
