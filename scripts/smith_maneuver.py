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

# --- 1. DATA LINKING & PROFILING ---
# Fetch client data from the profile page
prof = st.session_state.get('user_profile', {})
client_name1 = prof.get('p1_name', 'Client 1')
client_name2 = prof.get('p2_name', 'Client 2')
p1_income = float(prof.get('p1_t4', 0)) + float(prof.get('p1_bonus', 0))
p2_income = float(prof.get('p2_t4', 0))

# Determine Household Name
household_names = f"{client_name1} & {client_name2}" if client_name2 else client_name1

# Determine Higher Earner for Tax Strategy
if p1_income > p2_income:
    high_earner = client_name1
    high_income = p1_income
else:
    high_earner = client_name2 if client_name2 else client_name1
    high_income = p2_income

# Simple function to estimate marginal tax rate (Rough Canadian Estimate)
def estimate_marginal_rate(income):
    if income > 240000: return 53.5
    elif income > 170000: return 48.0
    elif income > 110000: return 43.0
    elif income > 55000: return 29.0
    else: return 20.0

suggested_tax_rate = estimate_marginal_rate(high_income)

# --- 2. THEME & BRANDING ---
SCENARIO_COLORS = ["#CEB36F", "#706262", "#2E2B28", "#C0A385", "#E7E7E7"]
PRINCIPAL_COLOR = "#CEB36F" # Gold for Equity/Portfolio
INTEREST_COLOR = "#2E2B28"  # Charcoal for Interest/Debt
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"
PRIMARY_GOLD = "#CEB36F"

# --- 3. PAGE HEADER ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=140)
with header_col2:
    st.title("The Smith Maneuver Strategy")

# --- 4. STORYTELLING (DYNAMIC) ---
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.5em;">🔄 {household_names}: Turning Mortgage Interest into Wealth</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        <b>{household_names}</b> are looking to optimize their debt. Instead of just paying down their mortgage, 
        they can use the <b>Smith Maneuver</b> to re-borrow the principal they pay off to invest in income-generating assets.
        This converts their non-deductible mortgage interest into <b>tax-deductible investment loan interest</b>, 
        generating annual tax refunds that can be used to pay down the mortgage even faster.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. STRATEGY INPUTS (MOVED TO MAIN PAGE) ---
with st.container(border=True):
    st.markdown("### ⚙️ Strategy Configuration")
    
    # Row 1: Mortgage Basics
    c1, c2, c3 = st.columns(3)
    with c1:
        mortgage_amt = st.number_input("Mortgage Balance ($)", value=500000.0, step=10000.0)
    with c2:
        amortization = st.slider("Amortization (Years)", 10, 30, 25)
    with c3:
        mortgage_rate = st.number_input("Mortgage Rate (%)", value=5.0, step=0.1)

    # Row 2: Investment & Tax Logic
    c4, c5, c6 = st.columns(3)
    with c4:
        # Investment Return (LOC)
        loc_rate = st.number_input("HELOC Rate (%)", value=6.0, step=0.1, help="Interest rate on the re-borrowed funds.")
    with c5:
        inv_return = st.number_input("Investment Return (%)", value=7.0, step=0.1, help="Expected return on the investment portfolio.")
    with c6:
        # Tax Rate (With Advice)
        tax_rate = st.number_input(
            "Marginal Tax Rate (%)", 
            value=suggested_tax_rate, 
            step=0.5, 
            help=f"Tip: Use the tax rate of the higher earner ({high_earner}) to maximize the deduction."
        )

    # Tax Strategy Callout
    if p1_income > 0 or p2_income > 0:
        st.caption(f"💡 **Tax Strategy:** Based on income, **{high_earner}** (Approx. {suggested_tax_rate}%) is likely the best person to hold the investment loan.")

# --- 6. CALCULATION ENGINE ---
# Basic Amortization
r_m = mortgage_rate / 100 / 12
n_m = amortization * 12
monthly_payment = mortgage_amt * (r_m * (1 + r_m)**n_m) / ((1 + r_m)**n_m - 1)

# Simulation Loop
balance = mortgage_amt
inv_loan = 0.0
portfolio = 0.0
cum_tax_refund = 0.0

data = []

for year in range(1, amortization + 1):
    interest_paid_mortgage = 0
    principal_paid_mortgage = 0
    
    # Monthly Cycle
    for month in range(12):
        if balance > 0:
            interest = balance * r_m
            principal = monthly_payment - interest
            if principal > balance: principal = balance
            
            balance -= principal
            interest_paid_mortgage += interest
            principal_paid_mortgage += principal
            
            # SMITH MANEUVER: Re-borrow the principal paid
            inv_loan += principal
    
    # Investment Growth (Annual)
    portfolio = (portfolio + principal_paid_mortgage) * (1 + inv_return / 100)
    
    # Tax Deduction Calculation
    # Interest on the Investment Loan is deductible
    inv_interest_cost = inv_loan * (loc_rate / 100)
    tax_refund = inv_interest_cost * (tax_rate / 100)
    
    # Re-invest the tax refund into the mortgage (Prepayment)
    if balance > 0:
        balance -= tax_refund
        # And immediately re-borrow that refund amount too!
        inv_loan += tax_refund
        portfolio += tax_refund # Add to investment pool
    
    cum_tax_refund += tax_refund
    
    data.append({
        "Year": year,
        "Mortgage Balance": max(0, balance),
        "Investment Loan": inv_loan,
        "Portfolio Value": portfolio,
        "Tax Refunds": cum_tax_refund,
        "Net Worth": portfolio - inv_loan - balance
    })
    
    if balance <= 0 and year < amortization:
        # Fill remaining years flat for chart aesthetics
        pass

df = pd.DataFrame(data)

# --- 7. RESULTS DASHBOARD ---
# Find payoff year
try:
    m_payoff = df[df["Mortgage Balance"] <= 100].iloc[0]["Year"]
except:
    m_payoff = amortization

st.divider()

col_res1, col_res2 = st.columns([1, 1])

with col_res1:
    st.subheader("1. Debt Conversion")
    st.markdown("Watch the **Bad Debt** (Mortgage) fall while **Good Debt** (Tax-Deductible Loan) rises.")
    
    fig_debt = go.Figure()
    fig_debt.add_trace(go.Scatter(x=df["Year"], y=df["Mortgage Balance"], name="Mortgage (Non-Deductible)", fill='tozeroy', line=dict(color=INTEREST_COLOR)))
    fig_debt.add_trace(go.Scatter(x=df["Year"], y=df["Investment Loan"], name="Investment Loan (Deductible)", line=dict(color=PRINCIPAL_COLOR, width=4)))
    
    fig_debt.update_layout(hovermode="x unified", plot_bgcolor="white", height=400, yaxis=dict(tickprefix="$"))
    st.plotly_chart(fig_debt, use_container_width=True)

with col_res2:
    st.subheader("2. Total Wealth Growth")
    st.markdown("The net result of the strategy: **Portfolio Value** vs. **Cumulative Tax Refunds**.")
    
    fig_wealth = go.Figure()
    fig_wealth.add_trace(go.Bar(x=df["Year"], y=df["Portfolio Value"], name="Portfolio (Stocks/Rental)", marker_color=PRINCIPAL_COLOR))
    fig_wealth.add_trace(go.Scatter(x=df["Year"], y=df["Tax Refunds"], name="Cumulative Tax Refunds", line=dict(color=SLATE_ACCENT, width=4)))
    
    fig_wealth.update_layout(hovermode="x unified", plot_bgcolor="white", height=400, yaxis=dict(tickprefix="$"))
    st.plotly_chart(fig_wealth, use_container_width=True)

# --- 8. STRATEGIC INSIGHT ---
final_port = df['Portfolio Value'].iloc[-1]
net_benefit = df['Net Worth'].iloc[-1]

st.info(f"""
**Analyst Insight:** By implementing the Smith Maneuver, **{household_names}** could convert their mortgage interest into **${cum_tax_refund:,.0f}** in tax refunds over the term. 
By Year {m_payoff}, the home is free of non-deductible debt, and you have built a **${final_port:,.0f}** investment portfolio.
""")

# --- 9. LEGAL DISCLAIMER ---
st.markdown("---")
st.markdown("""
<div style='background-color: #f8f9fa; padding: 16px 20px; border-radius: 5px; border: 1px solid #dee2e6;'>
    <p style='font-size: 12px; color: #6c757d; line-height: 1.6; margin-bottom: 0;'>
        <strong>⚠️ Strategy Disclaimer:</strong><br>
        The Smith Maneuver involves borrowing to invest, which increases risk. If investment returns are lower than the loan interest rate, losses may occur.
        Tax deductibility of interest is subject to CRA rules (money must be used for income-generating assets). 
        This tool provides estimates only. Consult a qualified accountant or financial planner before execution.
    </p>
</div>
""", unsafe_allow_html=True)
