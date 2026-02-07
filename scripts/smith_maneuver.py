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
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid {BORDER_GREY}; margin-bottom: 25px;">
    <h4 style="margin-top:0; color: {SLATE_ACCENT};">✅ Strategy Prerequisites</h4>
    <p style="font-size: 0.95em; line-height: 1.6;">
    Before executing, ensure you meet these 4 criteria:
    </p>
    <ul style="font-size: 0.9em; line-height: 1.6;">
        <li><b>A. Readvanceable Mortgage:</b> You need a HELOC that automatically increases limit as principal is paid (e.g., RBC Homeline, Scotia STEP).</li>
        <li><b>B. Positive Principal Paydown:</b> Your monthly payment must actually reduce the principal (interest-only mortgages don't work for the conversion).</li>
        <li><b>C. Non-Registered Account:</b> You cannot invest in RRSP/TFSA. To deduct interest, the account must be taxable.</li>
        <li><b>D. Income-Generating Assets:</b> You must invest in assets with a "reasonable expectation of income" (Dividends, Rent, or Interest). Pure capital gains stocks do not qualify for interest deductibility.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# --- 5. VISUAL EXPLAINER ---
st.subheader("⚙️ The Mechanics (Monthly Cycle)")
c1, c2, c3, c4, c5 = st.columns([1, 0.2, 1, 0.2, 1])

with c1:
    st.markdown(f"""
    <div style="text-align: center; border: 2px solid #DEE2E6; padding: 15px; border-radius: 10px; background-color: white;">
        <h2 style="margin:0;">🏠</h2>
        <h4 style="margin:5px 0;">1. Pay Mortgage</h4>
        <p style="font-size: 0.8em; color: #666; margin:0;">You pay <b>$1,000</b> principal to the bank.</p>
        <div style="margin-top:10px; background:#eee; padding:5px; border-radius:5px; font-weight:bold; color:#666;">Mortgage: -$1,000</div>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown("<h2 style='text-align: center; padding-top: 60px; color: #ccc;'>➔</h2>", unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div style="text-align: center; border: 2px solid {PRIMARY_GOLD}; padding: 15px; border-radius: 10px; background-color: #FFFDF5;">
        <h2 style="margin:0;">🏦</h2>
        <h4 style="margin:5px 0;">2. Re-Borrow</h4>
        <p style="font-size: 0.8em; color: #666; margin:0;">Bank lets you borrow that <b>$1,000</b> back immediately.</p>
        <div style="margin-top:10px; background:#FFF8E1; padding:5px; border-radius:5px; font-weight:bold; color:{PRIMARY_GOLD};">HELOC: +$1,000</div>
    </div>
    """, unsafe_allow_html=True)
with c4:
    st.markdown("<h2 style='text-align: center; padding-top: 60px; color: #ccc;'>➔</h2>", unsafe_allow_html=True)
with c5:
    st.markdown(f"""
    <div style="text-align: center; border: 2px solid #2E2B28; padding: 15px; border-radius: 10px; background-color: #F8F9FA;">
        <h2 style="margin:0;">📈</h2>
        <h4 style="margin:5px 0;">3. Invest</h4>
        <p style="font-size: 0.8em; color: #666; margin:0;">You buy <b>$1,000</b> of Dividend ETFs.</p>
        <div style="margin-top:10px; background:#ddd; padding:5px; border-radius:5px; font-weight:bold; color:#333;">Assets: +$1,000</div>
    </div>
    """, unsafe_allow_html=True)

st.caption("Step 4: At tax time, you claim the interest on the HELOC. The resulting Refund is used to pre-pay the mortgage, accelerating Step 1.")
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
        inv_return = st.number_input("Total Return (%)", value=8.0, step=0.1, help="Total expected growth (Dividends + Capital Appreciation).")
    with c6:
        div_yield = st.number_input("Dividend Yield (%)", value=5.0, step=0.1, help="The portion of return paid out as income.")

    # Row 3: Tax & Room
    c7, c8, c9 = st.columns(3)
    with c7:
         tax_rate = st.number_input("Marginal Tax Rate (%)", value=suggested_tax_rate, step=0.5)
    with c8:
        initial_lump = st.number_input("Initial Available HELOC ($)", value=0.0, step=5000.0, help="Existing room you can borrow immediately.")
    with c9:
        st.write("") 

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
    
    # 4. Tax Refund Event (Annual)
    refund_applied = 0.0
    if month % 12 == 1 and month > 1:
        # Calculate refund based on prev year interest deduction
        refund_amount = current_year_heloc_interest * (tax_rate / 100)
        
        # Apply Refund -> Mortgage -> Reborrow
        if balance > 0:
            balance -= refund_amount
            refund_applied = refund_amount
            new_borrowing += refund_amount 
        
        current_year_heloc_interest = 0.0 
        year_refund = refund_amount
        cum_tax_refund += refund_amount

    # 5. Invest (Growth)
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
            "Net Equity": portfolio - heloc_balance
        })
        
        year_refund = 0.0 
        current_year_borrows = 0.0
        
    if balance <= 0 and month >= n_m: break

df_annual = pd.DataFrame(annual_data)

# --- 8. 10-YEAR TABLE ---
st.divider()
st.subheader("📅 10-Year Execution Plan")
st.markdown("This table assumes **all tax refunds** generated from interest are used to prepay the mortgage, and then immediately re-borrowed.")

# Filter first 10 years
df_10 = df_annual[df_annual['Year'] <= 10].copy()

# Sum Row
sum_refund = df_10['Annual Tax Refund'].sum()
sum_divs = df_10['Dividend Income'].sum()

# Formatting
display_df = df_10[['Year', 'Mortgage Balance', 'Investment Loan', 'Portfolio Value', 'Annual Tax Refund', 'Dividend Income']].copy()
display_df.columns = ['Year', 'Mortgage Bal', 'HELOC Bal', 'Portfolio Value', 'Interest Refund', 'Dividend Income']

# Format Numbers
for col in display_df.columns:
    if col != 'Year':
        display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}")

# Add Sum Row
sum_row = pd.DataFrame([{
    'Year': 'TOTAL',
    'Mortgage Bal': '-',
    'HELOC Bal': '-',
    'Portfolio Value': '-',
    'Interest Refund': f"${sum_refund:,.0f}",
    'Dividend Income': f"${sum_divs:,.0f}"
}])

final_table = pd.concat([display_df, sum_row], ignore_index=True)
st.table(final_table)

st.caption(f"Note: Your **Total Return is {inv_return}%**, comprised of **{div_yield}% Dividend Yield** and **{inv_return - div_yield}% Capital Growth**. The Dividend Income column shows the cash flow generated to satisfy CRA requirements.")

# --- 9. CHARTS ---
st.divider()
st.subheader("📈 Long-Term Projection")
col_res1, col_res2 = st.columns(2)

with col_res1:
    fig_debt = go.Figure()
    fig_debt.add_trace(go.Scatter(x=df_annual["Year"], y=df_annual["Mortgage Balance"], name="Bad Debt", fill='tozeroy', line=dict(color=INTEREST_COLOR)))
    fig_debt.add_trace(go.Scatter(x=df_annual["Year"], y=df_annual["Investment Loan"], name="Good Debt", line=dict(color=PRINCIPAL_COLOR, width=4)))
    fig_debt.update_layout(title="Debt Swap", hovermode="x unified", plot_bgcolor="white", height=350, yaxis=dict(tickprefix="$"))
    st.plotly_chart(fig_debt, use_container_width=True)

with col_res2:
    fig_wealth = go.Figure()
    fig_wealth.add_trace(go.Bar(x=df_annual["Year"], y=df_annual["Portfolio Value"], name="Assets", marker_color=PRINCIPAL_COLOR))
    fig_wealth.add_trace(go.Scatter(x=df_annual["Year"], y=df_annual["Investment Loan"], name="Liabilities", line=dict(color=RISK_RED, width=2, dash='dash')))
    fig_wealth.update_layout(title="Assets vs Liabilities", hovermode="x unified", plot_bgcolor="white", height=350, yaxis=dict(tickprefix="$"))
    st.plotly_chart(fig_wealth, use_container_width=True)

# --- 10. RISK SIMULATOR ---
st.markdown("---")
st.subheader("⚠️ Stress Test: When Leverage Bites")
st.markdown("Use this to check safety in the event of a market crash.")

with st.container(border=True):
    c1, c2 = st.columns(2)
    with c1:
        crash_scenario = st.slider("📉 Market Drop (%)", 0, 50, 30)
    with c2:
        crash_year = st.slider("📅 Crash Happens in Year", 1, 10, 2)
    
    try:
        row = df_annual[df_annual['Year'] == crash_year].iloc[0]
        loan_at_crash = row["Investment Loan"]
        port_at_crash = row["Portfolio Value"]
        
        crashed_value = port_at_crash * (1 - crash_scenario / 100)
        underwater_amount = crashed_value - loan_at_crash
        
        st.divider()
        rc1, rc2, rc3 = st.columns(3)
        
        with rc1:
            st.metric(f"Loan (Year {crash_year})", f"${loan_at_crash:,.0f}")
        with rc2:
            st.metric(f"Portfolio (-{crash_scenario}%)", f"${crashed_value:,.0f}", delta=f"-${port_at_crash - crashed_value:,.0f}", delta_color="inverse")
        with rc3:
            if underwater_amount < 0:
                st.metric("Net Equity", f"-${abs(underwater_amount):,.0f}", delta="UNDERWATER", delta_color="inverse")
                st.error("🚨 DANGER: Liabilities exceed Assets.")
            else:
                st.metric("Net Equity", f"${underwater_amount:,.0f}", delta="Safe")
                st.success("✅ Buffer: You have positive equity.")

    except:
        st.write("Select a valid year.")

# --- 11. DISCLAIMER ---
st.markdown("---")
st.caption("Disclaimer: This model assumes interest deductibility. Dividends are taxable, which is not fully netted out in the refund column to show gross interest benefit. Consult a tax professional.")
