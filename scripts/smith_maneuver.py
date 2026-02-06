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

# --- 3. HEADER ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("The Smith Maneuver Strategy")

# --- 4. STORYTELLING ---
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.5em;">🔄 {household_names}: The "Money Move" Machine</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        The logic is a cycle: Every dollar you pay off your <b>Bad Debt</b> (Mortgage) instantly becomes available as <b>Good Debt</b> (HELOC).
        You assume the bank automatically lets you re-borrow that principal to invest. Additionally, if you have existing room in your HELOC, 
        you can jump-start the machine with a lump sum.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. INPUTS ---
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
        loc_rate = st.number_input("HELOC Rate (%)", value=6.0, step=0.1)
    with c5:
        inv_return = st.number_input("Inv. Return (%)", value=7.0, step=0.1)
    with c6:
        # Initial HELOC Room
        initial_lump = st.number_input("Initial Available HELOC ($)", value=0.0, step=5000.0, help="Existing room you can borrow immediately to start.")

    # Row 3: Tax
    c7, c8, c9 = st.columns(3)
    with c7:
         tax_rate = st.number_input("Marginal Tax Rate (%)", value=suggested_tax_rate, step=0.5)
    with c8:
        st.caption(f"💡 Strategy: Used **{high_earner}'s** rate.")

# --- 6. CALCULATION ENGINE ---
# Monthly Calculations
r_m = mortgage_rate / 100 / 12
n_m = amortization * 12
monthly_payment = mortgage_amt * (r_m * (1 + r_m)**n_m) / ((1 + r_m)**n_m - 1)

balance = mortgage_amt
heloc_balance = 0.0
portfolio = 0.0
cum_tax_refund = 0.0

# Initial Lump Sum Deployment (Month 0 event)
if initial_lump > 0:
    heloc_balance += initial_lump
    portfolio += initial_lump

annual_data = []
monthly_ledger = [] # For the 36-month view

current_year_heloc_interest = 0.0
prev_year_refund = 0.0

for month in range(1, n_m + 1):
    # 1. Mortgage Payment
    interest_m = balance * r_m
    principal_m = monthly_payment - interest_m
    if principal_m > balance: principal_m = balance
    
    balance -= principal_m
    
    # 2. READVANCE: The "Money Move"
    # Logic: Principal paid + Previous Tax Refund (if applied) becomes new borrowing room
    # Note: In this simulation, we re-borrow the Principal portion immediately.
    new_borrowing = principal_m 
    
    # 3. HELOC Interest Cost (Accrues monthly)
    interest_heloc = heloc_balance * (loc_rate / 100 / 12)
    current_year_heloc_interest += interest_heloc
    
    # 4. TAX REFUND EVENT (Assume happens in Month 13, 25, 37 etc for prev year)
    refund_applied = 0.0
    refund_reborrowed = 0.0
    
    if month % 12 == 1 and month > 1:
        # Calculate refund based on previous year's total HELOC interest
        refund_amount = current_year_heloc_interest * (tax_rate / 100)
        
        # APPLY STRATEGY: 
        # A. Refund pays down mortgage extra
        if balance > 0:
            balance -= refund_amount
            refund_applied = refund_amount
            
            # B. Since mortgage dropped, we re-borrow that amount immediately
            refund_reborrowed = refund_amount
            new_borrowing += refund_reborrowed
        
        # Reset tracker for next year
        current_year_heloc_interest = 0.0
        cum_tax_refund += refund_amount

    # 5. INVEST
    heloc_balance += new_borrowing
    portfolio += new_borrowing # Buy assets
    
    # Portfolio Growth (Monthly compounding for smoothness)
    portfolio = portfolio * (1 + inv_return / 100 / 12)
    
    # Record Monthly Data (First 36 Months)
    if month <= 36:
        monthly_ledger.append({
            "Month": month,
            "Mortgage Bal": balance,
            "Principal Pd": principal_m + refund_applied,
            "HELOC Borrowed": new_borrowing,
            "HELOC Interest": interest_heloc,
            "Tax Refund In": refund_applied if refund_applied > 0 else "-",
            "Portfolio Value": portfolio
        })

    # Record Annual Data
    if month % 12 == 0 or balance <= 0:
        year = month // 12
        annual_data.append({
            "Year": year,
            "Mortgage Balance": max(0, balance),
            "Investment Loan": heloc_balance,
            "Portfolio Value": portfolio,
            "Tax Refunds": cum_tax_refund,
            "Net Worth": portfolio - heloc_balance - balance
        })
        
    if balance <= 0 and month >= n_m: break

df_annual = pd.DataFrame(annual_data)
df_monthly = pd.DataFrame(monthly_ledger)

# --- 7. VISUAL EXPLAINER (THE MACHINE) ---
st.subheader("⚙️ How the \"Money Move\" Works")
c1, c2, c3, c4, c5 = st.columns([1, 0.2, 1, 0.2, 1])

with c1:
    st.markdown("""
    <div style="text-align: center; border: 2px solid #DEE2E6; padding: 10px; border-radius: 10px;">
        <h4>1. Pay Mortgage</h4>
        <p style="font-size: 0.9em; color: #666;">Monthly Pmt pays down principal.</p>
        <h3 style="color: #4D4D4D;">⬇️ Debt</h3>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown("<h2 style='text-align: center; padding-top: 40px;'>➔</h2>", unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div style="text-align: center; border: 2px solid {PRIMARY_GOLD}; padding: 10px; border-radius: 10px; background-color: #FFFDF5;">
        <h4>2. Re-Borrow</h4>
        <p style="font-size: 0.9em; color: #666;">Bank re-advances that exact amount.</p>
        <h3 style="color: {PRIMARY_GOLD};">⬆️ Loan</h3>
    </div>
    """, unsafe_allow_html=True)
with c4:
    st.markdown("<h2 style='text-align: center; padding-top: 40px;'>➔</h2>", unsafe_allow_html=True)
with c5:
    st.markdown("""
    <div style="text-align: center; border: 2px solid #2E2B28; padding: 10px; border-radius: 10px; background-color: #F8F9FA;">
        <h4>3. Invest</h4>
        <p style="font-size: 0.9em; color: #666;">Buy assets. Interest is now deductible.</p>
        <h3 style="color: #2E2B28;">💰 Assets</h3>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- 8. THE MONTHLY LEDGER (USER REQUEST) ---
st.subheader("📅 3-Year Monthly Schedule (The Mechanics)")
st.markdown("This table tracks exactly how money moves month-to-month. Notice specifically **Months 13, 25, and 37** where the Tax Refund hits, pays down the mortgage extra, and is immediately re-borrowed.")

# Formatting the dataframe for display
display_df = df_monthly.copy()
display_df['Mortgage Bal'] = display_df['Mortgage Bal'].apply(lambda x: f"${x:,.0f}")
display_df['Principal Pd'] = display_df['Principal Pd'].apply(lambda x: f"${x:,.0f}")
display_df['HELOC Borrowed'] = display_df['HELOC Borrowed'].apply(lambda x: f"${x:,.0f}")
display_df['HELOC Interest'] = display_df['HELOC Interest'].apply(lambda x: f"${x:,.2f}")
display_df['Tax Refund In'] = display_df['Tax Refund In'].apply(lambda x: f"${x:,.0f}" if x != "-" else "-")
display_df['Portfolio Value'] = display_df['Portfolio Value'].apply(lambda x: f"${x:,.0f}")

st.dataframe(
    display_df,
    column_config={
        "Month": st.column_config.NumberColumn("Mo.", format="%d"),
        "HELOC Borrowed": st.column_config.TextColumn("Re-Borrowed (Invested)", help="Amount moved from Mortgage Principal -> HELOC -> Investment"),
        "Tax Refund In": st.column_config.TextColumn("Tax Refund Event", help="Refund applied to Mortgage, then re-borrowed.")
    },
    use_container_width=True,
    hide_index=True,
    height=400
)

# --- 9. CHARTS ---
st.divider()
st.subheader("📈 Long-Term Projection")
col_res1, col_res2 = st.columns(2)

with col_res1:
    fig_debt = go.Figure()
    fig_debt.add_trace(go.Scatter(x=df_annual["Year"], y=df_annual["Mortgage Balance"], name="Mortgage (Bad Debt)", fill='tozeroy', line=dict(color=INTEREST_COLOR)))
    fig_debt.add_trace(go.Scatter(x=df_annual["Year"], y=df_annual["Investment Loan"], name="Inv Loan (Good Debt)", line=dict(color=PRINCIPAL_COLOR, width=4)))
    fig_debt.update_layout(title="Debt Conversion", hovermode="x unified", plot_bgcolor="white", height=350, yaxis=dict(tickprefix="$"))
    st.plotly_chart(fig_debt, use_container_width=True)

with col_res2:
    fig_wealth = go.Figure()
    fig_wealth.add_trace(go.Bar(x=df_annual["Year"], y=df_annual["Portfolio Value"], name="Portfolio Value", marker_color=PRINCIPAL_COLOR))
    fig_wealth.add_trace(go.Scatter(x=df_annual["Year"], y=df_annual["Tax Refunds"], name="Cumulative Refunds", line=dict(color=SLATE_ACCENT, width=4)))
    fig_wealth.update_layout(title="Net Wealth Creation", hovermode="x unified", plot_bgcolor="white", height=350, yaxis=dict(tickprefix="$"))
    st.plotly_chart(fig_wealth, use_container_width=True)

# --- 10. DISCLAIMER ---
st.markdown("---")
st.markdown("""
<div style='background-color: #f8f9fa; padding: 16px 20px; border-radius: 5px; border: 1px solid #dee2e6;'>
    <p style='font-size: 12px; color: #6c757d; line-height: 1.6; margin-bottom: 0;'>
        <strong>⚠️ Strategy Disclaimer:</strong><br>
        The Smith Maneuver involves borrowing to invest (leverage). This increases risk: if your portfolio drops, you still owe the loan.
        Tax rules regarding interest deductibility are strict (funds must be traceable to income-generating assets). 
        This tool assumes tax refunds are reinvested perfectly, which requires discipline. Consult a CPA.
    </p>
</div>
""", unsafe_allow_html=True)
