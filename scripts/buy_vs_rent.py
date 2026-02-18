import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, supabase

inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 1. DATA SETUP ---
prof = st.session_state.app_db.get('profile', {})
name1 = prof.get('p1_name') or "Primary Client"
household = f"{name1} & {prof.get('p2_name', '')}" if prof.get('p2_name') else name1
is_renter = prof.get('housing_status') == "Renting"

if 'buy_vs_rent' not in st.session_state.app_db:
    st.session_state.app_db['buy_vs_rent'] = {}
br_store = st.session_state.app_db['buy_vs_rent']

# --- INITIALIZATION LOCK ---
# Only run defaults if NEVER initialized.
if not br_store.get('initialized'):
    profile_rent = float(prof.get('current_rent', 2500.0)) if is_renter else 2500.0
    br_store.update({
        "price": 800000.0, 
        "dp": 200000.0, 
        "rate": 4.0, 
        "ann_tax": 2000.0,
        "mo_maint": 500.0, 
        "apprec": 1.5, 
        "rent": profile_rent, 
        "rent_inc": 2.5,
        "stock_ret": 8.0, 
        "years": 15.0,
        "initialized": True # Lock!
    })
    # Force Save
    if st.session_state.get('username') and supabase:
        try:
            supabase.table('user_vault').upsert({
                'id': st.session_state.username, 
                'data': st.session_state.app_db
            }).execute()
        except: pass

# --- 2. CALCULATION ENGINE ---
def run_wealth_comparison(price, dp, rate, apprec, ann_tax, mo_maint, rent, rent_inc, stock_ret, years):
    loan = price - dp
    m_rate = (rate/100)/12
    n_months = 25 * 12
    monthly_pi = loan * (m_rate * (1+m_rate)**n_months) / ((1+m_rate)**n_months - 1) if m_rate > 0 else loan / n_months
    
    data = []
    total_owner_unrec, total_renter_unrec = 0, 0
    curr_loan, curr_val, curr_rent, renter_portfolio = loan, price, rent, dp 
    
    for y in range(1, int(years) + 1):
        annual_int = 0
        for _ in range(12):
            mo_int = curr_loan * m_rate
            mo_prin = monthly_pi - mo_int
            annual_int += mo_int
            curr_loan -= mo_prin
        
        total_owner_unrec += annual_int + ann_tax + (mo_maint * 12)
        curr_val *= (1 + apprec/100)
        owner_net = curr_val - max(0, curr_loan) - ((curr_val * 0.03) + 1500)
        
        total_renter_unrec += curr_rent * 12
        owner_outlay = monthly_pi + (ann_tax/12) + mo_maint
        mo_save = owner_outlay - curr_rent
        for _ in range(12):
            renter_portfolio = (renter_portfolio + mo_save) * (1 + (stock_ret/100)/12)
            
        data.append({
            "Year": y, "Owner Net Wealth": owner_net, "Renter Wealth": renter_portfolio,
            "Owner Unrecoverable": total_owner_unrec, "Renter Unrecoverable": total_renter_unrec
        })
        curr_rent *= (1 + rent_inc/100)
    return pd.DataFrame(data)

# --- 3. UI LAYOUT ---
st.title("Rent vs. Own Analysis")
st.markdown(f"""
<div style="background-color: #F8F9FA; padding: 15px 25px; border-radius: 10px; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 20px;">
    <h3 style="color: #2E2B28; margin: 0 0 10px 0; font-size: 1.5em;">🛑 {household}: The Homebuyer's Dilemma</h3>
    <p style="color: #4A4E5A; font-size: 1.1em; margin: 0;">Is the "forced savings" of a mortgage worth more than a optimized investment portfolio?</p>
</div>
""", unsafe_allow_html=True)

col_left, col_right = st.columns(2)
with col_left:
    st.subheader("🏠 Homeownership Path")
    price = cloud_input("Purchase Price ($)", "buy_vs_rent", "price", step=50000.0)
    dp = cloud_input("Down Payment ($)", "buy_vs_rent", "dp", step=10000.0)
    rate = cloud_input("Mortgage Rate (%)", "buy_vs_rent", "rate", step=0.1)
    ann_tax = cloud_input("Annual Property Tax ($)", "buy_vs_rent", "ann_tax", step=100.0)
    mo_maint = cloud_input("Monthly Maintenance ($)", "buy_vs_rent", "mo_maint", step=50.0)
    apprec = cloud_input("Annual Appreciation (%)", "buy_vs_rent", "apprec", step=0.5)

with col_right:
    st.subheader("🏢 Rental Path")
    rent = cloud_input("Current Monthly Rent ($)", "buy_vs_rent", "rent", step=100.0)
    rent_inc = cloud_input("Annual Rent Increase (%)", "buy_vs_rent", "rent_inc", step=0.5)
    stock_ret = cloud_input("Target Stock Return (%)", "buy_vs_rent", "stock_ret", step=0.5)
    years = cloud_input("Analysis Horizon (Years)", "buy_vs_rent", "years", step=1.0)

df = run_wealth_comparison(price, dp, rate, apprec, ann_tax, mo_maint, rent, rent_inc, stock_ret, years)

# --- 4. RESULTS ---
owner_unrec, renter_unrec = df['Owner Unrecoverable'].iloc[-1], df['Renter Unrecoverable'].iloc[-1]
owner_wealth, renter_wealth = df['Owner Net Wealth'].iloc[-1], df['Renter Wealth'].iloc[-1]

st.subheader("📊 Performance Comparison")
v_col1, v_col2 = st.columns(2)

with v_col1:
    fig_unrec = go.Figure(data=[
        go.Bar(name='Homeowner', x=['Homeowner'], y=[owner_unrec], marker_color='#CEB36F', text=[f"${owner_unrec:,.0f}"], textposition='auto'),
        go.Bar(name='Renter', x=['Renter'], y=[renter_unrec], marker_color='#2E2B28', text=[f"${renter_unrec:,.0f}"], textposition='auto')
    ])
    fig_unrec.update_layout(title="Total Sunk Costs", margin=dict(t=40, b=0, l=0, r=0), height=300, showlegend=False)
    st.plotly_chart(fig_unrec, use_container_width=True)

with v_col2:
    fig_wealth = go.Figure(data=[
        go.Bar(name='Homeowner', x=['Homeowner'], y=[owner_wealth], marker_color='#CEB36F', text=[f"${owner_wealth:,.0f}"], textposition='auto'),
        go.Bar(name='Renter', x=['Renter'], y=[renter_wealth], marker_color='#2E2B28', text=[f"${renter_wealth:,.0f}"], textposition='auto')
    ])
    fig_wealth.update_layout(title="Final Net Worth", margin=dict(t=40, b=0, l=0, r=0), height=300, showlegend=False)
    st.plotly_chart(fig_wealth, use_container_width=True)

st.divider()
st.subheader("🎯 Strategic Wealth Verdict")
ins_col1, ins_col2 = st.columns(2)

with ins_col1:
    if owner_wealth > renter_wealth:
        st.success(f"🏆 **Wealth Champion: Homeowner**\n\nAhead by **${(owner_wealth - renter_wealth):,.0f}**.")
    else:
        st.warning(f"🏆 **Wealth Champion: Renter**\n\nAhead by **${(renter_wealth - owner_wealth):,.0f}**.")

with ins_col2:
    sunk_diff = abs(owner_unrec - renter_unrec)
    if owner_unrec < renter_unrec:
        st.info(f"✨ **Efficiency Champion: Homeowner**\n\nSaves **${sunk_diff:,.0f}** in lost costs.")
    else:
        st.info(f"✨ **Efficiency Champion: Renter**\n\nSaves **${sunk_diff:,.0f}** in lost costs.")

show_disclaimer()
