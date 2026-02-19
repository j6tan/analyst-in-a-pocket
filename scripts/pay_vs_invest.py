import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import time
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, load_user_data, init_session_state, supabase

# --- 1. UNIVERSAL AUTO-LOADER ---
init_session_state()
if st.session_state.get('username') and not st.session_state.app_db.get('profile'):
    with st.spinner("🔄 restoring your data..."):
        load_user_data(st.session_state.username)
        time.sleep(0.1)
        st.rerun()

inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 2. THEME & UTILS ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

def get_marginal_tax_rate(income):
    if income <= 55867: return 20.06
    elif income <= 111733: return 31.00
    elif income <= 173205: return 40.70
    elif income <= 246752: return 45.80
    else: return 53.50

# --- 3. DATA BRIDGING ---
prof = st.session_state.app_db.get('profile', {})
aff = st.session_state.app_db.get('affordability', {})
sm = st.session_state.app_db.get('simple_mortgage', {})

p1_name = prof.get('p1_name', 'Client 1')
p2_name = prof.get('p2_name', 'Client 2')

# Calculate Real-Time Income Sums for Tax Purpose
p1_inc = float(prof.get('p1_t4', 0)) + float(prof.get('p1_bonus', 0)) + float(prof.get('p1_commission', 0))
p2_inc = float(prof.get('p2_t4', 0)) + float(prof.get('p2_bonus', 0)) + float(prof.get('p2_commission', 0))

if 'pay_vs_invest' not in st.session_state.app_db:
    st.session_state.app_db['pay_vs_invest'] = {}
pvi_data = st.session_state.app_db['pay_vs_invest']

# Initialize Defaults from Affordability/Simple Mortgage
if not pvi_data.get('initialized'):
    pvi_data.update({
        "price": float(sm.get('price', aff.get('max_purchase', 800000))),
        "down": float(sm.get('down', aff.get('down_payment', 160000))),
        "rate": float(sm.get('rate', 5.0)),
        "amort": float(sm.get('amort', 25)),
        "extra_amt": 1000,
        "stock_return": 7.0,
        "initialized": True
    })

# --- 4. HEADER ---
st.title("Debt vs. Equity: The Wealth Choice")
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px; border-radius: 12px; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h4 style="color: {SLATE_ACCENT}; margin: 0;">Which dollar works harder?</h4>
    <p style="color: {SLATE_ACCENT}; font-size: 1.05em; line-height: 1.6; margin: 10px 0 0 0;">
        <b>{p1_name}</b>, every extra dollar you save has two potential homes: <b>Paying down your mortgage</b> (guaranteed, tax-free return) or <b>Investing in the market</b> (higher potential, but taxable). 
        This tool factors in the "After-Tax" reality to show you the true winner.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. INPUTS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏠 Mortgage Context")
    price = cloud_input("Purchase Price ($)", "pay_vs_invest", "price", step=5000)
    down = cloud_input("Down Payment ($)", "pay_vs_invest", "down", step=5000)
    m_rate = cloud_input("Interest Rate (%)", "pay_vs_invest", "rate", step=0.1)
    amort = cloud_input("Amortization (Years)", "pay_vs_invest", "amort", step=1)
    
    m_freq = st.selectbox("Payment Frequency", ["Monthly", "Bi-Weekly Accelerated"], key="pvi_freq")
    freq_map = {"Monthly": 12, "Bi-Weekly Accelerated": 26}
    periods_per_year = freq_map[m_freq]

with col2:
    st.subheader("💰 Extra Savings")
    extra_amt = cloud_input("Extra Savings Amount ($)", "pay_vs_invest", "extra_amt", step=100)
    extra_freq = st.selectbox("How often do you save this?", ["Every Mortgage Payment", "Quarterly", "Annually"], key="pvi_extra_freq")
    
    st.subheader("📈 Stock Expectations")
    stock_return = cloud_input("Expected Stock Return (%)", "pay_vs_invest", "stock_return", step=0.1)
    
    # Tax Selection (The "After-Tax" Factor)
    st.markdown("**Whose tax bracket for the stock account?**")
    t1, t2 = get_marginal_tax_rate(p1_inc), get_marginal_tax_rate(p2_inc)
    tax_map = {f"{p1_name} ({t1}%)": t1, f"{p2_name} ({t2}%)": t2}
    tax_rate = tax_map[st.radio("Select Owner", list(tax_map.keys()), horizontal=True, key="pvi_tax_owner")]

# --- 6. CALCULATIONS ---
loan_amt = price - down
n_months = int(amort * 12)
monthly_rate = (m_rate / 100) / 12

# Standard Payment
if monthly_rate > 0:
    base_monthly_pmt = loan_amt * (monthly_rate * (1 + monthly_rate)**n_months) / ((1 + monthly_rate)**n_months - 1)
else:
    base_monthly_pmt = loan_amt / n_months

# Simulation Logic
def run_simulation(loan, rate_ann, extra_val, extra_f_label, p_per_yr):
    # Setup
    r_mo = (rate_ann / 100) / 12
    m_pmt = base_monthly_pmt
    
    # Option A: Pay Down Mortgage
    bal_a = loan
    total_int_a = 0
    months_a = 0
    while bal_a > 0 and months_a < 600:
        months_a += 1
        int_mo = bal_a * r_mo
        total_int_a += int_mo
        
        # Calculate extra for this month
        extra_this_mo = 0
        if extra_f_label == "Every Mortgage Payment":
            # For simplicity, if Bi-weekly, we treat extra as (Amount * 26 / 12)
            extra_this_mo = extra_val * (p_per_yr / 12)
        elif extra_f_label == "Quarterly" and months_a % 3 == 0:
            extra_this_mo = extra_val
        elif extra_f_label == "Annually" and months_a % 12 == 0:
            extra_this_mo = extra_val
            
        prin_pay = (m_pmt + extra_this_mo) - int_mo
        if prin_pay > bal_a: prin_pay = bal_a
        bal_a -= prin_pay
        
    # Option B: Invest Extra Savings
    # We assume capital gains tax on stocks (50% inclusion)
    after_tax_growth = (stock_return / 100) * (1 - (tax_rate / 100 * 0.5))
    r_stock_mo = after_tax_growth / 12
    
    portfolio_b = 0
    months_b = int(amort * 12) # We compare over the full original term
    data_points = []
    
    # Tracking for Chart
    bal_a_tracking = loan
    total_int_a_tracking = 0
    
    for m in range(1, months_b + 1):
        # Invest the extra savings
        extra_this_mo = 0
        if extra_f_label == "Every Mortgage Payment":
            extra_this_mo = extra_val * (p_per_yr / 12)
        elif extra_f_label == "Quarterly" and m % 3 == 0:
            extra_this_mo = extra_val
        elif extra_f_label == "Annually" and m % 12 == 0:
            extra_this_mo = extra_val
            
        portfolio_b = (portfolio_b + extra_this_mo) * (1 + r_stock_mo)
        
        # Also track the "Faster Paydown" for the chart
        if bal_a_tracking > 0:
            int_m = bal_a_tracking * r_mo
            p_m = (m_pmt + extra_this_mo) - int_m
            if p_m > bal_a_tracking: p_m = bal_a_tracking
            bal_a_tracking -= p_m
        
        data_points.append({
            "Month": m, 
            "Stock Value": portfolio_b, 
            "Mortgage Saved": loan - bal_a_tracking
        })
        
    return months_a, portfolio_b, pd.DataFrame(data_points)

# Run
payoff_mo, final_stock_val, df = run_wealth_engine = run_simulation(loan_amt, m_rate, extra_amt, extra_freq, periods_per_year)

# --- 7. VISUALS ---
st.divider()
c1, c2, c3 = st.columns(3)
years_saved = amort - (payoff_mo / 12)
c1.metric("Time Saved", f"{years_saved:.1f} Years")
c2.metric("Final Stock Value", f"${final_stock_val:,.0f}")
c3.metric("After-Tax Stock Return", f"{stock_return * (1 - (tax_rate/100*0.5)):.2f}%")

st.subheader("📉 Wealth Trajectory Comparison")
fig = go.Figure()
fig.add_trace(go.Scatter(x=df['Month']/12, y=df['Stock Value'], name='Option B: Stock Portfolio', line=dict(color="#16A34A", width=3)))
fig.add_trace(go.Scatter(x=df['Month']/12, y=df['Mortgage Saved'], name='Option A: Extra Equity Paydown', line=dict(color=PRIMARY_GOLD, width=3)))
fig.update_layout(height=400, xaxis_title="Years", yaxis_title="Total Benefit ($)", margin=dict(l=0,r=0,t=20,b=20))
st.plotly_chart(fig, use_container_width=True)

# --- 8. THE VERDICT ---
winner = "Stock Market" if final_stock_val > (loan_amt) else "Mortgage Paydown"
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px; border-radius: 12px; border: 2px solid {PRIMARY_GOLD}; text-align: center;">
    <h3 style="margin: 0; color: {SLATE_ACCENT};">🏆 The Mathematical Winner: {winner}</h3>
    <p style="font-size: 1.1em; color: #666; margin-top: 10px;">
        Over the next {amort} years, choosing the {winner} path is projected to increase your net wealth by 
        <b>${abs(final_stock_val - loan_amt):,.0f}</b> more than the alternative.
    </p>
</div>
""", unsafe_allow_html=True)

show_disclaimer()
