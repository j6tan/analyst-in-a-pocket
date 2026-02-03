import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json

# --- 1. DATA LINKING & UTILS ---
prof = st.session_state.get('user_profile', {})
client_name1 = prof.get('p1_name', 'Dori') 
client_name2 = prof.get('p2_name', 'Kevin') 
household_names = f"{client_name1} & {client_name2}" if client_name2 else client_name1

# --- UPDATED: DYNAMIC LINKING TO AFFORDABILITY PAGE ---
# Points to 'aff_final' as defined in affordability (18).py
aff_store = st.session_state.get('aff_final', {})
raw_afford_max = aff_store.get('target_price', 800000.0)
raw_afford_down = aff_store.get('down_payment', 160000.0)

# Retrieve rate from Affordability Store
def get_default_rate():
    if 'aff_final' in st.session_state:
        return st.session_state.aff_final.get('contract_rate', 4.49)
    
    # Fallback to file
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            d = json.load(f)
            return d.get('rates', {}).get('five_year_fixed_uninsured', 4.49)
    return 4.49

# --- 2. PERSISTENCE ---
if "mort_scen_store" not in st.session_state:
    st.session_state.mort_scen_store = {
        "price": raw_afford_max,
        "down_payment": raw_afford_down,
        "rate": get_default_rate(),
        "amort": 25,
        "prepay_active": False,
        "prepay_amount": 1000.0,
        "freq": "Monthly"
    }
store = st.session_state.mort_scen_store

# --- 3. THEME ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
CHARCOAL = "#2E2B28"

def apply_style(fig, title):
    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color=SLATE_ACCENT)),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EEE")
    return fig

# --- 4. HEADER ---
st.title("The Mortgage Architect")
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD};">
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Now that we've established the limits for <b>{household_names}</b>, it's time to stress-test the structure. 
        This tool allows you to compare different amortization lengths and prepayment strategies to see how they impact your 
        long-term equity and interest costs.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR INPUTS ---
with st.sidebar:
    st.header("🏠 Property & Loan")
    
    # Sync button to refresh from Affordability Page
    if st.button("🔄 Sync with Affordability Page"):
        store['price'] = aff_store.get('target_price', 800000.0)
        store['down_payment'] = aff_store.get('down_payment', 160000.0)
        st.rerun()

    store['price'] = st.number_input("Purchase Price ($)", value=float(store['price']), step=10000.0)
    store['down_payment'] = st.number_input("Down Payment ($)", value=float(store['down_payment']), step=5000.0)
    
    st.divider()
    st.header("📈 Rates & Terms")
    store['rate'] = st.number_input("Mortgage Rate (%)", value=float(store['rate']), step=0.1)
    store['amort'] = st.selectbox("Amortization (Years)", [15, 20, 25, 30], index=2)
    store['freq'] = st.selectbox("Payment Frequency", ["Monthly", "Bi-Weekly", "Accelerated Bi-Weekly"])
    
    st.divider()
    st.header("⚡ Acceleration")
    store['prepay_active'] = st.checkbox("Enable Annual Prepayment?", value=store['prepay_active'])
    store['prepay_amount'] = st.number_input("Annual Lump Sum ($)", value=float(store['prepay_amount']), step=500.0)

# --- 6. CALCULATIONS ---
loan_amt = store['price'] - store['down_payment']
freq_map = {"Monthly": 12, "Bi-Weekly": 26, "Accelerated Bi-Weekly": 26}
n_periods = store['amort'] * freq_map[store['freq']]
periodic_rate = (store['rate'] / 100) / freq_map[store['freq']]

if store['freq'] == "Accelerated Bi-Weekly":
    monthly_pi = (loan_amt * ((store['rate']/100)/12)) / (1 - (1 + ((store['rate']/100)/12))**-(store['amort']*12))
    base_pmt = monthly_pi / 2
else:
    base_pmt = (loan_amt * periodic_rate) / (1 - (1 + periodic_rate)**-n_periods)

# --- 7. AMORTIZATION ENGINE ---
def run_scenario(p, r, n, freq, extra_pmt_active, extra_val):
    balance = p
    data = []
    total_int = 0
    
    for i in range(1, 1000): # Hard cap 1000 periods
        interest = balance * r
        # Prepayment logic: apply annual lump sum at the end of each year
        lump_sum = extra_val if (extra_pmt_active and i % freq_map[freq] == 0) else 0
        
        principal = min(balance, base_pmt - interest + lump_sum)
        balance -= principal
        total_int += interest
        
        if i % freq_map[freq] == 0 or balance <= 0:
            data.append({
                "Year": len(data) + 1,
                "Balance": max(0, balance),
                "Interest_Paid": total_int,
                "Principal_Paid": p - balance
            })
        if balance <= 0: break
    return data, total_int, len(data)

# Run Scenarios
res_std, int_std, years_std = run_scenario(loan_amt, periodic_rate, n_periods, store['freq'], False, 0)
res_acc, int_acc, years_acc = run_scenario(loan_amt, periodic_rate, n_periods, store['freq'], store['prepay_active'], store['prepay_amount'])

# --- 8. DASHBOARD ---
st.divider()
col_a, col_b, col_c = st.columns(3)

with col_a:
    st.metric("Total Interest Saved", f"${int_std - int_acc:,.0f}")
with col_b:
    st.metric("Time Saved", f"{years_std - years_acc} Years")
with col_c:
    st.metric("Final Payment Year", f"Year {years_acc}")

tabs = st.tabs(["📉 Balance Projection", "💰 Interest Accumulation", "📊 Milestone Analysis", "📋 Compare Data"])

with tabs[0]:
    df_std = pd.DataFrame(res_std)
    df_acc = pd.DataFrame(res_acc)
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df_std["Year"], y=df_std["Balance"], name="Standard", line=dict(color=SLATE_ACCENT, width=2, dash='dash')))
    fig1.add_trace(go.Scatter(x=df_acc["Year"], y=df_acc["Balance"], name="With Acceleration", line=dict(color=PRIMARY_GOLD, width=4)))
    st.plotly_chart(apply_style(fig1, "Mortgage Paydown Trajectory"), use_container_width=True)

with tabs[1]:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df_std["Year"], y=df_std["Interest_Paid"], name="Standard Interest", fill='tozeroy', line=dict(color=SLATE_ACCENT)))
    fig1.add_trace(go.Scatter(x=df_acc["Year"], y=df_acc["Interest_Paid"], name="Accelerated Interest", fill='tonexty', line=dict(color=PRIMARY_GOLD)))
    st.plotly_chart(apply_style(fig2, "Cumulative Interest Comparison"), use_container_width=True)

with tabs[2]:
    # Milestone check at Year 5
    m_yr = 5
    std_m = df_std.iloc[m_yr-1] if len(df_std) >= m_yr else df_std.iloc[-1]
    acc_m = df_acc.iloc[m_yr-1] if len(df_acc) >= m_yr else df_acc.iloc[-1]
    
    fig3 = go.Figure(data=[
        go.Bar(name='Standard', x=['Principal', 'Interest'], y=[std_m['Principal_Paid'], std_m['Interest_Paid']], marker_color=SLATE_ACCENT),
        go.Bar(name='Accelerated', x=['Principal', 'Interest'], y=[acc_m['Principal_Paid'], acc_m['Interest_Paid']], marker_color=PRIMARY_GOLD)
    ])
    fig3.update_layout(barmode='group')
    st.plotly_chart(apply_style(fig3, f"Year {m_yr} Milestone: Equity vs. Interest"), use_container_width=True)

with tabs[3]:
    st.subheader("Comparative Summary")
    comparison = pd.DataFrame([
        {"Metric": "Amortization Period", "Standard": f"{years_std} Years", "Accelerated": f"{years_acc} Years"},
        {"Metric": "Total Interest Paid", "Standard": f"${int_std:,.0f}", "Accelerated": f"${int_acc:,.0f}"},
        {"Metric": "Interest Savings", "Standard": "-", "Accelerated": f"${int_std - int_acc:,.0f}"}
    ])
    st.table(comparison)

# --- 9. LEGAL DISCLAIMER ---
st.markdown("---")
st.markdown("""
<div style='background-color: #f8f9fa; padding: 16px 20px; border-radius: 5px; border: 1px solid #dee2e6;'>
    <p style='font-size: 12px; color: #6c757d; line-height: 1.6; margin-bottom: 0;'>
        <strong>⚠️ Errors and Omissions Disclaimer:</strong><br>
        This mortgage architect provides estimates based on current math and standard Canadian rounding. 
        It does not account for future rate changes, renewal fees, or specific bank penalties. 
        Always consult with a licensed professional before finalizing mortgage details.
    </p>
</div>
""", unsafe_allow_html=True)
