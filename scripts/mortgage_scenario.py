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
aff_store = st.session_state.get('aff_final', {})

# Grabbing the raw price and down payment from the affordability store
raw_afford_price = aff_store.get('target_price', 800000.0)
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
        "price": raw_afford_price,
        "down_payment": raw_afford_down,
        "rate": get_default_rate(),
        "amort": 25,
        "prepay_pct": 0.0,
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
st.title("Mortgage Scenario Architect")
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
    
    # Re-sync logic to ensure latest values from affordability
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
    store['prepay_pct'] = st.slider("Annual Prepayment (%)", 0.0, 10.0, float(store['prepay_pct']))

# --- 6. CALCULATIONS ---
loan_amt = store['price'] - store['down_payment']
freq_map = {"Monthly": 12, "Bi-Weekly": 26, "Accelerated Bi-Weekly": 26}
n_periods = store['amort'] * freq_map[store['freq']]
periodic_rate = (store['rate'] / 100) / freq_map[store['freq']]

# Standard Payment
if store['freq'] == "Accelerated Bi-Weekly":
    monthly_pi = (loan_amt * ((store['rate']/100)/12)) / (1 - (1 + ((store['rate']/100)/12))**-(store['amort']*12))
    base_pmt = monthly_pi / 2
else:
    base_pmt = (loan_amt * periodic_rate) / (1 - (1 + periodic_rate)**-n_periods)

# --- 7. AMORTIZATION ENGINE ---
def run_scenario(p, r, n, freq, extra_pct):
    balance = p
    data = []
    total_int = 0
    annual_prepay = (p * (extra_pct/100)) / freq_map[freq]
    
    for i in range(1, int(n) + 1):
        interest = balance * r
        principal = min(balance, base_pmt - interest + annual_prepay)
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
    return pd.DataFrame(data), total_int, len(data)

# Run Scenarios
df_a, int_a, years_a = run_scenario(loan_amt, periodic_rate, n_periods, store['freq'], 0)
df_b, int_b, years_b = run_scenario(loan_amt, periodic_rate, n_periods, store['freq'], store['prepay_pct'])

# --- 8. RESULTS SUMMARY ---
st.divider()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Scheduled Payment", f"${base_pmt:,.2f}")
m2.metric("Total Interest Saved", f"${int_a - int_b:,.0f}")
m3.metric("Time Saved", f"{years_a - years_b} Years")
m4.metric("Loan Balance (5yr)", f"${df_b.iloc[4]['Balance'] if len(df_b)>4 else 0:,.0f}")

# --- 9. VISUALIZATIONS ---
tabs = st.tabs(["📉 Balance Projection", "💰 Interest Costs", "📊 Equity Growth", "📋 Data Comparison"])

with tabs[0]:
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df_a["Year"], y=df_a["Balance"], name="Standard", line=dict(color=SLATE_ACCENT, width=2, dash='dash')))
    fig1.add_trace(go.Scatter(x=df_b["Year"], y=df_b["Balance"], name="Strategy", line=dict(color=PRIMARY_GOLD, width=4)))
    st.plotly_chart(apply_style(fig1, "Mortgage Balance Over Time"), use_container_width=True)

with tabs[1]:
    int_df = pd.DataFrame({"Type": ["Standard", "Strategy"], "Interest": [int_a, int_b]})
    fig2 = px.bar(int_df, x="Type", y="Interest", color="Type", 
                 color_discrete_map={"Standard": SLATE_ACCENT, "Strategy": PRIMARY_GOLD},
                 text_auto='$,.0f')
    st.plotly_chart(apply_style(fig2, "Total Interest Lifetime Cost"), use_container_width=True)

with tabs[2]:
    m_yr = 5
    milestone_data = pd.DataFrame({
        "Label": ["Equity", "Interest"],
        "Standard": [df_a.iloc[m_yr-1]["Principal_Paid"], df_a.iloc[m_yr-1]["Interest_Paid"]],
        "Strategy": [df_b.iloc[m_yr-1]["Principal_Paid"], df_b.iloc[m_yr-1]["Interest_Paid"]]
    }).set_index("Label")
    st.bar_chart(milestone_data)

with tabs[3]:
    st.subheader("Amortization Schedule (Strategy)")
    st.dataframe(df_b.style.format({"Balance": "${:,.0f}", "Interest_Paid": "${:,.0f}", "Principal_Paid": "${:,.0f}"}))

# --- 10. LEGAL DISCLAIMER ---
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
