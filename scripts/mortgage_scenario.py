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

# Retrieve raw data from Affordability (if available)
raw_afford_max = st.session_state.get('max_purchase_power', 800000.0)
raw_afford_down = st.session_state.get('affordability_down_payment', 160000.0)

# Retrieve rate from Affordability Store
def get_default_rate():
    if 'aff_store' in st.session_state:
        return st.session_state.aff_store.get('contract_rate', 4.49)
    
    # Fallback to file
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            d = json.load(f)
            return d['rates'].get('five_year_fixed_uninsured', 4.49)
    return 4.49

default_rate = get_default_rate()

# --- 2. THEME & STYLING ---
PRIMARY_GOLD = "#CEB36F"
SLATE_ACCENT = "#4A4E5A"
OFF_WHITE = "#F8F9FA"

def apply_style(fig, title):
    fig.update_layout(
        title=dict(text=title, font=dict(size=20, color=SLATE_ACCENT)),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial", color=SLATE_ACCENT),
        hovermode="x unified",
        margin=dict(t=80, b=40, l=40, r=40)
    )
    fig.update_xaxes(showgrid=False, linecolor=SLATE_ACCENT)
    fig.update_yaxes(showgrid=True, gridcolor="#EEE")
    return fig

# --- 3. STATE INITIALIZATION ---
# RESTORED: Default values now use affordability data as the starting point
if 'mort_scen_store' not in st.session_state:
    st.session_state.mort_scen_store = {
        'price': float(raw_afford_max),
        'down': float(raw_afford_down),
        'rate_a': float(default_rate),
        'rate_b': float(default_rate - 0.25),
        'prepay_a': 0.0,
        'prepay_b': 500.0
    }

store = st.session_state.mort_scen_store

# --- 4. HEADER ---
st.title("The Scenario Comparison Matrix")
st.markdown(f"**Strategy Analysis for {household_names}**")

# --- 5. GLOBAL INPUT BAR ---
with st.container():
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        # User input updates the store directly
        store['price'] = st.number_input("Property Price ($)", value=store['price'], step=10000.0)
    with col2:
        store['down'] = st.number_input("Down Payment ($)", value=store['down'], step=5000.0)
    with col3:
        amort = st.selectbox("Amortization (Years)", [25, 30], index=1)

loan_amount = store['price'] - store['down']
st.info(f"Projected Mortgage Amount: **${loan_amount:,.2f}**")

# --- 6. SCENARIO CONFIGURATION ---
st.divider()
s_col1, s_col2 = st.columns(2)

with s_col1:
    st.subheader("Scenario A: Baseline")
    store['rate_a'] = st.number_input("Interest Rate (%)", value=store['rate_a'], key="ra", step=0.1)
    freq_a = st.selectbox("Payment Frequency", ["Monthly", "Bi-Weekly Accelerated"], key="fa")
    store['prepay_a'] = st.number_input("Monthly Extra Payment ($)", value=store['prepay_a'], key="pa")

with s_col2:
    st.subheader("Scenario B: Optimized")
    store['rate_b'] = st.number_input("Interest Rate (%)", value=store['rate_b'], key="rb", step=0.1)
    freq_b = st.selectbox("Payment Frequency", ["Monthly", "Bi-Weekly Accelerated"], index=1, key="fb")
    store['prepay_b'] = st.number_input("Monthly Extra Payment ($)", value=store['prepay_b'], key="pb")

# --- 7. MORTGAGE ENGINE ---
def calculate_mortgage(loan, rate, years, freq, extra):
    r = (rate / 100) / 12
    n = years * 12
    base_monthly = (loan * r) / (1 - (1 + r)**-n)
    
    if freq == "Bi-Weekly Accelerated":
        pmt = base_monthly / 2
        pmts_per_year = 26
    else:
        pmt = base_monthly
        pmts_per_year = 12
    
    total_monthly_avg = (pmt * pmts_per_year / 12) + extra
    
    balance = loan
    data = []
    total_interest = 0
    term_equity = 0
    month = 0
    
    while balance > 0 and month < 360:
        month += 1
        int_pmt = balance * (rate/100/12)
        prin_pmt = total_monthly_avg - int_pmt
        
        if prin_pmt > balance:
            prin_pmt = balance
            balance = 0
        else:
            balance -= prin_pmt
            
        total_interest += int_pmt
        if month == 60: term_equity = loan - balance
        
        data.append({"Month": month, "Balance": balance, "Interest_Paid": total_interest, "Equity": loan - balance})
        if balance <= 0: break
            
    return {
        "Data": pd.DataFrame(data),
        "Total_Life_Int": total_interest,
        "Payoff_Time": round(month / 12, 1),
        "Monthly_Avg": total_monthly_avg,
        "Term_Prin": term_equity
    }

res_a = calculate_mortgage(loan_amount, store['rate_a'], amort, freq_a, store['prepay_a'])
res_b = calculate_mortgage(loan_amount, store['rate_b'], amort, freq_b, store['prepay_b'])

# --- 8. VISUAL COMPARISON ---
st.divider()
results = [
    {"Name": "Scenario A", "Data": res_a['Data'], "Total_Life_Int": res_a['Total_Life_Int'], "Payoff_Time": res_a['Payoff_Time'], "Monthly_Avg": res_a['Monthly_Avg'], "Term_Prin": res_a['Term_Prin'], "Rate": store['rate_a'], "Freq": freq_a, "Prepay_Active": store['prepay_a'] > 0},
    {"Name": "Scenario B", "Data": res_b['Data'], "Total_Life_Int": res_b['Total_Life_Int'], "Payoff_Time": res_b['Payoff_Time'], "Monthly_Avg": res_b['Monthly_Avg'], "Term_Prin": res_b['Term_Prin'], "Rate": store['rate_b'], "Freq": freq_b, "Prepay_Active": store['prepay_b'] > 0}
]

tabs = st.tabs(["💰 Monthly Cash Flow", "📉 Debt Trajectory", "🏡 5-Year Milestone", "📋 Summary Table"])

with tabs[0]:
    cf_data = pd.DataFrame([{"Scenario": r['Name'], "Monthly Payment": r['Monthly_Avg']} for r in results])
    fig1 = px.bar(cf_data, x="Scenario", y="Monthly Payment", color="Scenario", 
                 color_discrete_sequence=[SLATE_ACCENT, PRIMARY_GOLD], text_auto='$,.0f')
    st.plotly_chart(apply_style(fig1, "Monthly Outflow Comparison"), use_container_width=True)

with tabs[1]:
    combined_data = pd.concat([r['Data'].assign(Scenario=r['Name']) for r in results])
    fig2 = px.line(combined_data, x="Month", y="Balance", color="Scenario",
                  color_discrete_sequence=[SLATE_ACCENT, PRIMARY_GOLD])
    st.plotly_chart(apply_style(fig2, "Projected Principal Reduction"), use_container_width=True)

with tabs[2]:
    milestone_data = []
    for r in results:
        milestone_data.append({"Scenario": r['Name'], "Type": "Equity Built", "Value": r['Term_Prin']})
        milestone_data.append({"Scenario": r['Name'], "Type": "Interest Paid", "Value": r['Data'].iloc[59]['Interest_Paid'] if len(r['Data'])>=60 else r['Total_Life_Int']})
    
    fig3 = px.bar(pd.DataFrame(milestone_data), x="Scenario", y="Value", color="Type", barmode="group",
                 color_discrete_sequence=[PRIMARY_GOLD, SLATE_ACCENT], text_auto='$,.0f')
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

# --- 12. LEGAL DISCLAIMER ---
st.markdown("---")
st.markdown("""
<div style='background-color: #f8f9fa; padding: 16px 20px; border-radius: 5px; border: 1px solid #dee2e6;'>
    <p style='font-size: 12px; color: #6c757d; line-height: 1.6; margin-bottom: 0;'>
        <strong>⚠️ Errors and Omissions Disclaimer:</strong><br>
        This tool is for <strong>informational and educational purposes only</strong>. Figures are based on mathematical estimates and historical data. 
        This does not constitute financial, legal, or tax advice. Consult with a professional before making significant financial decisions.
    </p>
</div>
""", unsafe_allow_html=True)
