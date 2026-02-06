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
        <br><br>
        <b>The Goal:</b> Convert your non-deductible mortgage into a tax-deductible investment loan faster than paying it off normally.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. VISUAL EXPLAINER ---
st.subheader("⚙️ How the Cycle Works")
c1, c2, c3, c4, c5 = st.columns([1, 0.2, 1, 0.2, 1])

with c1:
    st.markdown(f"""
    <div style="text-align: center; border: 2px solid #DEE2E6; padding: 15px; border-radius: 10px; background-color: white;">
        <h2 style="margin:0;">🏠</h2>
        <h4 style="margin:5px 0;">1. Pay Mortgage</h4>
        <p style="font-size: 0.8em; color: #666; margin:0;">Pay Principal</p>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown("<h2 style='text-align: center; padding-top: 40px; color: #ccc;'>➔</h2>", unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div style="text-align: center; border: 2px solid {PRIMARY_GOLD}; padding: 15px; border-radius: 10px; background-color: #FFFDF5;">
        <h2 style="margin:0;">🏦</h2>
        <h4 style="margin:5px 0;">2. Re-Borrow</h4>
        <p style="font-size: 0.8em; color: #666; margin:0;">Access HELOC</p>
    </div>
    """, unsafe_allow_html=True)
with c4:
    st.markdown("<h2 style='text-align: center; padding-top: 40px; color: #ccc;'>➔</h2>", unsafe_allow_html=True)
with c5:
    st.markdown(f"""
    <div style="text-align: center; border: 2px solid #2E2B28; padding: 15px; border-radius: 10px; background-color: #F8F9FA;">
        <h2 style="margin:0;">📈</h2>
        <h4 style="margin:5px 0;">3. Invest</h4>
        <p style="font-size: 0.8em; color: #666; margin:0;">Compound Growth</p>
    </div>
    """, unsafe_allow_html=True)

st.caption("The Accelerator: Tax refunds are used to prepay the mortgage, creating MORE room to borrow and invest immediately.")
st.divider()

# --- 6. INPUTS ---
with st.container(border=True):
    st.markdown("### 📝 Configure Your Scenario")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        mortgage_amt = st.number_input("Mortgage Balance ($)", value=500000.0, step=10000.0)
    with c2:
        amortization = st.slider("Amortization (Years)", 10, 30, 25)
    with c3:
        mortgage_rate = st.number_input("Mortgage Rate (%)", value=5.0, step=0.1)

    c4, c5, c6 = st.columns(3)
    with c4:
        loc_rate = st.number_input("HELOC Rate (%)", value=6.0, step=0.1)
    with c5:
        inv_return = st.number_input("Inv. Return (%)", value=7.0, step=0.1)
    with c6:
        initial_lump = st.number_input("Initial Available HELOC ($)", value=0.0, step=5000.0, help="Existing room you can borrow immediately.")

    c7, c8, c9 = st.columns(3)
    with c7:
         tax_rate = st.number_input("Marginal Tax Rate (%)", value=suggested_tax_rate, step=0.5)
    with c8:
        st.caption(f"💡 Strategy: Used **{high_earner}'s** rate.")

# --- 7. CALCULATION ENGINE ---
r_m = mortgage_rate / 100 / 12
n_m = amortization * 12
monthly_payment = mortgage_amt * (r_m * (1 + r_m)**n_m) / ((1 + r_m)**n_m - 1)

balance = mortgage_amt
heloc_balance = 0.0
portfolio = 0.0
cum_tax_refund = 0.0

if initial_lump > 0:
    heloc_balance += initial_lump
    portfolio += initial_lump

annual_data = []
current_year_heloc_interest = 0.0
year_refund = 0.0
year_principal_reborrowed = 0.0
current_year_borrows = 0.0

for month in range(1, n_m + 1):
    # 1. Mortgage
    interest_m = balance * r_m
    principal_m = monthly_payment - interest_m
    if principal_m > balance: principal_m = balance
    
    balance -= principal_m
    
    # 2. Reborrow Principal
    new_borrowing = principal_m 
    year_principal_reborrowed += principal_m
    
    # 3. Interest Tracking
    interest_heloc = heloc_balance * (loc_rate / 100 / 12)
    current_year_heloc_interest += interest_heloc
    
    # 4. Tax Refund Event (Once per year, Month 1 of new year)
    refund_applied = 0.0
    if month % 12 == 1 and month > 1:
        # Calculate refund based on prev year interest
        # (Approx logic: simulation simplifies cashflow timing slightly)
        refund_amount = current_year_heloc_interest * (tax_rate / 100)
        
        if balance > 0:
            balance -= refund_amount
            refund_applied = refund_amount
            new_borrowing += refund_amount # Re-borrow immediately
        
        current_year_heloc_interest = 0.0 # Reset for new year
        year_refund = refund_amount
        cum_tax_refund += refund_amount

    # 5. Invest
    current_year_borrows += new_borrowing
    heloc_balance += new_borrowing
    portfolio += new_borrowing 
    portfolio = portfolio * (1 + inv_return / 100 / 12)

    # Annual Snapshot
    if month % 12 == 0 or balance <= 0:
        year = month // 12
        # Logic to capture the refund that happened THIS calendar year loop
        # (Which was calculated based on LAST year's interest, but applied THIS year)
        
        annual_data.append({
            "Year": year,
            "Mortgage Balance": max(0, balance),
            "Investment Loan": heloc_balance,
            "Portfolio Value": portfolio,
            "Annual Tax Refund": year_refund,
            "Annual Re-Borrowed": current_year_borrows,
            "Net Equity": portfolio - heloc_balance
        })
        
        # Reset annual trackers
        year_refund = 0.0 
        current_year_borrows = 0.0
        
    if balance <= 0 and month >= n_m: break

df_annual = pd.DataFrame(annual_data)

# --- 8. 10-YEAR TABLE (UPDATED) ---
st.divider()
st.subheader("📅 10-Year Strategy Execution")
st.info("ℹ️ **Note on Tax Refunds:** This table assumes your tax refund is used to pre-pay the mortgage, and that specific amount is immediately re-borrowed to invest.")

# Filter first 10 years
df_10 = df_annual[df_annual['Year'] <= 10].copy()

# Sum Row Calculation
sum_refund = df_10['Annual Tax Refund'].sum()
sum_invested = df_10['Annual Re-Borrowed'].sum()

# Formatting for Display
display_df = df_10.copy()
display_df = display_df[['Year', 'Mortgage Balance', 'Annual Re-Borrowed', 'Annual Tax Refund', 'Investment Loan', 'Portfolio Value']]
display_df.columns = ['Year', 'Mortgage Bal', 'Total Invested (Year)', 'Tax Refund (Re-invested)', 'Total Loan', 'Portfolio Value']

# Format Numbers
for col in display_df.columns:
    if col != 'Year':
        display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}")

# Add Sum Row manually to dataframe for display
sum_row = pd.DataFrame([{
    'Year': 'TOTAL',
    'Mortgage Bal': '-',
    'Total Invested (Year)': f"${sum_invested:,.0f}",
    'Tax Refund (Re-invested)': f"${sum_refund:,.0f}",
    'Total Loan': '-',
    'Portfolio Value': '-'
}])

final_table = pd.concat([display_df, sum_row], ignore_index=True)

st.table(final_table)

# --- 9. CHARTS ---
st.divider()
st.subheader("📈 Long-Term Projection")
col_res1, col_res2 = st.columns(2)

with col_res1:
    fig_debt = go.Figure()
    fig_debt.add_trace(go.Scatter(x=df_annual["Year"], y=df_annual["Mortgage Balance"], name="Mortgage", fill='tozeroy', line=dict(color=INTEREST_COLOR)))
    fig_debt.add_trace(go.Scatter(x=df_annual["Year"], y=df_annual["Investment Loan"], name="Invest Loan", line=dict(color=PRINCIPAL_COLOR, width=4)))
    fig_debt.update_layout(title="Debt Swap: Bad to Good", hovermode="x unified", plot_bgcolor="white", height=350, yaxis=dict(tickprefix="$"))
    st.plotly_chart(fig_debt, use_container_width=True)

with col_res2:
    fig_wealth = go.Figure()
    fig_wealth.add_trace(go.Bar(x=df_annual["Year"], y=df_annual["Portfolio Value"], name="Assets", marker_color=PRINCIPAL_COLOR))
    fig_wealth.add_trace(go.Scatter(x=df_annual["Year"], y=df_annual["Investment Loan"], name="Liabilities", line=dict(color=RISK_RED, width=2, dash='dash')))
    fig_wealth.update_layout(title="Asset Growth vs Debt", hovermode="x unified", plot_bgcolor="white", height=350, yaxis=dict(tickprefix="$"))
    st.plotly_chart(fig_wealth, use_container_width=True)

# --- 10. RISK SIMULATOR (FIXED) ---
st.markdown("---")
st.subheader("⚠️ Stress Test: When Leverage Bites")
st.markdown("""
**Why did it look safe before?** You were looking at Year 25. By then, growth usually beats debt.
**The real risk is early on.** Use the slider below to crash the market in **Year 1 or 3**.
""")

with st.container(border=True):
    c1, c2 = st.columns(2)
    with c1:
        crash_scenario = st.slider("📉 Market Drop (%)", 0, 50, 30)
    with c2:
        crash_year = st.slider("📅 Crash Happens in Year", 1, 10, 2)
    
    # Get data for the specific crash year
    try:
        row = df_annual[df_annual['Year'] == crash_year].iloc[0]
        loan_at_crash = row["Investment Loan"]
        port_at_crash = row["Portfolio Value"]
        
        # Apply Crash
        crashed_value = port_at_crash * (1 - crash_scenario / 100)
        underwater_amount = crashed_value - loan_at_crash
        
        st.divider()
        rc1, rc2, rc3 = st.columns(3)
        
        with rc1:
            st.metric(f"Loan Balance (Year {crash_year})", f"${loan_at_crash:,.0f}")
        with rc2:
            st.metric(f"Portfolio (After -{crash_scenario}%)", f"${crashed_value:,.0f}", delta=f"-${port_at_crash - crashed_value:,.0f}", delta_color="inverse")
        with rc3:
            if underwater_amount < 0:
                st.metric("Net Position", f"-${abs(underwater_amount):,.0f}", delta="UNDERWATER", delta_color="inverse")
                st.error(f"🚨 In Year {crash_year}, you would owe the bank ${abs(underwater_amount):,.0f} more than your assets are worth.")
            else:
                st.metric("Net Position", f"${underwater_amount:,.0f}", delta="Safe")
                st.success(f"✅ In Year {crash_year}, your growth buffer absorbed the crash.")

    except:
        st.error("Select a valid year within the amortization period.")

# --- 11. DISCLAIMER ---
st.markdown("---")
st.caption("Strategy Disclaimer: Borrowing to invest increases risk. Tax rules are complex. Consult a professional.")
