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
prof = st.session_state.get('user_profile', {})
client_name1 = prof.get('p1_name', 'Dori') 
client_name2 = prof.get('p2_name', 'Kevin') 
household_names = f"{client_name1} & {client_name2}" if client_name2 else client_name1

# Initialize Store (Session State)
if 'aff_store' not in st.session_state:
    st.session_state.aff_store = {}
store = st.session_state.aff_store

# Set defaults if missing
if 'price' not in store: store['price'] = 800000.0
if 'down' not in store: store['down'] = 160000.0
if 'amort' not in store: store['amort'] = 25

# --- HELPER FUNCTIONS ---
def calculate_min_downpayment(purchase_price):
    if purchase_price <= 500000:
        return purchase_price * 0.05
    elif purchase_price < 1000000:
        return (500000 * 0.05) + ((purchase_price - 500000) * 0.10)
    else:
        return purchase_price * 0.20

def get_cmhc_premium_rate(ltv_pct):
    if ltv_pct <= 80: return 0.0
    if ltv_pct <= 85: return 0.0280
    if ltv_pct <= 90: return 0.0310
    if ltv_pct <= 95: return 0.0400
    return 0.0400 # Fallback

def get_default_rate():
    # 1. Try Session State
    if 'aff_store' in st.session_state:
        # Check if contract_rate exists
        return st.session_state.aff_store.get('contract_rate', 4.49)
    
    # 2. Try File (Safely)
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                d = json.load(f)
                return d.get('rates', {}).get('five_year_fixed_uninsured', 4.49)
        except Exception:
            return 4.49
            
    # 3. Default Fallback
    return 4.49

# --- 2. THEME & BRANDING ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"

# --- 3. PAGE HEADER ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=140)
with header_col2:
    st.title("Mortgage Scenario Modeler")

# --- 4. STORYTELLING ---
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px; border-radius: 10px; border-left: 5px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <p style="font-size: 1.1em; color: {CHARCOAL}; margin: 0;">
        <b>{household_names}</b> are evaluating different mortgage structures for their potential home purchase. 
        They want to compare how <b>accelerated payments</b>, <b>shorter amortizations</b>, or <b>lump sum prepayments</b> 
        could save them interest and build equity faster over the first 5-year term.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. MAIN PAGE INPUTS (Replaces Sidebar) ---
with st.container(border=True):
    st.markdown("### 🏠 Property & Mortgage Details")
    
    # Row 1: The Inputs
    col_i1, col_i2, col_i3 = st.columns(3)
    
    with col_i1:
        # We wrap store['price'] in float() to prevent type errors if it was stored as an int
        price = st.number_input("Property Price ($)", value=float(store['price']), step=5000.0, key="w_price")
        store['price'] = price 
    
    with col_i2:
        down = st.number_input("Down Payment ($)", value=float(store['down']), step=5000.0, key="w_down")
        store['down'] = down 
        
    with col_i3:
        # Ensure 'amort' is a valid option in the list
        current_amort = store.get('amort', 25)
        valid_options = [15, 20, 25, 30]
        if current_amort not in valid_options: current_amort = 25
        
        amort = st.selectbox("Amortization (Years)", options=valid_options, index=valid_options.index(current_amort), key="w_amort")
        store['amort'] = amort

    # --- LOGIC RESTORATION ---
    min_down_req = calculate_min_downpayment(price)
    is_valid_down = down >= min_down_req
    
    base_loan = price - down
    
    # Calculate LTV
    ltv = (base_loan / price) * 100 if price > 0 else 0
    
    # Calculate CMHC Premium
    cmhc_p = 0.0
    if ltv > 80:
        cmhc_p = get_cmhc_premium_rate(ltv) * base_loan
        
    final_loan = base_loan + cmhc_p
    
    st.divider()
    
    # Row 2: The Calculated Metrics
    col_m1, col_m2, col_m3 = st.columns(3)
    
    with col_m1:
        st.metric(label="Total Mortgage", value=f"${final_loan:,.0f}", help="Includes CMHC Premium if applicable")
    
    with col_m2:
        st.metric(label="LTV Ratio", value=f"{ltv:.1f}%", delta="High Ratio (Insured)" if ltv > 80 else "Conventional", delta_color="inverse")
        
    with col_m3:
        if cmhc_p > 0:
            st.metric(label="CMHC Premium Added", value=f"${cmhc_p:,.0f}")
        elif not is_valid_down:
            st.error(f"Min Down: ${min_down_req:,.0f}")
        else:
            st.metric(label="Insurance Premium", value="$0")

# --- 6. SCENARIO CONFIGURATION ---
st.subheader("⚙️ Compare Payment Strategies")

# Define tabs for different strategies
tabs = st.tabs(["1. Standard", "2. Accelerated Weekly", "3. Lump Sum Prepayment", "📊 Comparison Table"])

results = []

def calculate_mortgage(principal, rate, years, freq="Monthly", prepayment=0):
    r = (rate / 100)
    
    if freq == "Monthly":
        n_per_year = 12
    elif freq == "Bi-Weekly":
        n_per_year = 26
    elif freq == "Weekly":
        n_per_year = 52
    elif freq == "Accelerated Bi-Weekly":
        n_per_year = 26
    elif freq == "Accelerated Weekly":
        n_per_year = 52
        
    # Standard Monthly Payment Calculation (base)
    r_mo = r / 12
    n_mo = years * 12
    monthly_pmt = principal * (r_mo * (1 + r_mo)**n_mo) / ((1 + r_mo)**n_mo - 1)
    
    # Adjust payment based on frequency
    if freq == "Monthly":
        pmt = monthly_pmt
    elif freq == "Bi-Weekly":
        pmt = monthly_pmt * 12 / 26
    elif freq == "Weekly":
        pmt = monthly_pmt * 12 / 52
    elif freq == "Accelerated Bi-Weekly":
        pmt = monthly_pmt / 2
    elif freq == "Accelerated Weekly":
        pmt = monthly_pmt / 4
        
    # Generate Amortization Schedule (5 Year Term Focus)
    balance = principal
    total_int = 0
    total_prin = 0
    
    term_months = 60 # 5 years
    
    # Convert frequency to iteration steps
    if "Weekly" in freq:
        steps = 52 * 5
        rate_per_step = r / 52
    elif "Bi-Weekly" in freq:
        steps = 26 * 5
        rate_per_step = r / 26
    else:
        steps = 60
        rate_per_step = r / 12
        
    for i in range(1, steps + 1):
        if balance <= 0:
            break
            
        interest = balance * rate_per_step
        principal_pay = pmt - interest
        
        # Apply prepayment
        is_anniversary = False
        if "Monthly" in freq and i % 12 == 0: is_anniversary = True
        elif "Bi-Weekly" in freq and i % 26 == 0: is_anniversary = True
        elif "Weekly" in freq and i % 52 == 0: is_anniversary = True
        
        if is_anniversary:
            balance -= prepayment
            
        balance -= principal_pay
        total_int += interest
        total_prin += principal_pay
        
        if balance < 0: balance = 0
        
    return {
        "Monthly_Avg": monthly_pmt,
        "Term_Int": total_int,
        "Term_Prin": principal - balance,
        "Balance_At_Term": balance,
        "Total_Life_Int": total_int, 
        "Payoff_Time": years, 
        "Prepay_Active": "Yes" if prepayment > 0 else "No",
        "Freq": freq,
        "Rate": rate,
        "Name": "Scenario"
    }

default_rate = get_default_rate()

with tabs[0]:
    st.markdown("**The Baseline:** Standard Monthly Payments with no extra contributions.")
    rate_1 = st.number_input("Interest Rate (%)", value=default_rate, step=0.05, key="r1")
    res1 = calculate_mortgage(final_loan, rate_1, amort, freq="Monthly")
    res1['Name'] = "Standard Monthly"
    results.append(res1)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Monthly Payment", f"${res1['Monthly_Avg']:,.2f}")
    c2.metric("Interest Paid (5yr)", f"${res1['Term_Int']:,.0f}")
    c3.metric("Balance at Year 5", f"${res1['Balance_At_Term']:,.0f}")

with tabs[1]:
    st.markdown("**The Accelerator:** Paying weekly triggers more frequent principal pay-down.")
    rate_2 = st.number_input("Interest Rate (%)", value=default_rate, step=0.05, key="r2")
    res2 = calculate_mortgage(final_loan, rate_2, amort, freq="Accelerated Weekly")
    res2['Name'] = "Accelerated Weekly"
    results.append(res2)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Weekly Payment", f"${res2['Monthly_Avg']/4:,.2f}") # Approx
    c2.metric("Interest Paid (5yr)", f"${res2['Term_Int']:,.0f}", delta=f"${res1['Term_Int'] - res2['Term_Int']:,.0f} saved", delta_color="normal")
    c3.metric("Equity Gained (5yr)", f"${res2['Term_Prin']:,.0f}")

with tabs[2]:
    st.markdown("**The Lump Sum:** Putting an annual bonus directly onto the mortgage principal.")
    rate_3 = st.number_input("Interest Rate (%)", value=default_rate, step=0.05, key="r3")
    lump_sum = st.number_input("Annual Prepayment Amount ($)", value=5000, step=1000)
    res3 = calculate_mortgage(final_loan, rate_3, amort, freq="Monthly", prepayment=lump_sum)
    res3['Name'] = f"Monthly + ${lump_sum/1000}k Annual"
    results.append(res3)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Monthly Payment", f"${res3['Monthly_Avg']:,.2f}")
    c2.metric("Interest Paid (5yr)", f"${res3['Term_Int']:,.0f}", delta=f"${res1['Term_Int'] - res3['Term_Int']:,.0f} saved", delta_color="normal")
    c3.metric("Equity Gained (5yr)", f"${res3['Term_Prin']:,.0f}")

# --- 7. VISUAL COMPARISON ---
with tabs[3]:
    table_df = pd.DataFrame([{
        "Scenario": r['Name'],
        "Rate": f"{r['Rate']:.2f}%",
        "Frequency": r['Freq'],
        "Extra Pay Activity": r['Prepay_Active'], 
        "Monthly Out": f"${r['Monthly_Avg']:,.0f}",
        "Equity (5yr)": f"${r['Term_Prin']:,.0f}",
        "Total Interest": f"${r['Total_Life_Int']:,.0f}",
        "Savings vs A": f"${(results[0]['Total_Life_Int'] - r['Total_Life_Int']):,.0f}",
        "Payoff Time": f"{r['Payoff_Time']} yr"
    } for r in results])
    st.table(table_df)

    comp_data = []
    for r in results:
        comp_data.append({"Scenario": r['Name'], "Type": "Interest Paid", "Amount": r['Term_Int']})
        comp_data.append({"Scenario": r['Name'], "Type": "Equity Built", "Amount": r['Term_Prin']})
        
    df_comp = pd.DataFrame(comp_data)
    
    fig3 = px.bar(df_comp, x="Scenario", y="Amount", color="Type", barmode="group",
                  color_discrete_map={"Interest Paid": CHARCOAL, "Equity Built": PRIMARY_GOLD})
    
    def apply_style(fig, title):
        fig.update_layout(
            title=title,
            plot_bgcolor="white",
            font=dict(family="Inter", size=14, color="#1a1a1a"),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
            legend=dict(orientation="h", y=1.1, x=0)
        )
        return fig

    fig3.update_traces(texttemplate='%{y:$,.0f}', textposition='outside')
    fig3.update_yaxes(tickprefix="$")
    st.plotly_chart(apply_style(fig3, "5-Year Impact: Interest vs. Equity"), use_container_width=True)

# --- 12. LEGAL DISCLAIMER ---
st.markdown("---")
st.markdown("""
<div style='background-color: #f8f9fa; padding: 16px 20px; border-radius: 5px; border: 1px solid #dee2e6;'>
    <p style='font-size: 12px; color: #6c757d; line-height: 1.6; margin-bottom: 0;'>
        <strong>⚠️ Errors and Omissions Disclaimer:</strong><br>
        This tool is for <strong>informational and educational purposes only</strong>. Figures are based on mathematical estimates and historical data. 
        This does not constitute financial, legal, or tax advice. Mortgage approval and final figures are subject to lender policy, 
        creditworthiness, and current market conditions. Consult with a professional before making significant financial decisions.
    </p>
</div>
""", unsafe_allow_html=True)
