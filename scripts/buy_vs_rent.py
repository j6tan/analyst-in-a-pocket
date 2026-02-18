import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, supabase

# 1. Inject Style
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 1. THEME & BRANDING (Must be defined first to avoid NameError) ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"

# --- 2. DATA RETRIEVAL ---
prof = st.session_state.app_db.get('profile', {})
name1 = prof.get('p1_name') or "Primary Client"
name2 = prof.get('p2_name') or ""
household = f"{name1} and {name2}" if name2 else name1
is_renter = prof.get('housing_status') == "Renting"

# --- 3. PERSISTENCE & INITIALIZATION ---
if 'buy_vs_rent' not in st.session_state.app_db:
    st.session_state.app_db['buy_vs_rent'] = {}
br_store = st.session_state.app_db['buy_vs_rent']

# FIX: Only reset defaults if initialized flag is missing OR data is clearly empty (price=0)
if not br_store.get('initialized') or br_store.get('price', 0) == 0:
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
        "initialized": True # Logic Lock
    })
    # Force Save to Cloud
    if st.session_state.get("is_logged_in") and st.session_state.get("username"):
        try:
            supabase.table("user_vault").upsert({
                "id": st.session_state.username, 
                "data": st.session_state.app_db
            }).execute()
        except:
            pass

# --- 4. CALCULATION ENGINE ---
def run_wealth_comparison(price, dp, rate, apprec, ann_tax, mo_maint, rent, rent_inc, stock_ret, years):
    loan = price - dp
    m_rate = (rate/100)/12
    n_months = 25 * 12
    monthly_pi = loan * (m_rate * (1+m_rate)**n_months) / ((1+m_rate)**n_months - 1) if m_rate > 0 else loan / n_months
    
    data = []
    total_owner_unrecoverable = 0
    total_renter_unrecoverable = 0
    curr_loan, curr_val, curr_rent, renter_portfolio = loan, price, rent, dp 
    
    for y in range(1, int(years) + 1):
        annual_int = 0
        for _ in range(12):
            mo_interest = curr_loan * m_rate
            mo_principal = monthly_pi - mo_interest
            annual_int += mo_interest
            curr_loan -= mo_principal
        owner_lost_this_year = annual_int + ann_tax + (mo_maint * 12)
        total_owner_unrecoverable += owner_lost_this_year
        curr_val *= (1 + apprec/100)
        owner_wealth_net = curr_val - max(0, curr_loan) - ((curr_val * 0.03) + 1500)
        total_renter_unrecoverable += curr_rent * 12
        owner_mo_outlay = monthly_pi + (ann_tax/12) + mo_maint
        mo_savings_gap = owner_mo_outlay - curr_rent
        for _ in range(12):
            renter_portfolio = (renter_portfolio + mo_savings_gap) * (1 + (stock_ret/100)/12)
        data.append({
            "Year": y, "Owner Net Wealth": owner_wealth_net, "Renter Wealth": renter_portfolio,
            "Owner Unrecoverable": total_owner_unrecoverable, "Renter Unrecoverable": total_renter_unrecoverable
        })
        curr_rent *= (1 + rent_inc/100)
    return pd.DataFrame(data)

# --- 5. VISUALS ---
st.title("Rent vs. Own Analysis")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 20px;">
    <h3 style="color: {CHARCOAL}; margin: 0 0 10px 0; font-size: 1.5em;">🛑 {household}: The Homebuyer's Dilemma</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.4; margin: 0;">
        {name1} values the <b>equity growth</b> and stability of ownership, while {name2 if name2 else 'the household'} is focused on the <b>opportunity cost</b> of the stock market. 
        Is the "forced savings" of a mortgage worth more than a optimized investment portfolio?
    </p>
</div>
""", unsafe_allow_html=True)

# --- 6. INPUTS ---
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

# --- 7. CHARTS ---
owner_unrec, renter_unrec = df['Owner Unrecoverable'].iloc[-1], df['Renter Unrecoverable'].iloc[-1]
owner_wealth, renter_wealth = df['Owner Net Wealth'].iloc[-1], df['Renter Wealth'].iloc[-1]

st.subheader("📊 Performance Comparison")
v_col1, v_col2 = st.columns(2)

with v_col1:
    fig_unrec = go.Figure(data=[
        go.Bar(name='Homeowner', x=['Homeowner'], y=[owner_unrec], marker_color=PRIMARY_GOLD, text=[f"${owner_unrec:,.0f}"], textposition='auto'),
        go.Bar(name='Renter', x=['Renter'], y=[renter_unrec], marker_color=CHARCOAL, text=[f"${renter_unrec:,.0f}"], textposition='auto')
    ])
    fig_unrec.update_layout(title=dict(text="Total Sunk Costs", x=0.5, y=0.9, xanchor='center', yanchor='top'),
                            margin=dict(t=40, b=0, l=0, r=0), height=300, showlegend=False)
    st.plotly_chart(fig_unrec, use_container_width=True)

with v_col2:
    fig_wealth = go.Figure(data=[
        go.Bar(name='Homeowner', x=['Homeowner'], y=[owner_wealth], marker_color=PRIMARY_GOLD, text=[f"${owner_wealth:,.0f}"], textposition='auto'),
        go.Bar(name='Renter', x=['Renter'], y=[renter_wealth], marker_color=CHARCOAL, text=[f"${renter_wealth:,.0f}"], textposition='auto')
    ])
    fig_wealth.update_layout(title=dict(text="Final Net Worth", x=0.5, y=0.9, xanchor='center', yanchor='top'),
                             margin=dict(t=40, b=0, l=0, r=0), height=300, showlegend=False)
    st.plotly_chart(fig_wealth, use_container_width=True)

# --- 8. VERDICT ---
st.divider()
st.subheader("🎯 Strategic Wealth Verdict")
ins_col1, ins_col2 = st.columns(2)

with ins_col1:
    if owner_wealth > renter_wealth:
        st.success(f"🏆 **Wealth Champion: Homeowner**\n\nOwnership builds **${(owner_wealth - renter_wealth):,.0f} more** in assets over {int(years)} years.")
    else:
        st.warning(f"🏆 **Wealth Champion: Renter**\n\nStock returns currently outperform equity. The Renter is **${(renter_wealth - owner_wealth):,.0f} ahead**.")

with ins_col2:
    sunk_diff = abs(owner_unrec - renter_unrec)
    if owner_unrec < renter_unrec:
        st.info(f"✨ **Efficiency Champion: Homeowner**\n\nOwnership is **${sunk_diff:,.0f} cheaper** in 'dead money' lost than renting.")
    else:
        st.info(f"✨ **Efficiency Champion: Renter**\n\nRenting is **${sunk_diff:,.0f} cheaper** in pure cash-out costs.")

show_disclaimer()
