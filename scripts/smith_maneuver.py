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

# --- 3. HEADER ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("The Smith Maneuver Strategy")

# --- 4. PREREQUISITES CHECKLIST ---
with st.expander("✅ Strategy Prerequisites (Click to View)", expanded=False):
    st.markdown("""
    1. **Readvanceable Mortgage:** Automatic HELOC limit increase (e.g., RBC Homeline).
    2. **Principal Paydown:** Must be a standard amortizing mortgage.
    3. **Non-Registered Account:** Funds must be invested in a taxable account.
    4. **Income-Generating Assets:** Must pay dividends/interest (no pure growth stocks).
    """)

# --- 5. VISUAL EXPLAINER ---
st.subheader("⚙️ The Mechanics (Monthly Cycle)")
c1, c2, c3, c4, c5 = st.columns([1, 0.2, 1, 0.2, 1])

with c1:
    st.markdown(f"""
    <div style="text-align: center; border: 2px solid #DEE2E6; padding: 10px; border-radius: 10px; background-color: white;">
        <h4 style="margin:5px 0;">1. Pay Mortgage</h4>
        <div style="margin-top:5px; background:#eee; padding:5px; border-radius:5px; font-weight:bold; font-size: 0.9em; color:#666;">-$1,000</div>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown("<h2 style='text-align: center; padding-top: 30px; color: #ccc;'>➔</h2>", unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div style="text-align: center; border: 2px solid {PRIMARY_GOLD}; padding: 10px; border-radius: 10px; background-color: #FFFDF5;">
        <h4 style="margin:5px 0;">2. Re-Borrow</h4>
        <div style="margin-top:5px; background:#FFF8E1; padding:5px; border-radius:5px; font-weight:bold; font-size: 0.9em; color:{PRIMARY_GOLD};">+$1,000</div>
    </div>
    """, unsafe_allow_html=True)
with c4:
    st.markdown("<h2 style='text-align: center; padding-top: 30px; color: #ccc;'>➔</h2>", unsafe_allow_html=True)
with c5:
    st.markdown(f"""
    <div style="text-align: center; border: 2px solid #2E2B28; padding: 10px; border-radius: 10px; background-color: #F8F9FA;">
        <h4 style="margin:5px 0;">3. Invest</h4>
        <div style="margin-top:5px; background:#ddd; padding:5px; border-radius:5px; font-weight:bold; font-size: 0.9em; color:#333;">+$1,000</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- 6. INPUTS ---
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
        inv_return = st.number_input("Total Return (%)", value=8.0, step=0.1)
    with c6:
        div_yield = st.number_input("Dividend Yield (%)", value=5.0, step=0.1)

    # Row 3: Tax & Horizon
    c7, c8, c9 = st.columns(3)
    with c7:
         tax_rate = st.number_input("Marginal Tax Rate (%)", value=suggested_tax_rate, step=0.5)
    with c8:
        initial_lump = st.number_input("Initial HELOC Room ($)", value=0.0, step=5000.0)
    with c9:
        strategy_horizon = st.select_slider("Strategy Horizon (Years)", options=[5, 10, 15, 20, 25], value=10)

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
current_year_borrows = 0.0
year_heloc_interest_cost = 0.0

for month in range(1, n_m + 1):
    # 1. Mortgage
    interest_m = balance * r_m
    principal_m = monthly_payment - interest_m
    if principal_m > balance: principal_m = balance
    
    balance -= principal_m
    
    # 2. Reborrow Principal
    new_borrowing = principal_m 
    
    # 3. Interest Tracking
    interest_heloc = heloc_balance * (loc_rate / 100 / 12)
    current_year_heloc_interest += interest_heloc
    year_heloc_interest_cost += interest_heloc
    
    # 4. Tax Refund Event (Annual)
    if month % 12 == 1 and month > 1:
        refund_amount = current_year_heloc_interest * (tax_rate / 100)
        
        if balance > 0:
            balance -= refund_amount
            new_borrowing += refund_amount 
        
        current_year_heloc_interest = 0.0 
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
        
        annual_div_income = portfolio * (div_yield / 100)
        
        annual_data.append({
            "Year": year,
            "Mortgage Balance": max(0, balance),
            "Investment Loan": heloc_balance,
            "Portfolio Value": portfolio,
            "Annual Tax Refund": year_refund,
            "Dividend Income": annual_div_income,
            "Annual Interest Cost": year_heloc_interest_cost,
            "Net Equity": portfolio - heloc_balance
        })
        
        year_refund = 0.0 
        current_year_borrows = 0.0
        year_heloc_interest_cost = 0.0
        
    if balance <= 0 and month >= n_m: break

df_annual = pd.DataFrame(annual_data)

# --- 8. CASH FLOW ANALYSIS (NEW SECTION) ---
# Filter by Horizon
df_view = df_annual[df_annual['Year'] <= strategy_horizon].copy()

total_int_cost = df_view['Annual Interest Cost'].sum()
total_divs = df_view['Dividend Income'].sum()
total_refunds = df_view['Annual Tax Refund'].sum()
net_cashflow = (total_divs + total_refunds) - total_int_cost

st.divider()
st.subheader(f"💰 Cash Flow Analysis ({strategy_horizon} Year Horizon)")
st.markdown("Comparing the cost of the HELOC vs. the income it generates (Dividends + Tax Refunds).")

cf1, cf2, cf3, cf4 = st.columns(4)
with cf1:
    st.metric("Total Interest Cost", f"${total_int_cost:,.0f}", help="Total interest paid to the bank for the HELOC.")
with cf2:
    st.metric("Total Dividends", f"${total_divs:,.0f}", help="Cash income generated by the portfolio.")
with cf3:
    st.metric("Total Tax Refunds", f"${total_refunds:,.0f}", help="Cash returned by CRA due to interest deductions.")
with cf4:
    if net_cashflow > 0:
        st.metric("Net Cash Benefit", f"${net_cashflow:,.0f}", delta="Positive", help="Income exceeded Interest costs.")
    else:
        st.metric("Net Out-of-Pocket", f"-${abs(net_cashflow):,.0f}", delta="Negative", delta_color="inverse", help="You had to top up the interest payments.")

st.caption("**Note on Dividends:** This model assumes Dividends are used to help pay the HELOC interest. If Dividends > Interest, the excess is pocketed or reinvested.")

# --- 9. TABLE ---
st.divider()
st.subheader(f"📅 {strategy_horizon}-Year Projection")

display_df = df_view[['Year', 'Mortgage Balance', 'Investment Loan', 'Portfolio Value', 'Annual Tax Refund', 'Dividend Income']].copy()
display_df.columns = ['Year', 'Bad Debt (Mortgage)', 'Good Debt (HELOC)', 'Asset Value (Portfolio)', 'Tax Refund (Re-invested)', 'Dividend Cash Flow']

# Format
for col in display_df.columns:
    if col != 'Year':
        display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}")

st.table(display_df)

# --- 10. CHARTS (REDUCED HEIGHT) ---
st.divider()
st.subheader("📈 Visual Projection")
col_res1, col_res2 = st.columns(2)

with col_res1:
    fig_debt = go.Figure()
    fig_debt.add_trace(go.Scatter(x=df_annual["Year"], y=df_annual["Mortgage Balance"], name="Bad Debt", fill='tozeroy', line=dict(color=INTEREST_COLOR)))
    fig_debt.add_trace(go.Scatter(x=df_annual["Year"], y=df_annual["Investment Loan"], name="Good Debt", line=dict(color=PRINCIPAL_COLOR, width=4)))
    fig_debt.update_layout(title="Debt Swap", hovermode="x unified", plot_bgcolor="white", height=300, margin=dict(t=30, b=0), yaxis=dict(tickprefix="$"))
    st.plotly_chart(fig_debt, use_container_width=True)

with col_res2:
    fig_wealth = go.Figure()
    fig_wealth.add_trace(go.Bar(x=df_annual["Year"], y=df_annual["Portfolio Value"], name="Assets", marker_color=PRINCIPAL_COLOR))
    fig_wealth.add_trace(go.Scatter(x=df_annual["Year"], y=df_annual["Investment Loan"], name="Liabilities", line=dict(color=RISK_RED, width=2, dash='dash')))
    fig_wealth.update_layout(title="Net Wealth", hovermode="x unified", plot_bgcolor="white", height=300, margin=dict(t=30, b=0), yaxis=dict(tickprefix="$"))
    st.plotly_chart(fig_wealth, use_container_width=True)

# --- 11. RISK SIMULATOR ---
st.markdown("---")
st.subheader("⚠️ Stress Test")
with st.container(border=True):
    c1, c2 = st.columns(2)
    with c1:
        crash_scenario = st.slider("📉 Market Drop (%)", 0, 50, 30)
    with c2:
        crash_year = st.slider("📅 Crash Year", 1, 10, 2)
    
    try:
        row = df_annual[df_annual['Year'] == crash_year].iloc[0]
        loan = row["Investment Loan"]
        port = row["Portfolio Value"]
        crashed = port * (1 - crash_scenario / 100)
        net = crashed - loan
        
        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("Loan Balance", f"${loan:,.0f}")
        rc2.metric("Crashed Portfolio", f"${crashed:,.0f}", delta=f"-${port - crashed:,.0f}", delta_color="inverse")
        if net < 0:
            rc3.metric("Net Equity", f"-${abs(net):,.0f}", delta="UNDERWATER", delta_color="inverse")
        else:
            rc3.metric("Net Equity", f"${net:,.0f}", delta="Safe")
    except:
        st.write("Year out of range.")
