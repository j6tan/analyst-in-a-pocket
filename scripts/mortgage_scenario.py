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

# Fallback values from your original script if Affordability page hasn't been run
# Note: In affordability (17).py (which seems to be the base for 18), 
# max_purchase is often calculated. We try to grab 'max_purchase' first, 
# if not found, we look for 'target_price' (from the second script variant).
# Prioritizing the variable names from your affordability script logic.
raw_afford_max = aff_store.get('max_purchase', aff_store.get('target_price', 800000.0))
raw_afford_down = aff_store.get('down_payment', 160000.0)

# Retrieve rate from Affordability Store (or default)
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
if "mort_scen_list" not in st.session_state:
    # Initialize with ONE default scenario using the linked data
    st.session_state.mort_scen_list = [{
        "id": 1,
        "name": "Base Scenario",
        "price": raw_afford_max,       # Linked
        "down_payment": raw_afford_down, # Linked
        "rate": get_default_rate(),
        "amort": 25,
        "freq": "Monthly",
        "prepay_mode": "None", # None, Monthly, Annual, One-Time
        "prepay_amt": 0.0,
        "prepay_yr": 1
    }]

scenarios = st.session_state.mort_scen_list

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

# --- 5. SIDEBAR: SCENARIO MANAGEMENT ---
with st.sidebar:
    st.header("🛠️ Scenario Builder")
    
    # NEW: Sync Button for Manual Refresh
    if st.button("🔄 Reset to Affordability Defaults"):
        # Reset to a single scenario using latest affordability data
        latest_aff = st.session_state.get('aff_final', {})
        # Logic to grab max purchase or target price depending on which script populated it
        p_val = latest_aff.get('max_purchase', latest_aff.get('target_price', 800000.0))
        d_val = latest_aff.get('down_payment', 160000.0)
        
        st.session_state.mort_scen_list = [{
            "id": 1,
            "name": "Affordability Base",
            "price": p_val,
            "down_payment": d_val,
            "rate": get_default_rate(),
            "amort": 25,
            "freq": "Monthly",
            "prepay_mode": "None",
            "prepay_amt": 0.0,
            "prepay_yr": 1
        }]
        st.rerun()

    # Add New Scenario Button
    if st.button("➕ Add New Scenario"):
        if len(scenarios) < 5:
            last_s = scenarios[-1]
            new_id = last_s["id"] + 1
            # Copy previous settings as base
            scenarios.append({
                "id": new_id,
                "name": f"Scenario {new_id}",
                "price": last_s["price"],
                "down_payment": last_s["down_payment"],
                "rate": last_s["rate"],
                "amort": last_s["amort"],
                "freq": last_s["freq"],
                "prepay_mode": "None",
                "prepay_amt": 0.0,
                "prepay_yr": 1
            })
            st.rerun()
        else:
            st.warning("Max 5 scenarios allowed.")

    st.markdown("---")
    
    # EDIT TABS FOR SCENARIOS
    if len(scenarios) > 0:
        tabs = st.tabs([f"#{s['id']}" for s in scenarios])
        for i, tab in enumerate(tabs):
            s = scenarios[i]
            with tab:
                s['name'] = st.text_input("Label", s['name'], key=f"n_{s['id']}")
                s['price'] = st.number_input("Price", value=float(s['price']), step=5000.0, key=f"p_{s['id']}")
                s['down_payment'] = st.number_input("Down Pmt", value=float(s['down_payment']), step=5000.0, key=f"d_{s['id']}")
                s['rate'] = st.number_input("Rate %", value=float(s['rate']), step=0.1, key=f"r_{s['id']}")
                s['amort'] = st.selectbox("Amort", [15, 20, 25, 30], index=[15, 20, 25, 30].index(s['amort']), key=f"a_{s['id']}")
                s['freq'] = st.selectbox("Freq", ["Monthly", "Bi-Weekly", "Accelerated Bi-Weekly"], 
                                       index=["Monthly", "Bi-Weekly", "Accelerated Bi-Weekly"].index(s['freq']), key=f"f_{s['id']}")
                
                st.markdown("**Prepayment**")
                s['prepay_mode'] = st.selectbox("Type", ["None", "Monthly Top-up", "Annual Lump Sum", "One-Time Lump Sum"], 
                                              index=["None", "Monthly Top-up", "Annual Lump Sum", "One-Time Lump Sum"].index(s['prepay_mode']), 
                                              key=f"pm_{s['id']}")
                
                if s['prepay_mode'] != "None":
                    s['prepay_amt'] = st.number_input("Amount ($)", value=float(s['prepay_amt']), step=100.0, key=f"pa_{s['id']}")
                    if s['prepay_mode'] == "One-Time Lump Sum":
                        s['prepay_yr'] = st.number_input("In Year", value=int(s['prepay_yr']), min_value=1, max_value=30, key=f"py_{s['id']}")

                # Remove Button
                if len(scenarios) > 1:
                    if st.button("🗑️ Remove", key=f"rem_{s['id']}"):
                        scenarios.pop(i)
                        st.rerun()

# --- 6. CALCULATION ENGINE ---
freq_map = {"Monthly": 12, "Bi-Weekly": 26, "Accelerated Bi-Weekly": 26}

def run_simulation(s):
    loan = s['price'] - s['down_payment']
    rate_periodic = (s['rate']/100) / freq_map[s['freq']]
    n_periods = s['amort'] * freq_map[s['freq']]
    
    # Base Payment Calc
    if s['freq'] == "Accelerated Bi-Weekly":
        monthly_pi = (loan * ((s['rate']/100)/12)) / (1 - (1 + ((s['rate']/100)/12))**-(s['amort']*12))
        base_pmt = monthly_pi / 2
    else:
        base_pmt = (loan * rate_periodic) / (1 - (1 + rate_periodic)**-n_periods)
        
    # Amortization Loop
    balance = loan
    total_int = 0
    data = []
    
    # Cap at 50 years to avoid infinite loops
    max_iter = 50 * freq_map[s['freq']]
    
    term_int = 0
    term_prin = 0
    
    for i in range(1, max_iter + 1):
        interest = balance * rate_periodic
        
        # Prepayment Logic
        extra = 0
        if s['prepay_mode'] == "Monthly Top-up":
            # Convert monthly top-up logic to match frequency roughly
            if s['freq'] == "Monthly": extra = s['prepay_amt']
            else: extra = (s['prepay_amt'] * 12) / 26
            
        elif s['prepay_mode'] == "Annual Lump Sum":
            if i % freq_map[s['freq']] == 0: extra = s['prepay_amt']
            
        elif s['prepay_mode'] == "One-Time Lump Sum":
            if i == (s['prepay_yr'] * freq_map[s['freq']]): extra = s['prepay_amt']

        principal = min(balance, base_pmt - interest + extra)
        balance -= principal
        total_int += interest
        
        # 5-Year Term Stats
        if i <= 5 * freq_map[s['freq']]:
            term_int += interest
            term_prin += principal
            
        if i % freq_map[s['freq']] == 0 or balance <= 0:
            data.append({
                "Year": len(data) + 1,
                "Balance": max(0, balance),
                "Interest_Paid": total_int,
                "Principal_Paid": loan - balance
            })
            
        if balance <= 0: break
        
    return {
        "id": s['id'],
        "name": s['name'],
        "df": pd.DataFrame(data),
        "total_int": total_int,
        "years": len(data),
        "term_prin": term_prin,
        "term_int": term_int,
        "payment": base_pmt
    }

results = [run_simulation(s) for s in scenarios]

# --- 7. DASHBOARD & VISUALS ---
st.divider()

# Top Metrics Row (Comparing Scenario 1 vs Last Scenario added)
s1 = results[0]
s2 = results[-1] if len(results) > 1 else results[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Pmt ({s1['name']})", f"${s1['payment']:,.2f}")
if len(results) > 1:
    c2.metric("Interest Delta", f"${s1['total_int'] - s2['total_int']:,.0f}", delta_color="normal")
    c3.metric("Time Delta", f"{s1['years'] - s2['years']} Years")
else:
    c2.metric("Total Interest", f"${s1['total_int']:,.0f}")
    c3.metric("Payoff Time", f"{s1['years']} Years")
c4.metric(f"5yr Equity ({s1['name']})", f"${s1['term_prin']:,.0f}")

# Charts
tabs = st.tabs(["📉 Balance Curves", "💰 Interest Accumulation", "📊 5-Year Milestone", "📋 Summary Table"])

with tabs[0]:
    fig = go.Figure()
    for res in results:
        width = 4 if res == s2 and len(results) > 1 else 2
        dash = 'solid' if res == s2 else 'dash'
        fig.add_trace(go.Scatter(x=res['df']["Year"], y=res['df']["Balance"], name=res['name'], line=dict(width=width)))
    st.plotly_chart(apply_style(fig, "Mortgage Paydown Trajectories"), use_container_width=True)

with tabs[1]:
    fig2 = go.Figure()
    for res in results:
        fig2.add_trace(go.Scatter(x=res['df']["Year"], y=res['df']["Interest_Paid"], name=res['name'], fill='tonexty'))
    st.plotly_chart(apply_style(fig2, "Cumulative Interest Costs"), use_container_width=True)

with tabs[2]:
    # Bar chart for 5-Year Equity vs Interest
    data_milestone = []
    for res in results:
        data_milestone.append({"Scenario": res['name'], "Type": "Principal", "Amount": res['term_prin']})
        data_milestone.append({"Scenario": res['name'], "Type": "Interest", "Amount": res['term_int']})
    
    df_m = pd.DataFrame(data_milestone)
    fig3 = px.bar(df_m, x="Scenario", y="Amount", color="Type", barmode="group", 
                  color_discrete_map={"Principal": PRIMARY_GOLD, "Interest": SLATE_ACCENT}, text_auto='$,.0f')
    st.plotly_chart(apply_style(fig3, "5-Year Term: Where did your payments go?"), use_container_width=True)

with tabs[3]:
    summary_data = []
    for res in results:
        summary_data.append({
            "Name": res['name'],
            "Monthly Pmt": f"${res['payment']:,.2f}" if "Monthly" in [s['freq'] for s in scenarios if s['id'] == res['id']][0] else "Varies",
            "Total Interest": f"${res['total_int']:,.0f}",
            "Payoff Years": res['years'],
            "5yr Equity": f"${res['term_prin']:,.0f}"
        })
    st.table(pd.DataFrame(summary_data))

# --- 8. FOOTER ---
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
