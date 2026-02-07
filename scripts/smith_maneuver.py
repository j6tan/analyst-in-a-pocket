import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from style_utils import inject_global_css

# 1. Inject the Wealthsimple-inspired Editorial CSS
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 1. DATA LINKING ---
prof = st.session_state.get('user_profile', {})
client_name1 = prof.get('p1_name', 'Client 1')
client_name2 = prof.get('p2_name', 'Client 2')
p1_income = float(prof.get('p1_t4', 0)) + float(prof.get('p1_bonus', 0))
p2_income = float(prof.get('p2_t4', 0))

household_names = f"{client_name1} & {client_name2}" if client_name2 else client_name1

# Determine Higher Earner
if p1_income > p2_income:
    high_earner = client_name1
    high_income = p1_income
else:
    high_earner = client_name2 if client_name2 else client_name1
    high_income = p2_income

def estimate_marginal_rate(income):
    if income > 240000: return 53.5
    elif income > 170000: return 48.0
    elif income > 110000: return 43.0
    elif income > 55000: return 29.0
    else: return 20.0

suggested_tax_rate = estimate_marginal_rate(high_income)

# --- 2. THEME & COLORS ---
PRINCIPAL_COLOR = "#CEB36F" 
INTEREST_COLOR = "#2E2B28"  
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"
PRIMARY_GOLD = "#CEB36F"
RISK_RED = "#D9534F"
BASELINE_BLUE = "#1f77b4"

# --- 3. HEADER ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("The Smith Maneuver Strategy")

# --- 4. STORYTELLING ---
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.5em;">🔄 {household_names}: Recycling Your Debt</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Think of this as <b>"Debt Recycling."</b> Every month, you pay down your mortgage (Bad Debt). 
        The bank immediately lets you borrow that exact amount back (Good Debt) to invest. 
        Because the new loan is for investment, the interest is tax-deductible. 
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. PREREQUISITES ---
with st.expander("✅ Strategy Prerequisites (Click to View)", expanded=False):
    st.markdown("""
    1. **Readvanceable Mortgage:** Automatic HELOC limit increase.
    2. **Principal Paydown:** Must be a standard amortizing mortgage.
    3. **Non-Registered Account:** Funds must be invested in a taxable account.
    4. **Income-Generating Assets:** Must pay dividends/interest.
    """)

# --- 6. VISUAL EXPLAINER ---
st.subheader("⚙️ The Mechanics (Monthly Cycle)")
c1, c2, c3, c4, c5 = st.columns([1, 0.2, 1, 0.2, 1])
with c1:
    st.markdown(f"<div style='text-align:center; border:1px solid #ddd; padding:10px; border-radius:5px;'><b>1. Pay Mortgage</b><br><span style='color:#666'>-$1,000</span></div>", unsafe_allow_html=True)
with c2:
    st.markdown("<h2 style='text-align: center; color: #ccc;'>➔</h2>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div style='text-align:center; border:1px solid {PRIMARY_GOLD}; background:#FFFDF5; padding:10px; border-radius:5px;'><b>2. Re-Borrow</b><br><span style='color:{PRIMARY_GOLD}'>+$1,000</span></div>", unsafe_allow_html=True)
with c4:
    st.markdown("<h2 style='text-align: center; color: #ccc;'>➔</h2>", unsafe_allow_html=True)
with c5:
    st.markdown(f"<div style='text-align:center; border:1px solid #333; background:#f9f9f9; padding:10px; border-radius:5px;'><b>3. Invest</b><br><span style='color:#333'>+$1,000</span></div>", unsafe_allow_html=True)

st.divider()

# --- 7. INPUTS ---
with st.container(border=True):
    st.markdown("### 📝 Configure Your Scenario")
    
    # Row 1: Mortgage
    c1, c2, c3 = st.columns(3)
    with c1:
        mortgage_amt = st.number_input("Mortgage Balance ($)", value=500000.0, step=10000.0)
    with c2:
        amortization = st.slider("Amortization (Years)", 10, 30, 25)
    with c3:
        mortgage_rate = st.number_input("Mortgage Rate (%)", value=5.0, step=0.1)

    # Row 2: Investment Strategy
    c4, c5, c6 = st.columns(3)
    with c4:
        loc_rate = st.number_input("HELOC Rate (%)", value=6.0, step=0.1)
    with c5:
        inv_return = st.number_input("Total Return (%)", value=7.0, step=0.1)
    with c6:
        div_yield = st.number_input("Dividend Yield (%)", value=5.0, step=0.1)

    # Row 3: Tax & Horizon
    c7, c8, c9 = st.columns(3)
    with c7:
         tax_rate = st.number_input("Marginal Tax Rate (%)", value=suggested_tax_rate, step=0.5)
    with c8:
        initial_lump = st.number_input("Initial HELOC Room ($)", value=0.0, step=5000.0)
    with c9:
        strategy_horizon = st.select_slider("Strategy Horizon (Years)", options=[5, 10, 15, 20, 25, 30], value=25)

# --- 8. CALCULATION ENGINE ---
sim_years = max(amortization, strategy_horizon)
n_months = sim_years * 12

r_m = mortgage_rate / 100 / 12
n_m_amort = amortization * 12 
monthly_payment = mortgage_amt * (r_m * (1 + r_m)**n_m_amort) / ((1 + r_m)**n_m_amort - 1)

# Initialize Active Strategy
balance = mortgage_amt
heloc_balance = 0.0
portfolio = 0.0
cum_tax_refund = 0.0

if initial_lump > 0:
    heloc_balance += initial_lump
    portfolio += initial_lump

# Initialize Baseline (Do Nothing)
base_balance = mortgage_amt

annual_data = []
current_year_heloc_interest = 0.0
year_refund = 0.0
current_year_borrows = 0.0
year_heloc_interest_cost = 0.0

for month in range(1, n_months + 1):
    # --- BASELINE CALC ---
    base_principal = 0.0
    if base_balance > 0:
        base_int = base_balance * r_m
        base_principal = monthly_payment - base_int
        if base_principal > base_balance: base_principal = base_balance
        base_balance -= base_principal
    base_net_worth = (mortgage_amt - base_balance)

    # --- ACTIVE STRATEGY ---
    principal_m = 0.0
    if balance > 0:
        interest_m = balance * r_m
        principal_m = monthly_payment - interest_m
        if principal_m > balance: principal_m = balance
        balance -= principal_m
    
    # Reborrow
    new_borrowing = principal_m 
    
    # Interest
    interest_heloc = heloc_balance * (loc_rate / 100 / 12)
    current_year_heloc_interest += interest_heloc
    year_heloc_interest_cost += interest_heloc
    
    # Tax Refund (Annual)
    if month % 12 == 1 and month > 1:
        refund_amount = current_year_heloc_interest * (tax_rate / 100)
        
        if balance > 0:
            balance -= refund_amount
            new_borrowing += refund_amount 
        else:
            portfolio += refund_amount # Invest directly
        
        current_year_heloc_interest = 0.0 
        year_refund = refund_amount
        cum_tax_refund += refund_amount

    # Invest (Standard Growth)
    current_year_borrows += new_borrowing
    heloc_balance += new_borrowing
    portfolio += new_borrowing 
    portfolio = portfolio * (1 + inv_return / 100 / 12)

    # Annual Snapshot
    if month % 12 == 0:
        year = month // 12
        annual_div_income = portfolio * (div_yield / 100)
        
        annual_data.append({
            "Year": year,
            "Mortgage Balance": max(0, balance),
            "Investment Loan": heloc_balance,
            "Portfolio Value": portfolio,
            "Annual Tax Refund": year_refund,
            "Dividend Income": annual_div_income,
            "Annual Interest Cost": year_heloc_interest_cost,
            "Net Equity (Active)": portfolio - heloc_balance + (mortgage_amt - balance),
            "Baseline Net Worth": base_net_worth,
            "Baseline Mortgage": base_balance
        })
        
        year_refund = 0.0 
        current_year_borrows = 0.0
        year_heloc_interest_cost = 0.0

df_annual = pd.DataFrame(annual_data)
df_view = df_annual[df_annual['Year'] <= strategy_horizon].copy()

# --- 9. CASH FLOW ANALYSIS ---
total_int_cost = df_view['Annual Interest Cost'].sum()
total_divs = df_view['Dividend Income'].sum()
total_refunds = df_view['Annual Tax Refund'].sum()
net_cashflow = (total_divs + total_refunds) - total_int_cost

st.divider()
st.subheader(f"💰 Cash Flow Analysis ({strategy_horizon} Year Horizon)")

cf1, cf2, cf3, cf4 = st.columns(4)
with cf1:
    st.metric("Total Interest Cost", f"${total_int_cost:,.0f}", help=f"Cost of borrowing at {loc_rate}%")
with cf2:
    st.metric("Total Dividends", f"${total_divs:,.0f}", help=f"Cash generated at {div_yield}% yield")
with cf3:
    st.metric("Total Tax Refunds", f"${total_refunds:,.0f}", help="Based on HELOC Interest x Tax Rate")
with cf4:
    st.metric("Net Cash Benefit", f"${net_cashflow:,.0f}", delta="Positive" if net_cashflow > 0 else "Negative")

st.caption("**Note on Dividends:** This model assumes Dividends are used to help pay the HELOC interest.")

# --- 10. TABLE ---
st.divider()
st.subheader(f"📅 {strategy_horizon}-Year Projection")

display_df = df_view[['Year', 'Mortgage Balance', 'Investment Loan', 'Portfolio Value', 'Annual Tax Refund', 'Dividend Income']].copy()
display_df.columns = ['Year', 'Bad Debt (Mortgage)', 'Good Debt (HELOC)', 'Asset Value (Portfolio)', 'Tax Refund (Re-invested)', 'Dividend Cash Flow']

for col in display_df.columns:
    if col != 'Year':
        display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}")

st.table(display_df)

# --- 11. CHARTS ---
st.divider()
st.subheader("📈 Strategy vs. Do Nothing")

col_res1, col_res2 = st.columns(2)

with col_res1:
    # Chart 1: Debt Paydown Comparison
    fig_debt = go.Figure()
    # Active Strategy
    fig_debt.add_trace(go.Scatter(x=df_view["Year"], y=df_view["Mortgage Balance"], name="Active Mortgage", line=dict(color=INTEREST_COLOR, width=2)))
    # Baseline
    fig_debt.add_trace(go.Scatter(x=df_view["Year"], y=df_view["Baseline Mortgage"], name="Do Nothing Mortgage", line=dict(color=BASELINE_BLUE, dash='dot')))
    
    fig_debt.update_layout(title="Mortgage Paydown Speed", height=300, margin=dict(t=30, b=0), yaxis=dict(tickprefix="$"))
    st.plotly_chart(fig_debt, use_container_width=True)

with col_res2:
    # Chart 2: Net Worth Comparison
    fig_wealth = go.Figure()
    # Active Strategy Net Worth (Home Equity + Portfolio - HELOC)
    fig_wealth.add_trace(go.Scatter(x=df_view["Year"], y=df_view["Net Equity (Active)"], name="Active Net Worth", line=dict(color=PRINCIPAL_COLOR, width=3)))
    # Baseline Net Worth (Home Equity Only)
    fig_wealth.add_trace(go.Scatter(x=df_view["Year"], y=df_view["Baseline Net Worth"], name="Do Nothing Net Worth", line=dict(color=BASELINE_BLUE, dash='dot')))
    
    fig_wealth.update_layout(title="Total Net Worth Comparison", height=300, margin=dict(t=30, b=0), yaxis=dict(tickprefix="$"))
    st.plotly_chart(fig_wealth, use_container_width=True)

# --- 12. STRESS TEST SIMULATOR ---
st.markdown("---")
st.subheader("⚠️ Stress Test Simulator")
st.markdown("Use this section to check your safety margin. This does **not** affect the charts above.")

with st.container(border=True):
    c1, c2 = st.columns(2)
    with c1:
        crash_scenario = st.slider("📉 Potential Market Drop (%)", 0, 50, 30)
    with c2:
        crash_year = st.slider("📅 Crash Occurs in Year", 1, strategy_horizon, 5)
    
    try:
        # Pull data from the 'Happy Path' table above
        row = df_annual[df_annual['Year'] == crash_year].iloc[0]
        loan = row["Investment Loan"]
        port_value_before_crash = row["Portfolio Value"]
        
        # Apply local crash calculation
        crashed_value = port_value_before_crash * (1 - crash_scenario / 100)
        net_position = crashed_value - loan
        
        st.divider()
        rc1, rc2, rc3 = st.columns(3)
        
        with rc1:
            st.metric(f"Loan Balance (Year {crash_year})", f"${loan:,.0f}")
        with rc2:
            st.metric(f"Portfolio (After -{crash_scenario}%)", f"${crashed_value:,.0f}", delta=f"-${port_value_before_crash - crashed_value:,.0f}", delta_color="inverse")
        with rc3:
            if net_position < 0:
                st.metric("Net Equity Position", f"-${abs(net_position):,.0f}", delta="UNDERWATER", delta_color="inverse")
                st.error("🚨 WARNING: You owe more than you own.")
                 
            else:
                st.metric("Net Equity Position", f"${net_position:,.0f}", delta="Safe")
                st.success("✅ SOLVENT: You have a safety buffer.")

    except Exception as e:
        st.write("Year out of range.")
