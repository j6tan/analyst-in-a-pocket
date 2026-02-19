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

# --- 4. HEADER ---
st.title("Debt vs. Equity: The Wealth Choice")
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px; border-radius: 12px; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h4 style="color: #2E2B28; margin: 0;">The Compounding Effect of Debt Paydown</h4>
    <p style="color: {SLATE_ACCENT}; font-size: 1.05em; line-height: 1.6; margin: 10px 0 0 0;">
        <b>{p1_name} & {p2_name}</b>, when you pay down your mortgage, you don't just reduce your debt by $1,000. 
        You eliminate the interest on that $1,000 for every month remaining on your amortization. 
        This is a <b>guaranteed, tax-free return</b> that compounds exactly like a high-interest savings account.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. INPUTS ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("🏠 The Debt Variable")
    extra_amt = cloud_input("Extra Monthly Savings ($)", "pay_vs_invest", "extra_amt", step=100)
    m_rate = cloud_input("Mortgage Interest Rate (%)", "pay_vs_invest", "rate", step=0.1)
    amort = cloud_input("Comparison Horizon (Years)", "pay_vs_invest", "amort", step=1)

with col2:
    st.subheader("📈 The Market Variable")
    stock_return = cloud_input("Expected Stock Return (%)", "pay_vs_invest", "stock_return", step=0.1)
    acc_type = st.selectbox("Investment Account Type", ["Non-Registered", "TFSA", "RRSP"], key="pvi_acc_type")
    
    st.markdown("**Whose tax bracket applies?**")
    t1, t2 = get_marginal_tax_rate(p1_inc), get_marginal_tax_rate(p2_inc)
    tax_map = {f"{p1_name} ({t1}%)": t1, f"{p2_name} ({t2}%)": t2}
    tax_owner = st.radio("Select Owner", list(tax_map.keys()), horizontal=True, key="pvi_tax_owner")
    marginal_tax = tax_map[tax_owner]

# --- 6. CORE MATH ENGINE ---
n_months = int(amort * 12)
r_m_mo = (m_rate / 100) / 12
fv_mortgage = extra_amt * (((1 + r_m_mo)**n_months - 1) / r_m_mo)
interest_saved = fv_mortgage - (extra_amt * n_months)

if acc_type == "TFSA":
    net_growth_ann = stock_return
elif acc_type == "Non-Registered":
    net_growth_ann = stock_return * (1 - (marginal_tax / 100 * 0.5))
else: # RRSP
    net_growth_ann = stock_return

r_s_mo = (net_growth_ann / 100) / 12
effective_monthly_dep = extra_amt / (1 - (marginal_tax/100)) if acc_type == "RRSP" else extra_amt
fv_stock = effective_monthly_dep * (((1 + r_s_mo)**n_months - 1) / r_s_mo)

if acc_type == "RRSP":
    fv_stock *= (1 - (marginal_tax / 100))

# --- 7. VISUALS ---
st.divider()
k1, k2, k3 = st.columns(3)
with k1:
    st.metric("Total Interest Saved", f"${interest_saved:,.0f}")
with k2:
    st.metric("Total Wealth (Mortgage)", f"${fv_mortgage:,.0f}")
with k3:
    st.metric("Total Wealth (Stock)", f"${fv_stock:,.0f}")

history = []
for m in range(1, n_months + 1):
    val_m = extra_amt * (((1 + r_m_mo)**m - 1) / r_m_mo)
    val_s = effective_monthly_dep * (((1 + r_s_mo)**m - 1) / r_s_mo)
    if acc_type == "RRSP": val_s *= (1 - (marginal_tax / 100))
    history.append({"Year": m/12, "Mortgage Path": val_m, "Stock Path": val_s})

df = pd.DataFrame(history)
fig = go.Figure()
fig.add_trace(go.Scatter(x=df['Year'], y=df['Stock Path'], name='Option B: Stock Portfolio', line=dict(color="#16A34A", width=4)))
fig.add_trace(go.Scatter(x=df['Year'], y=df['Mortgage Path'], name='Option A: Mortgage Savings', line=dict(color=PRIMARY_GOLD, width=4)))
fig.update_layout(xaxis_title="Years", yaxis_title="Accumulated Wealth ($)", height=400, margin=dict(l=0,r=0,t=20,b=20))
st.plotly_chart(fig, use_container_width=True)

# --- 8. THE VERDICT ---
winner = "Stock Market" if fv_stock > fv_mortgage else "Mortgage Paydown"
diff = abs(fv_stock - fv_mortgage)

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 25px; border-radius: 12px; border: 2px solid {PRIMARY_GOLD}; text-align: center; margin-bottom: 30px;">
    <h3 style="margin: 0; color: #2E2B28;">🏆 The Wealth Winner: {winner}</h3>
    <p style="font-size: 1.15em; color: #4A4E5A; margin-top: 10px;">
        Choosing the {winner} path creates <b>${diff:,.0f} more</b> in total wealth over {amort} years.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 9. STRATEGIC COMMENTARY (NEW SECTION) ---
st.subheader("💡 Strategic Insights: Beyond the Numbers")
st_col1, st_col2 = st.columns(2)

with st_col1:
    st.markdown("### 🔄 The Acceleration Factor")
    st.write(f"""
    Many people feel that paying down a mortgage "accelerates" faster because it reduces the balance. 
    Mathematically, **this is identical to compounding.** * Paying down a **{m_rate}%** mortgage is a **guaranteed {m_rate}% return**. 
    * Investing in a TFSA at **{stock_return}%** is a **projected {stock_return}% return**. 
    If the mortgage and stock rates were the same, your net worth would be identical in both paths.
    """)
    
    st.markdown("### 🛡️ The Risk Premium")
    st.write(f"""
    The "Spread" is the extra return you get for taking on market risk. 
    In your case, the stock market is projected to outperform the mortgage by **{abs(net_growth_ann - m_rate):.1f}%** annually. 
    Is that extra profit worth the fact that stocks can go down, while your mortgage interest is a certain cost?
    """)

with st_col2:
    st.markdown("### 💧 Liquidity & Flexibility")
    st.write("""
    **Mortgage paydown is "trapped" wealth.** Once money is in the house, you usually need a loan (HELOC) or a sale to get it back. 
    **Stocks are liquid wealth.** In a TFSA or Non-Reg account, you can access your cash in days for emergencies or opportunities. 
    Even if the math favors the mortgage, many keep a stock portfolio for the flexibility it provides.
    """)
    
    st.markdown("### 🏛️ The Tax Reality")
    st.write(f"""
    Mortgage payoff is a **tax-free return**. 
    In a {acc_type} account, your 8.0% return becomes **{net_growth_ann:.2f}%** after the CRA takes their share. 
    The tool has automatically adjusted for your marginal tax bracket of **{marginal_tax}%** to ensure a true comparison.
    """)

show_disclaimer()
