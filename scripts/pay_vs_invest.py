import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import time
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, load_user_data, init_session_state, supabase

# --- 1. UNIVERSAL AUTO-LOADER ---
init_session_state()
if st.session_state.get('username') and not st.session_state.app_db.get('profile'):
    with st.spinner("🔄 restoring your data..."):
        load_user_data(st.session_state.username)
        time.sleep(0.1)
        st.rerun()

inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 2. THEME & UTILS ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

def get_marginal_tax_rate(income):
    # BC 2025 Combined Estimates
    if income <= 55867: return 20.06
    elif income <= 111733: return 31.00
    elif income <= 173205: return 40.70
    elif income <= 246752: return 45.80
    else: return 53.50

# --- 3. DATA RETRIEVAL ---
prof = st.session_state.app_db.get('profile', {})
p1_name = prof.get('p1_name', 'Dori')
p2_name = prof.get('p2_name', 'Kevin')
p1_inc = float(prof.get('p1_t4', 0)) + float(prof.get('p1_bonus', 0)) + float(prof.get('p1_commission', 0))
p2_inc = float(prof.get('p2_t4', 0)) + float(prof.get('p2_bonus', 0)) + float(prof.get('p2_commission', 0))

if 'pay_vs_invest' not in st.session_state.app_db:
    st.session_state.app_db['pay_vs_invest'] = {}
pvi_data = st.session_state.app_db['pay_vs_invest']

# --- 4. HEADER ---
st.title("Debt vs. Equity: The Wealth Choice")
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px; border-radius: 12px; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h4 style="color: {SLATE_ACCENT}; margin: 0;">Which dollar works harder?</h4>
    <p style="color: #6C757D; font-size: 1.05em; line-height: 1.6; margin: 10px 0 0 0;">
        Deciding between a <b>guaranteed {pvi_data.get('rate', 4.0)}% mortgage payoff</b> and the stock market depends heavily on <b>taxes</b>. 
        A TFSA is a pure win for stocks, but in a Non-Registered account, the "tax drag" might make the mortgage a better choice.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. INPUTS ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("🏠 Mortgage Details")
    price = cloud_input("Purchase Price ($)", "pay_vs_invest", "price", step=5000)
    down = cloud_input("Down Payment ($)", "pay_vs_invest", "down", step=5000)
    m_rate = cloud_input("Interest Rate (%)", "pay_vs_invest", "rate", step=0.1)
    amort = cloud_input("Amortization (Years)", "pay_vs_invest", "amort", step=1)

with col2:
    st.subheader("💰 The Decision")
    extra_amt = cloud_input("Extra Monthly Savings ($)", "pay_vs_invest", "extra_amt", step=100)
    stock_return = cloud_input("Expected Stock Return (%)", "pay_vs_invest", "stock_return", step=0.1)
    
    # --- NEW: ACCOUNT TYPE SELECTOR ---
    acc_type = st.selectbox("Account Type", ["Non-Registered", "TFSA", "RRSP"], key="pvi_acc_type")
    
    st.markdown("**Whose tax bracket applies?**")
    t1, t2 = get_marginal_tax_rate(p1_inc), get_marginal_tax_rate(p2_inc)
    tax_map = {f"{p1_name} ({t1}%)": t1, f"{p2_name} ({t2}%)": t2}
    tax_owner = st.radio("Select Owner", list(tax_map.keys()), horizontal=True, key="pvi_tax_owner")
    marginal_tax = tax_map[tax_owner]

# --- 6. CALCULATIONS ---
loan_amt = max(0, price - down)
n_months = int(amort * 12)
r_mo = (m_rate / 100) / 12
m_pmt = loan_amt * (r_mo * (1 + r_mo)**n_months) / ((1 + r_mo)**n_months - 1) if r_mo > 0 else loan_amt / n_months

# After-Tax Logic
if acc_type == "TFSA":
    net_stock_growth_mo = (stock_return / 100) / 12
elif acc_type == "Non-Registered":
    # 50% Inclusion on Capital Gains
    net_stock_growth_mo = ((stock_return / 100) * (1 - (marginal_tax / 100 * 0.5))) / 12
else: # RRSP
    # Growth is tax-free inside, but we reinvest the tax refund
    # Effective monthly deposit is grossed up
    net_stock_growth_mo = (stock_return / 100) / 12

# SIMULATION
history = []
bal_a = loan_amt # Mortgage path
port_a = 0 
port_b = 0 # Stock path

for m in range(1, n_months + 1):
    # Option B: Invest side-by-side
    monthly_invest_b = extra_amt
    if acc_type == "RRSP":
        # We assume you invest the refund immediately (Gross up: $1000 -> $1000 / (1-tax))
        monthly_invest_b = extra_amt / (1 - (marginal_tax / 100))
    
    port_b = (port_b + monthly_invest_b) * (1 + net_stock_growth_mo)
    
    # Option A: Pay down mortgage
    if bal_a > 0:
        int_m = bal_a * r_mo
        prin_m = (m_pmt + extra_amt) - int_m
        if prin_m > bal_a: 
            leftover = prin_m - bal_a
            bal_a = 0
            port_a = leftover # Start investing the residue
        else:
            bal_a -= prin_m
    else:
        # Mortgage gone. Invest Base + Extra
        monthly_invest_a = m_pmt + extra_amt
        if acc_type == "RRSP":
             monthly_invest_a = (m_pmt + extra_amt) / (1 - (marginal_tax / 100))
        port_a = (port_a + monthly_invest_a) * (1 + net_stock_growth_mo)

    # Sale Day Logic for comparison
    final_wealth_b = port_b
    final_wealth_a = port_a
    
    if acc_type == "RRSP":
        # Subtract tax upon withdrawal for both
        final_wealth_b *= (1 - (marginal_tax / 100))
        final_wealth_a *= (1 - (marginal_tax / 100))
        
    history.append({
        "Month": m,
        "Option A (Mortgage)": final_wealth_a + (loan_amt - bal_a),
        "Option B (Stocks)": final_wealth_b + (loan_amt - (loan_amt * (m/n_months)))
    })

df = pd.DataFrame(history)

# --- 7. VISUALS ---
st.divider()
final_a = history[-1]["Option A (Mortgage)"]
final_b = history[-1]["Option B (Stocks)"]
winner = "Stock Market" if final_b > final_a else "Mortgage Paydown"

c1, c2, c3 = st.columns(3)
c1.metric("Wealth from Paydown", f"${final_a:,.0f}")
c2.metric("Wealth from Stocks", f"${final_b:,.0f}")
c3.metric("Mathematical Winner", winner)

st.subheader(f"📈 Wealth Trajectory ({acc_type})")
fig = go.Figure()
fig.add_trace(go.Scatter(x=df['Month']/12, y=df['Option B (Stocks)'], name='Option B: Stock Path', line=dict(color="#16A34A", width=4)))
fig.add_trace(go.Scatter(x=df['Month']/12, y=df['Option A (Mortgage)'], name='Option A: Mortgage Path', line=dict(color=PRIMARY_GOLD, width=4)))
fig.update_layout(xaxis_title="Years", yaxis_title="Net Wealth ($)", height=450, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True)

st.success(f"🏆 **Mathematical Verdict:** Over {amort} years, the **{winner}** path increases your net wealth by **${abs(final_b - final_a):,.0f}** more.")

show_disclaimer()
