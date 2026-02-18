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

st.title("🏡 Mortgage Strategy Calculator")
st.markdown("""
    <div style="background-color: #F8F9FA; padding: 20px; border-radius: 10px; border-left: 5px solid #CEB36F; margin-bottom: 25px;">
        <h4 style="color: #4A4E5A; margin: 0 0 5px 0;">Strategy First, Math Second</h4>
        <p style="color: #6C757D; font-size: 1.05em; margin: 0; line-height: 1.5;">
            Most people focus on the monthly payment. Wealthy investors focus on the <b>Interest Curve</b>. 
            Use this tool to see how small "micro-payments" can destroy your debt years ahead of schedule.
        </p>
    </div>
""", unsafe_allow_html=True)

# --- 2. CALCULATION ENGINE ---
def simulate_mortgage_single(principal, annual_rate, amort_years, freq_label, extra_per_pmt=0, lump_sum_annual=0):
    freq_map = {
        "Monthly": 12, "Semi-monthly": 24, "Bi-weekly": 26, 
        "Weekly": 52, "Accelerated Bi-weekly": 26, "Accelerated Weekly": 52
    }
    p_yr = freq_map[freq_label]
    
    # Standard Mortgage Math
    m_rate = ((1 + (annual_rate / 100) / 2)**(2 / 12)) - 1
    num_m = amort_years * 12
    base_m_pmt = principal * (m_rate * (1 + m_rate)**num_m) / ((1 + m_rate)**num_m - 1)

    # Convert to chosen frequency
    if "Accelerated" in freq_label: 
        # Accelerated = Monthly Payment / (4 if weekly, 2 if bi-weekly)
        pmt = base_m_pmt / (4 if "Weekly" in freq_label else 2)
    else: 
        # Regular = Annualized Monthly / Periods per year
        pmt = (base_m_pmt * 12) / p_yr

    total_periodic = pmt + extra_per_pmt
    periodic_rate = ((1 + (annual_rate / 100) / 2)**(2 / p_yr)) - 1

    # --- TRUE AVERAGE MONTHLY TOTAL ---
    # (Base + Extra) * Payments/Year + Annual Lump Sum = Total Annual Outflow
    # Total Annual Outflow / 12 = Average Monthly Cost
    total_annual_outflow = (total_periodic * p_yr) + lump_sum_annual
    avg_monthly_total = total_annual_outflow / 12

    balance = principal
    total_life_int = 0
    
    # 5-Year Term Stats
    term_periods = int(5 * p_yr)
    term_int = 0
    term_prin = 0
    
    # Run Simulation
    for i in range(1, 15000): # Max iterations
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
        "avg_monthly_total": avg_monthly_total,
        "term_int": term_int,
        "term_prin": term_prin,
        "total_int": total_life_int,
        "payoff_years": payoff_years,
        "amort_years": amort_years
    }

# --- 3. INPUT SECTION ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("🏠 Mortgage Details")
    price = cloud_input("Purchase Price ($)", "simple_mortgage", "price", step=5000.0)
    down = cloud_input("Down Payment ($)", "simple_mortgage", "down", step=5000.0)
    rate = cloud_input("Interest Rate (%)", "simple_mortgage", "rate", step=0.1)
    amort = st.slider("Amortization", 5, 30, 25, key="simple_mortgage:amort", on_change=sync_widget, args=("simple_mortgage:amort",))
    st.session_state.app_db['simple_mortgage']['amort'] = amort

with c2:
    st.subheader("💸 Payment Methods")
    
    # Frequency Select
    freq_opts = ["Monthly", "Semi-monthly", "Bi-weekly", "Weekly", "Accelerated Bi-weekly", "Accelerated Weekly"]
    curr_freq = st.session_state.app_db['simple_mortgage'].get('freq', 'Monthly')
    if curr_freq not in freq_opts: curr_freq = 'Monthly'
    
    freq = st.selectbox("Payment Frequency", freq_opts, index=freq_opts.index(curr_freq), key="simple_mortgage_freq_widget")
    if freq != curr_freq:
        st.session_state.app_db['simple_mortgage']['freq'] = freq
        sync_widget("simple_mortgage:freq")

    extra = cloud_input("Extra Payment (Per Pay) $", "simple_mortgage", "extra_payment", step=50.0)
    lump = cloud_input("Annual Lump Sum $", "simple_mortgage", "lump_sum", step=1000.0)

st.divider()

# --- 4. THE OVERVIEW (Bottom Half) ---
loan_amt = max(0, price - down)

if loan_amt > 0 and rate > 0:
    # Calculations
    user_res = simulate_mortgage_single(loan_amt, rate, amort, freq, extra, lump)
    base_res = simulate_mortgage_single(loan_amt, rate, amort, "Monthly", 0, 0)
    
    int_saved = base_res['total_int'] - user_res['total_int']
    years_saved = base_res['payoff_years'] - user_res['payoff_years']
    months_saved = years_saved * 12
    
    # A. The Headline Metrics
    st.header("📊 Mortgage Overview")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Avg Monthly Total", 
        f"${user_res['avg_monthly_total']:,.0f}", 
        help=f"Includes Base Payment + Extra + Annual Lump Sum averaged over 12 months."
    )
    m2.metric("Interest Saved", f"${int_saved:,.0f}", delta="Wealth Created" if int_saved > 0 else None)
    m3.metric("Time Saved", f"{years_saved:.1f} Years", delta="Freedom Accelerated" if years_saved > 0 else None)
    m4.metric("Mortgage Free Year", f"{pd.Timestamp.now().year + int(user_res['payoff_years'])}")

    st.write("") # Spacer

    # B. Three Column Layout
    col_strat, col_chart, col_reality = st.columns([1.2, 1, 1])
    
    # --- COLUMN 1: STRATEGIC INSIGHT ---
    with col_strat:
        st.subheader("📝 Strategic Insight")
        
        if int_saved > 50000:
            st.success(f"Massive Impact: Your strategy is incredible. By paying extra, you are effectively earning a guaranteed {rate}% return on your money—tax-free.")
            st.markdown(f"You will destroy **${int_saved:,.0f}** of bank profit. That is money that stays in your family instead of going to the lender.")
        elif int_saved > 0:
            st.info(f"Good Start: You are shaving {months_saved:.0f} months off your mortgage. Consider increasing your extra payment to $200/mo to see a dramatic leap in savings.")
        else:
            st.warning("The Cost of Waiting: Sticking to the minimum payment means you will pay maximum interest. Try adding just $50 extra per payment to see how much time you save.")

    # --- COLUMN 2: PIE CHART ---
    with col_chart:
        chart_data = pd.DataFrame({
            "Category": ["Interest", "Principal"],
            "Amount": [user_res['term_int'], user_res['term_prin']]
        })
        
        fig = px.pie(
            chart_data, 
            values="Amount", 
            names="Category",
            hole=0.5,
            color="Category",
            color_discrete_map={"Interest": "#4A4E5A", "Principal": "#CEB36F"},
            title="First 5 Years"
        )
        fig.update_layout(
            showlegend=False,
            margin=dict(l=0, r=0, t=30, b=0),
            height=200,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        
        st.plotly_chart(fig, use_container_width=True)

    # --- COLUMN 3: REALITY CHECK ---
    with col_reality:
        st.markdown(f"""
        <div style="background-color: #E9ECEF; padding: 20px; border-radius: 10px; border: 1px solid #DEE2E6; height: 100%;">
            <h4 style="color: #4A4E5A; margin-top: 0; font-size: 1.1em;">5-Year Reality Check</h4>
            <p style="font-size: 0.9em; margin-bottom: 10px;">In the first 5 years alone:</p>
            <p style="font-size: 1.1em; color: #DC2626; font-weight: bold; margin: 0;">-${user_res['term_int']:,.0f}</p>
            <p style="font-size: 0.8em; color: #6C757D; margin-bottom: 15px;">Interest Paid to Bank</p>
            <p style="font-size: 1.1em; color: #16A34A; font-weight: bold; margin: 0;">+${user_res['term_prin']:,.0f}</p>
            <p style="font-size: 0.8em; color: #6C757D; margin: 0;">Equity You Keep</p>
        </div>
        """, unsafe_allow_html=True)

else:
    st.info("👈 Enter your loan details above to generate your strategy.")

show_disclaimer()
