import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from style_utils import inject_global_css

# 1. Inject the Wealthsimple-inspired Editorial CSS
inject_global_css()

# FIX: Removed 'kind="secondary"' which caused the crash.
# The default style is secondary, so we don't need to specify it.
if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 1. THEME & BRANDING ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"

# --- 2. DATA RETRIEVAL (GLOBAL PROFILE) ---
prof = st.session_state.get('user_profile', {})
name1 = prof.get('p1_name') or "Primary Client"
name2 = prof.get('p2_name') or ""
household = f"{name1} and {name2}" if name2 else name1

# --- 3. PERSISTENCE INITIALIZATION ---
if "aff_rent_store" not in st.session_state:
    st.session_state.aff_rent_store = {
        "price": 800000, "dp": 200000, "rate": 4.0, "ann_tax": 2000,
        "mo_maint": 500, "apprec": 3.0, "rent": 3000, "rent_inc": 2.0,
        "inv_return": 6.0, "years": 25
    }

def sync_rent():
    pass 

st.markdown(f"<h1>⚖️ Buy vs. Rent Analysis</h1>", unsafe_allow_html=True)
st.caption(f"Comparing wealth trajectories for **{household}**.")

# --- 4. INPUTS SECTION ---
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("### 🏠 Purchase Scenario")
        st.session_state.aff_rent_store['price'] = st.number_input("Purchase Price ($)", value=st.session_state.aff_rent_store['price'], step=10000)
        st.session_state.aff_rent_store['dp'] = st.number_input("Down Payment ($)", value=st.session_state.aff_rent_store['dp'], step=5000)
        st.session_state.aff_rent_store['rate'] = st.number_input("Mortgage Rate (%)", value=st.session_state.aff_rent_store['rate'], step=0.1)
        st.session_state.aff_rent_store['years'] = st.slider("Time Horizon (Years)", 5, 30, st.session_state.aff_rent_store['years'])

    with c2:
        st.markdown("### 💸 Ownership Costs")
        st.session_state.aff_rent_store['ann_tax'] = st.number_input("Annual Property Tax ($)", value=st.session_state.aff_rent_store['ann_tax'], step=100)
        st.session_state.aff_rent_store['mo_maint'] = st.number_input("Monthly Maintenance ($)", value=st.session_state.aff_rent_store['mo_maint'], step=50)
        st.session_state.aff_rent_store['apprec'] = st.number_input("Home Appreciation (%)", value=st.session_state.aff_rent_store['apprec'], step=0.1)

    with c3:
        st.markdown("### 🔑 Rental Alternative")
        st.session_state.aff_rent_store['rent'] = st.number_input("Monthly Rent ($)", value=st.session_state.aff_rent_store['rent'], step=50)
        st.session_state.aff_rent_store['rent_inc'] = st.number_input("Rent Increase (%)", value=st.session_state.aff_rent_store['rent_inc'], step=0.1)
        st.session_state.aff_rent_store['inv_return'] = st.number_input("Inv. Return Rate (%)", value=st.session_state.aff_rent_store['inv_return'], help="Return on the difference invested", step=0.1)

# --- 5. CALCULATION ENGINE ---
P = st.session_state.aff_rent_store['price']
DP = st.session_state.aff_rent_store['dp']
r_mort = st.session_state.aff_rent_store['rate'] / 100 / 12
n_months = 300 
Loan = P - DP
Monthly_PI = Loan * (r_mort * (1 + r_mort)**n_months) / ((1 + r_mort)**n_months - 1)
