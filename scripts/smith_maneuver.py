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

# --- 5. VISUAL EXPLAINER (THE CYCLE) ---
st.subheader("⚙️ How the Cycle Works (Example: $1,000 Payment)")
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
        <p style="font-size: 0.8em; color: #666; margin:0;">You buy <b>$1,000</b> of stocks. Interest is now deductible.</p>
        <div style="margin-top:10px; background:#ddd; padding:5px; border-radius:5px; font-weight:bold; color:#333;">Assets: +$1,000</div>
    </div>
    """, unsafe_allow_html=True)

st.caption("Step 4: At tax time, the interest you paid on the HELOC generates a Refund. You put that Refund into the Mortgage, and the cycle speeds up.")
st.divider()

# --- 6. INPUTS ---
with st.container(border=True):
    st.markdown("### 📝 Configure Your Scenario")
    
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
        initial_lump = st.number_input("Initial Available HELOC ($)", value=0.0, step=5000.0, help="Existing room you can borrow immediately.")

    # Row 3: Tax
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

# Initial Lump Sum
if initial_lump > 0:
    heloc_balance += initial_lump
    portfolio += initial_lump

annual_data = []
monthly_ledger = [] 

current_year_heloc_interest = 0.0

for month in range(1, n_m + 1):
    # 1. Mortgage Payment
    interest_m = balance * r_m
    principal_m = monthly_payment - interest_m
    if principal_m > balance: principal_m = balance
    
    balance -= principal_m
    
    # 2. READVANCE
    new_borrowing = principal_m 
    
    # 3. HELOC Interest Cost
    interest_heloc = heloc_balance * (loc_rate / 100 / 12)
    current_year_heloc_interest += interest_heloc
    
    # 4. TAX REFUND EVENT (Annual)
    refund_applied = 0.0
    if month % 12 == 1 and month > 1:
        refund_amount = current_year_heloc_interest * (tax_rate / 100)
        
        # Apply Refund to Mortgage -> Reborrow -> Invest
        if balance > 0:
            balance -= refund_amount
            refund_applied = refund_amount
            new_borrowing += refund_amount # Re-borrow the refund paydown
        
        current_year_heloc_interest = 0.0
        cum_tax_refund += refund_amount

    # 5. INVEST
    heloc_balance += new_borrowing
    portfolio += new_borrowing 
    portfolio = portfolio * (1 + inv_return / 100 / 12)
    
    # Monthly Ledger (36 Months)
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

    # Annual Data
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

# --- 8. MONTHLY LEDGER ---
st.divider()
st.subheader("📅 3-Year Monthly Schedule (The Mechanics)")
display_df = df_monthly.copy()
# Formatting
for col in ['Mortgage Bal', 'Principal Pd', 'HELOC Borrowed', 'Portfolio Value']:
    display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}")
display_df['HELOC Interest'] = display_df['HELOC Interest'].apply(lambda x: f"${x:,.2f}")
display_df['Tax Refund In'] = display_df['Tax Refund In'].apply(lambda x: f"${x:,.0f}" if x != "-" else "-")

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

# --- 10. RISK SIMULATOR (NEW FEATURE) ---
st.markdown("---")
st.subheader("⚠️ Stress Test: Understanding the Risks")
st.markdown("""
The biggest risk in the Smith Maneuver is **Leverage Risk**. You still owe the loan even if your investments drop.
Use the slider below to see what happens if the market crashes right after your strategy is fully deployed.
""")

with st.container(border=True):
    crash_scenario = st.slider("📉 Simulate Market Drop (%)", 0, 50, 20)
    
    # Calculate Impact based on Final Year data
    final_loan = df_annual.iloc[-1]["Investment Loan"]
    final_port = df_annual.iloc[-1]["Portfolio Value"]
    
    # Apply Crash
    crashed_port = final_port * (1 - crash_scenario / 100)
    net_position = crashed_port - final_loan
    
    rc1, rc2, rc3 = st.columns(3)
    
    with rc1:
        st.metric("Total Investment Loan", f"${final_loan:,.0f}", help="This amount creates a legal obligation to pay back, regardless of market performance.")
    with rc2:
        st.metric(f"Portfolio Value (-{crash_scenario}%)", f"${crashed_port:,.0f}", delta=f"-${final_port - crashed_port:,.0f}", delta_color="inverse")
    with rc3:
        if net_position < 0:
            st.metric("Net Position (Underwater)", f"-${abs(net_position):,.0f}", delta="UNDERWATER", delta_color="inverse")
            st.error("🚨 DANGER ZONE: You owe more than your assets are worth. The bank could call the loan.")
             

[Image of stock market crash graph]

        else:
            st.metric("Net Position (Safe)", f"${net_position:,.0f}", delta="Solvent")
            st.success("✅ Buffer: You still have equity despite the crash.")

# --- 11. DISCLAIMER ---
st.markdown("---")
st.caption("Strategy Disclaimer: Borrowing to invest increases risk. If investment returns are lower than the loan interest rate, losses may occur. Consult a professional.")
