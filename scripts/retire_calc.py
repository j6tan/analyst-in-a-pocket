import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import os
import base64
from style_utils import inject_global_css
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
nw_data = st.session_state.app_db.get('net_worth', {})

if 'retire_calc' not in st.session_state.app_db:
    st.session_state.app_db['retire_calc'] = {}
rc_data = st.session_state.app_db['retire_calc']

# Smart Name Formatting
p1_raw = prof.get('p1_name', '').strip() if isinstance(prof.get('p1_name'), str) else ''
p2_raw = prof.get('p2_name', '').strip() if isinstance(prof.get('p2_name'), str) else ''
greeting_names = f"{p1_raw} & {p2_raw}" if p1_raw and p2_raw else (p1_raw or "Primary Client")

# Estimate current invested assets from Net Worth page
current_invested = (
    float(nw_data.get('tfsa_value', 0)) + 
    float(nw_data.get('rrsp_value', 0)) + 
    float(nw_data.get('non_reg_value', 0)) +
    float(nw_data.get('crypto_value', 0))
)

if not rc_data.get('initialized'):
    rc_data['starting_assets'] = current_invested
    rc_data['initialized'] = True

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
        <h1 style='margin: 0 !important; padding: 0 !important; line-height: 1 !important;'>When Can I Retire?</h1>
    </div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">🏖️ The FIRE Roadmap</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Welcome to the lab, <b>{greeting_names}</b>. Let's calculate your exact FIRE Number based on your target lifestyle, and map out the exact age you can officially stop working.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. INPUT VARIABLES ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("👤 The Baseline")
    current_age = cloud_input("Current Age", "retire_calc", "current_age", step=1, default_val=35)
    starting_assets = cloud_input("Current Invested Assets ($)", "retire_calc", "starting_assets", step=5000)
    monthly_contribution = cloud_input("Monthly Contribution ($)", "retire_calc", "monthly_contribution", step=500, help="How much are you adding to your investments every month?")

with c2:
    st.subheader("🎯 The Target")
    target_spend = cloud_input("Desired Annual Retirement Spend ($)", "retire_calc", "target_spend", step=5000, default_val=80000, help="Your expected yearly expenses in retirement.")
    annual_return = cloud_input("Expected Market Return (%)", "retire_calc", "annual_return", step=0.1, default_val=7.0)
    swr = cloud_input("Safe Withdrawal Rate (%)", "retire_calc", "swr", step=0.1, default_val=4.0, help="The 4% rule is the gold standard for a 30+ year retirement.")

# --- 6. CORE MATH ENGINE ---
# Calculate the FIRE Number
fire_number = target_spend / (swr / 100) if swr > 0 else 0

# Compounding Loop
months = 0
current_balance = starting_assets
history = [{"Age": current_age, "Net Worth": current_balance}]

r_mo = (annual_return / 100) / 12

# Prevent infinite loops if return is deeply negative
max_months = 1200 # 100 years

if fire_number > 0 and current_balance < fire_number:
    while current_balance < fire_number and months < max_months:
        months += 1
        current_balance = current_balance * (1 + r_mo) + monthly_contribution
        
        # Save data point every 12 months for the chart
        if months % 12 == 0:
            history.append({"Age": current_age + (months / 12), "Net Worth": current_balance})

    # Add final crossing point if it didn't land exactly on a year
    if months % 12 != 0:
        history.append({"Age": current_age + (months / 12), "Net Worth": current_balance})

years_to_fire = months / 12
fire_age = current_age + years_to_fire

# --- 7. THE VERDICT (VISUAL METRICS) ---
st.divider()

if years_to_fire >= (max_months / 12):
    st.error("Based on these contributions and returns, the target FIRE number is currently unreachable within 100 years. Try increasing contributions or reducing target spend.")
else:
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Your FIRE Number", f"${fire_number:,.0f}")
    with k2:
        st.metric("Years to FIRE", f"{years_to_fire:.1f} Years")
    with k3:
        st.metric("Age at Retirement", f"{fire_age:.1f} Years Old")

    # --- 8. THE COMPOUNDING CHART ---
    df = pd.DataFrame(history)
    fig = go.Figure()

    # The Wealth Growth Line
    fig.add_trace(go.Scatter(
        x=df['Age'], 
        y=df['Net Worth'], 
        name='Projected Portfolio', 
        fill='tozeroy',
        line=dict(color=PRIMARY_GOLD, width=4),
        fillcolor='rgba(206, 179, 111, 0.2)'
    ))

    # The FIRE Target Line (Horizontal Dashed)
    fig.add_trace(go.Scatter(
        x=[current_age, fire_age], 
        y=[fire_number, fire_number], 
        name='FIRE Target', 
        line=dict(color=CHARCOAL, width=3, dash='dash')
    ))

    fig.update_layout(
        xaxis_title="Age", 
        yaxis_title="Portfolio Value ($)", 
        height=450, 
        margin=dict(l=0, r=0, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)

    st.info(f"💡 **Insight:** At age {fire_age:.1f}, your portfolio of **${fire_number:,.0f}** will theoretically generate **${target_spend:,.0f}** per year indefinitely without drawing down the principal, assuming a {annual_return}% return and {swr}% safe withdrawal rate.")
