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
# Retrieve the dictionary stored by affordability (18).py
aff_store = st.session_state.get('aff_final', {})

# Use the calculated max purchase price and down payment from affordability page
# Fallback to defaults only if the affordability page hasn't been run yet
raw_afford_max = aff_store.get('max_purchase', 800000.0) 
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
        "price": raw_afford_max,       # Linked to Affordability Page
        "down_payment": raw_afford_down, # Linked to Affordability Page
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
    
    # Sync button to refresh from Affordability Page (Manual Trigger)
    if st.button("🔄 Sync with Affordability Page"):
        latest_aff = st.session_state.get('aff_final', {})
        store['price'] = latest_aff.get('max_purchase', 800000.0)
        store['down_payment'] = latest_aff.get('down_payment', 160000.0)
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

# Standard Payment
if store['freq'] == "Accelerated Bi-Weekly":
    # Monthly payment divided by 2
    monthly_pi = (loan_amt * ((store['rate']/100)/12)) / (1 - (1 + ((store['rate']/100)/12))**-(store['amort']*12))
    base_pmt = monthly_pi / 2
else:
    base_pmt = (loan_amt * periodic_rate) / (1 - (1 + periodic_rate)**-n_periods)

# --- 7. AMORTIZATION ENGINE ---
def run_scenario(name, p, r, n, freq, extra_pmt_active, extra_val):
    balance = p
    data = []
    total_life_int = 0
    
    # 5-Year Term Metrics
    term_int = 0
    term_prin = 0
    
    # Dynamic Limit to prevent infinite loops (max 50 years)
    max_p = 50 * freq_map[freq]
    
    for i in range(1, max_p + 1):
        interest = balance * r
        # Prepayment logic: apply annual lump sum at the end of each year
        lump_sum = extra_val if (extra_pmt_active and i % freq_map[freq] == 0) else 0
        
        principal = min(balance, base_pmt - interest + lump_sum)
        balance -= principal
        total_life_int += interest
        
        # Track 5-year milestone
        if i <= 5 * freq_map[freq]:
            term_int += interest
            term_prin += principal
        
        if i % freq_map[freq] == 0 or balance <= 0:
            data.append({
                "Year": len(data) + 1,
                "Balance": max(0, balance),
                "Interest_Paid": total_life_int,
                "Principal_Paid": p - balance
            })
        if balance <= 0: break
    
    return {
        "Name": name,
        "df": pd.DataFrame(data),
        "Total_Life_Int": int(total_life_int),
        "Payoff_Time": len(data),
        "Term_Int": int(term_int),
        "Term_Prin": int(term_prin),
        "Rate": store['rate'],
        "Freq": freq,
        "Prepay_Active": extra_pmt_active,
        "Monthly_Avg": int(base_pmt if freq=="Monthly" else base_pmt * freq/12)
    }

# --- 8. RUN SCENARIOS ---
results = []
results.append(run_scenario("Standard", loan_amt, periodic_rate, n_periods, store['freq'], False, 0))
results.append(run_scenario("Acceleration Strategy", loan_amt, periodic_rate, n_periods, store['freq'], store['prepay_active'], store['prepay_amount']))

# --- 9. SUMMARY BAR ---
st.divider()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Periodic Payment", f"${base_pmt:,.2f}")
c2.metric("Interest Saved", f"${(results[0]['Total_Life_Int'] - results[1]['Total_Life_Int']):,}")
c3.metric("Time Saved", f"{results[0]['Payoff_Time'] - results[1]['Payoff_Time']} Years")
c4.metric("5-Year Equity", f"${results[1]['Term_Prin']:,}")

# --- 10. VISUAL ANALYTICS ---
tabs = st.tabs(["📉 Balance Trajectory", "💰 Cost of Borrowing", "📊 5-Year Equity Pulse", "📋 Structural Comparison"])

with tabs[0]:
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=results[0]['df']["Year"], y=results[0]['df']["Balance"], name="Standard", line=dict(color=SLATE_ACCENT, width=2, dash='dash')))
    fig1.add_trace(go.Scatter(x=results[1]['df']["Year"], y=results[1]['df']["Balance"], name="With Strategy", line=dict(color=PRIMARY_GOLD, width=4)))
    st.plotly_chart(apply_style(fig1, "Mortgage Paydown Forecast"), use_container_width=True)

with tabs[1]:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=results[0]['df']["Year"], y=results[0]['df']["Interest_Paid"], name="Standard Interest", fill='tozeroy', line=dict(color=SLATE_ACCENT)))
    fig2.add_trace(go.Scatter(x=results[1]['df']["Year"], y=results[1]['df']["Interest_Paid"], name="Strategy Interest", fill='tonexty', line=dict(color=PRIMARY_GOLD)))
    st.plotly_chart(apply_style(fig2, "Cumulative Interest Over Time"), use_container_width=True)

with tabs[2]:
    # Milestone check at Year 5
    fig3 = px.bar(
        pd.DataFrame([
            {"Type": "Principal", "Amount": results[0]['Term_Prin'], "Scen": "Standard"},
            {"Type": "Interest", "Amount": results[0]['Term_Int'], "Scen": "Standard"},
            {"Type": "Principal", "Amount": results[1]['Term_Prin'], "Scen": "Strategy"},
            {"Type": "Interest", "Amount": results[1]['Term_Int'], "Scen": "Strategy"}
        ]), 
        x="Scen", y="Amount", color="Type", barmode="group",
        color_discrete_map={"Principal": PRIMARY_GOLD, "Interest": SLATE_ACCENT}, text_auto='$,.0f'
    )
    fig3.update_traces(textfont_size=18, marker_line_width=0)
    st.plotly_chart(apply_style(fig3, "5-Year Milestone: Equity vs. Interest"), use_container_width=True)

with tabs[3]:
    table_df = pd.DataFrame([{
        "Scenario": r['Name'],
        "Rate": f"{r['Rate']:.2f}%",
        "Frequency": r['Freq'],
        "Extra Pay Activity": r['Prepay_Active'], 
        "Monthly Out": f"${r['Monthly_Avg']:,}",
        "Equity (5yr)": f"${r['Term_Prin']:,}",
        "Total Interest": f"${r['Total_Life_Int']:,}",
        "Savings vs A": f"${(results[0]['Total_Life_Int'] - r['Total_Life_Int']):,}",
        "Payoff Time": f"{r['Payoff_Time']} yr"
    } for r in results])
    st.table(table_df)

# --- 11. LEGAL DISCLAIMER ---
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
