import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
from style_utils import inject_global_css, show_disclaimer 

# --- SAFE IMPORT: Handle Missing Secrets Gracefully ---
# This prevents the "Connection Failed" error if secrets.toml is missing
try:
    from data_handler import supabase
except Exception:
    supabase = None

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

# --- 2. PERSISTENCE & INITIALIZATION ---
if 'mortgage_scenario' not in st.session_state.app_db:
    st.session_state.app_db['mortgage_scenario'] = {}
ms_data = st.session_state.app_db['mortgage_scenario']

# Retrieve Affordability Data (Robust Sync)
aff_store = st.session_state.app_db.get('affordability', {}) 

# Calculate Price from Affordability (since max_purchase might be missing)
aff_down = float(aff_store.get('down_payment', 0.0))
loan_cap = float(aff_store.get('loan_cap', 0.0))
aff_price = float(aff_store.get('max_purchase', 0.0))

# Fallback: Price = Loan Cap + Down Payment
if aff_price == 0 and loan_cap > 0:
    aff_price = loan_cap + aff_down

aff_amort = int(aff_store.get('amortization', 25))

# Retrieve Default Rate
def get_default_rate():
    if 'affordability' in st.session_state.app_db:
        aff = st.session_state.app_db['affordability']
        if aff.get('contract_rate'): return float(aff['contract_rate'])
        if aff.get('bank_rate'): return float(aff['bank_rate'])
    
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

# --- HELPER: CLOUD SAVE (CRASH PROOF) ---
def trigger_cloud_save():
    # 1. Force update the master app_db object
    st.session_state.app_db['mortgage_scenario'] = ms_data
    
    # 2. Check if we are logged in AND if Supabase is connected
    user = st.session_state.get('user')
    
    if user and supabase:
        try:
            # Handle both object-style and dict-style user objects
            user_id = user.id if hasattr(user, 'id') else user.get('id')
            
            supabase.table('user_data').update({
                'data': st.session_state.app_db
            }).eq('user_id', user_id).execute()
            
            # SUCCESS VISUAL
            st.toast("Saved successfully", icon="✅")
            
        except Exception as e:
            st.error(f"⚠️ Cloud Error: {e}")
    elif not supabase:
        # Don't crash, just warn gently
        st.toast("Offline Mode: Secrets missing", icon="⚠️")

# --- AUTO-HEAL INITIALIZATION ---
# Check if current data is "Stale" (Generic Defaults 800k/160k)
curr_price = float(ms_data.get('price', 800000.0))
curr_down = float(ms_data.get('down', 160000.0))

is_stale = (curr_price == 800000.0 and curr_down == 160000.0)
has_new_data = (aff_price > 0 and aff_price != 800000.0)

if not ms_data.get('initialized') or (is_stale and has_new_data):
    # Use Affordability data if available, otherwise defaults
    init_price = aff_price if aff_price > 0 else 800000.0
    init_down = aff_down if aff_down > 0 else 160000.0
    init_amort = aff_amort if aff_price > 0 else 25
    
    ms_data.update({
        "price": init_price,
        "down": init_down,
        "amort": init_amort,
        "scenarios": [
            {"label": "Standard Monthly", "rate": global_rate_default, "freq": "Monthly", "strat": "None", "extra": 0.0, "lump": 0.0, "double": False},
            {"label": "Accelerated Bi-Weekly", "rate": global_rate_default, "freq": "Accelerated Bi-weekly", "strat": "None", "extra": 0.0, "lump": 0.0, "double": False}
        ],
        "initialized": True
    })
    
    # Save immediately upon initialization
    trigger_cloud_save()

store = ms_data

# Double check scenarios list exists
if "scenarios" not in store:
    store["scenarios"] = [
        {"label": "Standard Monthly", "rate": global_rate_default, "freq": "Monthly", "strat": "None", "extra": 0.0, "lump": 0.0, "double": False}
    ]

# --- 4. CALLBACK: UPDATE STORE ---
def update_ms_store():
    # Capture Inputs
    if "ms_price" in st.session_state: store['price'] = st.session_state.ms_price
    if "ms_down" in st.session_state: store['down'] = st.session_state.ms_down
    if "w_amort" in st.session_state: store['amort'] = st.session_state.w_amort

    # Capture Scenarios
    for i in range(len(store['scenarios'])):
        s = store['scenarios'][i]
        s['label'] = st.session_state.get(f"n{i}", s['label'])
        s['rate'] = st.session_state.get(f"r{i}", s['rate'])
        s['freq'] = st.session_state.get(f"f{i}", s['freq'])
        s['strat'] = st.session_state.get(f"s{i}", s['strat'])
        s['extra'] = st.session_state.get(f"ex{i}", s['extra'])
        s['lump'] = st.session_state.get(f"ls{i}", s['lump'])
    
    # TRIGGER SAVE
    trigger_cloud_save()

if 'num_options' not in st.session_state:
    st.session_state.num_options = len(store['scenarios'])

# --- 5. STATE MANAGEMENT HELPERS ---
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
        trigger_cloud_save()

def remove_option():
    if st.session_state.num_options > 1:
        st.session_state.num_options -= 1
        store['scenarios'].pop()
        trigger_cloud_save()

# --- COLOR PALETTE ---
SCENARIO_COLORS = ["#CEB36F", "#706262", "#2E2B28", "#C0A385", "#E7E7E7"]
PRINCIPAL_COLOR = "#CEB36F"
INTEREST_COLOR = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"
PRIMARY_GOLD = "#CEB36F"

# --- 6. CORE ENGINE ---
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

# --- 7. INTERFACE ---
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

# --- 8. GLOBAL SETTINGS ---
with st.container(border=True):
    st.markdown("### 🏠 Property & Mortgage Details")
    
    col_i1, col_i2, col_i3 = st.columns(3)
    
    with col_i1:
        price = st.number_input(
            "Purchase Price ($)", 
            value=float(store.get('price', 800000.0)),
            step=5000.0, 
            key="ms_price", 
            on_change=update_ms_store
        )
    
    with col_i2:
        down = st.number_input(
            "Down Payment ($)", 
            value=float(store.get('down', 160000.0)),
            step=5000.0, 
            key="ms_down", 
            on_change=update_ms_store
        )
        
    with col_i3:
        amort = st.slider(
            "Amortization (Years)", 
            5, 30, 
            value=int(store.get('amort', 25)),
            key="w_amort", 
            on_change=update_ms_store
        )

    # --- CALCULATIONS ---
    min_down_req = calculate_min_downpayment(price)
    is_valid = down >= min_down_req
    base_loan = price - down
    ltv = (base_loan / price) * 100 if price > 0 else 0
    cmhc_p = get_cmhc_premium_rate(ltv) * base_loan
    final_loan = base_loan + cmhc_p
    
    st.markdown("<div style='margin: 10px 0; border-top: 1px solid #f0f0f0;'></div>", unsafe_allow_html=True)
    
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

# --- VALIDATION ---
if not is_valid:
    st.error(f"### 🛑 Legal Minimum Not Met")
    st.info(f"👉 Minimum Required: **${min_down_req:,.0f}**")
    st.stop()
        
# --- 9. SCENARIO GRID ---
total_cols = st.session_state.num_options
main_cols = st.columns([3] * total_cols + [1]) 
results = []

while len(store['scenarios']) < total_cols:
    add_option()
while len(store['scenarios']) > total_cols:
    store['scenarios'].pop()

for i in range(total_cols):
    s_data = store['scenarios'][i]
    with main_cols[i]:
        st.markdown(f"### Option {chr(65+i)}")
        
        name = st.text_input("Label", value=s_data['label'], key=f"n{i}", on_change=update_ms_store)
        rate = st.number_input("Rate %", value=float(s_data['rate']), step=0.01, key=f"r{i}", on_change=update_ms_store)
        
        freq = st.selectbox("Frequency", ["Monthly", "Semi-monthly", "Bi-weekly", "Weekly", "Accelerated Bi-weekly", "Accelerated Weekly"], 
                            index=["Monthly", "Semi-monthly", "Bi-weekly", "Weekly", "Accelerated Bi-weekly", "Accelerated Weekly"].index(s_data['freq']),
                            key=f"f{i}", on_change=update_ms_store)
        
        strat = st.selectbox("Strategy", ["None", "Extra/Pmt", "Double Up", "Annual Lump"], 
                             index=["None", "Extra/Pmt", "Double Up", "Annual Lump"].index(s_data['strat']),
                             key=f"s{i}", on_change=update_ms_store)
        
        ex, ls, db = 0, 0, False
        if strat == "Extra/Pmt": 
            ex = st.number_input("Extra $", value=float(s_data['extra']), key=f"ex{i}", on_change=update_ms_store)
        elif strat == "Annual Lump": 
            ls = st.number_input("Lump $", value=float(s_data['lump']), key=f"ls{i}", on_change=update_ms_store)
        elif strat == "Double Up": 
            db = True
        
        res = simulate_mortgage(final_loan, rate, amort, freq, ex, ls, db)
        res['Name'] = name
        results.append(res)

with main_cols[-1]:
    st.write("### ") 
    st.write("### ")
    if st.session_state.num_options < 5: st.button("➕", on_click=add_option, use_container_width=True)
    if st.session_state.num_options > 1: st.button("➖", on_click=remove_option, use_container_
