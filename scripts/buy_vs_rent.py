import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, supabase, load_user_data, init_session_state
import time

# --- UNIVERSAL AUTO-LOADER ---
init_session_state()
if st.session_state.get('username') and not st.session_state.app_db.get('profile'):
    with st.spinner("🔄 restoring your data..."):
        load_user_data(st.session_state.username)
        time.sleep(0.1)
        st.rerun()

# 1. Inject Style
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 1. THEME & BRANDING ---
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

if not br_store.get('initialized'):
    profile_rent = float(prof.get('rent_pmt', 2500)) if is_renter else 2500.0
    br_store.update({
        "price": 800000, 
        "dp": 200000, 
        "rate": 4.5, 
        "ann_tax": 3000,
        "mo_maint": 400, 
        "apprec": 3.0, 
        "rent": int(profile_rent), 
        "rent_inc": 2.0,
        "stock_ret": 6.0, 
        "years": 25,
        "initialized": True 
    })
    if st.session_state.get("is_logged_in") and st.session_state.get("username"):
        try:
            supabase.table("user_vault").upsert({
                "id": st.session_state.username, 
                "data": st.session_state.app_db
            }).execute()
        except: pass

# --- 4. CALCULATION ENGINE ---
def run_wealth_comparison(price, dp, rate, apprec, ann_tax, mo_maint, rent, rent_inc, stock_ret, years):
    # SAFETY: Ensure years is at least 1 to prevent empty dataframe crash
    if years < 1: years = 1
    
    loan = price - dp
    m_rate = (rate/100)/12
    n_months = 30 * 12 # Standard 30 year amort for calc
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
        
        # Sunk Costs
        owner_lost_this_year = annual_int + ann_tax + (mo_maint * 12)
        total_owner_unrecoverable += owner_lost_this_year
        
        # Value Growth
        curr_val *= (1 + apprec/100)
        
        # Net Worth Calculation (Equity - Selling Costs)
        owner_wealth_net = curr_val - max(0, curr_loan) - ((curr_val * 0.05)) # 5% Selling Cost
        
        # Renter Math
        total_renter_unrecoverable += curr_rent * 12
        owner_mo_outlay = monthly_pi + (ann_tax/12) + mo_maint
        mo_savings_gap = owner_mo_outlay - curr_rent
        
        # Invest the difference (or withdraw from portfolio if rent > buy cost)
        for _ in range(12):
            renter_portfolio = (renter_portfolio + mo_savings_gap) * (1 + (stock_ret/100)/12)
        
        data.append({
            "Year": y, 
            "Owner Net Wealth": owner_wealth_net, 
            "Renter Wealth": renter_portfolio,
            "Owner Unrecoverable": total_owner_unrecoverable, 
            "Renter Unrecoverable": total_renter_unrecoverable
        })
        curr_rent *= (1 + rent_inc/100)
    
    return pd.DataFrame(data)

# --- 5. STORYBOX ---
st.markdown("<style>div.block-container {padding-top: 1rem;}</style>", unsafe_allow_html=True)
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col2:
    st.title("Rent vs. Own Analysis")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 20px;">
    <h3 style="color: {CHARCOAL}; margin: 0 0 10px 0; font-size: 1.5em;">🛑 {household}: The Homebuyer's Dilemma</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.4; margin: 0;">
        {name1} values the <b>equity growth</b> and stability of ownership, while {name2 if name2 else 'the household'} is focused on the <b>opportunity cost</b> of the stock market. 
        Is the "forced savings" of a mortgage worth more than an optimized investment portfolio?
    </p>
</div>
""", unsafe_allow_html=True)

# --- 6. INPUTS ---
col_left, col_right = st.columns(2)
with col_left:
    st.subheader("🏠 Homeownership Path")
    price = cloud_input("Purchase Price ($)", "buy_vs_rent", "price", step=50000)
    dp = cloud_input("Down Payment ($)", "buy_vs_rent", "dp", step=10000)
    rate = cloud_input("Mortgage Rate (%)", "buy_vs_rent", "rate", step=0.1)
    ann_tax = cloud_input("Annual Property Tax ($)", "buy_vs_rent", "ann_tax", step=100)
    mo_maint = cloud_input("Monthly Maintenance ($)", "buy_vs_rent", "mo_maint", step=50)
    apprec = cloud_input("Annual Appreciation (%)", "buy_vs_rent", "apprec", step=0.1)

with col_right:
    st.subheader("🏢 Rental Path")
    rent = cloud_input("Current Monthly Rent ($)", "buy_vs_rent", "rent", step=100)
    rent_inc = cloud_input("Annual Rent Increase (%)", "buy_vs_rent", "rent_inc", step=0.1)
    stock_ret = cloud_input("Target Stock Return (%)", "buy_vs_rent", "stock_ret", step=0.1)
    # FIX: Added min_value=1 to prevent crash
    years = cloud_input("Analysis Horizon (Years)", "buy_vs_rent", "years", step=1, min_value=1)

# Ensure years is at least 1 even if DB says 0
if years < 1: years = 1

df = run_wealth_comparison(price, dp, rate, apprec, ann_tax, mo_maint, rent, rent_inc, stock_ret, years)

# --- 7. VISUALS ---
owner_unrec, renter_unrec = df['Owner Unrecoverable'].iloc[-1], df['Renter Unrecoverable'].iloc[-1]
owner_wealth, renter_wealth = df['Owner Net Wealth'].iloc[-1], df['Renter Wealth'].iloc[-1]

st.subheader("📊 Performance Comparison")
v_col1, v_col2 = st.columns(2)

with v_col1:
    fig_unrec = go.Figure(data=[
        go.Bar(name='Homeowner', x=['Homeowner'], y=[owner_unrec], marker_color=PRIMARY_GOLD, text=[f"${owner_unrec:,.0f}"], textposition='auto'),
        go.Bar(name='Renter', x=['Renter'], y=[renter_unrec], marker_color=CHARCOAL, text=[f"${renter_unrec:,.0f}"], textposition='auto')
    ])
    fig_unrec.update_layout(
        title=dict(text="Total Sunk Costs (Lost Money)", x=0.5, y=0.9),
        margin=dict(t=40, b=0, l=0, r=0), height=300, showlegend=False
    )
    st.plotly_chart(fig_unrec, use_container_width=True)

with v_col2:
    fig_wealth = go.Figure(data=[
        go.Bar(name='Homeowner', x=['Homeowner'], y=[owner_wealth], marker_color=PRIMARY_GOLD, text=[f"${owner_wealth:,.0f}"], textposition='auto'),
        go.Bar(name='Renter', x=['Renter'], y=[renter_wealth], marker_color=CHARCOAL, text=[f"${renter_wealth:,.0f}"], textposition='auto')
    ])
    fig_wealth.update_layout(
        title=dict(text=f"Net Worth after {years} Years", x=0.5, y=0.9),
        margin=dict(t=40, b=0, l=0, r=0), height=300, showlegend=False
    )
    st.plotly_chart(fig_wealth, use_container_width=True)

# --- 8. THE MISSING CHART: WEALTH TRAJECTORY ---
st.subheader("📈 The Break-Even Timeline")
st.caption("Track how your Net Worth changes year over year. The crossing point is your break-even year.")

fig_line = go.Figure()
fig_line.add_trace(go.Scatter(x=df['Year'], y=df['Owner Net Wealth'], mode='lines', name='Homeowner Wealth', line=dict(color=PRIMARY_GOLD, width=4)))
fig_line.add_trace(go.Scatter(x=df['Year'], y=df['Renter Wealth'], mode='lines', name='Renter Wealth', line=dict(color=CHARCOAL, width=3, dash='dash')))

fig_line.update_layout(
    height=400,
    margin=dict(l=20, r=20, t=20, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified"
)
st.plotly_chart(fig_line, use_container_width=True)

# --- 9. STRATEGIC VERDICT ---
st.divider()
st.subheader("🎯 Strategic Verdict")
ins_col1, ins_col2 = st.columns(2)

with ins_col1:
    if owner_wealth > renter_wealth:
        st.success(f"🏆 **Wealth Champion: Homeowner**\n\nOwnership builds **${(owner_wealth - renter_wealth):,.0f} more** in assets over {int(years)} years.")
    else:
        st.warning(f"🏆 **Wealth Champion: Renter**\n\nStock returns currently outperform equity. The Renter is **${(renter_wealth - owner_wealth):,.0f} ahead**.")

    sunk_diff = abs(owner_unrec - renter_unrec)
    if owner_unrec < renter_unrec:
        st.info(f"✨ **Efficiency Champion: Homeowner**\n\nOwnership wastes **${sunk_diff:,.0f} less** money (Interest/Tax/Maint) than Renting.")
    else:
        st.info(f"✨ **Efficiency Champion: Renter**\n\nRenting wastes **${sunk_diff:,.0f} less** money than Buying.")

with ins_col2:
    ahead_mask = df['Owner Net Wealth'] > df['Renter Wealth']
    
    # Check if lines ever cross
    if ahead_mask.all():
         st.write("**Analysis:** Buying is immediately wealthier than renting (usually due to high starting equity).")
    elif not ahead_mask.any():
         st.write("**Analysis:** Renting stays ahead the entire time. The stock market return is outpacing the real estate leverage.")
    else:
        # Find first year where Owner > Renter
        be_year = int(df[ahead_mask].iloc[0]['Year'])
        st.write(f"### ⏳ Break-Even: Year {be_year}")
        st.write(f"It takes **{be_year} years** for the Homeowner's equity to catch up to the Renter's portfolio.")
        st.caption("If you plan to move before this year, you are mathematically better off renting.")

show_disclaimer()
