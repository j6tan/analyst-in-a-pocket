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

# --- 3. DATA INIT ---
if 'net_worth' not in st.session_state.app_db:
    st.session_state.app_db['net_worth'] = {}
nw_data = st.session_state.app_db['net_worth']
prof = st.session_state.app_db.get('profile', {})

# Smart Name Formatting
p1_raw = prof.get('p1_name', '')
p1_raw = p1_raw.strip() if isinstance(p1_raw, str) else ''

p2_raw = prof.get('p2_name', '')
p2_raw = p2_raw.strip() if isinstance(p2_raw, str) else ''

if p1_raw and p2_raw:
    greeting_names = f"{p1_raw} & {p2_raw}"
elif p1_raw:
    greeting_names = p1_raw
else:
    greeting_names = "Primary Client"

# Pre-fill liabilities from the profile page if they exist
if not nw_data.get('initialized'):
    nw_data['mortgage_debt'] = prof.get('m_bal', 0.0)
    nw_data['cc_debt'] = prof.get('cc_pmt', 0.0) * 12 # Rough estimate, user can override
    nw_data['initialized'] = True

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
        <h1 style='margin: 0 !important; padding: 0 !important; line-height: 1 !important;'>Personal Net Worth</h1>
    </div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">📊 The Ultimate FIRE Metric</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Your net worth is the absolute scorecard of your financial independence journey. Track your assets, subtract your liabilities, and watch your FIRE number grow over time.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. THE LEDGER (INPUTS) ---
col_assets, col_liabs = st.columns(2)

with col_assets:
    st.subheader("🟢 Assets (What you own)")
    # Real Estate
    re_value = cloud_input("Primary Residence Value", "net_worth", "home_value", step=5000, help="e.g., Current estimated market value of your condo/house")
    re_inv_value = cloud_input("Investment Properties", "net_worth", "inv_re_value", step=5000)
    
    # Liquid / Market
    tfsa_value = cloud_input("TFSA Portfolio", "net_worth", "tfsa_value", step=1000, help="e.g., Individual stocks like FTG, MDA, PNG, CS, or index funds")
    rrsp_value = cloud_input("RRSP Portfolio", "net_worth", "rrsp_value", step=1000)
    non_reg_value = cloud_input("Non-Registered Accounts", "net_worth", "non_reg_value", step=1000)
    crypto_value = cloud_input("Crypto Holdings", "net_worth", "crypto_value", step=500, help="e.g., Bitcoin ETFs or direct holdings")
    cash_value = cloud_input("Cash & Checking", "net_worth", "cash_value", step=500)
    
    total_assets = re_value + re_inv_value + tfsa_value + rrsp_value + non_reg_value + crypto_value + cash_value

with col_liabs:
    st.subheader("🔴 Liabilities (What you owe)")
    mortgage_debt = cloud_input("Primary Mortgage Balance", "net_worth", "mortgage_debt", step=1000)
    inv_mortgage_debt = cloud_input("Investment Mortgages", "net_worth", "inv_mortgage_debt", step=1000)
    heloc_debt = cloud_input("HELOC / Margin Debt", "net_worth", "heloc_debt", step=500)
    car_debt = cloud_input("Car Loans", "net_worth", "car_debt", step=500)
    student_debt = cloud_input("Student Loans", "net_worth", "student_debt", step=500)
    cc_debt = cloud_input("Credit Card Debt", "net_worth", "cc_debt", step=100)
    
    total_liabs = mortgage_debt + inv_mortgage_debt + heloc_debt + car_debt + student_debt + cc_debt

# --- 6. CALCULATIONS & METRICS ---
net_worth = total_assets - total_liabs

st.divider()
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Total Assets", f"${total_assets:,.0f}")
with m2:
    st.metric("Total Liabilities", f"${total_liabs:,.0f}")
with m3:
    st.metric("Total Net Worth", f"${net_worth:,.0f}", delta=None)

# --- 7. VISUALIZATION (ASSET ALLOCATION) ---
st.subheader("🥧 Asset Allocation")

if total_assets > 0:
    labels = ['Primary Home', 'Investment RE', 'TFSA', 'RRSP', 'Non-Registered', 'Crypto', 'Cash']
    values = [re_value, re_inv_value, tfsa_value, rrsp_value, non_reg_value, crypto_value, cash_value]
    
    # Filter out $0 values so the chart stays clean
    filtered_labels = [l for l, v in zip(labels, values) if v > 0]
    filtered_values = [v for v in values if v > 0]
    
    # Custom Brand Colors for the chart
    custom_colors = [CHARCOAL, PRIMARY_GOLD, SLATE_ACCENT, '#6c757d', '#adb5bd', '#e9ecef', BORDER_GREY]

    fig = go.Figure(data=[go.Pie(
        labels=filtered_labels, 
        values=filtered_values, 
        hole=.4,
        marker=dict(colors=custom_colors, line=dict(color=OFF_WHITE, width=2))
    )])
    
    fig.update_layout(
        margin=dict(t=20, b=20, l=0, r=0),
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Enter your assets above to generate your allocation chart.")
