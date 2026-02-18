import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import math
from style_utils import inject_global_css, show_disclaimer 
from data_handler import cloud_input, sync_widget

# 1. Inject Style
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 1. INITIALIZATION ---
if 'app_db' not in st.session_state:
    st.session_state.app_db = {}

# Ensure the section exists in the database
if 'simple_mortgage' not in st.session_state.app_db:
    st.session_state.app_db['simple_mortgage'] = {}

st.title("🏡 Simple Mortgage Calculator")
st.markdown("""
    <div style="background-color: #F8F9FA; padding: 15px; border-radius: 10px; border-left: 5px solid #CEB36F; margin-bottom: 20px;">
        <p style="color: #4A4E5A; font-size: 1.1em; margin: 0;">
            Calculate your payments, visualize your equity, and see how <b>pre-payments</b> can destroy your debt faster.
        </p>
    </div>
""", unsafe_allow_html=True)

# --- 2. CALCULATION ENGINE (Reused from Pro Tool) ---
def simulate_mortgage_single(principal, annual_rate, amort_years, freq_label, extra_per_pmt=0, lump_sum_annual=0):
    freq_map = {"Monthly": 12, "Semi-monthly": 24, "Bi-weekly": 26, "Weekly": 52, "Accelerated Bi-weekly": 26, "Accelerated Weekly": 52}
    p_yr = freq_map[freq_label]
    
    # Standard Mortgage Math
    m_rate = ((1 + (annual_rate / 100) / 2)**(2 / 12)) - 1
    num_m = amort_years * 12
    base_m_pmt = principal * (m_rate * (1 + m_rate)**num_m) / ((1 + m_rate)**num_m - 1)

    # Convert to chosen frequency
    if "Accelerated" in freq_label: 
        pmt = base_m_pmt / (4 if "Weekly" in freq_label else 2)
    else: 
        pmt = (base_m_pmt * 12) / p_yr

    total_periodic = pmt + extra_per_pmt
    periodic_rate = ((1 + (annual_rate / 100) / 2)**(2 / p_yr)) - 1

    balance = principal
    t_int, t_prin = 0, 0
    total_life_int = 0
    
    # 5-Year Term Stats
    term_periods = int(5 * p_yr)
    term_int = 0
    term_prin = 0
    
    # Run Simulation
    for i in range(1, 15000): # Max iterations to prevent infinite loop
        if balance <= 0.05: break 
        
        interest_charge = balance * periodic_rate
        actual_p = total_periodic
        
        # Apply Lump Sum annually
        if i % p_yr == 0: actual_p += lump_sum_annual
        
        # Cap payment at remaining balance
        if (actual_p - interest_charge) > balance: 
            actual_p = balance + interest_charge
            
        principal_part = actual_p - interest_charge
        balance -= principal_part
        total_life_int += interest_charge
        
        if i <= term_periods:
            term_int += interest_charge
            term_prin += principal_part

    # Calculate Payoff Time in Years
    payoff_years = i / p_yr

    return {
        "pmt_amt": pmt,
        "total_periodic": total_periodic,
        "term_int": term_int,
        "term_prin": term_prin,
        "total_int": total_life_int,
        "payoff_years": payoff_years
    }

# --- 3. INPUTS ---
col_main, col_sidebar = st.columns([2, 1])

with col_main:
    st.subheader("1. Property Details")
    c1, c2 = st.columns(2)
    with c1:
        price = cloud_input("Home Price ($)", "simple_mortgage", "price", step=5000.0)
        rate = cloud_input("Interest Rate (%)", "simple_mortgage", "rate", step=0.1)
    with c2:
        down = cloud_input("Down Payment ($)", "simple_mortgage", "down", step=5000.0)
        amort = st.slider("Amortization (Years)", 5, 30, 25, key="simple_mortgage:amort", on_change=sync_widget, args=("simple_mortgage:amort",))
        # Ensure database is updated for slider
        st.session_state.app_db['simple_mortgage']['amort'] = amort

    st.subheader("2. Payment Strategy")
    c3, c4 = st.columns(2)
    with c3:
        # Frequency Select
        freq_opts = ["Monthly", "Semi-monthly", "Bi-weekly", "Weekly", "Accelerated Bi-weekly", "Accelerated Weekly"]
        curr_freq = st.session_state.app_db['simple_mortgage'].get('freq', 'Monthly')
        if curr_freq not in freq_opts: curr_freq = 'Monthly'
        
        freq = st.selectbox("Payment Frequency", freq_opts, index=freq_opts.index(curr_freq), key="simple_mortgage_freq_widget")
        if freq != curr_freq:
            st.session_state.app_db['simple_mortgage']['freq'] = freq
            sync_widget("simple_mortgage:freq") # Force sync

    with c4:
        extra = cloud_input("Extra Payment (Per Pay) $", "simple_mortgage", "extra_payment", step=50.0)
        lump = cloud_input("Annual Lump Sum $", "simple_mortgage", "lump_sum", step=1000.0)

# --- 4. CALCULATIONS ---
loan_amt = max(0, price - down)

if loan_amt > 0 and rate > 0:
    # A. User Scenario
    user_res = simulate_mortgage_single(loan_amt, rate, amort, freq, extra, lump)
    
    # B. Baseline Scenario (Standard Monthly, No Extras) - For comparison
    base_res = simulate_mortgage_single(loan_amt, rate, amort, "Monthly", 0, 0)
    
    # Comparisons
    int_saved = base_res['total_int'] - user_res['total_int']
    time_saved_months = (base_res['payoff_years'] - user_res['payoff_years']) * 12
    
    with col_sidebar:
        st.markdown("### 📊 Your Results")
        
        # Main Metric: Payment
        st.metric(label=f"{freq} Payment", value=f"${user_res['total_periodic']:,.2f}")
        
        if extra > 0 or lump > 0 or "Accelerated" in freq:
            st.success(f"🎉 **Savings Unlocked!**")
            st.write(f"Interest Saved: **${int_saved:,.0f}**")
            st.write(f"Time Saved: **{time_saved_months:.1f} months**")
        
        # 5-Year Chart
        st.markdown("---")
        st.markdown("**5-Year Progress**")
        
        df_chart = pd.DataFrame([
            {"Type": "Interest Paid", "Amount": user_res['term_int']},
            {"Type": "Principal Paid", "Amount": user_res['term_prin']}
        ])
        
        fig = px.bar(
            df_chart, x="Type", y="Amount", color="Type", 
            text_auto='$,.0f',
            color_discrete_map={"Interest Paid": "#4A4E5A", "Principal Paid": "#CEB36F"}
        )
        fig.update_layout(
            showlegend=False, 
            margin=dict(l=0, r=0, t=0, b=0), 
            height=200,
            yaxis=dict(showgrid=False, visible=False),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

else:
    with col_sidebar:
        st.info("Enter property details to see your payment breakdown.")

# --- 5. DISCLAIMER ---
show_disclaimer()
