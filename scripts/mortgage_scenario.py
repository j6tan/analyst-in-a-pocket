import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
from style_utils import inject_global_css

# 1. Inject the Wealthsimple-inspired Editorial CSS
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 1. DATA LINKING & UTILS ---
prof = st.session_state.app_db.get('profile', {})
client_name1 = prof.get('p1_name', 'Dori') 
client_name2 = prof.get('p2_name', 'Kevin') 
household_names = f"{client_name1} & {client_name2}" if client_name2 else client_name1

# --- 1. DATA LINKING ---
aff_store = st.session_state.get('aff_final', {})

# This pulls the actual calculated Loan and Down Payment from your other page
if "scenario_initialized" not in st.session_state:
    init_loan = aff_store.get('loan_amt', 640000.0)
    init_down = aff_store.get('down_payment', 160000.0)
    
    # We set these in Session State so the widgets can find them
    st.session_state.ms_price = float(init_loan + init_down)
    st.session_state.ms_down = float(init_down)
    st.session_state.scenario_initialized = True

# Retrieve rate from Affordability Store (SAFE VERSION)
def get_default_rate():
    if 'aff_final' in st.session_state:
        # Use the correct dictionary name: aff_final
        return st.session_state.aff_final.get('contract_rate', 4.49)
    
    # Fallback to file (with crash protection)
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                d = json.load(f)
                return d.get('rates', {}).get('five_year_fixed_uninsured', 4.49)
        except Exception:
            return 4.49
    return 4.49

global_rate_default = get_default_rate()

# --- 2. ROUNDING LOGIC ---
def smart_round_price(price):
    if price >= 1000000:
        return float(round(price, -4))
    else:
        return float(round(price, -3))

# --- 3. PERSISTENCE INITIALIZATION (SHADOW STORE) ---
if 'scen_store' not in st.session_state:
    st.session_state.scen_store = {
        "price": float(st.session_state.get('ms_price', 800000.0)),
        "down": float(st.session_state.get('ms_down', 160000.0)),
        "amort": 25,
        "scenarios": [] 
    }
    
    st.session_state.scen_store["scenarios"] = [
        {"label": "Standard Monthly", "rate": global_rate_default, "freq": "Monthly", "strat": "None", "extra": 0.0, "lump": 0.0, "double": False},
        {"label": "Accelerated Bi-Weekly", "rate": global_rate_default, "freq": "Accelerated Bi-weekly", "strat": "None", "extra": 0.0, "lump": 0.0, "double": False}
    ]

store = st.session_state.scen_store

if 'num_options' not in st.session_state:
    st.session_state.num_options = len(store['scenarios'])

# --- 4. STATE MANAGEMENT HELPERS ---
def add_option():
    if st.session_state.num_options < 5:
        st.session_state.num_options += 1
        store['scenarios'].append({
            "label": f"Scenario {chr(65 + len(store['scenarios']))}", 
            "rate": store['scenarios'][0]['rate'], 
            "freq": "Monthly", 
            "strat": "None", 
            "extra": 0.0, 
            "lump": 0.0, 
            "double": False
        })

def remove_option():
    if st.session_state.num_options > 1:
        st.session_state.num_options -= 1
        store['scenarios'].pop()

# --- COLOR PALETTE ---
SCENARIO_COLORS = ["#CEB36F", "#706262", "#2E2B28", "#C0A385", "#E7E7E7"]
PRINCIPAL_COLOR = "#CEB36F"
INTEREST_COLOR = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"
PRIMARY_GOLD = "#CEB36F"

# --- 5. CORE ENGINE ---
def calculate_min_downpayment(price):
    if price >= 1000000: return price * 0.20
    elif price <= 500000: return price * 0.05
    else: return (500000 * 0.05) + ((price - 500000) * 0.10)

def get_cmhc_premium_rate(ltv):
    if ltv <= 80: return 0.0
    elif ltv <= 85: return 0.0280 
    elif ltv <= 90: return 0.0310 
    elif ltv <= 95: return 0.0400 
    return 0.0400

def simulate_mortgage(principal, annual_rate, amort_years, freq_label, extra_per_pmt=0, lump_sum_annual=0, double_up=False):
    freq_map = {"Monthly": 12, "Semi-monthly": 24, "Bi-weekly": 26, "Weekly": 52, "Accelerated Bi-weekly": 26, "Accelerated Weekly": 52}
    p_yr = freq_map[freq_label]
    periodic_rate = ((1 + (annual_rate / 100) / 2)**(2 / p_yr)) - 1
    m_rate = ((1 + (annual_rate / 100) / 2)**(2 / 12)) - 1
    num_m = amort_years * 12
    base_m_pmt = principal * (m_rate * (1 + m_rate)**num_m) / ((1 + m_rate)**num_m - 1)

    if "Accelerated" in freq_label: pmt = base_m_pmt / (4 if "Weekly" in freq_label else 2)
    else: pmt = (base_m_pmt * 12) / p_yr

    base_out = (pmt * 2 if double_up else pmt)
    total_periodic = base_out + extra_per_pmt
    true_monthly_out = (total_periodic * p_yr + lump_sum_annual) / 12

    balance, t_int, t_prin, total_lifeline_int = principal, 0, 0, 0
    history = []
    term_periods = int(5 * p_yr)
    
    for i in range(1, 15000):
        if balance <= 0.05: break 
        interest_charge = balance * periodic_rate
        actual_p = total_periodic
        if i % p_yr == 0: actual_p += lump_sum_annual
        if (actual_p - interest_charge) > balance: actual_p = balance + interest_charge
        principal_part = actual_p - interest_charge
        balance -= principal_part
        total_lifeline_int += interest_charge
        if i <= term_periods:
            t_int += interest_charge
            t_prin += principal_part
        if i % p_yr == 0 or balance <= 0:
            history.append({"Year": round(i/p_yr, 2), "Balance": round(max(0, balance))})

    return {
        "Monthly_Avg": round(true_monthly_out), "Term_Int": round(t_int), "Term_Prin": round(t_prin),
        "Total_Life_Int": round(total_lifeline_int), "History": pd.DataFrame(history), 
        "Freq": freq_label, "Rate": annual_rate, "Payoff_Time": round(i/p_yr, 1),
        "Prepay_Active": "None" if (extra_per_pmt == 0 and lump_sum_annual == 0 and not double_up) else "Active",
        "Name": "" 
    }

# --- 7. INTERFACE (HEADER & STORYTELLING) ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("Mortgage Scenario Analysis") 

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 15px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.5em;">🏛️ {household_names}: Outsmarting the Bank</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        {household_names}, you've calculated your affordability. Now, let's see how different interest rates and 
        <b>prepayment strategies</b> can shave years off your debt. Every dollar saved in interest is a dollar 
        kept in your pocket.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 6. GLOBAL SETTINGS (MOVED TO MAIN PAGE) ---
with st.container(border=True):
    st.markdown("### 🏠 Property & Mortgage Details")
    
    # 3-Column Inputs
    col_i1, col_i2, col_i3 = st.columns(3)
    
    with col_i1:
        price = st.number_input("Purchase Price ($)", step=5000.0, key="ms_price")
        st.session_state.scen_store['price'] = price
    
    with col_i2:
        down = st.number_input("Down Payment ($)", step=5000.0, key="ms_down")
        st.session_state.scen_store['down'] = down
        
    with col_i3:
        amort = st.slider("Amortization (Years)", 5, 30, value=int(st.session_state.scen_store['amort']), key="w_amort")
        st.session_state.scen_store['amort'] = amort

    # --- LOGIC & CALCULATIONS (Preserved Exactly) ---
    min_down_req = calculate_min_downpayment(price)
    is_valid = down >= min_down_req
    base_loan = price - down
    ltv = (base_loan / price) * 100 if price > 0 else 0
    cmhc_p = get_cmhc_premium_rate(ltv) * base_loan
    final_loan = base_loan + cmhc_p
    
    # --- COMPACT SEPARATOR (Replaces st.divider for less whitespace) ---
    st.markdown("<div style='margin: 10px 0; border-top: 1px solid #f0f0f0;'></div>", unsafe_allow_html=True)
    
    # Metrics Row
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("Total Mortgage", f"${final_loan:,.0f}", help="Includes CMHC Premium if applicable")
    with col_m2:
        st.metric("LTV Ratio", f"{ltv:.1f}%")
    with col_m3:
        if is_valid and cmhc_p > 0: 
            st.warning(f"CMHC Premium: ${cmhc_p:,.0f}")
        elif not is_valid:
            st.error(f"Min Down: ${min_down_req:,.0f}")

# --- VALIDATION CHECK ---
if not is_valid:
    st.error(f"### 🛑 Legal Minimum Not Met")
    st.info(f"👉 Minimum Required: **${min_down_req:,.0f}**")
    st.stop()
        
# --- 8. SCENARIO GRID ---
total_cols = st.session_state.num_options
main_cols = st.columns([3] * total_cols + [1]) 
results = []
while len(store['scenarios']) < total_cols:
    add_option()

for i in range(total_cols):
    s_data = store['scenarios'][i]
    with main_cols[i]:
        st.markdown(f"### Option {chr(65+i)}")
        name = st.text_input("Label", value=s_data['label'], key=f"n{i}")
        store['scenarios'][i]['label'] = name
        rate = st.number_input("Rate %", value=float(s_data['rate']), step=0.01, key=f"r{i}")
        store['scenarios'][i]['rate'] = rate
        freq = st.selectbox("Frequency", ["Monthly", "Semi-monthly", "Bi-weekly", "Weekly", "Accelerated Bi-weekly", "Accelerated Weekly"], 
                            index=["Monthly", "Semi-monthly", "Bi-weekly", "Weekly", "Accelerated Bi-weekly", "Accelerated Weekly"].index(s_data['freq']),
                            key=f"f{i}")
        store['scenarios'][i]['freq'] = freq
        strat = st.selectbox("Strategy", ["None", "Extra/Pmt", "Double Up", "Annual Lump"], 
                             index=["None", "Extra/Pmt", "Double Up", "Annual Lump"].index(s_data['strat']),
                             key=f"s{i}")
        store['scenarios'][i]['strat'] = strat
        ex, ls, db = 0, 0, False
        if strat == "Extra/Pmt": 
            ex = st.number_input("Extra $", value=float(s_data['extra']), key=f"ex{i}")
            store['scenarios'][i]['extra'] = ex
        elif strat == "Annual Lump": 
            ls = st.number_input("Lump $", value=float(s_data['lump']), key=f"ls{i}")
            store['scenarios'][i]['lump'] = ls
        elif strat == "Double Up": 
            db = True
            store['scenarios'][i]['double'] = True
        else:
            store['scenarios'][i]['extra'] = 0.0
            store['scenarios'][i]['lump'] = 0.0
            store['scenarios'][i]['double'] = False
        res = simulate_mortgage(final_loan, rate, amort, freq, ex, ls, db)
        res['Name'] = name
        # FIX: The 'res' dictionary already contains the History DataFrame 
        # and all calculated metrics from the simulate_mortgage function.
        results.append(res)

with main_cols[-1]:
    st.write("### ") 
    st.write("### ")
    if st.session_state.num_options < 5: st.button("➕", on_click=add_option, use_container_width=True)
    if st.session_state.num_options > 1: st.button("➖", on_click=remove_option, use_container_width=True)

st.divider()

# --- 9. DYNAMIC RECOMMENDATION ---
best_int_scenario = min(results, key=lambda x: x['Total_Life_Int'])
total_savings = results[0]['Total_Life_Int'] - best_int_scenario['Total_Life_Int']

st.markdown("### 🎯 Professional Recommendation")
if total_savings > 0:
    st.success(f"**Recommendation:** Strategy {best_int_scenario['Name']} is the highest-value option. It saves you **${total_savings:,.0f}** in total interest and eliminates your debt **{results[0]['Payoff_Time'] - best_int_scenario['Payoff_Time']:.1f} years** faster.")
else:
    st.info(f"**Recommendation:** No interest savings detected. Switching to **Accelerated** payments is the most impactful way to pay off the principal faster.")

st.divider()

# --- 10. STYLE HELPER ---
def apply_style(fig, title_text):
    fig.update_layout(
        template="plotly_white",
        title=dict(text=title_text, font=dict(size=24, color="#2E2B28")),
        xaxis=dict(title_font=dict(size=20, color="#2E2B28"), tickfont=dict(size=16)),
        yaxis=dict(title_font=dict(size=20, color="#2E2B28"), tickfont=dict(size=16), tickformat="$,.0f"),
        legend=dict(font=dict(size=16))
    )
    return fig

# --- 11. ANALYSIS TABS ---
tabs = st.tabs(["📉 Balance Projection", "💰 Monthly Cash-Out", "📊 5-Year Progress", "📑 Summary Table"])

with tabs[0]:
    fig1 = go.Figure()
    for i, r in enumerate(results): 
        fig1.add_trace(go.Scatter(x=r['History']['Year'], y=r['History']['Balance'], name=r['Name'], line=dict(color=SCENARIO_COLORS[i % len(SCENARIO_COLORS)], width=4)))
    st.plotly_chart(apply_style(fig1, "Projected Mortgage Balance"), use_container_width=True)

with tabs[1]:
    avg_df = pd.DataFrame([{"Scenario": r['Name'], "Monthly Out": r['Monthly_Avg']} for r in results])
    fig2 = px.bar(avg_df, x="Scenario", y="Monthly Out", color="Scenario", text_auto='$,.0f', color_discrete_sequence=SCENARIO_COLORS)
    fig2.update_traces(textfont_size=18, marker_line_width=0)
    st.plotly_chart(apply_style(fig2, "Total Monthly Budget Requirement"), use_container_width=True)

with tabs[2]:
    stack_list = []
    for r in results:
        # Use Term_Prin and Term_Int which are calculated inside simulate_mortgage
        stack_list.append({"Scenario": r['Name'], "Amount": r['Term_Prin'], "Type": "Equity Built"})
        stack_list.append({"Scenario": r['Name'], "Amount": r['Term_Int'], "Type": "Interest Paid"})
    
    fig3 = px.bar(pd.DataFrame(stack_list), x="Scenario", y="Amount", color="Type", barmode="stack", 
                  color_discrete_map={"Equity Built": PRINCIPAL_COLOR, "Interest Paid": INTEREST_COLOR}, text_auto='$,.0f')
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
st.caption("Analyst in a Pocket | Strategic Debt Management & Equity Planning")










