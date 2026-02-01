import streamlit as st
import pandas as pd
import os
import json
import math

# --- 1. THEME & STYLING ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

# --- ROUNDING UTILITY ---
def custom_round_up(n):
    if n <= 0: return 0.0
    digits = int(math.log10(n)) + 1
    if digits <= 3: step = 10
    elif digits <= 5: step = 100
    elif digits == 6: step = 1000
    elif digits == 7: step = 10000
    else: step = 50000 
    return float(math.ceil(n / step) * step)

# --- 2. DATA CROSS-REFERENCING ---
prof = st.session_state.get('user_profile', {})
current_res_prov = prof.get('province', 'BC')
p1_name = prof.get('p1_name', 'Client 1')
p2_name = prof.get('p2_name', 'Client 2')

def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"rates": {"five_year_fixed_uninsured": 4.26}, "provincial_yields": {"BC": 3.8}}

intel = load_market_intel()

# --- 3. TITLE ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("The Portfolio Expansion Map")

# --- 4. TOP LEVEL SELECTORS ---
ts_col1, ts_col2 = st.columns(2)
with ts_col1:
    prov_options = ["BC", "Alberta", "Ontario", "Manitoba", "Quebec", "Saskatchewan", "Nova Scotia", "New Brunswick"]
    def_idx = prov_options.index(current_res_prov) if current_res_prov in prov_options else 0
    asset_province = st.selectbox("Asset Location (Province):", options=prov_options, index=def_idx)
with ts_col2:
    use_case = st.selectbox("Primary Use Case:", ["Rental Property", "Family Vacation Home"])
    is_rental = True if use_case == "Rental Property" else False

scraped_yield = intel.get("provincial_yields", {}).get(asset_province, 3.8)
tax_rate_lookup = {"BC": 0.0031, "Ontario": 0.0076, "Alberta": 0.0064}
default_tax_rate = tax_rate_lookup.get(asset_province, 0.0075)

# --- 5. PERSISTENCE & INITIALIZATION ---
if "aff_second_store" not in st.session_state:
    init_price = 600000.0
    st.session_state.aff_second_store = {
        "down_payment": 200000.0,
        "target_price": init_price,
        "manual_rent": (init_price * (scraped_yield/100)) / 12,
        "contract_rate": float(intel.get('rates', {}).get('five_year_fixed_uninsured', 4.26)),
        "strata_mo": 400.0,
        "insurance_mo": 100.0,
        "vacancy_months": 1.0,
        "rm_mo": 150.0,
        "mgmt_pct": 5.0,
        "annual_prop_tax": init_price * default_tax_rate
    }
store = st.session_state.aff_second_store

def get_float(k, d=0.0):
    try: return float(prof.get(k, d))
    except: return d

p1_annual = get_float('p1_t4') + get_float('p1_bonus') + get_float('p1_commission')
p2_annual = get_float('p2_t4') + get_float('p2_bonus') + get_float('p2_commission')
m_inc = (p1_annual + p2_annual + (get_float('inv_rental_income', 0) * 0.80)) / 12

m_bal = get_float('m_bal')
m_rate_p = (get_float('m_rate', 4.0) / 100) / 12
primary_mtg = (m_bal * m_rate_p) / (1
