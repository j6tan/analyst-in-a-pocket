import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, supabase

# 1. Inject Style
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 1. DATA LINKING ---
prof = st.session_state.app_db.get('profile', {})
primary = st.session_state.app_db.get('primary_residence', {})

client_name1 = prof.get('p1_name', 'Client 1')
client_name2 = prof.get('p2_name', 'Client 2')
p1_income = float(prof.get('p1_t4', 0)) + float(prof.get('p1_bonus', 0))
p2_income = float(prof.get('p2_t4', 0))

household_names = f"{client_name1} & {client_name2}" if client_name2 else client_name1

# Determine Lead Taxpayer
if p1_income > p2_income:
    high_income = p1_income
else:
    high_income = p2_income

def estimate_marginal_rate(income):
    if income > 240000: return 53.5
    elif income > 170000: return 48.0
    elif income > 110000: return 43.0
    elif income > 55000: return 29.0
    else: return 20.0

suggested_tax_rate = estimate_marginal_rate(high_income)

# --- 2. PERSISTENCE & INITIALIZATION ---
if 'smith_maneuver' not in st.session_state.app_db:
    st.session_state.app_db['smith_maneuver'] = {}
sm_data = st.session_state.app_db['smith_maneuver']

if not sm_data.get('initialized'):
    # Logic: Pull from profile if available, otherwise use defaults
    init_mortgage = float(primary.get('mortgage_balance', 500000.0))
    init_rate = float(primary.get('mortgage_interest_rate', 5.0))
    init_amort = int(primary.get('remaining_amortization', 25))
    
    sm_data.update({
        "mortgage_amt": init_mortgage,
        "amortization": init_amort,
        "mortgage_rate": init_rate,
        "loc_rate": init_rate + 1.0, # Smart Spread Logic
        "inv_return": 7.0,
        "div_yield": 5.0,
        "tax_rate": float(suggested_tax_rate),
        "initial_lump": 0.0,
        "strategy_horizon": 25,
        "initialized": True
    })

# --- 3. THEME & COLORS ---
PRINCIPAL_COLOR = "#CEB36F" 
INTEREST_COLOR = "#2E2B28"  
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"
PRIMARY_GOLD = "#CEB36F"
BASELINE_BLUE = "#1f77b4"

# --- 4. HEADER ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("The Smith Maneuver Strategy")

# --- 5. RICH STORYTELLING ---
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.5em;">🔄 {household_names}: Turning Mortgage Interest into Tax Refunds</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        <b>The Smith Maneuver</b> is a debt conversion strategy where we systematically re-borrow the principal you pay down on your mortgage to invest in income-generating assets. 
        This converts your <b>Non-Deductible "Bad Debt"</b> (Mortgage) into <b>Tax-Deductible "Good Debt"</b> (Investment Loan). The resulting tax refunds are used to prepay the mortgage even faster, creating a virtuous cycle of wealth creation.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 6. CHECKLIST ---
with st.expander("✅ Checklist: Are you ready for this strategy?", expanded=False):
    st.markdown("""
    To execute this strategy legally and effectively, you must meet these criteria:
    1.  **Readvanceable Mortgage:** You need a HELOC that automatically increases limit as principal is paid.
    2.  **Positive Principal Paydown:** Your monthly payment must actually reduce the principal.
    3.  **Non-Registered Account:** Interest is only deductible in taxable accounts.
    4.  **Income-Generating Assets:** Must have a "reasonable expectation of income" (Dividends/Rent/Interest).
    """)

# --- 7. MECHANICS (THE CYCLE) ---
st.divider()
st.subheader("⚙️ The Mechanics: Follow the Dollar")
st.markdown("Here is exactly what happens every single month:")

c1, c2, c3, c4, c5 = st.columns([1, 0.2, 1, 0.2, 1])
with c1:
    st.markdown("<div style='text-align:center; border:1px solid #ddd; padding:10px; border-radius:8px; height:100%;'><div style='font-size:2em;'>🏠</div><div style='font-weight:bold; margin-top:5px;'>1. Pay Mortgage</div><div style='background:#eee; padding:5px; border-radius:5px; font-weight:bold; color:#555;'>Principal: -$1,000</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown("<div style='display:flex; align-items:center; justify-content:center; height:100%; font-size:2em; color:#ccc;'>➔</div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div style='text-align:center; border:1px solid {PRIMARY_GOLD}; background:#FFFDF5; padding:10px; border-radius:8px; height:100%;'><div style='font-size:2em;'>🏦</div><div style='font-weight:bold; margin-top:5px;'>2. Re-Borrow</div><div style='background:#FFF8E1; padding:5px; border-radius:5px; font-weight:bold; color:{PRIMARY_GOLD};'>HELOC: +$1,000</div></div>", unsafe_allow_html=True)
with c4:
    st.markdown("<div style='display:flex; align-items:center; justify-content:center; height:100%; font-size:2em; color:#ccc;'>➔</div>", unsafe_allow_html=True)
with c5:
    st.markdown("<div style='text-align:center; border:1px solid #333; background:#F8F9FA; padding:10px; border-radius:8px; height:100%;'><div style='font-size:2em;'>📈</div><div style='font-weight:bold; margin-top:5px;'>3. Invest</div><div style='background:#ddd; padding:5px; border-radius:5px; font-weight:bold; color:#333;'>Assets: +$1,000</div></div>", unsafe_allow_html=True)

# CSS Padding added to prevent "crowding" (1mm ≈ 4px, but 15px used for standard editorial spacing)
st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
st.info("💡 **The Accelerator:** At the end of the year, the interest you paid on Step 2 generates a tax refund. You take that refund and apply it to Step 1 (Prepayment), which speeds up the entire cycle.")

st.divider()

# --- 8. INPUTS ---
with st.container(border=True):
    st.markdown("### 📝 Configure Your Scenario")
    c1, c2, c3 = st.columns(3)
    with c1:
        mortgage_amt = cloud_input("Mortgage Balance ($)", "smith_maneuver", "mortgage_amt", step=10000.0)
    with c2:
        amortization = st.slider("Amortization (Years)", 10, 30, int(sm_data.get('amortization', 25)))
        sm_data['amortization'] = amortization
    with c3:
        mortgage_rate = cloud_input("Mortgage Rate (%)", "smith_maneuver", "mortgage_rate", step=0.1)

    c4, c5, c6 = st.columns(3)
    with c4:
        loc_rate = cloud_input("HELOC Rate (%)", "smith_maneuver", "loc_rate", step=0.1)
    with c5:
        inv_return = cloud_input("Total Return (%)", "smith_maneuver", "inv_return", step=0.1)
    with c6:
        div_yield = cloud_input("Dividend Yield (%)", "smith_maneuver", "div_yield", step=0.1)

    c7, c8, c9 = st.columns(3)
    with c7:
         tax_rate = cloud_input("Marginal Tax Rate (%)", "smith_maneuver", "tax_rate", step=0.5)
    with c8:
        initial_lump = cloud_input("Initial HELOC Room ($)", "smith_maneuver", "initial_lump", step=5000.0)
    with c9:
        strategy_horizon = st.slider("Strategy Horizon (Years)", 5, 30, int(sm_data.get('strategy_horizon', 25)), step=5)
        sm_data['strategy_horizon'] = strategy_horizon

# --- 9. CALCULATION ENGINE ---
sim_years = max(amortization, strategy_horizon)
n_months = sim_years * 12
r_m = mortgage_rate / 100 / 12
n_m_amort = amortization * 12 
monthly_payment = mortgage_amt * (r_m * (1 + r_m)**n_m_amort) / ((1 + r_m)**n_m_amort - 1)

balance, heloc_balance, portfolio, cum_tax_refund = mortgage_amt, 0.0, 0.0, 0.0
if initial_lump > 0:
    heloc_balance += initial_lump
    portfolio += initial_lump

base_balance = mortgage_amt
annual_data = []
current_year_heloc_interest = 0.0
year_refund, current_year_borrows, year_heloc_interest_cost = 0.0, 0.0, 0.0

for month in range(1, n_months + 1):
    # Baseline
    base_principal = 0.0
    if base_balance > 0:
        base_int = base_balance * r_m
        base_principal = monthly_payment - base_int
        if base_principal > base_balance: base_principal = base_balance
        base_balance -= base_principal
    base_net_worth = (mortgage_amt - base_balance)

    # Active Strategy
    principal_m = 0.0
    if balance > 0:
        interest_m = balance * r_m
        principal_m = monthly_payment - interest_m
        if principal_m > balance: principal_m = balance
        balance -= principal_m
    new_borrowing = principal_m 
    
    interest_heloc = heloc_balance * (loc_rate / 100 / 12)
    current_year_heloc_interest += interest_heloc
    year_heloc_interest_cost += interest_heloc
    
    if month % 12 == 1 and month > 1:
        refund_amount = current_year_heloc_interest * (tax_rate / 100)
        if balance > 0:
            balance -= refund_amount
            new_borrowing += refund_amount 
        else:
            portfolio += refund_amount
        current_year_heloc_interest, year_refund = 0.0, refund_amount
        cum_tax_refund += refund_amount

    current_year_borrows += new_borrowing
    heloc_balance += new_borrowing
    portfolio = (portfolio + new_borrowing) * (1 + inv_return / 100 / 12)

    if month % 12 == 0:
        annual_div_income = portfolio * (div_yield / 100)
        annual_data.append({
            "Year": month // 12, "Mortgage Balance": max(0, balance), "Investment Loan": heloc_balance,
            "Portfolio Value": portfolio, "Annual Tax Refund": year_refund, "Dividend Income": annual_div_income,
            "Annual Interest Cost": year_heloc_interest_cost,
            "Net Equity (Active)": portfolio - heloc_balance + (mortgage_amt - balance),
            "Baseline Net Worth": base_net_worth, "Baseline Mortgage": base_balance
        })
        year_refund, current_year_borrows, year_heloc_interest_cost = 0.0, 0.0, 0.0

df_annual = pd.DataFrame(annual_data)
df_view = df_annual[df_annual['Year'] <= strategy_horizon].copy()

# --- 10. CASH FLOW ---
total_int_cost = df_view['Annual Interest Cost'].sum()
total_divs = df_view['Dividend Income'].sum()
total_refunds = df_view['Annual Tax Refund'].sum()
net_cashflow = (total_divs + total_refunds) - total_int_cost

st.divider()
st.subheader(f"💰 Cash Flow Analysis ({strategy_horizon} Year Horizon)")
cf1, cf2, cf3, cf4 = st.columns(4)
cf1.metric("Total Interest Cost", f"${total_int_cost:,.0f}")
cf2.metric("Total Dividends", f"${total_divs:,.0f}")
cf3.metric("Total Tax Refunds", f"${total_refunds:,.0f}")
cf4.metric("Net Cash Benefit", f"${net_cashflow:,.0f}", delta="Positive" if net_cashflow > 0 else "Negative")

# --- 11. TABLE ---
st.divider()
st.subheader(f"📅 {strategy_horizon}-Year Projection")
display_df = df_view[['Year', 'Mortgage Balance', 'Investment Loan', 'Portfolio Value', 'Annual Tax Refund', 'Dividend Income']].copy()
display_df.columns = ['Year', 'Bad Debt', 'Good Debt', 'Asset Value', 'Tax Refund', 'Dividend CF']
for col in display_df.columns:
    if col != 'Year': display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}")
st.table(display_df)

# --- 12. CHARTS ---
st.divider()
st.subheader("📈 Strategy vs. Do Nothing")
col_res1, col_res2 = st.columns(2)
with col_res1:
    fig_debt = go.Figure()
    fig_debt.add_trace(go.Scatter(x=df_view["Year"], y=df_view["Mortgage Balance"], name="Active", line=dict(color=INTEREST_COLOR, width=2)))
    fig_debt.add_trace(go.Scatter(x=df_view["Year"], y=df_view["Baseline Mortgage"], name="Baseline", line=dict(color=BASELINE_BLUE, dash='dot')))
    fig_debt.update_layout(title="Mortgage Paydown Speed", height=300, yaxis=dict(tickprefix="$"))
    st.plotly_chart(fig_debt, use_container_width=True)
with col_res2:
    fig_wealth = go.Figure()
    fig_wealth.add_trace(go.Scatter(x=df_view["Year"], y=df_view["Net Equity (Active)"], name="Active", line=dict(color=PRINCIPAL_COLOR, width=3)))
    fig_wealth.add_trace(go.Scatter(x=df_view["Year"], y=df_view["Baseline Net Worth"], name="Baseline", line=dict(color=BASELINE_BLUE, dash='dot')))
    fig_wealth.update_layout(title="Total Net Worth", height=300, yaxis=dict(tickprefix="$"))
    st.plotly_chart(fig_wealth, use_container_width=True)

# --- 13. STRESS TEST ---
st.markdown("---")
st.subheader("⚠️ Stress Test Simulator")
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    crash_drop = st.slider("Crash Magnitude (%)", 0, 50, 30, key="stress_drop")
    crash_start = st.slider("Crash Starts (Year)", 1, strategy_horizon, min(5, strategy_horizon), key="stress_start")
    crash_duration = st.slider("Recovery Duration (Years)", 1, 10, 3, key="stress_dur")
    try:
        row_before = df_annual[df_annual['Year'] == crash_start].iloc[0]
        loan_at_start, port_at_start = row_before["Investment Loan"], row_before["Portfolio Value"]
        port_after_drop = port_at_start * (1 - crash_drop / 100)
        total_stagnation_cost = (loan_at_start * (loc_rate / 100)) * crash_duration
        net_equity_at_recovery = port_after_drop - loan_at_start
        st.divider()
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("Portfolio (After Drop)", f"${port_after_drop:,.0f}", delta=f"-${port_at_start - port_after_drop:,.0f}", delta_color="inverse")
        col_s2.metric(f"Cost to Hold ({crash_duration} yrs)", f"${total_stagnation_cost:,.0f}")
        if net_equity_at_recovery < 0:
            col_s3.metric("Net Equity Position", f"-${abs(net_equity_at_recovery):,.0f}", delta="UNDERWATER", delta_color="inverse")
            st.error("🚨 Warning: Liability exceeds Assets")
        else:
            col_s3.metric("Net Equity Position", f"${net_equity_at_recovery:,.0f}", delta="Safe")
            st.success("✅ Solvent (Assets > Loan)")
    except Exception as e:
        st.write(f"Simulation data unavailable.")

# --- 14. DISCLAIMER ---
show_disclaimer()
